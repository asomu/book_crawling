from __future__ import annotations

import threading
import time

from sqlalchemy import select

from app.config.settings import AppSettings
from app.infrastructure.db.models import CrawlJob
from app.infrastructure.db.session import SessionLocal
from app.worker.processor import CrawlProcessor


class CrawlWorker:
    def __init__(self, settings: AppSettings, processor: CrawlProcessor) -> None:
        self.settings = settings
        self.processor = processor
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, name="crawl-worker", daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            handled = self.process_one()
            if not handled:
                time.sleep(self.settings.worker_poll_interval)

    def process_one(self) -> bool:
        session = SessionLocal()
        try:
            job = (
                session.execute(
                    select(CrawlJob)
                    .where(CrawlJob.status == "pending")
                    .order_by(CrawlJob.created_at.asc())
                )
                .scalars()
                .first()
            )
            if not job:
                return False
            self.processor.process_job(session, job)
            return True
        finally:
            session.close()
