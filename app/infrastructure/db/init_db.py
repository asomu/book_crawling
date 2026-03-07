from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config.settings import BASE_DIR, get_settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine


def init_db() -> None:
    settings = get_settings()
    config = Config((BASE_DIR / "alembic.ini").as_posix())
    config.set_main_option("sqlalchemy.url", settings.database_url)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if tables and "alembic_version" not in tables:
        command.stamp(config, "head")
        return

    try:
        command.upgrade(config, "head")
    except Exception:
        Base.metadata.create_all(bind=engine)
