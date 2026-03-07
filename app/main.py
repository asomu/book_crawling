from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.settings import get_settings
from app.infrastructure.db.init_db import init_db
from app.infrastructure.images.pipeline import ImagePipeline
from app.infrastructure.storage.filesystem import FilesystemStorage
from app.web.routes import router
from app.worker.processor import CrawlProcessor
from app.worker.queue import CrawlWorker


def configure_logging() -> None:
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.logs_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging()
    init_db()

    storage = FilesystemStorage(settings)
    pipeline = ImagePipeline(settings, storage)
    processor = CrawlProcessor(settings, storage, pipeline)
    worker = CrawlWorker(settings, processor)

    app.state.settings = settings
    app.state.storage = storage
    app.state.pipeline = pipeline
    app.state.processor = processor
    app.state.worker = worker

    worker.start()
    yield
    worker.stop()


app = FastAPI(title="Book Crawling 후딱 v2", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.include_router(router)
