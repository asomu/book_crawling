from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config.settings import AppSettings


class FilesystemStorage:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def asset_path(self, isbn: str, variant: str, suffix: str = ".jpg") -> Path:
        folder = self.settings.assets_dir / isbn
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{variant}{suffix}"

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
        candidate = self.settings.data_dir.parent / file_path
        return candidate if candidate.exists() else None
