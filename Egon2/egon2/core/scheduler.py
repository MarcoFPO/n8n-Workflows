"""EgonScheduler — APScheduler-Wrapper (Phase-1-Skeleton).

Phase 1: kein Job registriert. Initialisiert nur den AsyncIOScheduler mit
SQLAlchemyJobStore (sqlite WAL) und Europe/Berlin-Timezone.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


class EgonScheduler:
    """APScheduler mit SQLite-JobStore (WAL) und Europe/Berlin."""

    def __init__(self, scheduler_db_path: Path | str) -> None:
        self._path: Path = Path(scheduler_db_path)
        self._scheduler: AsyncIOScheduler | None = None

    def _init_wal(self) -> None:
        """WAL-Modus für scheduler.db aktivieren."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()
        finally:
            conn.close()

    def start(self) -> None:
        """Scheduler initialisieren und starten."""
        self._init_wal()
        jobstore = SQLAlchemyJobStore(url=f"sqlite:///{self._path}")
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": jobstore},
            timezone="Europe/Berlin",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,
            },
        )
        self._scheduler.start()
        logger.info("scheduler.started path=%s", self._path)

    def shutdown(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler.shutdown")

    @property
    def scheduler(self) -> AsyncIOScheduler | None:
        return self._scheduler


__all__ = ["EgonScheduler"]
