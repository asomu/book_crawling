from io import BytesIO
from pathlib import Path
from urllib.parse import unquote_plus
from zipfile import ZipFile

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import delete

from app.config.settings import get_settings
from app.domain.enums import Site
from app.infrastructure.db.models import Book, ImageAsset, SiteCredential
from app.infrastructure.db.session import SessionLocal

from app.main import app


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
                title="ZIP 테스트",
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
        assert f"{isbn}/cover.jpg" in names
        csv_text = archive.read("books.csv").decode("utf-8-sig")
        assert "isbn,site,title,author,publisher" in csv_text
        assert isbn in csv_text
        assert "ZIP 테스트" in csv_text


def test_download_selected_books_returns_zip():
    settings = get_settings()
    isbn = "9999990000002"
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
                title="선택 다운로드 테스트",
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
        assert f"{isbn}/cover.jpg" in names
        csv_text = archive.read("books.csv").decode("utf-8-sig")
        assert isbn in csv_text
        assert "선택 다운로드 테스트" in csv_text


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
