from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


def _detect_bundle_dir() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return BASE_DIR


def _default_user_data_dir() -> Path:
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_app_data / "BookCrawling"
    return BASE_DIR


class AppSettings(BaseSettings):
    app_name: str = "Book Crawling 후딱 v2"
    environment: str = "development"
    bundle_dir: Path = Field(default_factory=_detect_bundle_dir)
    user_data_dir: Path = Field(default_factory=_default_user_data_dir)
    database_url: str = ""
    data_dir: Optional[Path] = None
    assets_dir: Optional[Path] = None
    browser_state_dir: Optional[Path] = None
    snapshots_dir: Optional[Path] = None
    logs_dir: Optional[Path] = None
    resource_dir: Optional[Path] = None
    template_dir: Optional[Path] = None
    static_dir: Optional[Path] = None
    alembic_dir: Optional[Path] = None
    alembic_ini_path: Optional[Path] = None
    secret_key_path: Optional[Path] = None
    secret_key: Optional[str] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )
    worker_poll_interval: float = 1.5
    worker_max_candidates: int = 5
    requested_by_default: str = "local-operator"
    browser_headless: bool = True
    yes24_storage_state_path: Optional[Path] = None
    desktop_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOOKCRAWLER_",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        self.bundle_dir = self.bundle_dir.expanduser().resolve()
        self.user_data_dir = self.user_data_dir.expanduser()

        if self.data_dir is None:
            self.data_dir = self.user_data_dir / "data"
        if self.assets_dir is None:
            self.assets_dir = self.data_dir / "assets"
        if self.browser_state_dir is None:
            self.browser_state_dir = self.data_dir / "browser"
        if self.snapshots_dir is None:
            self.snapshots_dir = self.data_dir / "snapshots"
        if self.logs_dir is None:
            self.logs_dir = self.user_data_dir / "logs"
        if self.resource_dir is None:
            self.resource_dir = self.bundle_dir / "resource"
        if self.template_dir is None:
            self.template_dir = self.bundle_dir / "app" / "web" / "templates"
        if self.static_dir is None:
            self.static_dir = self.bundle_dir / "app" / "web" / "static"
        if self.alembic_dir is None:
            self.alembic_dir = self.bundle_dir / "alembic"
        if self.alembic_ini_path is None:
            self.alembic_ini_path = self.bundle_dir / "alembic.ini"
        if self.secret_key_path is None:
            self.secret_key_path = self.data_dir / "secret.key"
        if self.yes24_storage_state_path is None:
            self.yes24_storage_state_path = self.browser_state_dir / "yes24-state.json"
        if not self.database_url:
            self.database_url = f"sqlite:///{(self.data_dir / 'book_crawling_v2.db').as_posix()}"

    def ensure_runtime_dirs(self) -> None:
        for path in (
            self.user_data_dir,
            self.data_dir,
            self.assets_dir,
            self.browser_state_dir,
            self.snapshots_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def configure_process_environment(self) -> None:
        bundled_browser_dir = self.bundle_dir / "ms-playwright"
        if bundled_browser_dir.exists() and "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled_browser_dir.as_posix()

    @property
    def runtime_root(self) -> Path:
        try:
            self.data_dir.relative_to(self.user_data_dir)
        except ValueError:
            return self.data_dir.parent
        return self.user_data_dir


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.ensure_runtime_dirs()
    settings.configure_process_environment()
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()
