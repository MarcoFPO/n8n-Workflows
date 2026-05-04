"""FastAPI-Entrypoint für Egon2.

Lifespan in 9 Stufen — siehe `docs/LLD-Interfaces.md` §1.3.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request

from egon2.agents.registry import AgentRegistry
from egon2.core.agent_dispatcher import AgentDispatcher
from egon2.core.context_manager import ContextManager
from egon2.core.message_queue import Channel, IncomingMessage, MessageConsumer, MessageQueue
from egon2.core.scheduler import EgonScheduler
from egon2.core.task_manager import TaskManager
from egon2.database import Database
from egon2.executors.shell_executor import ShellExecutor
from egon2.executors.ssh_executor import SSHExecutor
from egon2.interfaces.matrix_bot import MatrixBot
from egon2.interfaces.telegram_bot import TelegramBot
from egon2.llm_client import LLMClient
from egon2.settings import get_settings
from egon2.state import AppState


# --- Logging-Setup -----------------------------------------------------------


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()


# --- Lifespan ---------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    settings = get_settings()
    state = AppState(settings=settings)
    app.state.egon = state

    # Stufe 1 — DB + WAL + Migrationen
    state.db = Database(settings.db_path)
    await state.db.init()
    logger.info("startup.db_ready", path=str(settings.db_path))

    # Stufe 2 — recover_orphaned
    n = await state.db.recover_orphaned()
    if n:
        logger.info("startup.recovered_orphans", count=n)

    # Stufe 3 — Knowledge-Client (Phase 3)
    state.knowledge = None

    # Stufe 4 — LLM-Client + Verbindungstest
    state.llm = LLMClient(settings)
    ok = await state.llm.ping()
    if not ok:
        logger.warning("startup.llm_unreachable", url=settings.llm_api_url)
    else:
        logger.info("startup.llm_ok", url=settings.llm_api_url)

    # Stufe 5 — Executors + Queue + Manager + Dispatcher + Consumer
    state.ssh_executor = SSHExecutor(
        key_path=Path(settings.ssh_key_path),
        known_hosts=Path(settings.ssh_known_hosts) if settings.ssh_known_hosts else None,
    )
    state.shell_executor = ShellExecutor(cwd=settings.data_dir.parent / "work")
    logger.info("startup.executors_ready", ssh_key=settings.ssh_key_path)

    state.queue = MessageQueue(maxsize=settings.message_queue_maxsize)
    state.tasks = TaskManager(state.db)
    state.registry = AgentRegistry(state.db)
    state.context = ContextManager(state.db, knowledge_client=state.knowledge)
    state.dispatcher = AgentDispatcher(
        db=state.db,
        llm=state.llm,
        tasks=state.tasks,
        registry=state.registry,
        context=state.context,
        ssh_executor=state.ssh_executor,
    )

    async def _typing_loop(msg: IncomingMessage) -> None:
        """Sendet alle 4 s einen Typing-Indicator bis zur Cancellation."""
        while True:
            try:
                if msg.channel == Channel.MATRIX and state.matrix_bot:
                    await state.matrix_bot.send_typing(msg.chat_id)
                elif msg.channel == Channel.TELEGRAM and state.telegram_bot:
                    await state.telegram_bot.send_typing(msg.chat_id)
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(4)

    async def _progress_loop(msg: IncomingMessage) -> None:
        """Sendet alle 20 s ein '.' als Lebenszeichen bei langen LLM-Calls."""
        await asyncio.sleep(20)
        while True:
            try:
                if msg.channel == Channel.MATRIX and state.matrix_bot:
                    await state.matrix_bot.send_message(msg.chat_id, ".")
                elif msg.channel == Channel.TELEGRAM and state.telegram_bot:
                    await state.telegram_bot.send_message(msg.chat_id, ".")
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(20)

    async def dispatch_and_reply(msg: IncomingMessage) -> None:
        assert state.dispatcher is not None
        typing_task = asyncio.create_task(_typing_loop(msg), name="typing-loop")
        progress_task = asyncio.create_task(_progress_loop(msg), name="progress-dots")
        try:
            reply = await state.dispatcher.handle(msg)
        finally:
            typing_task.cancel()
            progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing_task
            with contextlib.suppress(asyncio.CancelledError):
                await progress_task
        try:
            if msg.channel == Channel.MATRIX and state.matrix_bot:
                await state.matrix_bot.send_message(msg.chat_id, reply)
            elif msg.channel == Channel.TELEGRAM and state.telegram_bot:
                await state.telegram_bot.send_message(msg.chat_id, reply)
        except Exception:  # noqa: BLE001
            logger.exception("dispatch.send_failed", channel=msg.channel.value)

    state.consumer = MessageConsumer(
        queue=state.queue,
        dispatch_fn=dispatch_and_reply,
        sem_size=settings.consumer_semaphore_size,
    )

    # Stufe 6 — Matrix-Bot
    state.matrix_bot = MatrixBot(settings, state.queue)
    try:
        await state.matrix_bot.start()
        logger.info("startup.matrix_started", enabled=settings.matrix_enabled)
    except Exception as exc:  # noqa: BLE001
        logger.warning("startup.matrix_failed", error=str(exc))

    # Stufe 7 — Telegram-Bot
    state.telegram_bot = TelegramBot(settings, state.queue)
    try:
        await state.telegram_bot.initialize()
        await state.telegram_bot.start()
        await state.telegram_bot.start_polling()
        logger.info("startup.telegram_started", enabled=settings.telegram_enabled)
    except Exception as exc:  # noqa: BLE001
        logger.warning("startup.telegram_failed", error=str(exc))

    # Stufe 8 — Consumer
    await state.consumer.start()
    logger.info("startup.consumer_started")

    # Stufe 9 — Scheduler
    state.scheduler = EgonScheduler(settings.scheduler_db_path)
    state.scheduler.start()

    from egon2.jobs.news_report import register_jobs
    from egon2.jobs.bookstack_sync import register_bookstack_sync
    from egon2.jobs.mikrotik_update import register_mikrotik_update
    register_jobs(state.scheduler, app)
    register_bookstack_sync(state.scheduler, app)
    register_mikrotik_update(state.scheduler, app)

    # Onboarding-Hinweis im Log
    if not await state.db.has_any_assistant_message():
        logger.info("startup.first_run", onboarding_ready=True)

    logger.info(
        "startup.complete",
        matrix=settings.matrix_enabled,
        telegram=settings.telegram_enabled,
    )

    try:
        yield
    finally:
        # === SHUTDOWN (spiegelverkehrt) ===
        if state.scheduler:
            try:
                state.scheduler.shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.scheduler_failed")
        if state.matrix_bot:
            try:
                await state.matrix_bot.stop()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.matrix_failed")
        if state.telegram_bot:
            try:
                await state.telegram_bot.stop()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.telegram_failed")
        if state.consumer:
            try:
                await state.consumer.stop()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.consumer_failed")
        if state.ssh_executor:
            try:
                await state.ssh_executor.aclose()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.ssh_executor_failed")
        if state.llm:
            try:
                await state.llm.aclose()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.llm_failed")
        if state.db:
            try:
                await state.db.checkpoint_and_close()
            except Exception:  # noqa: BLE001
                logger.exception("shutdown.db_failed")
        logger.info("shutdown.complete")


# --- App --------------------------------------------------------------------


app = FastAPI(title="Egon2", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> dict[str, bool]:
    state: AppState = request.app.state.egon
    return {
        "db": state.db is not None,
        "llm": state.llm is not None,
        "queue": state.queue is not None,
        "consumer": state.consumer is not None,
    }


@app.post("/admin/jobs/run/{job_name}")
async def run_job_now(job_name: str, request: Request) -> dict[str, str]:
    """Manueller Job-Trigger für Entwicklung/Debug."""
    if job_name == "news_report":
        from egon2.jobs.news_report import news_report_job
        asyncio.create_task(news_report_job(), name=f"manual_{job_name}")
        return {"status": "triggered", "job": job_name}
    return {"status": "unknown_job", "job": job_name}


__all__ = ["app", "lifespan"]
