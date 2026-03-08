from __future__ import annotations

from pathlib import Path

import pytest

from app.config.settings import AppSettings
from app.domain.errors import SearchNoResultError
from app.infrastructure.crawlers.yes24.adapter import YES24_HOME_URL, YES24_SEARCH_URL, Yes24CrawlerAdapter
from app.infrastructure.storage.filesystem import FilesystemStorage


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "html"
RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resource"


class FakePage:
    def __init__(self, responses: list[tuple[str, str, str]]) -> None:
        self._responses = list(responses)
        self._content = ""
        self.goto_calls: list[str] = []
        self.url = ""

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        self.goto_calls.append(url)
        expected_prefix, response_url, response_html = self._responses.pop(0)
        assert wait_until == "domcontentloaded"
        assert url.startswith(expected_prefix)
        self.url = response_url
        self._content = response_html

    def wait_for_timeout(self, milliseconds: int) -> None:
        assert milliseconds == 600

    def content(self) -> str:
        return self._content


def _build_adapter(tmp_path: Path, username: str = "", password: str = "") -> Yes24CrawlerAdapter:
    settings = AppSettings(
        data_dir=tmp_path / "data",
        assets_dir=tmp_path / "data" / "assets",
        browser_state_dir=tmp_path / "data" / "browser",
        snapshots_dir=tmp_path / "data" / "snapshots",
        logs_dir=tmp_path / "logs",
        resource_dir=RESOURCE_DIR,
    )
    settings.ensure_runtime_dirs()
    storage = FilesystemStorage(settings)
    return Yes24CrawlerAdapter(settings, storage, username, password)


def test_fetch_book_warms_up_home_before_search(tmp_path: Path):
    search_html = (FIXTURE_DIR / "yes24_search.html").read_text(encoding="utf-8")
    detail_html = (FIXTURE_DIR / "yes24_detail.html").read_text(encoding="utf-8")
    adapter = _build_adapter(tmp_path)
    adapter._page = FakePage(
        [
            (YES24_HOME_URL, YES24_HOME_URL, "<html><head><title>예스24</title></head><body>홈</body></html>"),
            (
                YES24_SEARCH_URL.format(query=""),
                YES24_SEARCH_URL.format(query="9791130671017"),
                search_html,
            ),
            (
                "https://www.yes24.com/product/goods/1111",
                "https://www.yes24.com/product/goods/1111",
                detail_html,
            ),
        ]
    )

    result = adapter.fetch_book("9791130671017")

    assert adapter._page.goto_calls == [
        YES24_HOME_URL,
        YES24_SEARCH_URL.format(query="9791130671017"),
        "https://www.yes24.com/product/goods/1111",
    ]
    assert result.book.product_url == "https://www.yes24.com/product/goods/1111"


def test_fetch_book_retries_search_after_login_when_main_redirect_detected(monkeypatch, tmp_path: Path):
    search_html = (FIXTURE_DIR / "yes24_search.html").read_text(encoding="utf-8")
    detail_html = (FIXTURE_DIR / "yes24_detail.html").read_text(encoding="utf-8")
    redirect_html = "<html><head><title>예스24</title></head><body><div>메인 페이지</div></body></html>"
    adapter = _build_adapter(tmp_path, username="demo", password="secret")
    adapter._page = FakePage(
        [
            (YES24_HOME_URL, YES24_HOME_URL, "<html><head><title>예스24</title></head><body>홈</body></html>"),
            (YES24_SEARCH_URL.format(query=""), YES24_HOME_URL, redirect_html),
            (YES24_HOME_URL, YES24_HOME_URL, "<html><head><title>예스24</title></head><body>홈</body></html>"),
            (
                YES24_SEARCH_URL.format(query=""),
                YES24_SEARCH_URL.format(query="9791130671017"),
                search_html,
            ),
            (
                "https://www.yes24.com/product/goods/1111",
                "https://www.yes24.com/product/goods/1111",
                detail_html,
            ),
        ]
    )
    login_calls: list[bool] = []

    def fake_login(self) -> None:
        login_calls.append(True)
        self._login_attempted = True
        self._authenticated = True

    monkeypatch.setattr(Yes24CrawlerAdapter, "login", fake_login)

    result = adapter.fetch_book("9791130671017")

    assert len(login_calls) == 1
    assert adapter._page.goto_calls == [
        YES24_HOME_URL,
        YES24_SEARCH_URL.format(query="9791130671017"),
        YES24_HOME_URL,
        YES24_SEARCH_URL.format(query="9791130671017"),
        "https://www.yes24.com/product/goods/1111",
    ]
    assert result.book.product_url == "https://www.yes24.com/product/goods/1111"


def test_fetch_book_reports_redirect_when_anonymous_search_stays_on_main_page(tmp_path: Path):
    redirect_html = "<html><head><title>예스24</title></head><body><div>메인 페이지</div></body></html>"
    adapter = _build_adapter(tmp_path)
    adapter._page = FakePage(
        [
            (YES24_HOME_URL, YES24_HOME_URL, "<html><head><title>예스24</title></head><body>홈</body></html>"),
            (YES24_SEARCH_URL.format(query=""), YES24_HOME_URL, redirect_html),
        ]
    )

    with pytest.raises(SearchNoResultError) as exc:
        adapter.fetch_book("9791130671017")

    assert "redirected to the main page" in exc.value.message
