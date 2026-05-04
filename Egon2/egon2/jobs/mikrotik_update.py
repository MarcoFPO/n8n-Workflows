"""Wöchentlicher MikroTik RouterOS Update Job.

Verbindet sich sequenziell via SSH (Passwort-Auth) zu jedem konfigurierten
MikroTik-Gerät, setzt den Update-Kanal auf 'stable' und startet das Upgrade.
Nach dem Installieren trennt RouterOS die Verbindung (Neustart) — das ist
erwartetes Verhalten und wird als Erfolg gewertet.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import asyncssh

from egon2.core.scheduler import EgonScheduler

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

_app: "FastAPI | None" = None

MIKROTIK_HOSTS: list[str] = [
    "10.100.1.1",
    "10.100.1.3",
    "10.100.1.5",
    "10.100.1.6",
    "10.100.1.7",
    "10.100.1.8",
]

_SSH_USER = "claude"
_SSH_PASSWORD = "claude"
_CONNECT_TIMEOUT = 20.0
_CMD_TIMEOUT = 30.0
_INTER_DEVICE_PAUSE = 60  # Sekunden Pause nach jedem Gerät (Neustart abwarten)


async def _run_cmd(conn: asyncssh.SSHClientConnection, cmd: str) -> str:
    result = await asyncio.wait_for(
        conn.run(cmd, check=False),
        timeout=_CMD_TIMEOUT,
    )
    return ((result.stdout or "") + (result.stderr or "")).strip()


async def _update_device(host: str) -> tuple[str, bool]:
    """Führt RouterOS-Upgrade auf einem Gerät durch.

    Returns: (status_text, success)
    """
    try:
        async with asyncssh.connect(
            host,
            username=_SSH_USER,
            password=_SSH_PASSWORD,
            known_hosts=None,
            connect_timeout=_CONNECT_TIMEOUT,
        ) as conn:
            # Aktuell installierte Version ermitteln
            ver_out = await _run_cmd(conn, "/system resource print")
            current = ""
            for line in ver_out.splitlines():
                if "version" in line.lower():
                    current = line.strip()
                    break

            # Kanal auf stable setzen + Update-Check anstoßen
            await _run_cmd(conn, "/system package update set channel=stable")
            await asyncio.sleep(2)
            check_out = await _run_cmd(conn, "/system package update check-for-updates")
            await asyncio.sleep(3)

            # Update-Status abfragen
            status_out = await _run_cmd(conn, "/system package update print")
            combined = (check_out + "\n" + status_out).lower()

            installed = ""
            latest = ""
            for line in (check_out + "\n" + status_out).splitlines():
                ll = line.lower()
                if "installed-version" in ll or "installed version" in ll:
                    installed = line.strip()
                if "latest-version" in ll or "latest version" in ll:
                    latest = line.strip()

            if "status: system is already up to date" in combined or \
               ("installed" in combined and "latest" in combined and
                    _same_version(installed, latest)):
                return (
                    f"{host}: Bereits aktuell — {current}",
                    True,
                )

            # Upgrade starten
            await _run_cmd(conn, "/system package update install")
            return (
                f"{host}: Upgrade gestartet — {current} → {latest or '?'}",
                True,
            )

    except (asyncssh.DisconnectError, asyncssh.ConnectionLost, ConnectionResetError):
        # RouterOS trennt Verbindung sofort nach "install" (Neustart) — erwartet
        return (f"{host}: Upgrade angestoßen (Verbindung getrennt — Neustart)", True)
    except TimeoutError:
        return (f"{host}: Verbindungs-Timeout ({_CONNECT_TIMEOUT:.0f}s)", False)
    except asyncssh.PermissionDenied:
        return (f"{host}: SSH-Authentifizierung fehlgeschlagen", False)
    except Exception as exc:  # noqa: BLE001
        return (f"{host}: Fehler — {exc}", False)


def _same_version(installed: str, latest: str) -> bool:
    """Grober Versionsvergleich — True wenn gleiche Versionsnummer."""
    def _extract(s: str) -> str:
        for part in s.split():
            if part[0].isdigit():
                return part.rstrip(";:,")
        return s

    iv = _extract(installed)
    lv = _extract(latest)
    return bool(iv and lv and iv == lv)


async def _log_run(db, status: str, output: str, started_at: str) -> None:
    try:
        async with db.connection() as conn:
            await conn.execute(
                "INSERT INTO scheduler_log "
                "(id, job_name, started_at, finished_at, status, output) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    "mikrotik_weekly_update",
                    started_at,
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    output[:4000],
                ),
            )
            await conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("mikrotik_update.log_failed err=%s", exc)


async def mikrotik_update_job() -> None:
    """Wöchentlicher MikroTik RouterOS Update — sequenziell über alle Hosts."""
    if _app is None:
        logger.warning("mikrotik_update.no_app_state")
        return

    started_at = datetime.now(timezone.utc).isoformat()
    state = getattr(_app.state, "egon", None)
    if state is None or state.db is None:
        logger.warning("mikrotik_update.state_unavailable")
        return

    settings = state.settings

    async def _notify(text: str) -> None:
        try:
            matrix_room = settings.news_report_matrix_room
            if matrix_room and state.matrix_bot and settings.matrix_enabled:
                await state.matrix_bot.send_message(matrix_room, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mikrotik_update.matrix_notify_failed err=%s", exc)
        try:
            tg_chat = settings.news_report_telegram_chat
            if tg_chat and state.telegram_bot and settings.telegram_enabled:
                await state.telegram_bot.send_message(tg_chat, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mikrotik_update.telegram_notify_failed err=%s", exc)

    logger.info("mikrotik_update.started hosts=%d", len(MIKROTIK_HOSTS))
    await _notify(
        f"MikroTik Update-Runde gestartet — {len(MIKROTIK_HOSTS)} Geräte sequenziell"
    )

    results: list[tuple[str, bool]] = []
    for i, host in enumerate(MIKROTIK_HOSTS):
        logger.info("mikrotik_update.processing host=%s (%d/%d)", host, i + 1, len(MIKROTIK_HOSTS))
        status_text, ok = await _update_device(host)
        results.append((status_text, ok))
        logger.info("mikrotik_update.result ok=%s text=%s", ok, status_text)

        if i < len(MIKROTIK_HOSTS) - 1:
            await asyncio.sleep(_INTER_DEVICE_PAUSE)

    ok_count = sum(1 for _, ok in results if ok)
    fail_count = len(results) - ok_count
    lines = "\n".join(
        f"{'OK' if ok else 'FEHLER'} {text}" for text, ok in results
    )
    summary = (
        f"MikroTik Update abgeschlossen — {ok_count}/{len(results)} OK\n\n{lines}"
    )
    await _notify(summary)

    status = "done" if fail_count == 0 else "partial"
    await _log_run(state.db, status, summary, started_at)
    logger.info("mikrotik_update.done ok=%d fail=%d", ok_count, fail_count)


def register_mikrotik_update(scheduler: EgonScheduler, app: "FastAPI") -> None:
    global _app
    _app = app
    if scheduler.scheduler is None:
        logger.warning("mikrotik_update.scheduler_not_started")
        return
    scheduler.scheduler.add_job(
        mikrotik_update_job,
        "cron",
        day_of_week="sun",
        hour=3,
        minute=0,
        timezone="Europe/Berlin",
        id="mikrotik_weekly_update",
        replace_existing=True,
    )
    logger.info("mikrotik_update.registered cron=Sun_03:00")


__all__ = ["mikrotik_update_job", "register_mikrotik_update"]
