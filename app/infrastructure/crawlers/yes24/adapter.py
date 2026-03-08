from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from app.config.settings import AppSettings
from app.domain.errors import (
    AdultVerificationRequiredError,
    LoginFailedError,
    SearchNoResultError,
    SelectorChangedError,
)
from app.domain.interfaces import CrawlerAdapter
from app.domain.schemas import FetchBookResult, HealthcheckResult
from app.infrastructure.crawlers.yes24.parser import (
    extract_search_candidate_urls,
    has_adult_gate,
    looks_like_search_redirect_page,
    parse_detail_page,
)
from app.infrastructure.storage.filesystem import FilesystemStorage


YES24_HOME_URL = "https://www.yes24.com/Main/default.aspx"
YES24_LOGIN_URL = "https://www.yes24.com/Templates/FTLogin.aspx"
YES24_SEARCH_URL = "https://www.yes24.com/Product/Search?domain=BOOK&query={query}"


class Yes24CrawlerAdapter(CrawlerAdapter):
    def __init__(
        self,
        settings: AppSettings,
        storage: FilesystemStorage,
        username: str,
        password: str,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.username = username
        self.password = password
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.last_snapshot_path: Optional[Path] = None
        self._authenticated = False
        self._login_attempted = False

    def __enter__(self) -> "Yes24CrawlerAdapter":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.settings.browser_headless)
        self._context = self._browser.new_context(
            storage_state=self.settings.yes24_storage_state_path.as_posix()
            if self.settings.yes24_storage_state_path.exists()
            else None,
            user_agent=self.settings.user_agent,
        )
        self._page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def login(self) -> None:
        self._login_attempted = True
        self._authenticated = False
        if not self.username or not self.password:
            raise LoginFailedError("Yes24 credentials are missing. Save them on the settings page.")
        try:
            page = self._require_page()
            page.goto(YES24_LOGIN_URL, wait_until="domcontentloaded")
            page.fill("#SMemberID", self.username)
            page.fill("#SMemberPassword", self.password)
            page.click("#btnLogin")
            page.wait_for_timeout(1500)

            if "FTLogin" in page.url:
                content = page.content()
                self._save_snapshot("yes24-login-failure", content)
                raise LoginFailedError("Yes24 rejected the provided credentials.")
            self._context.storage_state(path=self.settings.yes24_storage_state_path.as_posix())
            self._authenticated = True
        except LoginFailedError:
            raise
        except Exception as exc:
            raise LoginFailedError(f"Yes24 login flow failed: {exc}") from exc

    def fetch_book(self, isbn: str) -> FetchBookResult:
        try:
            candidates = self._resolve_candidate_urls(isbn)
            return self._fetch_matching_candidate(isbn, candidates)
        except (AdultVerificationRequiredError, LoginFailedError, SearchNoResultError, SelectorChangedError):
            raise
        except Exception as exc:
            raise SelectorChangedError(f"Yes24 fetch flow failed for ISBN {isbn}: {exc}") from exc

    def healthcheck(self) -> HealthcheckResult:
        if not self.username or not self.password:
            return HealthcheckResult(
                ok=True,
                message="저장된 로그인 정보가 없습니다. 비성인 도서는 익명 수집으로 계속 동작합니다.",
            )
        try:
            self.login()
        except LoginFailedError as exc:
            return HealthcheckResult(ok=False, message=exc.message)
        except Exception as exc:
            return HealthcheckResult(ok=False, message=f"Playwright healthcheck failed: {exc}")
        return HealthcheckResult(ok=True, message="Yes24 login and browser startup succeeded.")

    def _require_page(self) -> Page:
        if not self._page:
            raise SelectorChangedError("Browser page was not initialized.")
        return self._page

    def _resolve_candidate_urls(self, isbn: str) -> list[str]:
        search_html, current_url = self._search_by_isbn(isbn)
        if has_adult_gate(search_html):
            self._save_snapshot(isbn, search_html, suffix="search-adult-gate")
            raise AdultVerificationRequiredError(
                f"ISBN {isbn} 은(는) Yes24에서 성인인증이 필요한 도서라 익명 수집을 진행할 수 없습니다."
            )

        candidates = extract_search_candidate_urls(search_html, limit=self.settings.worker_max_candidates)
        if candidates:
            return candidates

        redirected_to_main = looks_like_search_redirect_page(search_html, current_url)
        if redirected_to_main and self._retry_search_with_login():
            search_html, current_url = self._search_by_isbn(isbn)
            if has_adult_gate(search_html):
                self._save_snapshot(isbn, search_html, suffix="search-adult-gate")
                raise AdultVerificationRequiredError(
                    f"ISBN {isbn} 은(는) Yes24에서 성인인증이 필요한 도서라 익명 수집을 진행할 수 없습니다."
                )

            candidates = extract_search_candidate_urls(search_html, limit=self.settings.worker_max_candidates)
            if candidates:
                return candidates
            redirected_to_main = looks_like_search_redirect_page(search_html, current_url)

        self._save_snapshot(isbn, search_html, suffix="search")
        if redirected_to_main:
            raise SearchNoResultError(self._search_redirect_message(isbn))
        raise SearchNoResultError(f"No Yes24 candidates were found for ISBN {isbn}.")

    def _fetch_matching_candidate(self, isbn: str, candidates: list[str]) -> FetchBookResult:
        page = self._require_page()
        for candidate in candidates:
            page.goto(candidate, wait_until="domcontentloaded")
            page.wait_for_timeout(600)
            detail_html = page.content()
            if has_adult_gate(detail_html):
                self._save_snapshot(isbn, detail_html, suffix="detail-adult-gate")
                raise AdultVerificationRequiredError(
                    f"ISBN {isbn} 은(는) Yes24에서 성인인증이 필요한 도서라 익명 수집을 진행할 수 없습니다."
                )
            result = parse_detail_page(detail_html, product_url=page.url)
            self._save_snapshot(isbn, detail_html, suffix="detail")
            if result.book.isbn.replace("-", "") == isbn.replace("-", ""):
                result.source_snapshot_path = self.last_snapshot_path
                return result

        raise SearchNoResultError(f"No matching Yes24 product matched ISBN {isbn}.")

    def _search_by_isbn(self, isbn: str) -> tuple[str, str]:
        page = self._require_page()
        self._warm_up_search_session(page)
        search_url = YES24_SEARCH_URL.format(query=quote_plus(isbn))
        page.goto(search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(600)
        return page.content(), page.url

    def _warm_up_search_session(self, page: Page) -> None:
        page.goto(YES24_HOME_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(600)

    def _retry_search_with_login(self) -> bool:
        if not self.username or not self.password:
            return False
        if self._authenticated or self._login_attempted:
            return False
        self.login()
        return True

    def _search_redirect_message(self, isbn: str) -> str:
        if self._authenticated:
            return (
                f"Yes24 search for ISBN {isbn} was redirected to the main page even after applying stored credentials. "
                "상품 상세 페이지를 찾지 못했습니다."
            )
        if self.username and self.password:
            return (
                f"Yes24 search for ISBN {isbn} was redirected to the main page. "
                "익명 검색이 차단되었고 저장된 자격증명으로도 검색 세션을 복구하지 못했습니다."
            )
        return (
            f"Yes24 search for ISBN {isbn} was redirected to the main page. "
            "익명 검색이 차단되었을 수 있으니 저장된 자격증명으로 다시 시도하거나 상태 점검으로 로그인 세션을 갱신하세요."
        )

    def _save_snapshot(self, isbn: str, html: str, suffix: str = "page") -> None:
        path = self.storage.snapshot_path(isbn, suffix, html)
        self.storage.save_text(path, html)
        self.last_snapshot_path = path
