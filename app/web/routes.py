from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote_plus
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.config.settings import get_settings
from app.domain.enums import EventLevel, JobItemStatus, JobStatus, Site
from app.domain.schemas import HealthcheckResult
from app.domain.services.credentials import CredentialCipher
from app.infrastructure.crawlers.yes24.adapter import Yes24CrawlerAdapter
from app.infrastructure.db.models import Book, CrawlEvent, CrawlJob, CrawlJobItem, ImageAsset, SiteCredential
from app.infrastructure.db.session import SessionLocal


router = APIRouter()
settings = get_settings()
templates = Jinja2Templates(directory=settings.template_dir.as_posix())


def _format_dt(value):
    if not value:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


templates.env.filters["datetime"] = _format_dt

_ARCHIVE_SEGMENT_MAX_LENGTH = 120
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def _session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _parse_isbns(raw: str) -> list[str]:
    normalized = []
    seen = set()
    for line in raw.splitlines():
        isbn = "".join(ch for ch in line.strip() if ch.isdigit())
        if len(isbn) not in (10, 13):
            continue
        if isbn in seen:
            continue
        seen.add(isbn)
        normalized.append(isbn)
    return normalized


def _job_counts(job: CrawlJob) -> dict[str, int]:
    counts = {status.value: 0 for status in JobItemStatus}
    for item in job.items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def _event_tone(event: CrawlEvent) -> str:
    if event.level == EventLevel.ERROR.value:
        return "danger"
    if event.level == EventLevel.WARNING.value:
        return "warning"

    message = (event.message or "").lower()
    if "job finished" in message:
        return "job-finish"
    if "item completed" in message:
        return "item-success"
    if "item started" in message:
        return "item-start"
    if "job started" in message:
        return "job-start"
    if "job created" in message:
        return "job-created"
    return "neutral"


def _event_label(event: CrawlEvent) -> str:
    if event.level == EventLevel.ERROR.value:
        return "ERROR"
    if event.level == EventLevel.WARNING.value:
        return "WARNING"

    message = (event.message or "").lower()
    if "job finished" in message:
        return "JOB FINISH"
    if "item completed" in message:
        return "ITEM DONE"
    if "item started" in message:
        return "ITEM START"
    if "job started" in message:
        return "JOB START"
    if "job created" in message:
        return "JOB CREATED"
    return "INFO"


def _asset_absolute_path(file_path: str) -> Path:
    path = Path(file_path)
    if not path.is_absolute():
        path = settings.runtime_root / path
    return path


def _book_metadata_csv(books: Iterable[Book]) -> bytes:
    fieldnames = [
        "isbn",
        "site",
        "title",
        "author",
        "publisher",
        "category",
        "price_original",
        "price_sale",
        "published_date",
        "page_count",
        "book_size",
        "product_url",
        "last_crawled_at",
        "asset_count",
        "description",
    ]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for book in books:
        writer.writerow(
            {
                "isbn": book.isbn,
                "site": book.site,
                "title": book.title,
                "author": book.author,
                "publisher": book.publisher,
                "category": book.category,
                "price_original": book.price_original,
                "price_sale": book.price_sale,
                "published_date": book.published_date,
                "page_count": book.page_count,
                "book_size": book.book_size,
                "product_url": book.product_url,
                "last_crawled_at": _format_dt(book.last_crawled_at),
                "asset_count": len(book.assets),
                "description": book.description,
            }
        )
    return buffer.getvalue().encode("utf-8-sig")


def _sanitize_archive_segment(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).rstrip(". ")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = f"{cleaned}_"
    return cleaned or fallback


def _archive_directory_name(base_name: str, *, suffix: str = "") -> str:
    available = max(1, _ARCHIVE_SEGMENT_MAX_LENGTH - len(suffix))
    truncated = base_name[:available].rstrip(". ")
    if not truncated:
        truncated = base_name[:available] or "book"
    return f"{truncated}{suffix}"[:_ARCHIVE_SEGMENT_MAX_LENGTH]


def _book_archive_directories(books: Iterable[Book]) -> dict[str, str]:
    directories: dict[str, str] = {}
    used_names: set[str] = set()

    for book in sorted(books, key=lambda item: (item.title or "", item.isbn)):
        base_name = _sanitize_archive_segment(book.title, fallback=book.isbn)
        directory_name = _archive_directory_name(base_name)
        if directory_name in used_names:
            directory_name = _archive_directory_name(base_name, suffix=f" ({book.isbn})")

        suffix = 2
        while directory_name in used_names:
            directory_name = _archive_directory_name(base_name, suffix=f" ({book.isbn}) {suffix}")
            suffix += 1

        directories[book.isbn] = directory_name
        used_names.add(directory_name)

    return directories


def _book_archive_members(books: Iterable[Book]) -> list[tuple[str, Path | bytes]]:
    book_list = list(books)
    asset_members: list[tuple[str, Path | bytes]] = []
    directory_names = _book_archive_directories(book_list)
    for book in book_list:
        for asset in sorted(book.assets, key=lambda item: item.variant):
            path = _asset_absolute_path(asset.file_path)
            if not path.exists():
                continue
            asset_members.append((f"{directory_names[book.isbn]}/{asset.variant}.jpg", path))

    if not asset_members:
        return []

    return [("books.csv", _book_metadata_csv(book_list)), *asset_members]


def _log_archive_members() -> list[tuple[str, Path | bytes]]:
    members: list[tuple[str, Path | bytes]] = []
    if not settings.logs_dir.exists():
        return members

    for path in sorted(settings.logs_dir.glob("*")):
        if path.is_file():
            members.append((f"logs/{path.name}", path))
    return members


def _zip_response(members: list[tuple[str, Path | bytes]], filename: str) -> StreamingResponse:
    if not members:
        raise HTTPException(status_code=404, detail="No generated assets were found for download.")

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for arcname, source in members:
            if isinstance(source, Path):
                archive.write(source, arcname=arcname)
            else:
                archive.writestr(arcname, source)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _credential_saved(credential: SiteCredential | None) -> bool:
    return bool(credential and credential.username.strip())


def _runtime_checks(credential: SiteCredential | None) -> list[dict[str, str]]:
    path_entries = [
        ("앱 모드", "Desktop" if settings.desktop_mode else "Server"),
        ("Bundle Root", settings.bundle_dir.as_posix()),
        ("User Data", settings.user_data_dir.as_posix()),
        ("Database", settings.database_url),
        ("Assets", settings.assets_dir.as_posix()),
        ("Logs", settings.logs_dir.as_posix()),
        ("Browser State", settings.yes24_storage_state_path.as_posix()),
        ("Templates", settings.template_dir.as_posix()),
        ("Static", settings.static_dir.as_posix()),
        ("Resource", settings.resource_dir.as_posix()),
    ]
    checks = [
        {
            "label": label,
            "value": value,
            "status": "ok",
        }
        for label, value in path_entries
    ]
    checks.extend(
        [
            {
                "label": "Credential Saved",
                "value": "yes" if _credential_saved(credential) else "no",
                "status": "ok" if _credential_saved(credential) else "warning",
            },
            {
                "label": "Secret Key",
                "value": "ready" if settings.secret_key_path.exists() else "pending",
                "status": "ok" if settings.secret_key_path.exists() else "warning",
            },
            {
                "label": "Bundled Browser",
                "value": os.getenv("PLAYWRIGHT_BROWSERS_PATH", "system/default"),
                "status": "ok" if os.getenv("PLAYWRIGHT_BROWSERS_PATH") else "warning",
            },
        ]
    )
    return checks


def _settings_context(
    request: Request,
    credential: SiteCredential | None,
    *,
    message: str = "",
    health_result: HealthcheckResult | None = None,
) -> dict:
    return {
        "credential": credential,
        "message": message,
        "health_result": health_result,
        "runtime_checks": _runtime_checks(credential),
        "first_run": not _credential_saved(credential),
    }


def _open_directory(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    command = ["open", path.as_posix()] if sys.platform == "darwin" else ["xdg-open", path.as_posix()]
    subprocess.Popen(command)


def _settings_redirect(message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/settings?message={quote_plus(message)}", status_code=303)


@router.get("/healthz")
def healthz():
    return {
        "ok": True,
        "mode": "desktop" if settings.desktop_mode else "server",
        "user_data_dir": settings.user_data_dir.as_posix(),
    }


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, message: str = ""):
    with SessionLocal() as session:
        credential = session.get(SiteCredential, Site.YES24.value)
        recent_jobs = (
            session.execute(
                select(CrawlJob)
                .options(joinedload(CrawlJob.items))
                .order_by(CrawlJob.created_at.desc())
                .limit(8)
            )
            .unique()
            .scalars()
            .all()
        )
        recent_events = (
            session.execute(
                select(CrawlEvent)
                .order_by(CrawlEvent.created_at.desc())
                .limit(8)
            )
            .scalars()
            .all()
        )
        stats = {
            "books": session.scalar(select(func.count(Book.isbn))) or 0,
            "jobs": session.scalar(select(func.count(CrawlJob.id))) or 0,
            "running": session.scalar(select(func.count(CrawlJob.id)).where(CrawlJob.status == JobStatus.RUNNING.value)) or 0,
            "failed_items": session.scalar(
                select(func.count(CrawlJobItem.id)).where(CrawlJobItem.status == JobItemStatus.FAILED.value)
            )
            or 0,
        }
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "recent_jobs": recent_jobs,
                "job_counts": _job_counts,
                "recent_events": recent_events,
                "stats": stats,
                "message": message,
                "event_tone": _event_tone,
                "event_label": _event_label,
                "show_onboarding": not _credential_saved(credential),
            },
        )


@router.get("/partials/dashboard-jobs", response_class=HTMLResponse)
def dashboard_jobs_partial(request: Request):
    with SessionLocal() as session:
        recent_jobs = (
            session.execute(
                select(CrawlJob)
                .options(joinedload(CrawlJob.items))
                .order_by(CrawlJob.created_at.desc())
                .limit(8)
            )
            .unique()
            .scalars()
            .all()
        )
        return templates.TemplateResponse(
            request,
            "partials/dashboard_jobs.html",
            {"recent_jobs": recent_jobs, "job_counts": _job_counts},
        )


@router.post("/jobs")
def create_job(
    request: Request,
    isbn_list: str = Form(default=""),
    requested_by: str = Form(default=settings.requested_by_default),
):
    isbns = _parse_isbns(isbn_list)
    if not isbns:
        return RedirectResponse(url="/?message=유효한+ISBN을+입력하세요.", status_code=303)

    with SessionLocal() as session:
        job = CrawlJob(site=Site.YES24.value, status=JobStatus.PENDING.value, requested_by=requested_by.strip() or settings.requested_by_default)
        session.add(job)
        session.flush()
        for isbn in isbns:
            session.add(CrawlJobItem(job_id=job.id, isbn=isbn, status=JobItemStatus.PENDING.value))
        session.add(
            CrawlEvent(
                job_id=job.id,
                level=EventLevel.INFO.value,
                message="Job created.",
                payload_json={"isbn_count": len(isbns)},
            )
        )
        session.commit()
        return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int):
    with SessionLocal() as session:
        job = (
            session.execute(
                select(CrawlJob)
                .where(CrawlJob.id == job_id)
                .options(joinedload(CrawlJob.items), joinedload(CrawlJob.events))
            )
            .unique()
            .scalars()
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return templates.TemplateResponse(
            request,
            "jobs/detail.html",
            {"job": job, "job_counts": _job_counts(job), "event_tone": _event_tone, "event_label": _event_label},
        )


@router.get("/jobs/{job_id}/panel", response_class=HTMLResponse)
def job_panel(request: Request, job_id: int):
    with SessionLocal() as session:
        job = (
            session.execute(
                select(CrawlJob)
                .where(CrawlJob.id == job_id)
                .options(joinedload(CrawlJob.items), joinedload(CrawlJob.events))
            )
            .unique()
            .scalars()
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return templates.TemplateResponse(
            request,
            "jobs/panel.html",
            {"job": job, "job_counts": _job_counts(job), "event_tone": _event_tone, "event_label": _event_label},
        )


@router.post("/jobs/{job_id}/retry-failed")
def retry_failed_items(job_id: int):
    with SessionLocal() as session:
        job = session.get(CrawlJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        failed_items = (
            session.execute(
                select(CrawlJobItem)
                .where(CrawlJobItem.job_id == job_id)
                .where(CrawlJobItem.status == JobItemStatus.FAILED.value)
            )
            .scalars()
            .all()
        )
        for item in failed_items:
            item.status = JobItemStatus.PENDING.value
            item.error_code = ""
            item.error_message = ""
        job.status = JobStatus.PENDING.value
        job.started_at = None
        job.finished_at = None
        session.add(
            CrawlEvent(
                job_id=job.id,
                level=EventLevel.INFO.value,
                message="Failed items were reset for retry.",
                payload_json={"retry_count": len(failed_items)},
            )
        )
        session.commit()
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@router.get("/jobs/{job_id}/download")
def download_job_assets(job_id: int):
    with SessionLocal() as session:
        job = (
            session.execute(
                select(CrawlJob)
                .where(CrawlJob.id == job_id)
                .options(joinedload(CrawlJob.items))
            )
            .unique()
            .scalars()
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        success_isbns = sorted(
            {
                item.isbn
                for item in job.items
                if item.status == JobItemStatus.SUCCESS.value
            }
        )
        if not success_isbns:
            raise HTTPException(status_code=404, detail="No successful items are available for download.")

        books = (
            session.execute(select(Book).where(Book.isbn.in_(success_isbns)).options(joinedload(Book.assets)))
            .unique()
            .scalars()
            .all()
        )
        return _zip_response(_book_archive_members(books), f"job-{job_id}-assets.zip")


@router.get("/books", response_class=HTMLResponse)
def books_list(request: Request, q: str = ""):
    with SessionLocal() as session:
        query = select(Book).options(joinedload(Book.assets)).order_by(Book.last_crawled_at.desc())
        if q.strip():
            keyword = f"%{q.strip()}%"
            query = query.where(
                or_(
                    Book.title.ilike(keyword),
                    Book.isbn.ilike(keyword),
                    Book.publisher.ilike(keyword),
                    Book.author.ilike(keyword),
                )
            )
        books = session.execute(query.limit(50)).unique().scalars().all()
        return templates.TemplateResponse(
            request,
            "books/list.html",
            {"books": books, "query": q},
        )


@router.post("/books/download")
def download_selected_books(isbns: list[str] = Form(default=[])):
    normalized = [isbn.strip() for isbn in isbns if isbn.strip()]
    if not normalized:
        return RedirectResponse(url="/books", status_code=303)

    with SessionLocal() as session:
        books = (
            session.execute(select(Book).where(Book.isbn.in_(normalized)).options(joinedload(Book.assets)))
            .unique()
            .scalars()
            .all()
        )
        return _zip_response(_book_archive_members(books), "selected-books-assets.zip")


@router.get("/books/{isbn}", response_class=HTMLResponse)
def book_detail(request: Request, isbn: str):
    with SessionLocal() as session:
        book = (
            session.execute(select(Book).where(Book.isbn == isbn).options(joinedload(Book.assets)))
            .unique()
            .scalars()
            .first()
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        recent_items = (
            session.execute(
                select(CrawlJobItem)
                .where(CrawlJobItem.isbn == isbn)
                .order_by(CrawlJobItem.updated_at.desc())
                .limit(10)
            )
            .scalars()
            .all()
        )
        return templates.TemplateResponse(
            request,
            "books/detail.html",
            {"book": book, "recent_items": recent_items},
        )


@router.get("/books/{isbn}/download")
def download_book_assets(isbn: str):
    with SessionLocal() as session:
        book = (
            session.execute(select(Book).where(Book.isbn == isbn).options(joinedload(Book.assets)))
            .unique()
            .scalars()
            .first()
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return _zip_response(_book_archive_members([book]), f"book-{isbn}-assets.zip")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, message: str = ""):
    with SessionLocal() as session:
        credential = session.get(SiteCredential, Site.YES24.value)
        return templates.TemplateResponse(
            request,
            "settings/index.html",
            _settings_context(request, credential, message=message),
        )


@router.post("/settings/credentials")
def save_credentials(
    username: str = Form(""),
    password: str = Form(""),
):
    username = username.strip()
    password = password.strip()

    with SessionLocal() as session:
        credential = session.get(SiteCredential, Site.YES24.value)

        if not username and not password:
            if credential is not None:
                session.delete(credential)
                session.commit()
            return _settings_redirect("저장된 로그인 정보가 없습니다. 익명 수집으로 계속 동작합니다.")

        if not username or not password:
            return _settings_redirect("Username과 password를 함께 입력하거나 둘 다 비워 두세요.")

        cipher = CredentialCipher(settings)
        if credential is None:
            credential = SiteCredential(site=Site.YES24.value)
            session.add(credential)
        credential.username = username
        credential.password_encrypted = cipher.encrypt(password)
        session.commit()
    return _settings_redirect("Yes24 자격증명을 저장했습니다.")


@router.post("/settings/healthcheck", response_class=HTMLResponse)
def settings_healthcheck(request: Request):
    with SessionLocal() as session:
        credential = session.get(SiteCredential, Site.YES24.value)
        cipher = CredentialCipher(settings)
        username = credential.username if credential else ""
        password = cipher.decrypt(credential.password_encrypted) if credential else ""
    if not username or not password:
        return templates.TemplateResponse(
            request,
            "settings/healthcheck_result.html",
            {
                "health_result": HealthcheckResult(
                    ok=True,
                    message="저장된 로그인 정보가 없습니다. 비성인 도서는 익명 수집으로 계속 동작합니다.",
                )
            },
        )
    from app.infrastructure.storage.filesystem import FilesystemStorage

    storage = FilesystemStorage(settings)
    try:
        with Yes24CrawlerAdapter(settings, storage, username, password) as adapter:
            result = adapter.healthcheck()
    except Exception as exc:
        result = HealthcheckResult(ok=False, message=f"Healthcheck bootstrap failed: {exc}")
    return templates.TemplateResponse(
        request,
        "settings/healthcheck_result.html",
        {"health_result": result},
    )


@router.post("/settings/open-data-folder")
def open_data_folder():
    try:
        _open_directory(settings.user_data_dir)
    except Exception:
        return RedirectResponse(url="/settings?message=폴더를+열지+못했습니다.", status_code=303)
    return RedirectResponse(url="/settings?message=데이터+폴더를+열었습니다.", status_code=303)


@router.get("/settings/logs/download")
def download_logs():
    return _zip_response(_log_archive_members(), "book-crawling-logs.zip")


@router.get("/media/{asset_id}")
def media_asset(asset_id: int):
    with SessionLocal() as session:
        asset = session.get(ImageAsset, asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        file_path = Path(asset.file_path)
        if not file_path.is_absolute():
            file_path = settings.runtime_root / file_path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Asset file not found")
        return FileResponse(file_path)
