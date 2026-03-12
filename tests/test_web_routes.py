from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote_plus
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete, select

from app.config.settings import get_settings
from app.domain.enums import Site
from app.infrastructure.db.models import Book, ImageAsset, SiteCredential
from app.infrastructure.db.session import SessionLocal

from app.main import app


def _upsert_book(
    *,
    isbn: str,
    title: str,
    author: str,
    publisher: str,
    last_crawled_at: datetime | None = None,
    asset_variants: tuple[str, ...] = (),
) -> Path:
    settings = get_settings()
    asset_dir = settings.assets_dir / isbn
    asset_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
        book = session.get(Book, isbn)
        if not book:
            book = Book(
                isbn=isbn,
                site="yes24",
                title=title,
                author=author,
                publisher=publisher,
                description="",
                category="테스트",
                price_original="10000",
                price_sale="9000",
                published_date="2024년 01월 01일",
                page_count="100쪽",
                book_size="120*180*10mm",
                product_url="https://example.com",
            )
            session.add(book)
        else:
            book.title = title
            book.author = author
            book.publisher = publisher
        if last_crawled_at is not None:
            book.last_crawled_at = last_crawled_at

        for index, variant in enumerate(asset_variants):
            asset_path = asset_dir / f"{variant}.jpg"
            image = Image.new("RGB", (120 + index, 180 + index), (40 + index, 70, 100))
            image.save(asset_path, format="JPEG")
            session.add(
                ImageAsset(
                    isbn=isbn,
                    variant=variant,
                    file_path=str(asset_path.relative_to(settings.user_data_dir)),
                    width=120 + index,
                    height=180 + index,
                )
            )

        session.commit()

    return asset_dir


def test_create_job_renders_detail_page():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/jobs",
            data={"requested_by": "route-tester", "isbn_list": "9791130671017"},
        )
        assert response.status_code == 200
        assert "Job #" in response.text
        assert "실패 항목 재시도" in response.text


def test_create_job_without_isbn_redirects_back_with_message():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/jobs",
            data={"requested_by": "route-tester"},
        )
        assert response.status_code == 200
        assert "유효한 ISBN을 입력하세요." in response.text
        assert "작업 생성" in response.text


def test_download_single_book_assets_returns_zip():
    settings = get_settings()
    isbn = "9999990000001"
    title = "ZIP 테스트"
    asset_dir = settings.assets_dir / isbn
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / "cover.jpg"

    image = Image.new("RGB", (120, 180), (40, 70, 100))
    image.save(asset_path, format="JPEG")

    with SessionLocal() as session:
        session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
        book = session.get(Book, isbn)
        if not book:
            book = Book(
                isbn=isbn,
                site="yes24",
                title=title,
                author="테스터",
                publisher="테스트출판사",
                description="",
                category="테스트",
                price_original="10000",
                price_sale="9000",
                published_date="2024년 01월 01일",
                page_count="100쪽",
                book_size="120*180*10mm",
                product_url="https://example.com",
            )
            session.add(book)
        session.add(
            ImageAsset(
                isbn=isbn,
                variant="cover",
                file_path=str(asset_path.relative_to(settings.user_data_dir)),
                width=120,
                height=180,
            )
        )
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/books/{isbn}/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.content[:2] == b"PK"

    with ZipFile(BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert "books.csv" in names
        assert f"{title}/{title}_cover.jpg" in names
        csv_text = archive.read("books.csv").decode("utf-8-sig")
        assert "isbn,site,title,author,publisher" in csv_text
        assert isbn in csv_text
        assert title in csv_text


def test_download_selected_books_returns_zip():
    settings = get_settings()
    isbn = "9999990000002"
    title = "선택 다운로드 테스트"
    asset_dir = settings.assets_dir / isbn
    asset_dir.mkdir(parents=True, exist_ok=True)
    asset_path = asset_dir / "cover.jpg"

    image = Image.new("RGB", (100, 150), (120, 60, 90))
    image.save(asset_path, format="JPEG")

    with SessionLocal() as session:
        session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
        book = session.get(Book, isbn)
        if not book:
            book = Book(
                isbn=isbn,
                site="yes24",
                title=title,
                author="테스터",
                publisher="테스트출판사",
                description="",
                category="테스트",
                price_original="10000",
                price_sale="9000",
                published_date="2024년 01월 01일",
                page_count="100쪽",
                book_size="120*180*10mm",
                product_url="https://example.com",
            )
            session.add(book)
        session.add(
            ImageAsset(
                isbn=isbn,
                variant="cover",
                file_path=str(asset_path.relative_to(settings.user_data_dir)),
                width=100,
                height=150,
            )
        )
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/books/download", data={"isbns": [isbn]})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.content[:2] == b"PK"

    with ZipFile(BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert "books.csv" in names
        assert f"{title}/{title}_cover.jpg" in names
        csv_text = archive.read("books.csv").decode("utf-8-sig")
        assert isbn in csv_text
        assert title in csv_text


def test_download_selected_books_sanitizes_duplicate_title_folders():
    settings = get_settings()
    first_isbn = "9999990000011"
    second_isbn = "9999990000012"
    title = '중복/제목: 테스트'

    for isbn, variant in ((first_isbn, "cover"), (second_isbn, "detail")):
        asset_dir = settings.assets_dir / isbn
        asset_dir.mkdir(parents=True, exist_ok=True)
        asset_path = asset_dir / f"{variant}.jpg"
        image = Image.new("RGB", (80, 120), (90, 110, 130))
        image.save(asset_path, format="JPEG")

        with SessionLocal() as session:
            session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
            book = session.get(Book, isbn)
            if not book:
                book = Book(
                    isbn=isbn,
                    site="yes24",
                    title=title,
                    author="테스터",
                    publisher="테스트출판사",
                    description="",
                    category="테스트",
                    price_original="10000",
                    price_sale="9000",
                    published_date="2024년 01월 01일",
                    page_count="100쪽",
                    book_size="120*180*10mm",
                    product_url="https://example.com",
                )
                session.add(book)
            else:
                book.title = title
            session.add(
                ImageAsset(
                    isbn=isbn,
                    variant=variant,
                    file_path=str(asset_path.relative_to(settings.user_data_dir)),
                    width=80,
                    height=120,
                )
            )
            session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/books/download", data={"isbns": [first_isbn, second_isbn]})
        assert response.status_code == 200

    with ZipFile(BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert "중복_제목_ 테스트/중복_제목_ 테스트_cover.jpg" in names
        assert f"중복_제목_ 테스트 ({second_isbn})/중복_제목_ 테스트_detail.jpg" in names


def test_download_selected_books_keeps_duplicate_long_titles_unique():
    settings = get_settings()
    first_isbn = "9999990000021"
    second_isbn = "9999990000022"
    title = "아주긴제목" * 30

    for isbn in (first_isbn, second_isbn):
        asset_dir = settings.assets_dir / isbn
        asset_dir.mkdir(parents=True, exist_ok=True)
        asset_path = asset_dir / "cover.jpg"
        image = Image.new("RGB", (90, 140), (70, 90, 150))
        image.save(asset_path, format="JPEG")

        with SessionLocal() as session:
            session.execute(delete(ImageAsset).where(ImageAsset.isbn == isbn))
            book = session.get(Book, isbn)
            if not book:
                book = Book(
                    isbn=isbn,
                    site="yes24",
                    title=title,
                    author="테스터",
                    publisher="테스트출판사",
                    description="",
                    category="테스트",
                    price_original="10000",
                    price_sale="9000",
                    published_date="2024년 01월 01일",
                    page_count="100쪽",
                    book_size="120*180*10mm",
                    product_url="https://example.com",
                )
                session.add(book)
            else:
                book.title = title
            session.add(
                ImageAsset(
                    isbn=isbn,
                    variant="cover",
                    file_path=str(asset_path.relative_to(settings.user_data_dir)),
                    width=90,
                    height=140,
                )
            )
            session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/books/download", data={"isbns": [first_isbn, second_isbn]})
        assert response.status_code == 200

    with ZipFile(BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        cover_names = [name for name in names if name.endswith("_cover.jpg")]
        assert len(cover_names) == 2
        assert len({name.split("/")[0] for name in cover_names}) == 2
        assert any(first_isbn in name or second_isbn in name for name in cover_names)


def test_settings_healthcheck_without_credentials_reports_anonymous_mode():
    with SessionLocal() as session:
        session.execute(delete(SiteCredential).where(SiteCredential.site == Site.YES24.value))
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/settings/healthcheck")
        assert response.status_code == 200
        assert "익명 수집으로 계속 동작합니다" in response.text


def test_save_credentials_empty_submission_redirects_without_422():
    with SessionLocal() as session:
        session.execute(delete(SiteCredential).where(SiteCredential.site == Site.YES24.value))
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/settings/credentials",
            data={"username": "", "password": ""},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "익명 수집으로 계속 동작합니다." in unquote_plus(response.headers["location"])

    with SessionLocal() as session:
        assert session.get(SiteCredential, Site.YES24.value) is None


def test_save_credentials_rejects_partial_input():
    with SessionLocal() as session:
        session.execute(delete(SiteCredential).where(SiteCredential.site == Site.YES24.value))
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/settings/credentials",
            data={"username": "demo", "password": ""},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "Username과 password를 함께 입력하거나 둘 다 비워 두세요." in unquote_plus(response.headers["location"])

    with SessionLocal() as session:
        assert session.get(SiteCredential, Site.YES24.value) is None


def test_healthz_reports_ready():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["ok"] is True


def test_settings_page_shows_runtime_actions():
    with SessionLocal() as session:
        session.execute(delete(SiteCredential).where(SiteCredential.site == Site.YES24.value))
        session.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/settings")
        assert response.status_code == 200
        assert "데이터 폴더 열기" in response.text
        assert "로그 내보내기" in response.text
        assert "처음 실행할 때 확인할 것" in response.text


def test_download_logs_returns_zip():
    settings = get_settings()
    log_file = settings.logs_dir / "app.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("desktop-log", encoding="utf-8")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/settings/logs/download")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert response.content[:2] == b"PK"


def test_books_list_supports_sorting_and_toggle_links():
    older = datetime.utcnow() - timedelta(days=2)
    newer = datetime.utcnow() - timedelta(days=1)
    first_isbn = "9999990000101"
    second_isbn = "9999990000102"
    _upsert_book(
        isbn=first_isbn,
        title="Alpha Sort Route",
        author="Writer B",
        publisher="Publisher Z",
        last_crawled_at=older,
        asset_variants=("cover", "detail"),
    )
    _upsert_book(
        isbn=second_isbn,
        title="Beta Sort Route",
        author="Writer A",
        publisher="Publisher A",
        last_crawled_at=newer,
        asset_variants=("cover",),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        ascending = client.get("/books?q=Sort+Route&sort=title&dir=asc")
        assert ascending.status_code == 200
        assert ascending.text.index("Alpha Sort Route") < ascending.text.index("Beta Sort Route")
        assert 'class="table-sort-link active" href="/books?q=Sort+Route&amp;sort=title"' in ascending.text

        descending = client.get("/books?q=Sort+Route&sort=assets&dir=desc")
        assert descending.status_code == 200
        assert descending.text.index(first_isbn) < descending.text.index(second_isbn)
        assert "sort=assets&amp;dir=asc" in descending.text


def test_delete_selected_books_removes_records_and_files():
    settings = get_settings()
    isbn = "9999990000103"
    asset_dir = _upsert_book(
        isbn=isbn,
        title="Delete Route Test",
        author="Delete Writer",
        publisher="Delete Publisher",
        last_crawled_at=datetime.utcnow(),
        asset_variants=("cover",),
    )
    snapshot_dir = settings.snapshots_dir / isbn
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / "snapshot.html"
    snapshot_file.write_text("<html>snapshot</html>", encoding="utf-8")
    asset_path = asset_dir / "cover.jpg"

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/books/delete",
            data={"isbns": [isbn], "q": "Delete Route", "sort": "title", "dir": "asc"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert "Delete+Route" in response.headers["location"]
    assert "sort=title" in response.headers["location"]
    assert "dir=asc" in response.headers["location"]
    assert "1%EA%B6%8C%EC%9D%98+%EB%8F%84%EC%84%9C+%EB%8D%B0%EC%9D%B4%ED%84%B0" in response.headers["location"]

    with SessionLocal() as session:
        assert session.get(Book, isbn) is None
        assert session.execute(select(ImageAsset).where(ImageAsset.isbn == isbn)).scalars().first() is None

    assert not asset_path.exists()
    assert not snapshot_file.exists()
    assert not asset_dir.exists()
    assert not snapshot_dir.exists()
