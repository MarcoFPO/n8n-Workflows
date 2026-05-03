from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from egon2.core.scheduler import EgonScheduler
from egon2.sync.bookstack import BookStackSync

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_app: "FastAPI | None" = None


async def bookstack_sync_job() -> None:
    if _app is None:
        return
    state = getattr(_app.state, "egon", None)
    if state is None or state.db is None:
        logger.warning("bookstack_sync.state_unavailable")
        return
    settings = state.settings
    if not settings.bookstack_token_id or not settings.bookstack_token_secret:
        return
    sync = BookStackSync(state.db, settings)
    try:
        synced, errors = await sync.sync_pending()
    except Exception:
        logger.exception("bookstack_sync.failed")
        return
    if synced or errors:
        logger.info("bookstack_sync.done synced=%d errors=%d", synced, errors)


def register_bookstack_sync(scheduler: EgonScheduler, app: "FastAPI") -> None:
    global _app
    _app = app
    if scheduler.scheduler is None:
        logger.warning("bookstack_sync.scheduler_not_started")
        return
    scheduler.scheduler.add_job(
        bookstack_sync_job,
        "interval",
        minutes=30,
        id="bookstack_sync",
        replace_existing=True,
    )
    logger.info("bookstack_sync.registered interval=30min")


__all__ = ["bookstack_sync_job", "register_bookstack_sync"]
