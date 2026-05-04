"""Matrix-Bot für Egon2 (matrix-nio, async).

Soft-fail wenn `settings.matrix_password` leer ist — Egon läuft dann ohne
Matrix-Anbindung weiter (Telegram bleibt aktiv). Federation-Hardening:
nur Sender und Räume des eigenen Homeservers werden akzeptiert.

Siehe `docs/LLD-Interfaces.md` §2 für die vollständige Spezifikation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from egon2.core.message_queue import (
    Channel,
    IncomingMessage,
    MessageQueue,
    safe_wrap,
)
from egon2.exceptions import MatrixSendError
from egon2.settings import Settings

try:  # matrix-nio ist eine optionale Dependency zur Laufzeit (für Tests)
    from nio import (  # type: ignore[import-untyped]
        AsyncClient,
        AsyncClientConfig,
        InviteMemberEvent,
        LoginResponse,
        MatrixRoom,
        RoomMessageText,
    )
except ImportError:  # pragma: no cover
    AsyncClient = None  # type: ignore[assignment,misc]
    AsyncClientConfig = None  # type: ignore[assignment,misc]
    InviteMemberEvent = None  # type: ignore[assignment,misc]
    LoginResponse = None  # type: ignore[assignment,misc]
    MatrixRoom = None  # type: ignore[assignment,misc]
    RoomMessageText = None  # type: ignore[assignment,misc]


logger = logging.getLogger(__name__)


class MatrixBot:
    """Async Matrix-Bot mit Reconnect-Loop und Federation-Hardening."""

    def __init__(self, settings: Settings, queue: MessageQueue) -> None:
        self._settings = settings
        self._queue = queue
        self._client: AsyncClient | None = None  # type: ignore[valid-type]
        self._sync_task: asyncio.Task[None] | None = None
        self._enabled: bool = settings.matrix_enabled
        self._running: bool = False
        # Federation-Hardening: Suffix aus matrix_user_id ableiten (@user:server → :server)
        uid = settings.matrix_user_id
        self._hs_suffix: str = (":" + uid.split(":", 1)[1]) if ":" in uid else ""

    # --- Status ------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._enabled

    def is_connected(self) -> bool:
        return (
            self._enabled
            and self._running
            and self._client is not None
            and getattr(self._client, "logged_in", False)
        )

    # --- Lifecycle ---------------------------------------------------------

    async def start(self) -> None:
        """Login + Initial-Sync + Background-Sync-Task starten.

        Bevorzugt Access-Token-Login (restore_login), fällt auf Passwort zurück.
        Soft-fail wenn weder Token noch Passwort konfiguriert.
        """
        if not self._enabled:
            logger.warning(
                "matrix.disabled — weder Access-Token noch Passwort konfiguriert."
            )
            return
        if AsyncClient is None:  # pragma: no cover
            logger.warning("matrix.disabled — matrix-nio nicht installiert.")
            self._enabled = False
            return

        config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=False,
        )
        self._client = AsyncClient(
            homeserver=self._settings.matrix_homeserver,
            user=self._settings.matrix_user_id,
            device_id=self._settings.matrix_device_id or None,
            config=config,
        )

        if self._settings.matrix_access_token:
            # Access-Token-Login: kein neues Login, Session bleibt erhalten
            self._client.restore_login(
                user_id=self._settings.matrix_user_id,
                device_id=self._settings.matrix_device_id,
                access_token=self._settings.matrix_access_token,
            )
            logger.info("matrix.restored_login device=%s", self._settings.matrix_device_id)
        else:
            # Fallback: Passwort-Login
            resp = await self._client.login(
                self._settings.matrix_password,
                device_name=self._settings.matrix_device_name,
            )
            if LoginResponse is None or not isinstance(resp, LoginResponse):
                logger.error("matrix.login_failed: %s", resp)
                self._enabled = False
                await self._client.close()
                self._client = None
                return
            logger.info("matrix.password_login ok")

        # Initial-Sync VOR Callback-Registrierung — sonst flutet die History
        # die Queue beim Erststart.
        await self._client.sync(timeout=10_000, full_state=False)

        # Erst NACH dem Initial-Sync Callbacks registrieren.
        self._client.add_event_callback(self._on_room_message, RoomMessageText)
        self._client.add_event_callback(self._on_invite, InviteMemberEvent)

        self._running = True
        self._sync_task = asyncio.create_task(
            self._sync_forever(), name="matrix-sync"
        )
        logger.info("matrix.started user=%s", self._settings.matrix_user_id)

    async def stop(self) -> None:
        """Sync-Task canceln, Client schließen."""
        self._running = False
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                logger.exception("matrix.sync_task crashed during stop")
            self._sync_task = None
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                logger.exception("matrix.close failed (suppressed)")
            self._client = None

    # --- Outgoing ----------------------------------------------------------

    async def send_typing(self, room_id: str) -> None:
        """Sendet einen Typing-Indicator (5 s Fenster). Fehler werden unterdrückt."""
        if self._client is None or not self._running:
            return
        try:
            await self._client.room_typing(room_id, typing_state=True, timeout=5000)
        except Exception:  # noqa: BLE001
            pass

    async def send_message(self, room_id: str, text: str) -> None:
        """Sendet eine Textnachricht an einen Raum.

        Bei Fehler wird `MatrixSendError` geloggt — kein Re-Raise, sonst
        würde ein einzelner Sende-Fehler den Consumer-Task abreißen.
        """
        if self._client is None or not self._running:
            logger.warning("matrix.send.skipped — bot not running room=%s", room_id)
            return
        try:
            await self._client.room_send(
                room_id=room_id,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": text},
                ignore_unverified_devices=True,
            )
        except Exception as exc:  # noqa: BLE001
            err = MatrixSendError(f"send to {room_id} failed: {exc}")
            logger.error("matrix.send_error: %s", err)

    # --- Callbacks ---------------------------------------------------------

    async def _on_room_message(
        self,
        room: "MatrixRoom",  # type: ignore[valid-type]
        event: "RoomMessageText",  # type: ignore[valid-type]
    ) -> None:
        """Filtert eingehende Raum-Nachrichten und legt sie in die Queue."""
        if self._client is None:
            return
        logger.info(
            "matrix.msg.received sender=%s room=%s text=%.60r",
            event.sender, room.room_id, event.body or "",
        )
        # Eigene Echo-Nachrichten ignorieren
        if event.sender == self._settings.matrix_user_id:
            logger.debug("matrix.msg.echo_skipped sender=%s", event.sender)
            return
        # Federation-Hardening: nur eigener Homeserver
        if not event.sender.endswith(self._hs_suffix):
            logger.warning(
                "matrix.msg.foreign_homeserver sender=%s", event.sender
            )
            return
        if not room.room_id.endswith(self._hs_suffix):
            logger.warning(
                "matrix.msg.foreign_room room=%s sender=%s",
                room.room_id,
                event.sender,
            )
            return

        raw = event.body or ""
        ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        msg = IncomingMessage(
            channel=Channel.MATRIX,
            chat_id=room.room_id,
            user_id=event.sender,
            raw_text=raw,
            wrapped_text=safe_wrap("matrix", raw),
            ts_ms=ts_ms,
            metadata={"event_id": getattr(event, "event_id", "")},
        )
        ok = await self._queue.put(msg)
        if not ok:
            await self.send_message(
                room.room_id,
                "Bin gerade ausgelastet — kurz später nochmal.",
            )

    async def _on_invite(
        self,
        room: "MatrixRoom",  # type: ignore[valid-type]
        event: "InviteMemberEvent",  # type: ignore[valid-type]
    ) -> None:
        """Joint nur Räume des eigenen Homeservers, eingeladen vom eigenen HS."""
        if self._client is None:
            return
        if event.state_key != self._settings.matrix_user_id:
            return
        if not (
            event.sender.endswith(self._hs_suffix)
            and room.room_id.endswith(self._hs_suffix)
        ):
            logger.warning(
                "matrix.invite.rejected room=%s by=%s", room.room_id, event.sender
            )
            try:
                await self._client.room_leave(room.room_id)
            except Exception:  # noqa: BLE001
                logger.exception("matrix.invite.leave failed")
            return
        try:
            await self._client.join(room.room_id)
            logger.info(
                "matrix.invite.joined room=%s by=%s", room.room_id, event.sender
            )
        except Exception:  # noqa: BLE001
            logger.exception("matrix.invite.join failed room=%s", room.room_id)

    # --- Sync-Loop ---------------------------------------------------------

    async def _sync_forever(self) -> None:
        """Endlos-Sync mit exponentiellem Backoff bei Fehlern."""
        assert self._client is not None
        backoff = 1.0
        while self._running:
            try:
                await self._client.sync_forever(
                    timeout=30_000, full_state=False
                )
                backoff = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "matrix.sync.error: %s (backoff=%.1fs)", exc, backoff
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 60.0)


__all__ = ["MatrixBot"]
