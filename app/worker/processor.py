from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config.settings import AppSettings
from app.domain.enums import AssetKind, EventLevel, JobItemStatus, JobStatus, Site
from app.domain.errors import CrawlError, DetailPageNotFoundError, ImageDownloadFailedError, LoginFailedError, StorageFailedError
from app.domain.schemas import StoredAsset
from app.domain.services.credentials import CredentialCipher
from app.infrastructure.crawlers.yes24.adapter import Yes24CrawlerAdapter
from app.infrastructure.db.models import Book, CrawlEvent, CrawlJob, CrawlJobItem, ImageAsset, SiteCredential
from app.infrastructure.images.pipeline import ImagePipeline
from app.infrastructure.storage.filesystem import FilesystemStorage


class CrawlProcessor:
    def __init__(self, settings: AppSettings, storage: FilesystemStorage, image_pipeline: ImagePipeline) -> None:
        self.settings = settings
        self.storage = storage
        self.image_pipeline = image_pipeline
        self.cipher = CredentialCipher(settings)

    def process_job(self, session: Session, job: CrawlJob) -> None:
        credential = session.get(SiteCredential, Site.YES24.value)
        username = credential.username if credential else ""
        password = self.cipher.decrypt(credential.password_encrypted) if credential else ""

        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        self._event(session, job, None, EventLevel.INFO, "Job started.", {"job_id": job.id})
        session.commit()

        try:
            with Yes24CrawlerAdapter(self.settings, self.storage, username, password) as adapter:
                if username and password:
                    try:
                        adapter.login()
                        self._event(
                            session,
                            job,
                            None,
                            EventLevel.INFO,
                            "Stored Yes24 credentials were applied.",
                            {"authenticated": True},
                        )
                    except LoginFailedError as exc:
                        self._event(
                            session,
                            job,
                            None,
                            EventLevel.WARNING,
                            f"Stored Yes24 credentials could not be applied: {exc.message}",
                            {"authenticated": False, "code": exc.code},
                        )
                    session.commit()

                items = (
                    session.execute(
                        select(CrawlJobItem)
                        .where(CrawlJobItem.job_id == job.id)
                        .where(CrawlJobItem.status == JobItemStatus.PENDING.value)
                        .order_by(CrawlJobItem.id.asc())
                    )
                    .scalars()
                    .all()
                )
                for item in items:
                    self._process_item(session, job, item, adapter)
        except CrawlError as exc:
            pending_items = (
                session.execute(
                    select(CrawlJobItem)
                    .where(CrawlJobItem.job_id == job.id)
                    .where(CrawlJobItem.status.in_([JobItemStatus.PENDING.value, JobItemStatus.RUNNING.value]))
                )
                .scalars()
                .all()
            )
            for item in pending_items:
                item.status = JobItemStatus.FAILED.value
                item.error_code = exc.code
                item.error_message = exc.message
            self._event(session, job, None, EventLevel.ERROR, exc.message, {"code": exc.code})
            session.commit()
        except Exception as exc:
            wrapped = StorageFailedError(f"Unexpected job failure: {exc}")
            pending_items = (
                session.execute(
                    select(CrawlJobItem)
                    .where(CrawlJobItem.job_id == job.id)
                    .where(CrawlJobItem.status.in_([JobItemStatus.PENDING.value, JobItemStatus.RUNNING.value]))
                )
                .scalars()
                .all()
            )
            for item in pending_items:
                item.status = JobItemStatus.FAILED.value
                item.error_code = wrapped.code
                item.error_message = wrapped.message
            self._event(session, job, None, EventLevel.ERROR, wrapped.message, {"code": wrapped.code})
            session.commit()

        self._finalize_job(session, job)

    def _process_item(self, session: Session, job: CrawlJob, item: CrawlJobItem, adapter: Yes24CrawlerAdapter) -> None:
        item.status = JobItemStatus.RUNNING.value
        item.attempt_count += 1
        item.error_code = ""
        item.error_message = ""
        self._event(session, job, item, EventLevel.INFO, "Item started.", {"isbn": item.isbn})
        session.commit()

        try:
            result = adapter.fetch_book(item.isbn)
            if not result.cover_image_url:
                raise DetailPageNotFoundError(f"Cover image is missing for ISBN {item.isbn}.")
            if not result.detail_image_url:
                raise DetailPageNotFoundError(f"Detail image is missing for ISBN {item.isbn}.")

            cover_bytes = self._download_image(result.cover_image_url)
            detail_bytes = self._download_image(result.detail_image_url)
            assets = self.image_pipeline.generate_assets(item.isbn, cover_bytes, detail_bytes)
            self._upsert_book(session, result.book)
            self._replace_assets(session, item.isbn, assets)

            item.status = JobItemStatus.SUCCESS.value
            self._event(
                session,
                job,
                item,
                EventLevel.INFO,
                "Item completed.",
                {
                    "isbn": item.isbn,
                    "snapshot_path": str(result.source_snapshot_path) if result.source_snapshot_path else "",
                },
            )
            session.commit()
        except CrawlError as exc:
            item.status = JobItemStatus.FAILED.value
            item.error_code = exc.code
            item.error_message = exc.message
            self._event(session, job, item, EventLevel.ERROR, exc.message, {"code": exc.code, "isbn": item.isbn})
            session.commit()
        except Exception as exc:
            wrapped = StorageFailedError(f"Unexpected item failure: {exc}")
            item.status = JobItemStatus.FAILED.value
            item.error_code = wrapped.code
            item.error_message = wrapped.message
            self._event(session, job, item, EventLevel.ERROR, wrapped.message, {"code": wrapped.code, "isbn": item.isbn})
            session.commit()

    def _download_image(self, url: str) -> bytes:
        try:
            response = httpx.get(url, headers={"User-Agent": self.settings.user_agent}, timeout=20)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            raise ImageDownloadFailedError(f"Failed to download image {url}: {exc}") from exc

    def _upsert_book(self, session: Session, payload) -> None:
        existing = session.get(Book, payload.isbn)
        if existing is None:
            existing = Book(isbn=payload.isbn)
            session.add(existing)

        existing.site = payload.site.value
        existing.title = payload.title
        existing.author = payload.author
        existing.publisher = payload.publisher
        existing.description = payload.description
        existing.category = payload.category
        existing.price_original = payload.price_original
        existing.price_sale = payload.price_sale
        existing.published_date = payload.published_date
        existing.page_count = payload.page_count
        existing.book_size = payload.book_size
        existing.product_url = payload.product_url
        existing.last_crawled_at = datetime.utcnow()

    def _replace_assets(self, session: Session, isbn: str, assets: list[StoredAsset]) -> None:
        session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
        for asset in assets:
            session.add(
                ImageAsset(
                    isbn=isbn,
                    variant=asset.kind.value,
                    file_path=asset.file_path,
                    width=asset.width,
                    height=asset.height,
                )
            )

    def _finalize_job(self, session: Session, job: CrawlJob) -> None:
        counts = {
            status: count
            for status, count in session.execute(
                select(CrawlJobItem.status, func.count(CrawlJobItem.id))
                .where(CrawlJobItem.job_id == job.id)
                .group_by(CrawlJobItem.status)
            )
        }
        success_count = counts.get(JobItemStatus.SUCCESS.value, 0)
        failed_count = counts.get(JobItemStatus.FAILED.value, 0)
        if failed_count and success_count:
            job.status = JobStatus.PARTIAL_SUCCESS.value
        elif failed_count and not success_count:
            job.status = JobStatus.FAILED.value
        elif success_count:
            job.status = JobStatus.SUCCESS.value
        else:
            job.status = JobStatus.CANCELLED.value
        job.finished_at = datetime.utcnow()
        self._event(
            session,
            job,
            None,
            EventLevel.INFO,
            "Job finished.",
            {"status": job.status, "success_count": success_count, "failed_count": failed_count},
        )
        session.commit()

    def _event(
        self,
        session: Session,
        job: CrawlJob,
        item: CrawlJobItem | None,
        level: EventLevel,
        message: str,
        payload: dict,
    ) -> None:
        session.add(
            CrawlEvent(
                job_id=job.id,
                job_item_id=item.id if item else None,
                level=level.value,
                message=message,
                payload_json=payload,
            )
        )
