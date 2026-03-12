from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config.settings import AppSettings


_ASSET_FILENAME_MAX_LENGTH = 140


class FilesystemStorage:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def asset_path(self, isbn: str, title: str, variant: str, suffix: str = ".jpg") -> Path:
        folder = self.settings.assets_dir / isbn
        folder.mkdir(parents=True, exist_ok=True)
        return folder / self.asset_filename(isbn, title, variant, suffix)

    def asset_filename(self, isbn: str, title: str, variant: str, suffix: str = ".jpg") -> str:
        asset_suffix = f"_{variant}{suffix}"
        title_prefix = self._asset_title_prefix(isbn, title, asset_suffix)
        return f"{title_prefix}{asset_suffix}"

    def asset_download_name(self, isbn: str, title: str, file_path: str, variant: str) -> str:
        existing_name = Path(file_path).name or f"{variant}.jpg"
        if existing_name != f"{variant}.jpg":
            return existing_name
        title_prefix = self._asset_title_prefix(isbn, title, f"_{existing_name}")
        return f"{title_prefix}_{existing_name}"

    def snapshot_path(self, isbn: str, kind: str, content: str) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        digest = hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest()[:10]
        folder = self.settings.snapshots_dir / isbn
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{stamp}-{kind}-{digest}.html"

    def save_bytes(self, path: Path, content: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def save_text(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def resolve_asset(self, file_path: str) -> Optional[Path]:
        path = Path(file_path)
        if path.is_absolute():
            return path if path.exists() else None
        candidate = self.settings.runtime_root / file_path
        return candidate if candidate.exists() else None

    def _asset_title_prefix(self, isbn: str, title: str, suffix: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title.strip())
        cleaned = re.sub(r"\s+", " ", cleaned).rstrip(". ")
        if not cleaned:
            cleaned = isbn
        available = max(1, _ASSET_FILENAME_MAX_LENGTH - len(suffix))
        truncated = cleaned[:available].rstrip(". ")
        return truncated or isbn
