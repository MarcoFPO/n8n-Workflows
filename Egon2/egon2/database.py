"""Egon2 Datenbank-Schicht — aiosqlite mit WAL, Migrationen, UnitOfWork.

Siehe LLD-Persistenz §2 für die vollständige Spezifikation.

Schlüsselpunkte:
- Persistente Pragmas (journal_mode=WAL, mmap_size) werden einmalig gesetzt.
- Per-Connection-Pragmas (foreign_keys, synchronous, temp_store, cache_size,
  busy_timeout) MÜSSEN bei jeder neuen Connection neu gesetzt werden.
- Migrationen sind versioniert und laufen in Transaktionen.
- Crash-Recovery: orphaned `running` Tasks werden auf `failed` gesetzt.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import AsyncIterator, Final, Self

import aiosqlite

from egon2.exceptions import DatabaseError

logger = logging.getLogger(__name__)


SCHEMA_VERSION: Final[int] = 1

PERSISTENT_PRAGMAS: Final[tuple[str, ...]] = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA mmap_size = 134217728",  # 128 MiB
)

PER_CONNECTION_PRAGMAS: Final[tuple[str, ...]] = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA cache_size = -16384",  # 16 MiB
    "PRAGMA busy_timeout = 5000",
)


def iso_utc_now() -> str:
    """UTC-Now im strikten ISO8601-Format mit Mikrosekunden und Z-Suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ---------------------------------------------------------------------------
# Schema (Migration v1) — siehe LLD-Persistenz §3
# ---------------------------------------------------------------------------

SQL_CREATE_SCHEMA_MIGRATIONS: Final[str] = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_AGENTS: Final[str] = """
CREATE TABLE IF NOT EXISTS agents (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    description          TEXT,
    system_prompt        TEXT NOT NULL,
    capabilities         TEXT NOT NULL DEFAULT '[]',
    work_location        TEXT NOT NULL DEFAULT 'local'
                         CHECK (work_location IN ('local', 'lxc126', 'lxc_any')),
    prompt_version       INTEGER NOT NULL DEFAULT 1,
    status               TEXT NOT NULL DEFAULT 'active'
                         CHECK (status IN ('pending_approval', 'active', 'inactive')),
    deactivated_reason   TEXT,
    promoted_to_builtin  INTEGER NOT NULL DEFAULT 0
                         CHECK (promoted_to_builtin IN (0, 1)),
    use_count            INTEGER NOT NULL DEFAULT 0,
    last_used_at         TEXT,
    created_by           TEXT DEFAULT 'seed',
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_TASKS: Final[str] = """
CREATE TABLE IF NOT EXISTS tasks (
    id                       TEXT PRIMARY KEY,
    title                    TEXT NOT NULL,
    description              TEXT,
    source_channel           TEXT,
    status                   TEXT NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','running','done','failed','cancelled','waiting_approval')),
    assigned_agent           TEXT REFERENCES agents(id),
    result                   TEXT,
    parent_task_id           TEXT REFERENCES tasks(id),
    request_id               TEXT,
    cancelled_reason         TEXT,
    overhead_tokens_input    INTEGER DEFAULT 0,
    overhead_tokens_output   INTEGER DEFAULT 0,
    created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_AGENT_ASSIGNMENTS: Final[str] = """
CREATE TABLE IF NOT EXISTS agent_assignments (
    id                      TEXT PRIMARY KEY,
    agent_id                TEXT NOT NULL REFERENCES agents(id),
    task_id                 TEXT NOT NULL REFERENCES tasks(id),
    brief                   TEXT,
    result                  TEXT,
    status                  TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running','done','failed','cancelled')),
    tokens_input            INTEGER,
    tokens_output           INTEGER,
    cost_estimate           REAL,
    duration_ms             INTEGER,
    quality_score           INTEGER,
    prompt_version_used     INTEGER,
    predecessor_confidence  TEXT,
    assigned_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at            TEXT
)
"""

SQL_CREATE_AGENT_PROMPT_HISTORY: Final[str] = """
CREATE TABLE IF NOT EXISTS agent_prompt_history (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    prompt_version  INTEGER NOT NULL,
    system_prompt   TEXT NOT NULL,
    changed_by      TEXT,
    change_reason   TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_CONVERSATIONS: Final[str] = """
CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    channel    TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    timestamp  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_NOTES: Final[str] = """
CREATE TABLE IF NOT EXISTS notes (
    id                 TEXT PRIMARY KEY,
    title              TEXT,
    content            TEXT NOT NULL,
    tags               TEXT DEFAULT '[]',
    source_channel     TEXT,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    synced_knowledge   INTEGER DEFAULT 0,
    synced_bookstack   INTEGER DEFAULT 0,
    synced_github      INTEGER DEFAULT 0,
    bookstack_page_id  INTEGER DEFAULT NULL
)
"""

SQL_CREATE_HEALTH_CHECKS: Final[str] = """
CREATE TABLE IF NOT EXISTS health_checks (
    id            TEXT PRIMARY KEY,
    check_type    TEXT,
    target        TEXT,
    status        TEXT,
    findings      TEXT DEFAULT '[]',
    action_taken  TEXT,
    checked_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_SCHEDULER_LOG: Final[str] = """
CREATE TABLE IF NOT EXISTS scheduler_log (
    id            TEXT PRIMARY KEY,
    job_name      TEXT,
    started_at    TEXT,
    finished_at   TEXT,
    status        TEXT,
    output        TEXT
)
"""

SQL_CREATE_COMMAND_AUDIT: Final[str] = """
CREATE TABLE IF NOT EXISTS command_audit (
    id           TEXT PRIMARY KEY,
    sender_id    TEXT,
    channel      TEXT,
    command      TEXT,
    result       TEXT,
    executed_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

SQL_CREATE_WERKSTATT_RETENTION: Final[str] = """
CREATE TABLE IF NOT EXISTS werkstatt_retention (
    task_id      TEXT PRIMARY KEY REFERENCES tasks(id),
    path         TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    cleaned_up   INTEGER DEFAULT 0
)
"""

# Indizes
SQL_INDEX_CONVERSATIONS: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_conversations_channel_ts "
    "ON conversations(channel, timestamp DESC)"
)
SQL_INDEX_TASKS_STATUS: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
)
SQL_INDEX_TASKS_PARENT: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id)"
)
SQL_INDEX_TASKS_ASSIGNED_AGENT: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks(assigned_agent)"
)
SQL_INDEX_NOTES: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at DESC)"
)
SQL_INDEX_NOTES_SYNCED: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_notes_synced "
    "ON notes(synced_knowledge, synced_bookstack, synced_github)"
)
SQL_INDEX_AGENTS_STATUS: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)"
)
SQL_INDEX_AGENT_ASSIGNMENTS_AGENT: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_assignments_agent ON agent_assignments(agent_id)"
)
SQL_INDEX_AGENT_ASSIGNMENTS_TASK: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_assignments_task ON agent_assignments(task_id)"
)
SQL_INDEX_AGENT_ASSIGNMENTS_ASSIGNED_AT: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_assignments_assigned_at "
    "ON agent_assignments(assigned_at DESC)"
)
SQL_INDEX_HEALTH_CHECKS: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_health_checks_at "
    "ON health_checks(checked_at DESC)"
)
SQL_INDEX_COMMAND_AUDIT: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_command_audit_at "
    "ON command_audit(executed_at DESC)"
)
SQL_INDEX_WERKSTATT_RETENTION_PENDING: Final[str] = (
    "CREATE INDEX IF NOT EXISTS idx_werkstatt_cleanup "
    "ON werkstatt_retention(cleaned_up) WHERE cleaned_up = 0"
)


MIGRATIONS: Final[dict[int, tuple[str, ...]]] = {
    1: (
        SQL_CREATE_AGENTS,
        SQL_CREATE_TASKS,
        SQL_CREATE_AGENT_ASSIGNMENTS,
        SQL_CREATE_AGENT_PROMPT_HISTORY,
        SQL_CREATE_CONVERSATIONS,
        SQL_CREATE_NOTES,
        SQL_CREATE_HEALTH_CHECKS,
        SQL_CREATE_SCHEDULER_LOG,
        SQL_CREATE_COMMAND_AUDIT,
        SQL_CREATE_WERKSTATT_RETENTION,
        SQL_INDEX_CONVERSATIONS,
        SQL_INDEX_TASKS_STATUS,
        SQL_INDEX_TASKS_PARENT,
        SQL_INDEX_TASKS_ASSIGNED_AGENT,
        SQL_INDEX_NOTES,
        SQL_INDEX_NOTES_SYNCED,
        SQL_INDEX_AGENTS_STATUS,
        SQL_INDEX_AGENT_ASSIGNMENTS_AGENT,
        SQL_INDEX_AGENT_ASSIGNMENTS_TASK,
        SQL_INDEX_AGENT_ASSIGNMENTS_ASSIGNED_AT,
        SQL_INDEX_HEALTH_CHECKS,
        SQL_INDEX_COMMAND_AUDIT,
        SQL_INDEX_WERKSTATT_RETENTION_PENDING,
    ),
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


class Database:
    """Zentrale SQLite-Verwaltung. Singleton pro Prozess."""

    def __init__(self, db_path: str | Path) -> None:
        self.path: Path = Path(db_path)
        self._initialised: bool = False

    # ---- Connection-Handling ----

    async def acquire(self) -> aiosqlite.Connection:
        """Öffnet eine neue, frisch konfigurierte Connection.

        Caller ist verantwortlich für `await conn.close()`. Für den
        regulären Pfad bevorzugt `connection()` als Context-Manager
        verwenden.
        """
        conn: aiosqlite.Connection = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        for pragma in PER_CONNECTION_PRAGMAS:
            await conn.execute(pragma)
        return conn

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Async Context-Manager — liefert eine konfigurierte Connection.

        Per-Connection-Pragmas werden bei jeder neuen Connection gesetzt
        (sonst fallen synchronous/temp_store/cache_size/busy_timeout auf
        SQLite-Defaults zurück).
        """
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await conn.close()

    # ---- Lifecycle ----

    async def init(self) -> None:
        """Idempotent: Verzeichnisse anlegen, Pragmas setzen, Migrationen ausführen."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with aiosqlite.connect(self.path) as conn:
                conn.row_factory = aiosqlite.Row
                for pragma in PERSISTENT_PRAGMAS:
                    await conn.execute(pragma)
                for pragma in PER_CONNECTION_PRAGMAS:
                    await conn.execute(pragma)
                await conn.commit()
                await self._run_migrations(conn)
            self._initialised = True
            logger.info(
                "Database initialised at %s (schema v%d)",
                self.path,
                SCHEMA_VERSION,
            )
            # Seed-Hook (lazy import — Registry darf optional fehlen,
            # z. B. bei Tests die nur die DB-Schicht prüfen).
            try:
                from egon2.agents.registry import AgentRegistry  # noqa: WPS433
            except ImportError:
                logger.debug("AgentRegistry not importable, skipping seed")
            else:
                seeded = await AgentRegistry(self).seed_if_empty()
                if seeded:
                    logger.info("Seeded %d builtin agents", seeded)
        except aiosqlite.Error as exc:
            raise DatabaseError(f"Database init failed: {exc}") from exc

    # Alias — einige Module der Spezifikation nennen die Funktion `initialise`
    initialise = init

    async def _run_migrations(self, conn: aiosqlite.Connection) -> None:
        """Führt alle Migrationen > current_version transaktional aus."""
        await conn.execute(SQL_CREATE_SCHEMA_MIGRATIONS)
        await conn.commit()

        cur = await conn.execute("SELECT MAX(version) FROM schema_migrations")
        row = await cur.fetchone()
        current: int = row[0] if row and row[0] is not None else 0
        await cur.close()

        versions = sorted(MIGRATIONS.keys())
        if versions and versions != list(range(1, max(versions) + 1)):
            raise DatabaseError(f"Migration version gaps detected: {versions}")

        for version in versions:
            if version <= current:
                continue
            logger.info("Applying migration v%d", version)
            await conn.execute("BEGIN")
            try:
                for stmt in MIGRATIONS[version]:
                    await conn.execute(stmt)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, iso_utc_now()),
                )
                await conn.execute("COMMIT")
            except Exception:
                logger.exception("Migration v%d failed — rolling back", version)
                await conn.execute("ROLLBACK")
                raise

    async def checkpoint_and_close(self) -> None:
        """WAL-Checkpoint + Datenbank-Aufräumen beim Shutdown."""
        try:
            async with self.connection() as conn:
                await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                await conn.commit()
            logger.info("WAL checkpoint completed for %s", self.path)
        except aiosqlite.Error as exc:
            logger.warning("WAL checkpoint failed: %s", exc)

    # ---- Crash-Recovery ----

    async def recover_orphaned(self) -> int:
        """Markiert alle `running`-Tasks als `failed` (cancelled_reason='service_crash').

        Wird beim Startup aufgerufen — wenn der Prozess während eines
        laufenden Assignments gecrasht ist, hängen Tasks sonst auf
        ewig im Status `running`.

        Returns:
            Anzahl der recovereten Tasks.
        """
        async with self.connection() as conn:
            cur = await conn.execute(
                """
                UPDATE tasks
                   SET status = 'failed',
                       cancelled_reason = 'service_crash',
                       updated_at = ?
                 WHERE status = 'running'
                """,
                (iso_utc_now(),),
            )
            count = cur.rowcount or 0
            await cur.close()
            await conn.commit()
            if count:
                logger.warning("Recovered %d orphaned running task(s)", count)
            return count

    # ---- Onboarding-Helper ----

    async def has_any_assistant_message(self) -> bool:
        """True, sobald jemals eine `assistant`-Nachricht gespeichert wurde."""
        async with self.connection() as conn:
            cur = await conn.execute(
                "SELECT 1 FROM conversations WHERE role = 'assistant' LIMIT 1"
            )
            row = await cur.fetchone()
            await cur.close()
            return row is not None


# ---------------------------------------------------------------------------
# UnitOfWork — Multi-Repo-Transaktionen
# ---------------------------------------------------------------------------


class UnitOfWork:
    """Geteilte Connection für atomare Multi-Repo-Writes.

    Verwendung:
        async with UnitOfWork(db) as uow:
            await tasks_repo.update_status(task_id, 'done', conn=uow.conn)
            await assignments_repo.complete(..., conn=uow.conn)
            await agents_repo.bump_use_count(agent_id, conn=uow.conn)

    Commit beim sauberen Verlassen, Rollback bei Exception.

    Verbindliche Regeln:
      1. Eine UoW = eine Transaktion. Nicht verschachteln.
      2. Repository-Methoden mit `conn=` committen NICHT selbst.
      3. Nur Schreiboperationen brauchen UoW.
      4. Keine externen I/O-Operationen (HTTP, Subprocess) innerhalb der UoW.
    """

    def __init__(self, database: Database) -> None:
        self._db: Database = database
        self._cm: AsyncIterator[aiosqlite.Connection] | None = None
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("UnitOfWork is not entered (use 'async with')")
        return self._conn

    async def __aenter__(self) -> Self:
        self._cm = self._db.connection()
        self._conn = await self._cm.__aenter__()  # type: ignore[union-attr]
        await self._conn.execute("BEGIN")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._conn is not None and self._cm is not None
        try:
            if exc_type is None:
                await self._conn.execute("COMMIT")
            else:
                logger.warning("UnitOfWork rollback (%s)", exc_type.__name__)
                await self._conn.execute("ROLLBACK")
        finally:
            await self._cm.__aexit__(exc_type, exc, tb)  # type: ignore[union-attr]
            self._conn = None
            self._cm = None


__all__ = [
    "Database",
    "UnitOfWork",
    "SCHEMA_VERSION",
    "MIGRATIONS",
    "iso_utc_now",
]
