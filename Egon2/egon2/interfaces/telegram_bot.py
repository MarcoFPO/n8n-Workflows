"""Telegram-Bot für Egon2 (python-telegram-bot v21).

Soft-fail wenn `settings.telegram_token` leer ist — Egon läuft dann ohne
Telegram-Anbindung weiter. Whitelist via `settings.telegram_whitelist`
(Liste numerischer User-IDs).

Wichtig: `Application.run_polling()` wird NICHT verwendet (zerstört den
FastAPI-Lifespan). Stattdessen explizites Lifecycle:
  initialize → start → updater.start_polling
und spiegelbildlich beim Shutdown.

Single-User: `concurrent_updates(False)` — sequenzielle Verarbeitung
ist ausreichend; vereinfacht Backpressure (Finding K5).

Siehe `docs/LLD-Interfaces.md` §3 für die vollständige Spezifikation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from egon2.core.message_queue import (
    Channel,
    IncomingMessage,
    MessageQueue,
    safe_wrap,
)
from egon2.exceptions import TelegramSendError
from egon2.settings import Settings

try:  # python-telegram-bot v21
    from telegram import Update  # type: ignore[import-untyped]
    from telegram.constants import ChatAction  # type: ignore[import-untyped]
    from telegram.ext import (  # type: ignore[import-untyped]
        Application,
        ApplicationBuilder,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
except ImportError:  # pragma: no cover
    ChatAction = None  # type: ignore[assignment,misc]
    Update = None  # type: ignore[assignment,misc]
    Application = None  # type: ignore[assignment,misc]
    ApplicationBuilder = None  # type: ignore[assignment,misc]
    CommandHandler = None  # type: ignore[assignment,misc]
    ContextTypes = None  # type: ignore[assignment,misc]
    MessageHandler = None  # type: ignore[assignment,misc]
    filters = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class TelegramBot:
    """Async Telegram-Bot mit explizitem Lifecycle (PTB v21)."""

    def __init__(self, settings: Settings, queue: MessageQueue) -> None:
        self._settings = settings
        self._queue = queue
        self._app: Application | None = None  # type: ignore[valid-type]
        self._enabled: bool = bool(settings.telegram_token)
        self._whitelist: frozenset[int] = frozenset(settings.telegram_whitelist)
        self._running: bool = False

    # --- Status ------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    def is_running(self) -> bool:
        return self._running

    # --- Lifecycle ---------------------------------------------------------

    async def initialize(self) -> None:
        """Application-Builder konfigurieren, Handler registrieren, initialisieren."""
        if not self._enabled:
            logger.warning(
                "telegram.disabled — kein Token konfiguriert, Telegram-Bot startet nicht."
            )
            return
        if ApplicationBuilder is None:  # pragma: no cover
            logger.warning("telegram.disabled — python-telegram-bot nicht installiert.")
            self._enabled = False
            return

        self._app = (
            ApplicationBuilder()
            .token(self._settings.telegram_token)
            .concurrent_updates(False)  # K5: Single-User, sequenzielles Dispatch
            .build()
        )
        self._register_handlers()
        await self._app.initialize()

    async def start(self) -> None:
        """Application starten (NICHT polling — das macht `start_polling`)."""
        if not self._enabled or self._app is None:
            return
        await self._app.start()
        self._running = True

    async def start_polling(self) -> None:
        """Updater-Polling starten — drop_pending_updates.

        Bei manueller Lifecycle-Steuerung (initialize→start→start_polling)
        registriert PTB keine eigenen Signal-Handler — stop_signals existiert
        nur auf Application.run_polling(), nicht auf Updater.start_polling().
        """
        if not self._enabled or self._app is None:
            return
        await self._app.updater.start_polling(
            allowed_updates=["message"],
            drop_pending_updates=True,
        )

    async def stop(self) -> None:
        """Spiegelbildlich zur Startup: updater → app stop → app shutdown."""
        if not self._enabled or self._app is None:
            return
        try:
            if self._app.updater is not None and self._app.updater.running:
                await self._app.updater.stop()
        except Exception:  # noqa: BLE001
            logger.exception("telegram.updater.stop failed (suppressed)")
        try:
            await self._app.stop()
        except Exception:  # noqa: BLE001
            logger.exception("telegram.app.stop failed (suppressed)")
        try:
            await self._app.shutdown()
        except Exception:  # noqa: BLE001
            logger.exception("telegram.app.shutdown failed (suppressed)")
        self._running = False

    # --- Outgoing ----------------------------------------------------------

    async def send_typing(self, chat_id: str | int) -> None:
        """Sendet `typing…`-Indicator (~5 s). Fehler werden unterdrückt."""
        if not self._enabled or self._app is None or ChatAction is None:
            return
        try:
            await self._app.bot.send_chat_action(
                chat_id=chat_id, action=ChatAction.TYPING
            )
        except Exception:  # noqa: BLE001
            pass

    async def send_message(self, chat_id: str | int, text: str) -> None:
        """Sendet eine Textnachricht. Bei Fehler: `TelegramSendError` loggen."""
        if not self._enabled or self._app is None:
            logger.warning("telegram.send.skipped — bot not running chat=%s", chat_id)
            return
        try:
            await self._app.bot.send_message(chat_id=chat_id, text=text)
        except Exception as exc:  # noqa: BLE001
            err = TelegramSendError(f"send to {chat_id} failed: {exc}")
            logger.error("telegram.send_error: %s", err)

    # --- Handler-Registrierung --------------------------------------------

    def _register_handlers(self) -> None:
        assert self._app is not None
        self._app.add_handler(CommandHandler("status", self._on_status))
        self._app.add_handler(CommandHandler("hilfe", self._on_hilfe))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
        )

    # --- Handler -----------------------------------------------------------

    async def _on_text(
        self,
        update: "Update",  # type: ignore[valid-type]
        context: "ContextTypes.DEFAULT_TYPE",  # type: ignore[valid-type]
    ) -> None:
        """Free-Text-Handler: Whitelist prüfen, Forward-Detection, IncomingMessage."""
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message
        if user is None or chat is None or message is None:
            return
        if user.id not in self._whitelist:
            logger.warning("telegram.unauthorized user_id=%s", user.id)
            return

        raw = message.text or ""
        # Forwarded-Detection (Finding M3): erlaubt es dem Consumer,
        # Cancel-Intent bei weitergeleiteten Texten zu unterdrücken.
        forwarded = getattr(message, "forward_origin", None) is not None
        metadata: dict[str, object] = {"forwarded": forwarded}
        if forwarded:
            metadata["forwarded_from"] = str(message.forward_origin)

        ts_ms = (
            int(message.date.replace(tzinfo=timezone.utc).timestamp() * 1000)
            if message.date is not None
            else int(datetime.now(timezone.utc).timestamp() * 1000)
        )

        msg = IncomingMessage(
            channel=Channel.TELEGRAM,
            chat_id=str(chat.id),
            user_id=str(user.id),
            raw_text=raw,
            wrapped_text=safe_wrap("telegram", raw),
            ts_ms=ts_ms,
            metadata=metadata,
        )
        ok = await self._queue.put(msg)
        if not ok:
            try:
                await message.reply_text(
                    "Gerade ausgelastet — kurz später nochmal."
                )
            except Exception:  # noqa: BLE001
                logger.exception("telegram.backpressure_reply failed")

    async def _on_status(
        self,
        update: "Update",  # type: ignore[valid-type]
        context: "ContextTypes.DEFAULT_TYPE",  # type: ignore[valid-type]
    ) -> None:
        """`/status`-Slash-Command. Phase-1: knapper Health-Hinweis."""
        if update.effective_user is None or update.effective_message is None:
            return
        if update.effective_user.id not in self._whitelist:
            return
        await update.effective_message.reply_text(
            "Egon ist da. Queue-Größe: %d." % self._queue.qsize()
        )

    async def _on_hilfe(
        self,
        update: "Update",  # type: ignore[valid-type]
        context: "ContextTypes.DEFAULT_TYPE",  # type: ignore[valid-type]
    ) -> None:
        """`/hilfe`-Slash-Command. Phase-1: kurzer Befehlsüberblick."""
        if update.effective_user is None or update.effective_message is None:
            return
        if update.effective_user.id not in self._whitelist:
            return
        text = (
            "Was ich kann:\n"
            "  /status   — kurzer Lebenszeichen-Check\n"
            "  /hilfe    — diese Übersicht\n"
            "Sonst: schick einfach Text. Ich kümmere mich darum."
        )
        await update.effective_message.reply_text(text)


__all__ = ["TelegramBot"]
