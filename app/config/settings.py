from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class AppSettings(BaseSettings):
    app_name: str = "Book Crawling 후딱 v2"
    environment: str = "development"
    database_url: str = Field(
        default=f"sqlite:///{(BASE_DIR / 'data' / 'book_crawling_v2.db').as_posix()}",
    )
    data_dir: Path = BASE_DIR / "data"
    assets_dir: Path = BASE_DIR / "data" / "assets"
    browser_state_dir: Path = BASE_DIR / "data" / "browser"
    snapshots_dir: Path = BASE_DIR / "data" / "snapshots"
    logs_dir: Path = BASE_DIR / "logs"
    resource_dir: Path = BASE_DIR / "resource"
    secret_key_path: Path = BASE_DIR / "data" / "secret.key"
    secret_key: Optional[str] = None
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )
    worker_poll_interval: float = 1.5
    worker_max_candidates: int = 5
    requested_by_default: str = "local-operator"
    browser_headless: bool = True
    yes24_storage_state_path: Path = BASE_DIR / "data" / "browser" / "yes24-state.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOOKCRAWLER_",
        extra="ignore",
    )

    def ensure_runtime_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.assets_dir,
            self.browser_state_dir,
            self.snapshots_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.ensure_runtime_dirs()
    return settings
