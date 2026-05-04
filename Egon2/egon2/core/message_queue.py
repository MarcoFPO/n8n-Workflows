"""Message-Queue und Consumer für Egon2.

Definiert das `IncomingMessage`-Datenmodell, die `Channel`-Enum, eine
async `MessageQueue` mit Backpressure (non-blocking put → False bei voll)
sowie einen `MessageConsumer`, der Messages mit beschränkter Parallelität
(Semaphore) abarbeitet.

Siehe `docs/LLD-Core.md` §1.2/1.3/1.6.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class Channel(StrEnum):
    """Eingangskanäle für Messages."""

    MATRIX = "matrix"
    TELEGRAM = "telegram"
    SCHEDULER = "scheduler"


@dataclass(slots=True, frozen=True)
class IncomingMessage:
    """Eine eingegangene Nachricht aus einem Interface.

    Attributes:
        channel: Eingangskanal (Matrix / Telegram / Scheduler).
        chat_id: Matrix `room_id` oder Telegram `chat_id` — IMMER als String.
        user_id: Eindeutige User-ID des Senders.
        raw_text: Original-Text (ungewrapped) — nötig für Cancel-Erkennung
            und `/status`-Anzeige im UI.
        wrapped_text: Über `safe_wrap()` neutralisierter Text für LLM-Calls.
        ts_ms: Zeitstempel in Millisekunden seit Epoch (UTC).
        message_id: Eindeutige interne ID (16 Hex-Zeichen).
        metadata: Freier Metadaten-Slot (z. B. `forwarded`, `reply_to`).
    """

    channel: Channel
    chat_id: str
    user_id: str
    raw_text: str
    wrapped_text: str
    ts_ms: int
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    metadata: dict[str, Any] = field(default_factory=dict)


def safe_wrap(source: str, content: str) -> str:
    """Kapselt externen Content in `<external source="...">…</external>`.

    Vorhandene `<external>`-Tags werden vorher neutralisiert (M10-Fix),
    damit Prompt-Injection durch eingeschleuste Tags nicht möglich ist.
    """
    content = content.replace("<external", "[external").replace(
        "</external>", "[/external]"
    )
    return f'<external source="{source}">{content}</external>'


class MessageQueue:
    """Async-Queue mit Backpressure.

    `put()` ist non-blocking und liefert `False`, wenn die Queue voll ist —
    Caller (Bots) loggen dann eine 'overload'-Warnung und droppen ggf. die
    Nachricht oder antworten dem User mit einer Fehlermeldung.
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._q: asyncio.Queue[IncomingMessage] = asyncio.Queue(maxsize=maxsize)

    async def put(self, msg: IncomingMessage) -> bool:
        """Non-blocking put. Returns False wenn die Queue voll ist."""
        try:
            self._q.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            return False

    async def get(self) -> IncomingMessage:
        """Blockierendes Lesen — wird vom Consumer-Loop benutzt."""
        return await self._q.get()

    def task_done(self) -> None:
        """Signalisiert der Queue, dass eine Message vollständig verarbeitet wurde."""
        self._q.task_done()

    def qsize(self) -> int:
        return self._q.qsize()

    def is_full(self) -> bool:
        return self._q.full()


class MessageConsumer:
    """Verarbeitet Messages aus der `MessageQueue`.

    Beschränkt die maximale Parallelität auf `sem_size` (default 3) — so
    überlasten wir den LLM-Wrapper nicht. Der eigentliche Dispatcher ist
    von außen injiziert (`dispatch_fn`), damit dieses Modul zirkulär-frei
    bleibt.
    """

    def __init__(
        self,
        queue: MessageQueue,
        dispatch_fn: Callable[[IncomingMessage], Coroutine[Any, Any, Any]],
        sem_size: int = 3,
    ) -> None:
        self._queue = queue
        self._dispatch_fn = dispatch_fn
        self._sem = asyncio.Semaphore(sem_size)
        self._running_tasks: set[asyncio.Task[Any]] = set()
        self._stopping = False
        self._loop_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Startet den Consumer-Loop als Task."""
        if self._loop_task is not None:
            raise RuntimeError("MessageConsumer already started")
        self._loop_task = asyncio.create_task(self._run(), name="msg-consumer")

    async def stop(self) -> None:
        """Stoppt den Consumer und awaitet alle laufenden Handler.

        WICHTIG: kein `queue.join()` — wir warten ausschließlich auf
        `_running_tasks` (K2-Fix). Sonst würde `join()` ewig hängen,
        falls eine Message nie `task_done()` aufruft.
        """
        self._stopping = True
        if self._loop_task is not None:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        if self._running_tasks:
            await asyncio.gather(*list(self._running_tasks), return_exceptions=True)

    async def _run(self) -> None:
        """Dauerschleife: holt Messages und feuert Handler-Tasks ab."""
        while not self._stopping:
            try:
                msg = await self._queue.get()
            except asyncio.CancelledError:
                # Safety: task_done auch bei Cancel — Queue-Counter sauber halten.
                # Wenn `get()` gecancelt wird, war noch keine Message gezogen,
                # daher KEIN task_done() hier (würde ValueError werfen).
                raise
            t = asyncio.create_task(
                self._handle(msg), name=f"handle-{msg.message_id}"
            )
            self._running_tasks.add(t)
            t.add_done_callback(self._running_tasks.discard)

    async def _handle(self, msg: IncomingMessage) -> None:
        """Führt den Dispatcher unter Semaphore aus, fängt Fehler weich."""
        async with self._sem:
            try:
                await self._dispatch_fn(msg)
            except Exception:  # noqa: BLE001 — Dispatcher loggt selbst.
                logger.exception(
                    "Dispatcher raised for message %s (channel=%s)",
                    msg.message_id,
                    msg.channel,
                )
            finally:
                self._queue.task_done()
