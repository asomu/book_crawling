"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("isbn", sa.String(length=13), nullable=False),
        sa.Column("site", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("price_original", sa.String(length=50), nullable=False),
        sa.Column("price_sale", sa.String(length=50), nullable=False),
        sa.Column("published_date", sa.String(length=50), nullable=False),
        sa.Column("page_count", sa.String(length=50), nullable=False),
        sa.Column("book_size", sa.String(length=50), nullable=False),
        sa.Column("product_url", sa.String(length=500), nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("isbn"),
    )
    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "site_credentials",
        sa.Column("site", sa.String(length=20), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("site"),
    )
    op.create_table(
        "crawl_job_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("isbn", sa.String(length=13), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["crawl_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_job_items_isbn"), "crawl_job_items", ["isbn"], unique=False)
    op.create_index(op.f("ix_crawl_job_items_job_id"), "crawl_job_items", ["job_id"], unique=False)
    op.create_table(
        "crawl_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("job_item_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["crawl_jobs.id"]),
        sa.ForeignKeyConstraint(["job_item_id"], ["crawl_job_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_crawl_events_job_id"), "crawl_events", ["job_id"], unique=False)
    op.create_table(
        "image_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("isbn", sa.String(length=13), nullable=False),
        sa.Column("variant", sa.String(length=30), nullable=False),
        sa.Column("file_path", sa.String(length=600), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["isbn"], ["books.isbn"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_image_assets_isbn"), "image_assets", ["isbn"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_image_assets_isbn"), table_name="image_assets")
    op.drop_table("image_assets")
    op.drop_index(op.f("ix_crawl_events_job_id"), table_name="crawl_events")
    op.drop_table("crawl_events")
    op.drop_index(op.f("ix_crawl_job_items_job_id"), table_name="crawl_job_items")
    op.drop_index(op.f("ix_crawl_job_items_isbn"), table_name="crawl_job_items")
    op.drop_table("crawl_job_items")
    op.drop_table("site_credentials")
    op.drop_table("crawl_jobs")
    op.drop_table("books")
