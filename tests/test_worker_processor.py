from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import AppSettings
from app.domain.enums import AssetKind, JobItemStatus, JobStatus, Site
from app.domain.schemas import BookPayload, FetchBookResult, StoredAsset
from app.domain.services.credentials import CredentialCipher
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import Book, CrawlJob, CrawlJobItem, ImageAsset, SiteCredential
from app.infrastructure.images.pipeline import ImagePipeline
from app.infrastructure.storage.filesystem import FilesystemStorage
from app.worker.processor import CrawlProcessor


def _image_bytes(size: tuple[int, int], color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


class FakeAdapter:
    login_calls = 0

    def __init__(self, *args, **kwargs):
        self.last_snapshot_path = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def login(self):
        FakeAdapter.login_calls += 1

    def fetch_book(self, isbn: str) -> FetchBookResult:
        return FetchBookResult(
            book=BookPayload(
                isbn=isbn,
                site=Site.YES24,
                title="테스트 북",
                author="저자",
                publisher="출판사",
                description="설명",
                category="카테고리",
                price_original="15000",
                price_sale="13500",
                published_date="2024년 05월 17일",
                page_count="220쪽",
                book_size="135*210*15mm",
                product_url="https://www.yes24.com/product/goods/1111",
            ),
            cover_image_url="https://example.com/cover.jpg",
            detail_image_url="https://example.com/detail.jpg",
            source_snapshot_path=None,
        )


def test_processor_marks_job_success(monkeypatch, tmp_path: Path):
    FakeAdapter.login_calls = 0
    settings = AppSettings(
        data_dir=tmp_path / "data",
        assets_dir=tmp_path / "data" / "assets",
        browser_state_dir=tmp_path / "data" / "browser",
        snapshots_dir=tmp_path / "data" / "snapshots",
        logs_dir=tmp_path / "logs",
        resource_dir=Path(__file__).resolve().parents[1] / "resource",
    )
    settings.ensure_runtime_dirs()

    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    storage = FilesystemStorage(settings)
    pipeline = ImagePipeline(settings, storage)
    processor = CrawlProcessor(settings, storage, pipeline)
    cipher = CredentialCipher(settings)

    monkeypatch.setattr("app.worker.processor.Yes24CrawlerAdapter", FakeAdapter)
    monkeypatch.setattr(
        processor,
        "_download_image",
        lambda url: _image_bytes((600, 900), (20, 50, 90))
        if "cover" in url
        else _image_bytes((900, 1300), (90, 40, 20)),
    )

    with SessionLocal() as session:
        session.add(
            SiteCredential(
                site=Site.YES24.value,
                username="demo",
                password_encrypted=cipher.encrypt("demo"),
            )
        )
        job = CrawlJob(site=Site.YES24.value, status=JobStatus.PENDING.value, requested_by="tester")
        session.add(job)
        session.flush()
        session.add(CrawlJobItem(job_id=job.id, isbn="9791130671017", status=JobItemStatus.PENDING.value))
        session.commit()
        session.refresh(job)

        processor.process_job(session, job)

        refreshed_job = session.get(CrawlJob, job.id)
        assert refreshed_job.status == JobStatus.SUCCESS.value

        item = session.execute(select(CrawlJobItem).where(CrawlJobItem.job_id == job.id)).scalar_one()
        assert item.status == JobItemStatus.SUCCESS.value
        assert FakeAdapter.login_calls == 1

        book = session.get(Book, "9791130671017")
        assert book is not None

        asset_count = session.execute(select(ImageAsset).where(ImageAsset.isbn == "9791130671017")).scalars().all()
        assert len(asset_count) == 5
        assert all(Path(asset.file_path).name.startswith("테스트 북_") for asset in asset_count)


def test_replace_assets_removes_superseded_files(tmp_path: Path):
    settings = AppSettings(
        data_dir=tmp_path / "data",
        assets_dir=tmp_path / "data" / "assets",
        browser_state_dir=tmp_path / "data" / "browser",
        snapshots_dir=tmp_path / "data" / "snapshots",
        logs_dir=tmp_path / "logs",
        resource_dir=Path(__file__).resolve().parents[1] / "resource",
    )
    settings.ensure_runtime_dirs()

    engine = create_engine(f"sqlite:///{(tmp_path / 'replace-assets.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    storage = FilesystemStorage(settings)
    pipeline = ImagePipeline(settings, storage)
    processor = CrawlProcessor(settings, storage, pipeline)

    isbn = "9791130671017"
    old_path = settings.assets_dir / isbn / "옛 제목_cover.jpg"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_bytes(b"old")
    new_path = settings.assets_dir / isbn / "새 제목_cover.jpg"
    new_path.write_bytes(b"new")

    with SessionLocal() as session:
        session.add(
            Book(
                isbn=isbn,
                site=Site.YES24.value,
                title="옛 제목",
                author="저자",
                publisher="출판사",
                description="설명",
                category="테스트",
                price_original="15000",
                price_sale="13500",
                published_date="2024년 05월 17일",
                page_count="220쪽",
                book_size="135*210*15mm",
                product_url="https://www.yes24.com/product/goods/1111",
            )
        )
        session.add(
            ImageAsset(
                isbn=isbn,
                variant=AssetKind.COVER.value,
                file_path=str(old_path.relative_to(settings.runtime_root)),
                width=100,
                height=150,
            )
        )
        session.commit()

        processor._replace_assets(
            session,
            isbn,
            [
                StoredAsset(
                    kind=AssetKind.COVER,
                    file_path=str(new_path.relative_to(settings.runtime_root)),
                    width=100,
                    height=150,
                )
            ],
        )
        session.commit()

        stored_assets = session.execute(select(ImageAsset).where(ImageAsset.isbn == isbn)).scalars().all()
        assert [asset.file_path for asset in stored_assets] == [str(new_path.relative_to(settings.runtime_root))]

    assert not old_path.exists()
    assert new_path.exists()
