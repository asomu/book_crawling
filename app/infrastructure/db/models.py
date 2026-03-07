from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import AssetKind, EventLevel, JobItemStatus, JobStatus, Site
from app.infrastructure.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Book(Base):
    __tablename__ = "books"

    isbn: Mapped[str] = mapped_column(String(13), primary_key=True)
    site: Mapped[str] = mapped_column(String(20), default=Site.YES24.value, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    price_original: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    price_sale: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    published_date: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    page_count: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    book_size: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    product_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    last_crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    assets: Mapped[list["ImageAsset"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site: Mapped[str] = mapped_column(String(20), default=Site.YES24.value, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.PENDING.value, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["CrawlJobItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    events: Mapped[list["CrawlEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class CrawlJobItem(Base):
    __tablename__ = "crawl_job_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False, index=True)
    isbn: Mapped[str] = mapped_column(String(13), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default=JobItemStatus.PENDING.value, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    job: Mapped[CrawlJob] = relationship(back_populates="items")
    events: Mapped[list["CrawlEvent"]] = relationship(back_populates="job_item", cascade="all, delete-orphan")


class ImageAsset(Base):
    __tablename__ = "image_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isbn: Mapped[str] = mapped_column(ForeignKey("books.isbn"), nullable=False, index=True)
    variant: Mapped[str] = mapped_column(String(30), default=AssetKind.COVER.value, nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    book: Mapped[Book] = relationship(back_populates="assets")


class CrawlEvent(Base):
    __tablename__ = "crawl_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id"), nullable=False, index=True)
    job_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crawl_job_items.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(20), default=EventLevel.INFO.value, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped[CrawlJob] = relationship(back_populates="events")
    job_item: Mapped[Optional[CrawlJobItem]] = relationship(back_populates="events")


class SiteCredential(Base, TimestampMixin):
    __tablename__ = "site_credentials"

    site: Mapped[str] = mapped_column(String(20), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, default="", nullable=False)
