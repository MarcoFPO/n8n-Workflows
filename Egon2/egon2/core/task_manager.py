"""TaskManager — State-Machine + CRUD für die `tasks`-Tabelle.

Siehe LLD-Core §3 für die vollständige Spezifikation. Diese Implementierung
deckt den Single-User-Pragmatik-Pfad ab:
- Optimistic Locking via `WHERE status = ?` im UPDATE-Statement.
- Erlaubte Übergänge gemäß §3.2.
- `cancelled_reason` wird beim Cancel persistiert (F7).
"""

from __future__ import annotations

import logging
from typing import Final
from uuid import uuid4

from egon2.database import Database, iso_utc_now
from egon2.exceptions import (
    InvalidTaskTransitionError,
    TaskNotFoundError,
)

logger = logging.getLogger(__name__)


# Erlaubte Übergänge — Quelle = §3.2 (LLD-Core).
_ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "pending": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"done", "failed", "cancelled", "waiting_approval"}),
    "waiting_approval": frozenset({"running", "failed", "cancelled"}),
    # Terminal:
    "done": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


class TaskManager:
    """State-Machine + CRUD für Tasks.

    Alle Methoden sind async, alle Transitionen verwenden Optimistic Locking:
    Das UPDATE-Statement enthält den **alten** Status als zusätzliche WHERE-
    Bedingung; betrifft das UPDATE 0 Zeilen, prüft die Methode den aktuellen
    Status und wirft `TaskNotFoundError` oder `InvalidTaskTransitionError`.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        title: str,
        description: str = "",
        source_channel: str = "matrix",
        request_id: str | None = None,
        parent_task_id: str | None = None,
    ) -> str:
        """Legt einen neuen Task im Status `pending` an. Gibt die ID zurück."""
        task_id = uuid4().hex
        now = iso_utc_now()
        async with self._db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (
                    id, title, description, source_channel, status,
                    parent_task_id, request_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    task_id,
                    title,
                    description,
                    source_channel,
                    parent_task_id,
                    request_id,
                    now,
                    now,
                ),
            )
            await conn.commit()
        logger.debug("task created id=%s title=%r", task_id, title[:60])
        return task_id

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get(self, task_id: str) -> dict | None:
        """Liefert den Task als Dict, oder None falls nicht vorhanden."""
        async with self._db.connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = await cur.fetchone()
            await cur.close()
            return dict(row) if row else None

    async def list_recent(self, limit: int = 10) -> list[dict]:
        """Letzte N Tasks unabhängig vom Status — neueste zuerst."""
        async with self._db.connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            )
            rows = await cur.fetchall()
            await cur.close()
            return [dict(r) for r in rows]

    async def get_last_running(
        self, source_channel: str | None = None
    ) -> dict | None:
        """Letzter laufender Task (für Cancel-Intent).

        Optional auf einen Eingangskanal eingeschränkt.
        """
        async with self._db.connection() as conn:
            if source_channel is None:
                cur = await conn.execute(
                    """
                    SELECT * FROM tasks
                     WHERE status = 'running'
                     ORDER BY created_at DESC
                     LIMIT 1
                    """
                )
            else:
                cur = await conn.execute(
                    """
                    SELECT * FROM tasks
                     WHERE status = 'running' AND source_channel = ?
                     ORDER BY created_at DESC
                     LIMIT 1
                    """,
                    (source_channel,),
                )
            row = await cur.fetchone()
            await cur.close()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # State-Machine
    # ------------------------------------------------------------------

    async def start(self, task_id: str, agent_id: str | None = None) -> None:
        """`pending` → `running`. Optional bindet einen Agenten an den Task."""
        await self._transition(
            task_id,
            from_status="pending",
            to_status="running",
            extra_sets={"assigned_agent": agent_id} if agent_id else None,
        )

    async def finish(self, task_id: str, result: str) -> None:
        """`running` → `done`. Speichert das Ergebnis."""
        await self._transition(
            task_id,
            from_status="running",
            to_status="done",
            extra_sets={"result": result},
        )

    async def fail(self, task_id: str, reason: str = "") -> None:
        """`running` → `failed`. `reason` wird in `result` als FAILED:-Marker
        abgelegt."""
        await self._transition(
            task_id,
            from_status="running",
            to_status="failed",
            extra_sets={"result": f"FAILED: {reason}" if reason else "FAILED"},
        )

    async def cancel(self, task_id: str, reason: str = "user_request") -> None:
        """Cancelt den Task aus `pending` oder `running`.

        Versucht zuerst `pending → cancelled`; gelingt das nicht, versucht es
        `running → cancelled`. Andere Status werfen
        `InvalidTaskTransitionError`.
        """
        # Direkter Fast-Path über UPDATE mit WHERE status IN (...)
        now = iso_utc_now()
        async with self._db.connection() as conn:
            cur = await conn.execute(
                """
                UPDATE tasks
                   SET status = 'cancelled',
                       cancelled_reason = ?,
                       updated_at = ?
                 WHERE id = ?
                   AND status IN ('pending', 'running', 'waiting_approval')
                """,
                (reason, now, task_id),
            )
            rowcount = cur.rowcount or 0
            await cur.close()
            await conn.commit()
        if rowcount == 0:
            await self._raise_for_missed_update(task_id, "cancelled")
        logger.info("task cancelled id=%s reason=%r", task_id, reason)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _transition(
        self,
        task_id: str,
        *,
        from_status: str,
        to_status: str,
        extra_sets: dict[str, object] | None = None,
    ) -> None:
        """Optimistic-Locking-Übergang von `from_status` nach `to_status`."""
        if to_status not in _ALLOWED_TRANSITIONS.get(from_status, frozenset()):
            raise InvalidTaskTransitionError(
                f"Transition {from_status!r} -> {to_status!r} ist nicht erlaubt"
            )
        sets_sql = ["status = ?", "updated_at = ?"]
        values: list[object] = [to_status, iso_utc_now()]
        if extra_sets:
            for col, val in extra_sets.items():
                sets_sql.append(f"{col} = ?")
                values.append(val)
        values.extend([task_id, from_status])

        sql = (
            "UPDATE tasks SET "
            + ", ".join(sets_sql)
            + " WHERE id = ? AND status = ?"
        )
        async with self._db.connection() as conn:
            cur = await conn.execute(sql, values)
            rowcount = cur.rowcount or 0
            await cur.close()
            await conn.commit()
        if rowcount == 0:
            await self._raise_for_missed_update(task_id, to_status, from_status)
        logger.debug(
            "task transition id=%s %s -> %s", task_id, from_status, to_status
        )

    async def _raise_for_missed_update(
        self,
        task_id: str,
        to_status: str,
        expected_from: str | None = None,
    ) -> None:
        """0 betroffene Zeilen — entscheide ob Task fehlt oder Status falsch."""
        existing = await self.get(task_id)
        if existing is None:
            raise TaskNotFoundError(f"Task {task_id} nicht gefunden")
        actual = existing.get("status")
        if expected_from is not None:
            raise InvalidTaskTransitionError(
                f"Task {task_id} hat Status {actual!r}, "
                f"erwartet {expected_from!r} für Übergang nach {to_status!r}"
            )
        raise InvalidTaskTransitionError(
            f"Task {task_id} im Status {actual!r} kann nicht nach "
            f"{to_status!r} überführt werden"
        )


__all__ = ["TaskManager"]
