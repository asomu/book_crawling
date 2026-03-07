from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.enums import AssetKind, Site


class BookPayload(BaseModel):
    isbn: str = Field(min_length=10, max_length=13)
    site: Site = Site.YES24
    title: str
    author: str = ""
    publisher: str = ""
    description: str = ""
    category: str = ""
    price_original: str = ""
    price_sale: str = ""
    published_date: str = ""
    page_count: str = ""
    book_size: str = ""
    product_url: str = ""


class FetchBookResult(BaseModel):
    book: BookPayload
    cover_image_url: Optional[str] = None
    detail_image_url: Optional[str] = None
    source_snapshot_path: Optional[Path] = None


class HealthcheckResult(BaseModel):
    ok: bool
    message: str


@dataclass(frozen=True)
class DownloadedImage:
    url: str
    content: bytes


class StoredAsset(BaseModel):
    kind: AssetKind
    file_path: str
    width: int
    height: int
