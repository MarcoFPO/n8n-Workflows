# LLD — Egon2: Persistenz-Schicht

**Version:** 1.3
**Stand:** 2026-05-02
**Bezug:** HLD-Egon2.md v1.5, Abschnitt 8 (Persistenz); Audit-Report `docs/audit/Persistenz-Review.md`
**Autor:** Marco Doehler / Claude

**Changelog v1.1:** Audit-Findings eingearbeitet (Migrations-Atomarität, Multi-Repo-Transaktionen, Per-Connection-Pragmas, ISO8601-Datetime, fehlende Indizes/Spalten/Tabellen, Backup-Rotation Off-by-One, Knowledge-Migration mit gestopptem MCP-Server).

**Changelog v1.2:** Spec-Findings eingearbeitet: Backup-Einschränkungen dokumentiert (F1), Sync-Flags dreistufig + BookStack-ID-Tracking (F2), fehlende Schema-Spalten `deactivated_reason`/`promoted_to_builtin`/`prompt_version_used`/`cancelled_reason`/`request_id` + vollständige `agent_prompt_history`-Spec (F3).

**Changelog v1.3 (Audit-Runde-2-Findings 2026-05-02):**
- Fix: `bump_prompt_version()` INSERT verwendete `changed_at` (nicht existent) statt `created_at` und fehlte `id`-Feld (PRIMARY KEY ohne DEFAULT) — hätte `OperationalError` bei Laufzeit verursacht (§6.6).
- Fix: `agents`-DDL fehlte `use_count INTEGER NOT NULL DEFAULT 0` und `last_used_at TEXT` — von LLD-Agenten genutzte Felder (§3.1).
- Fix: `AssignmentStatus` Literal und `agent_assignments` CHECK-Constraint fehlte `'cancelled'` — Inkonsistenz mit Task-Status-Machine (§3.3, §4.1).
- Fix: `tasks`-DDL fehlte `sender_id TEXT` — für `last_task_for_sender()` benötigt (§3.2).
- Fix: `cost_sum_last_n_days()` nutzte `datetime('now', ?)` → ISO8601-Format-Mismatch; jetzt `strftime('%Y-%m-%dT%H:%M:%S.000000Z', 'now', ?)` (§6.7).
- Fix: `uuid`-Import in `agents.py` ergänzt (§6.6).

---

## 1. Überblick

Die Persistenz-Schicht von Egon2 besteht aus drei voneinander getrennten Speicher-Domänen:

| Domäne | Ort | Datei / Endpoint | Zweck |
|---|---|---|---|
| **Operativ-DB** | LXC 128 | `/opt/egon2/data/egon2.db` | conversations, tasks, notes, agents, agent_assignments, agent_prompt_history, health_checks, scheduler_log |
| **Scheduler-DB** | LXC 128 | `/opt/egon2/data/scheduler.db` | APScheduler JobStore (von APScheduler verwaltet, aber im Backup-Job dieses LLDs mit erfasst) |
| **Knowledge Store** | LXC 107 | `http://10.1.1.107:8080` (`mcp_knowledge_v5.db`) | langfristiges Wissen, News, Notizen-Sync |

Dieses LLD spezifiziert vollständig die Operativ-DB (`egon2.db`), die Migration des Knowledge Store, den Backup-Job (inkl. Scheduler-DB) sowie das Repository-Pattern für den Datenzugriff.

### 1.1 DATETIME-Konvention (verbindlich)

Alle Zeitspalten werden als `TEXT` gespeichert. Das Format ist striktes ISO8601-UTC mit Mikrosekunden-Präzision und `T`-Separator:

```
YYYY-MM-DDTHH:MM:SS.ffffffZ        z.B. 2026-05-02T13:14:15.123456Z
```

- **Defaults im Schema** verwenden `DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))` — niemals `CURRENT_TIMESTAMP` (das produziert `'YYYY-MM-DD HH:MM:SS'` ohne `T` und ohne `Z`).
- **Im Repository-Code** wird mit `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")` geschrieben — Hilfsfunktion `iso_utc_now()` in `egon2/utils/time.py`.
- Lexikografische String-Sortierung entspricht der zeitlichen Sortierung — kritisch für `ORDER BY assigned_at`.

---

## 2. `database.py` — Modul-Spezifikation

### 2.1 Verantwortlichkeiten

- Initialisierung der SQLite-Datei (`egon2.db`) inklusive WAL-Modus und Pragma-Tuning
- Bereitstellung eines async Context-Managers für aiosqlite-Connections — **mit Per-Connection-Pragma-Initialisierung**
- Ausführung des Schema-Migrations-Systems (idempotent, versioniert, **transaktional pro Migration**)
- Seed-Daten für die `agents`-Tabelle (10 initiale Spezialisten)

### 2.2 Verbindungs-Management

aiosqlite öffnet pro Operation eine kurzlebige Connection. Wichtig: **Per-Connection-Pragmas** (`foreign_keys`, `synchronous`, `temp_store`, `cache_size`, `busy_timeout`) müssen bei **jeder** neuen Connection erneut gesetzt werden — nur `journal_mode=WAL` ist persistent in der DB-Datei.

```python
# egon2/database.py
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Final

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH: Final[Path] = Path("/opt/egon2/data/egon2.db")
SCHEMA_VERSION: Final[int] = 1

# Persistente Pragmas — einmalig in initialise() gesetzt, in DB-Datei verankert.
PERSISTENT_PRAGMAS: Final[tuple[str, ...]] = (
    "PRAGMA journal_mode = WAL",
    "PRAGMA mmap_size = 134217728",       # 128 MiB memory-mapped I/O
)

# Per-Connection-Pragmas — MÜSSEN bei JEDER neuen Connection gesetzt werden.
PER_CONNECTION_PRAGMAS: Final[tuple[str, ...]] = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA cache_size = -16384",         # 16 MiB Page-Cache
    "PRAGMA busy_timeout = 5000",         # 5s Wartezeit auf Lock
)


def iso_utc_now() -> str:
    """Liefert UTC-Now im strikten ISO8601-Format mit Mikrosekunden und Z-Suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Database:
    """Zentrale SQLite-Verwaltung. Singleton pro Prozess."""

    def __init__(self, path: Path = DB_PATH) -> None:
        self.path: Path = path
        self._initialised: bool = False

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Async Context-Manager — liefert eine konfigurierte Connection.

        WICHTIG: Per-Connection-Pragmas werden bei jeder neuen Connection gesetzt,
        sonst fallen synchronous/temp_store/cache_size/busy_timeout auf SQLite-
        Defaults zurück (siehe Audit §4.1).
        """
        conn: aiosqlite.Connection = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        try:
            for pragma in PER_CONNECTION_PRAGMAS:
                await conn.execute(pragma)
            yield conn
        finally:
            await conn.close()

    async def initialise(self) -> None:
        """Idempotent — setzt persistente Pragmas, legt Schema an, führt Migrationen aus."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as conn:
            for pragma in PERSISTENT_PRAGMAS:
                await conn.execute(pragma)
            for pragma in PER_CONNECTION_PRAGMAS:
                await conn.execute(pragma)
            await conn.commit()
            await self._run_migrations(conn)
            await self._seed_agents(conn)
        self._initialised = True
        logger.info("Database initialised at %s (schema v%d)", self.path, SCHEMA_VERSION)

    async def _run_migrations(self, conn: aiosqlite.Connection) -> None:
        """Führt alle Migrationen >= aktueller schema_version atomar aus.

        Jede Migration läuft in einer eigenen expliziten Transaktion. Bei einem
        Fehler wird die gesamte Migration zurückgerollt — kein partieller Zustand.
        Lückencheck: MIGRATIONS-Versionen müssen lückenlos 1..N sein.
        """
        await conn.execute(SQL_CREATE_SCHEMA_VERSION)
        await conn.commit()
        cur = await conn.execute("SELECT MAX(version) FROM schema_version")
        row = await cur.fetchone()
        current: int = row[0] if row and row[0] is not None else 0

        versions = sorted(MIGRATIONS.keys())
        if versions and versions != list(range(1, max(versions) + 1)):
            raise RuntimeError(f"Migration version gaps: {versions}")

        for version in versions:
            if version <= current:
                continue
            logger.info("Applying migration v%d", version)
            await conn.execute("BEGIN")
            try:
                for stmt in MIGRATIONS[version]:
                    await conn.execute(stmt)
                await conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (version, iso_utc_now()),
                )
                await conn.execute("COMMIT")
            except Exception:
                logger.exception("Migration v%d failed — rolling back", version)
                await conn.execute("ROLLBACK")
                raise

    async def _seed_agents(self, conn: aiosqlite.Connection) -> None:
        """Legt die 10 initialen Spezialisten an, falls nicht vorhanden."""
        from egon2.agents.registry import AGENT_SEED  # lazy import
        for agent in AGENT_SEED:
            await conn.execute(
                """
                INSERT INTO agents (id, name, description, system_prompt,
                                    capabilities, work_location, prompt_version,
                                    is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (
                    agent["id"], agent["name"], agent["description"],
                    agent["system_prompt"], json.dumps(agent["capabilities"]),
                    agent["work_location"],
                    iso_utc_now(),
                    iso_utc_now(),
                ),
            )
        await conn.commit()


db: Final[Database] = Database()
```

### 2.3 Migration-System

- **Tabelle `schema_version`** speichert die angewendeten Versionen.
- Migrationen werden als geordnetes Mapping `MIGRATIONS: dict[int, tuple[str, ...]]` verwaltet.
- Jede Migration ist eine Liste von SQL-Statements, die **in einer einzigen Transaktion** ausgeführt werden (BEGIN/COMMIT/ROLLBACK — siehe `_run_migrations`).
- SQLite ab 3.25 unterstützt `CREATE TABLE`, `CREATE INDEX` und `ALTER TABLE ADD COLUMN` transaktional sicher (Debian 12 hat 3.40+).
- Eine bereits angewendete Version wird nicht erneut ausgeführt (Idempotenz garantiert).
- Schema-Änderungen erfordern: neue Versions-Nummer + Eintrag in `MIGRATIONS`.
- **Pre-Migration-Backup:** Vor jeder Migration > 1 wird `egon2.db` automatisch nach `egon2.db.pre-vN.bak` kopiert (Recovery-Pfad: alte Datei zurückspielen).

```python
SQL_CREATE_SCHEMA_VERSION: Final[str] = """
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
)
"""

# Reihenfolge in MIGRATIONS[1]:
# 1) agents       (FK-Ziel für tasks.assigned_agent und agent_assignments.agent_id)
# 2) tasks        (FK-Ziel für agent_assignments.task_id)
# 3) agent_assignments
# 4) agent_prompt_history
# 5) conversations / notes / health_checks / scheduler_log
# 6) Indizes
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
        SQL_INDEX_CONVERSATIONS,
        SQL_INDEX_TASKS_STATUS,
        SQL_INDEX_TASKS_PARENT,
        SQL_INDEX_TASKS_ASSIGNED_AGENT,
        SQL_INDEX_NOTES,
        SQL_INDEX_NOTES_SYNCED,
        SQL_INDEX_AGENT_ASSIGNMENTS_AGENT,
        SQL_INDEX_AGENT_ASSIGNMENTS_TASK,
        SQL_INDEX_AGENT_ASSIGNMENTS_ASSIGNED_AT,
        SQL_INDEX_HEALTH_CHECKS,
    ),
}
```

#### Generisches Migrations-Helper-Pattern

Für externe Migrationen (z.B. Knowledge Store auf LXC 107) verwenden wir denselben Transaktions-Schutz:

```python
async def run_migration(conn: aiosqlite.Connection, statements: list[str]) -> None:
    """Führt eine Liste von Statements in einer expliziten Transaktion aus.

    Bei einem Fehler wird ROLLBACK ausgeführt und die Exception propagiert.
    """
    await conn.execute("BEGIN")
    try:
        for stmt in statements:
            await conn.execute(stmt)
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
```

---

## 3. Vollständiges SQLite-Schema (`egon2.db`)

Alle Statements sind direkt ausführbar (keine Platzhalter, alle Constraints inkl. Indizes). Alle DATETIME-Spalten sind `TEXT` mit ISO8601-UTC-Default (siehe §1.1).

### 3.1 `agents`

(Wird vor `tasks` angelegt — FK-Ziel.)

```sql
CREATE TABLE IF NOT EXISTS agents (
    id                   TEXT PRIMARY KEY,           -- z.B. 'researcher'
    name                 TEXT NOT NULL,
    description          TEXT,
    system_prompt        TEXT NOT NULL,
    capabilities         TEXT NOT NULL,              -- JSON-Array
    work_location        TEXT NOT NULL
                         CHECK (work_location IN ('local', 'lxc126', 'lxc_any')),
    prompt_version       INTEGER NOT NULL DEFAULT 1,
    is_active            INTEGER NOT NULL DEFAULT 1  CHECK (is_active IN (0, 1)),
    deactivated_reason   TEXT
                         CHECK (deactivated_reason IN (
                             'inactive_14d', '3_failed_assignments',
                             'user_request', 'limit_reached'
                         )),                         -- NULL wenn is_active=1
    promoted_to_builtin  INTEGER NOT NULL DEFAULT 0  CHECK (promoted_to_builtin IN (0, 1)),
    use_count            INTEGER NOT NULL DEFAULT 0,
    last_used_at         TEXT,
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
-- (Kein zusätzlicher Unique-Index auf id — der PRIMARY KEY ist bereits unique.)
```

> **`deactivated_reason`:** Wird gesetzt wenn `is_active` auf `0` wechselt. Werte:
> - `'inactive_14d'` — kein Einsatz in 14 Tagen (automatisch durch Inspector)
> - `'3_failed_assignments'` — drei aufeinanderfolgende fehlgeschlagene Assignments
> - `'user_request'` — explizit per `/agenten deaktiviere <id>` vom User
> - `'limit_reached'` — Limit dynamischer Spezialisten wurde beim Neuanlegen überschritten
>
> **`promoted_to_builtin`:** Wird auf `1` gesetzt wenn ein dynamischer Spezialist via `/agenten promote <id>` in die permanente Liste überführt wird.

### 3.2 `tasks`

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    description      TEXT,
    intent           TEXT CHECK (intent IN ('task', 'note', 'question', 'conversation')),
    source_channel   TEXT CHECK (source_channel IN ('matrix', 'telegram', 'scheduler', 'system')),
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'done', 'failed',
                                       'waiting_approval', 'cancelled')),
    assigned_agent   TEXT REFERENCES agents(id) ON DELETE SET NULL,
    result           TEXT,
    parent_task_id   TEXT REFERENCES tasks(id) ON DELETE CASCADE,
    sender_id        TEXT,                           -- Matrix-MXID oder Telegram-User-ID
    cancelled_reason TEXT,                           -- gesetzt wenn status='cancelled'
    request_id       TEXT,                           -- 8-Zeichen Correlation-ID vom IncomingMessage
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_status         ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_parent         ON tasks (parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at     ON tasks (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent
    ON tasks (assigned_agent) WHERE assigned_agent IS NOT NULL;
```

> **`tasks.intent`** korrespondiert zum Brief-Format (HLD §6.3) und unterscheidet `task | note | question | conversation`. Wird vom Inspector/Analyst zur Aggregation genutzt.
>
> **`tasks.cancelled_reason`:** Freitext, der den Grund für eine User- oder System-initiierte Stornierung beschreibt (z.B. `'user_correction'`, `'intent_mismatch'`). Nur gesetzt wenn `status = 'cancelled'`.
>
> **`tasks.request_id`:** 8-Zeichen alphanumerische Correlation-ID. Wird vom IncomingMessage-Processor generiert und durch den gesamten Task-Lebenszyklus mitgeführt. Ermöglicht Korrelation von Logs, Health-Checks und User-Antworten zu einem eingehenden Request.

### 3.3 `agent_assignments`

```sql
CREATE TABLE IF NOT EXISTS agent_assignments (
    id                  TEXT PRIMARY KEY,
    agent_id            TEXT NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    task_id             TEXT NOT NULL REFERENCES tasks(id)  ON DELETE CASCADE,
    brief               TEXT NOT NULL,                       -- JSON
    result              TEXT,
    status              TEXT NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'done', 'failed', 'cancelled')),
    prompt_version_used INTEGER,                             -- welche prompt_version hat diesen Assignment ausgeführt
    tokens_input        INTEGER,
    tokens_output       INTEGER,
    cost_estimate       REAL,
    duration_ms         INTEGER,
    quality_score       INTEGER CHECK (quality_score BETWEEN 1 AND 5),
    assigned_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at        TEXT
);

CREATE INDEX IF NOT EXISTS idx_assignments_agent
    ON agent_assignments (agent_id, assigned_at DESC);
CREATE INDEX IF NOT EXISTS idx_assignments_task
    ON agent_assignments (task_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_assigned_at
    ON agent_assignments (assigned_at DESC);
```

> **`prompt_version_used`:** Wird beim Anlegen des Assignments aus `agents.prompt_version` kopiert. Ermöglicht retrospektive Analyse: nach welchem Inspector-Patch hat sich die Qualität eines Spezialisten verändert?

### 3.4 `agent_prompt_history`

Versionsgeschichte aller `system_prompt`-Änderungen — ermöglicht Rollback und A/B-Vergleich (HLD §11).

```sql
CREATE TABLE IF NOT EXISTS agent_prompt_history (
    id             TEXT PRIMARY KEY,                  -- UUID
    agent_id       TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    prompt_version INTEGER NOT NULL,
    system_prompt  TEXT NOT NULL,
    changed_by     TEXT CHECK (changed_by IN ('inspector', 'user', 'system')),
    change_reason  TEXT,                              -- Freitext, z.B. 'inspector_repair' oder 'user_promote'
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(agent_id, prompt_version)
);

CREATE INDEX IF NOT EXISTS idx_prompt_history_agent
    ON agent_prompt_history (agent_id, prompt_version DESC);
```

`AgentRepository.bump_prompt_version()` legt automatisch einen Eintrag an (siehe §6.6).

> **Felder:**
> - `changed_by`: Wer hat die Änderung veranlasst — `'inspector'` (automatische Reparatur), `'user'` (via `/agenten promote` oder `/agenten rollback`), `'system'` (Deployment/Seed).
> - `change_reason`: Optionaler Freitext für Audit-Trail — z.B. `'inspector_repair: quality_score avg 2.1'` oder `'user_rollback: bad output on task #312'`.
> - `prompt_version`: Korrespondiert zu `agents.prompt_version` zum Zeitpunkt dieser Änderung. Ermöglicht den Rollback: `agents.system_prompt = history.system_prompt WHERE agent_id = ? AND prompt_version = ?`.

### 3.5 `conversations`

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    channel     TEXT NOT NULL CHECK (channel IN ('matrix', 'telegram')),
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    timestamp   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_conversations_channel_ts
    ON conversations (channel, timestamp DESC);
```

### 3.6 `notes`

Die Sync-Flags sind **dreistufige Integers** (nicht Boolean), um Partial-Failure-Szenarien korrekt abzubilden:

| Wert | Bedeutung |
|------|-----------|
| `0`  | `pending` — noch nicht synchronisiert |
| `1`  | `synced` — letzter Versuch erfolgreich |
| `2`  | `error` — letzter Versuch fehlgeschlagen, wird beim nächsten Sync-Job erneut versucht |

**GitHub-Sync-Strategie bei non-fast-forward:** Lokal ist immer Master. Bei Konflikt: `git fetch` + `git reset --hard origin/main` vor dem Push (Cloud ist Downstream).

**BookStack-Dedup-Strategie:** `bookstack_page_id` wird beim ersten erfolgreichen Create gesetzt. Alle folgenden Sync-Läufe führen ein Update durch, wenn die ID gesetzt ist — kein zweites Create.

```sql
CREATE TABLE IF NOT EXISTS notes (
    id                  TEXT PRIMARY KEY,
    title               TEXT,
    content             TEXT NOT NULL,
    tags                TEXT,                         -- JSON-Array
    source_channel      TEXT CHECK (source_channel IN ('matrix', 'telegram', 'scheduler', 'system')),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    synced_knowledge    INTEGER NOT NULL DEFAULT 0
                        CHECK (synced_knowledge IN (0, 1, 2)),   -- 0=pending 1=synced 2=error
    synced_bookstack    INTEGER NOT NULL DEFAULT 0
                        CHECK (synced_bookstack IN (0, 1, 2)),   -- 0=pending 1=synced 2=error
    synced_github       INTEGER NOT NULL DEFAULT 0
                        CHECK (synced_github IN (0, 1, 2)),      -- 0=pending 1=synced 2=error
    bookstack_page_id   INTEGER DEFAULT NULL           -- gesetzt nach erstem BookStack-Create; Update statt Create
);

CREATE INDEX IF NOT EXISTS idx_notes_source_created
    ON notes (source_channel, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_synced
    ON notes (synced_bookstack, synced_github);
CREATE INDEX IF NOT EXISTS idx_notes_pending_knowledge
    ON notes (created_at) WHERE synced_knowledge = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_bookstack
    ON notes (created_at) WHERE synced_bookstack = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_github
    ON notes (created_at) WHERE synced_github = 0;
```

> **Sync-Job-Logik:** `list_pending_sync()` selektiert Einträge mit `synced_<target> IN (0, 2)` — also sowohl `pending` als auch `error`-Einträge werden erneut versucht. Bei Erfolg → `1`. Bei erneutem Fehler → `2`.

### 3.7 `health_checks`

```sql
CREATE TABLE IF NOT EXISTS health_checks (
    id           TEXT PRIMARY KEY,
    check_type   TEXT NOT NULL CHECK (check_type IN ('system', 'data', 'agent')),
    target       TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('ok', 'repaired', 'warning', 'degraded', 'critical')),
    findings     TEXT,                                  -- JSON-Array
    action_taken TEXT,
    checked_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_health_type_time
    ON health_checks (check_type, checked_at DESC);
```

### 3.8 `scheduler_log`

```sql
CREATE TABLE IF NOT EXISTS scheduler_log (
    id           TEXT PRIMARY KEY,
    job_name     TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    status       TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'skipped')),
    output       TEXT
);

CREATE INDEX IF NOT EXISTS idx_scheduler_job_started
    ON scheduler_log (job_name, started_at DESC);
```

### 3.9 `schema_version`

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

---

## 4. Knowledge Store Migration (LXC 107)

### 4.1 Bestehende Struktur (`mcp_knowledge_v5.db`)

```sql
-- bestehend, NICHT ändern (außer ALTER TABLE)
CREATE TABLE knowledge_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel     TEXT NOT NULL,
    title       TEXT,
    content     TEXT NOT NULL,
    tags        TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE channels (
    name        TEXT PRIMARY KEY,
    description TEXT
);
```

### 4.2 Erweiterungs-Statements (idempotent)

SQLite kennt kein `ADD COLUMN IF NOT EXISTS` — Idempotenz wird im Migrations-Skript per `PRAGMA table_info` geprüft.

```sql
-- Logisch zu erreichen:
ALTER TABLE knowledge_entries ADD COLUMN knowledge_type TEXT NOT NULL DEFAULT 'general';
ALTER TABLE knowledge_entries ADD COLUMN domain         TEXT NOT NULL DEFAULT 'general';
ALTER TABLE knowledge_entries ADD COLUMN importance     INTEGER NOT NULL DEFAULT 5;
ALTER TABLE knowledge_entries ADD COLUMN source         TEXT;
ALTER TABLE knowledge_entries ADD COLUMN refs           TEXT;       -- JSON ([{"type":"bookstack","url":"..."}])
ALTER TABLE knowledge_entries ADD COLUMN expires_at     TEXT;

CREATE INDEX IF NOT EXISTS idx_ke_channel_active
    ON knowledge_entries (channel, is_active);
CREATE INDEX IF NOT EXISTS idx_ke_type_domain
    ON knowledge_entries (knowledge_type, domain);
CREATE INDEX IF NOT EXISTS idx_ke_expires
    ON knowledge_entries (expires_at)
    WHERE expires_at IS NOT NULL;
```

> **Hinweis:** Spalte `references` ist in SQLite ein reserviertes Wort — wir verwenden `refs`. In der Anwendung wird über das Pydantic-Modell `KnowledgeEntry.references` mit `alias='refs'` aliased; Client-Serialisierung verwendet konsistent `by_alias=True`.

### 4.3 Migrations-Procedure (KRITISCH: MCP-Server stoppen!)

**Die Migration darf NIEMALS bei laufendem MCP-Server ausgeführt werden.** Ein laufender Server hält ggf. WAL-Connections offen, cacht Spaltenanzahl bei `SELECT *` und kann zur Laufzeit crashen, wenn das Schema sich ändert.

**Verbindlicher Ablauf:**

```bash
# 1. MCP-Server stoppen (auf LXC 107)
ssh root@10.1.1.107 "systemctl stop mcp-knowledge"

# 2. Backup der DB (Server ist down, einfaches cp ist sicher)
ssh root@10.1.1.107 "cp /opt/mcp-knowledge/mcp_knowledge_v5.db \
                       /opt/mcp-knowledge/backup/mcp_knowledge_v5.pre-migration.db"

# 3. Migration ausführen
ssh root@10.1.1.107 "cd /opt/mcp-knowledge && python3 -m egon2.knowledge.migration"

# 4. Integritäts-Check
ssh root@10.1.1.107 "sqlite3 /opt/mcp-knowledge/mcp_knowledge_v5.db 'PRAGMA integrity_check;'"

# 5. MCP-Server wieder starten
ssh root@10.1.1.107 "systemctl start mcp-knowledge"

# 6. Health-Check
curl -fsS http://10.1.1.107:8080/health
```

**SQLite-Versions-Check** im Migrations-Skript: `ALTER TABLE … ADD COLUMN NOT NULL DEFAULT` mit konstantem Default braucht SQLite ≥ 3.35. Fail-Fast wenn ältere Version.

#### deploy.sh-Pseudocode (Auszug)

```bash
#!/usr/bin/env bash
# scripts/deploy_knowledge_migration.sh
set -euo pipefail

REMOTE="root@10.1.1.107"
DB="/opt/mcp-knowledge/mcp_knowledge_v5.db"
BACKUP="/opt/mcp-knowledge/backup/mcp_knowledge_v5.pre-$(date +%Y%m%d-%H%M%S).db"

echo "[1/6] Stopping MCP server on LXC 107…"
ssh "$REMOTE" "systemctl stop mcp-knowledge"

echo "[2/6] Backing up DB → $BACKUP"
ssh "$REMOTE" "cp $DB $BACKUP"

echo "[3/6] Running migration…"
ssh "$REMOTE" "cd /opt/mcp-knowledge && python3 -m egon2.knowledge.migration"

echo "[4/6] Integrity check…"
RESULT=$(ssh "$REMOTE" "sqlite3 $DB 'PRAGMA integrity_check;'")
if [[ "$RESULT" != "ok" ]]; then
    echo "INTEGRITY CHECK FAILED — restoring backup"
    ssh "$REMOTE" "cp $BACKUP $DB"
    ssh "$REMOTE" "systemctl start mcp-knowledge"
    exit 1
fi

echo "[5/6] Starting MCP server…"
ssh "$REMOTE" "systemctl start mcp-knowledge"

echo "[6/6] Health check…"
sleep 2
curl -fsS http://10.1.1.107:8080/health
echo "Migration complete."
```

### 4.4 Idempotentes Migrations-Skript

```python
# egon2/knowledge/migration.py
from __future__ import annotations

import logging
from typing import Final

import aiosqlite

logger = logging.getLogger(__name__)

KNOWLEDGE_DB: Final[str] = "/opt/mcp-knowledge/mcp_knowledge_v5.db"   # Pfad auf LXC 107
MIN_SQLITE: Final[tuple[int, int]] = (3, 35)

NEW_COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ("knowledge_type", "TEXT NOT NULL DEFAULT 'general'"),
    ("domain",         "TEXT NOT NULL DEFAULT 'general'"),
    ("importance",     "INTEGER NOT NULL DEFAULT 5"),
    ("source",         "TEXT"),
    ("refs",           "TEXT"),
    ("expires_at",     "TEXT"),
)

NEW_INDEXES: Final[tuple[str, ...]] = (
    "CREATE INDEX IF NOT EXISTS idx_ke_channel_active "
    "ON knowledge_entries (channel, is_active)",
    "CREATE INDEX IF NOT EXISTS idx_ke_type_domain "
    "ON knowledge_entries (knowledge_type, domain)",
    "CREATE INDEX IF NOT EXISTS idx_ke_expires "
    "ON knowledge_entries (expires_at) WHERE expires_at IS NOT NULL",
)

DEFAULT_CHANNELS: Final[tuple[tuple[str, str], ...]] = (
    ("general",   "Allgemeines Wissen, Fakten, User-Präferenzen"),
    ("it",        "Infrastruktur, Konfigurationen, Lösungen"),
    ("network",   "Netzwerk-spezifisches Wissen"),
    ("project",   "Projektspezifisches Wissen"),
    ("personal",  "Persönliche Informationen, Gewohnheiten"),
    ("news",      "Tägliche News-Reports (30 Tage TTL)"),
    ("reference", "Zeiger auf externes Spezialwissen"),
)


async def migrate(db_path: str = KNOWLEDGE_DB) -> None:
    """Idempotente Migration des Knowledge Store.

    VORAUSSETZUNG: MCP-Server muss gestoppt sein (siehe §4.3).
    Verifiziert SQLite ≥ 3.35, läuft transaktional.
    """
    async with aiosqlite.connect(db_path) as conn:
        # Versions-Gate
        cur = await conn.execute("SELECT sqlite_version()")
        row = await cur.fetchone()
        version = row[0] if row else "0.0"
        major, minor, *_ = (int(p) for p in version.split("."))
        if (major, minor) < MIN_SQLITE:
            raise RuntimeError(
                f"SQLite >= {MIN_SQLITE[0]}.{MIN_SQLITE[1]} required, got {version}"
            )

        existing: set[str] = await _existing_columns(conn, "knowledge_entries")

        # Transaktional ausführen
        await conn.execute("BEGIN")
        try:
            for col_name, col_def in NEW_COLUMNS:
                if col_name in existing:
                    logger.debug("Column %s already present — skip", col_name)
                    continue
                sql = f"ALTER TABLE knowledge_entries ADD COLUMN {col_name} {col_def}"
                logger.info("Adding column: %s", col_name)
                await conn.execute(sql)
            for idx_sql in NEW_INDEXES:
                await conn.execute(idx_sql)
            for name, desc in DEFAULT_CHANNELS:
                await conn.execute(
                    "INSERT INTO channels (name, description) VALUES (?, ?) "
                    "ON CONFLICT(name) DO NOTHING",
                    (name, desc),
                )
            await conn.execute("COMMIT")
        except Exception:
            await conn.execute("ROLLBACK")
            raise

        logger.info("Knowledge Store migration complete")


async def _existing_columns(conn: aiosqlite.Connection, table: str) -> set[str]:
    cur = await conn.execute(
        "SELECT name FROM pragma_table_info(?)", (table,),
    )
    rows = await cur.fetchall()
    return {row[0] for row in rows}
```

### 4.5 HTTP-Client `mcp_client.py` — Spezifikation

Der MCP-Server auf LXC 107 (Port 8080) wird via HTTP angesprochen. Connection-Pool max 5 (gemäß HLD §9). Pydantic-Serialisierung nutzt **konsequent `by_alias=True`**, damit `references` als `refs` an den Server geht.

#### Endpoints

| Methode | Pfad | Zweck | Request | Response |
|---|---|---|---|---|
| `GET` | `/health` | Liveness-Probe | — | `{"status":"ok"}` |
| `GET` | `/entries` | Liste/Filter | Query: `channel`, `domain`, `knowledge_type`, `limit`, `active_only` | `[KnowledgeEntry]` |
| `GET` | `/entries/{id}` | Einzeln lesen | — | `KnowledgeEntry` |
| `POST` | `/entries` | Neu anlegen | `KnowledgeEntryCreate` (mit `refs`) | `KnowledgeEntry` (201) |
| `PATCH` | `/entries/{id}` | Teilweise aktualisieren | `KnowledgeEntryUpdate` | `KnowledgeEntry` |
| `DELETE` | `/entries/{id}` | Soft-Delete (`is_active=0`) | — | 204 |
| `POST` | `/search` | Volltext / Tag-Suche | `SearchQuery` | `[KnowledgeEntry]` |
| `POST` | `/expire` | Abgelaufene deaktivieren | — | `{"expired": int}` |

#### Pydantic-Modelle

```python
# egon2/knowledge/mcp_client.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Final, Literal, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field

KnowledgeType = Literal["general", "reference", "news", "note"]
Domain = Literal["general", "it", "network", "project", "personal", "news", "reference"]


class KnowledgeReference(BaseModel):
    type: str
    url: str


class KnowledgeEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    channel: str
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    knowledge_type: KnowledgeType = "general"
    domain: Domain = "general"
    importance: int = Field(default=5, ge=1, le=10)
    source: str | None = None
    references: list[KnowledgeReference] = Field(default_factory=list, alias="refs")
    expires_at: datetime | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class KnowledgeEntryCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    channel: str
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    knowledge_type: KnowledgeType = "general"
    domain: Domain = "general"
    importance: int = 5
    source: str | None = None
    references: list[KnowledgeReference] = Field(default_factory=list, alias="refs")
    expires_at: datetime | None = None


class KnowledgeEntryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    importance: int | None = None
    domain: Domain | None = None
    knowledge_type: KnowledgeType | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class SearchQuery(BaseModel):
    query: str
    channel: str | None = None
    domain: Domain | None = None
    limit: int = 10


class McpClient:
    """Async HTTP-Client für den Knowledge MCP-Server auf LXC 107."""

    BASE_URL: Final[str] = "http://10.1.1.107:8080"

    def __init__(self, base_url: str = BASE_URL, timeout: float = 10.0) -> None:
        limits = httpx.Limits(max_connections=5, max_keepalive_connections=5)
        transport = httpx.AsyncHTTPTransport(retries=3)
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout, limits=limits, transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/health")
        except httpx.HTTPError:
            return False
        return r.status_code == 200 and r.json().get("status") == "ok"

    async def list_entries(
        self,
        *,
        channel: str | None = None,
        domain: Domain | None = None,
        knowledge_type: KnowledgeType | None = None,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[KnowledgeEntry]:
        params: dict[str, Any] = {"limit": limit, "active_only": active_only}
        if channel: params["channel"] = channel
        if domain: params["domain"] = domain
        if knowledge_type: params["knowledge_type"] = knowledge_type
        r = await self._client.get("/entries", params=params)
        r.raise_for_status()
        return [KnowledgeEntry.model_validate(e) for e in r.json()]

    async def get_entry(self, entry_id: int) -> KnowledgeEntry:
        r = await self._client.get(f"/entries/{entry_id}")
        r.raise_for_status()
        return KnowledgeEntry.model_validate(r.json())

    async def create_entry(self, payload: KnowledgeEntryCreate) -> KnowledgeEntry:
        r = await self._client.post(
            "/entries",
            json=payload.model_dump(mode="json", by_alias=True),
        )
        r.raise_for_status()
        return KnowledgeEntry.model_validate(r.json())

    async def update_entry(self, entry_id: int, payload: KnowledgeEntryUpdate) -> KnowledgeEntry:
        r = await self._client.patch(
            f"/entries/{entry_id}",
            json=payload.model_dump(mode="json", exclude_none=True, by_alias=True),
        )
        r.raise_for_status()
        return KnowledgeEntry.model_validate(r.json())

    async def delete_entry(self, entry_id: int) -> None:
        r = await self._client.delete(f"/entries/{entry_id}")
        r.raise_for_status()

    async def search(self, query: SearchQuery) -> list[KnowledgeEntry]:
        r = await self._client.post("/search", json=query.model_dump(mode="json"))
        r.raise_for_status()
        return [KnowledgeEntry.model_validate(e) for e in r.json()]

    async def expire_outdated(self) -> int:
        r = await self._client.post("/expire")
        r.raise_for_status()
        return int(r.json().get("expired", 0))
```

---

## 5. Backup-Job

### 5.1 Anforderungen

- Tägliche Sicherung von **`egon2.db` UND `scheduler.db`** → `/opt/egon2/backup/`
- Rotation: nur die letzten 7 Tage werden behalten — **`-mtime +6`** (nicht `+7`, sonst Off-by-One: würde 8 Tage halten)
- Konsistente Kopie auch bei laufenden Schreiboperationen → `sqlite3 .backup`
- Aufruf via APScheduler-Job um 02:00, parallel als systemd-Timer-Sicherung möglich
- Backup-Verzeichnis und Log-Verzeichnis müssen `egon2:egon2` gehören (`chown egon2:egon2 /var/log/egon2 /opt/egon2/backup`)

### 5.2 Shell-Implementierung (`scripts/backup_egon2.sh`)

```bash
#!/usr/bin/env bash
# /opt/egon2/scripts/backup_egon2.sh
# Tägliches Backup von egon2.db und scheduler.db mit 7-Tage-Rotation.

set -euo pipefail
export LANG=C   # reproduzierbare date/stat Outputs

DB_PATH="/opt/egon2/data/egon2.db"
SCHED_PATH="/opt/egon2/data/scheduler.db"
BACKUP_DIR="/opt/egon2/backup"
RETENTION_DAYS=6   # find -mtime +6 hält die letzten 7 Tage (inkl. heute)
TS="$(date +%Y%m%d)"
TARGET_EGON="${BACKUP_DIR}/egon2-${TS}.db"
TARGET_SCHED="${BACKUP_DIR}/scheduler_${TS}.db"
LOG="/var/log/egon2/backup.log"

mkdir -p "${BACKUP_DIR}" "$(dirname "${LOG}")"

log() { printf '%s  %s\n' "$(date -Iseconds)" "$*" | tee -a "${LOG}" >&2; }

trap 'log "ERROR at line $LINENO (exit $?)"; exit 1' ERR

backup_one() {
    local src="$1" dst="$2"
    if [[ ! -f "$src" ]]; then
        log "Source DB not found: $src"
        return 2
    fi
    log "Starting backup ${src} → ${dst}"
    sqlite3 "$src" ".backup '${dst}'"
    if ! sqlite3 "$dst" "PRAGMA integrity_check;" | grep -qx "ok"; then
        log "Integrity check FAILED for ${dst}"
        rm -f "$dst"
        return 3
    fi
    local size
    size=$(stat -c '%s' "$dst")
    log "Backup OK ($size bytes): $dst"
}

backup_one "${DB_PATH}"    "${TARGET_EGON}"
backup_one "${SCHED_PATH}" "${TARGET_SCHED}"

# Rotation: alles älter als RETENTION_DAYS löschen — deterministische Variante
mapfile -t removed < <(find "${BACKUP_DIR}" -maxdepth 1 -type f \
    \( -name 'egon2-*.db' -o -name 'scheduler_*.db' \) \
    -mtime "+${RETENTION_DAYS}")
for f in "${removed[@]}"; do
    rm -f "$f" && log "Rotated out: $f"
done

log "Backup job done"
exit 0
```

### 5.3 APScheduler-Hook

```python
# egon2/core/scheduler.py (Auszug)
import asyncio
import logging

logger = logging.getLogger(__name__)


async def backup_job() -> None:
    """02:00 — ruft das Shell-Skript auf, loggt Ergebnis in scheduler_log."""
    proc = await asyncio.create_subprocess_exec(
        "/opt/egon2/scripts/backup_egon2.sh",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error("Backup failed (rc=%s): %s", proc.returncode, stderr.decode())
        raise RuntimeError(f"Backup exited {proc.returncode}")
    logger.info("Backup OK: %s", stdout.decode().strip())
```

### 5.4 Fehlerbehandlung

| Szenario | Erkennung | Reaktion |
|---|---|---|
| DB-Datei fehlt | `[[ ! -f ]]` | exit 2, Inspector-Alert (degraded) |
| `sqlite3 .backup` schlägt fehl | `set -e` + ERR-Trap | exit 1, Stderr im Log, Matrix-Alert |
| Integritäts-Check fehlschlägt | `PRAGMA integrity_check != ok` | Backup-Datei löschen, exit 3, Matrix-Alert |
| Disk voll | `.backup` schlägt fehl | exit 1, ERR-Trap loggt Zeile, Matrix-Alert |
| Rotation-Fehler | `find …` Exit-Code | nicht-fataler Log-Eintrag (Backup selbst war OK) |

Der Job-Exit-Code wird via `agent_dispatcher` als `health_checks`-Eintrag (`check_type='system'`, `target='backup'`) gespeichert.

---

## 6. Repository-Pattern

Jede Tabelle erhält eine eigene Repository-Klasse mit asynchronen CRUD-Methoden. Alle Methoden akzeptieren eine optionale `aiosqlite.Connection` (für Transaktionen).

### 6.1 Connection-Parameter-Pattern (verbindlich)

**Regel:** Eine Repository-Methode darf `commit()` **nur dann** aufrufen, wenn sie ihre Connection selbst geöffnet hat. Wird eine externe Connection via `conn=` übergeben, **darf kein Commit erfolgen** — sonst wird eine umschließende Multi-Repo-Transaktion mittendrin gebrochen (Audit §5.1, KRITISCH).

Der `_conn`-Helper liefert deshalb ein Tupel `(connection, owns)`:

```python
# egon2/repositories/_base.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

from egon2.database import db


@asynccontextmanager
async def _conn(
    conn: aiosqlite.Connection | None,
) -> AsyncIterator[tuple[aiosqlite.Connection, bool]]:
    """Liefert (connection, owns).

    owns=True: Connection wurde lokal geöffnet — Methode MUSS committen und schließen.
    owns=False: Connection ist extern (Multi-Repo-Transaktion) — Methode DARF NICHT committen.
    """
    if conn is not None:
        yield conn, False
        return
    async with db.connection() as c:
        yield c, True
```

Repository-Methoden verwenden den Helper konsequent:

```python
async def update_status(self, task_id: str, status: str, *, conn=None) -> None:
    async with _conn(conn) as (c, owns):
        await c.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        if owns:
            await c.commit()
```

### 6.2 Domain-Modelle (Pydantic)

```python
# egon2/models.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Channel = Literal["matrix", "telegram", "scheduler", "system"]
Intent = Literal["task", "note", "question", "conversation"]
TaskStatus = Literal["pending", "running", "done", "failed", "waiting_approval", "cancelled"]
WorkLocation = Literal["local", "lxc126", "lxc_any"]
AssignmentStatus = Literal["running", "done", "failed", "cancelled"]
HealthCheckType = Literal["system", "data", "agent"]
HealthStatus = Literal["ok", "repaired", "warning", "degraded", "critical"]
DeactivatedReason = Literal["inactive_14d", "3_failed_assignments", "user_request", "limit_reached"]
SyncStatus = Literal[0, 1, 2]   # 0=pending, 1=synced, 2=error


class _TzAware(BaseModel):
    """Mixin: alle datetime-Felder sind UTC-aware."""
    @field_validator("*", mode="after")
    @classmethod
    def _ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class Conversation(_TzAware):
    id: str
    channel: Literal["matrix", "telegram"]
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime


class Task(_TzAware):
    id: str
    title: str
    description: str | None = None
    intent: Intent | None = None
    source_channel: Channel | None = None
    status: TaskStatus = "pending"
    assigned_agent: str | None = None
    result: str | None = None
    parent_task_id: str | None = None
    cancelled_reason: str | None = None     # gesetzt wenn status='cancelled'
    request_id: str | None = None           # 8-Zeichen Correlation-ID
    created_at: datetime
    updated_at: datetime


class Note(_TzAware):
    id: str
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    source_channel: Channel | None = None
    created_at: datetime
    synced_knowledge: int = 0   # 0=pending, 1=synced, 2=error
    synced_bookstack: int = 0   # 0=pending, 1=synced, 2=error
    synced_github: int = 0      # 0=pending, 1=synced, 2=error
    bookstack_page_id: int | None = None   # gesetzt nach erstem BookStack-Create


class Agent(_TzAware):
    id: str
    name: str
    description: str | None = None
    system_prompt: str
    capabilities: list[str]
    work_location: WorkLocation
    prompt_version: int = 1
    is_active: bool = True
    deactivated_reason: DeactivatedReason | None = None
    promoted_to_builtin: bool = False
    created_at: datetime
    updated_at: datetime


class AgentAssignment(_TzAware):
    id: str
    agent_id: str
    task_id: str
    brief: dict
    result: str | None = None
    status: AssignmentStatus = "running"
    prompt_version_used: int | None = None  # kopiert von agents.prompt_version beim Anlegen
    tokens_input: int | None = None
    tokens_output: int | None = None
    cost_estimate: float | None = None
    duration_ms: int | None = None
    quality_score: int | None = None
    assigned_at: datetime
    completed_at: datetime | None = None


class HealthCheck(_TzAware):
    id: str
    check_type: HealthCheckType
    target: str
    status: HealthStatus
    findings: list[str] = Field(default_factory=list)
    action_taken: str | None = None
    checked_at: datetime


class SchedulerLogEntry(_TzAware):
    id: str
    job_name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal["ok", "failed", "skipped"]
    output: str | None = None
```

### 6.3 ConversationRepository

```python
# egon2/repositories/conversations.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import Conversation
from egon2.repositories._base import _conn


class ConversationRepository:
    async def add(
        self,
        channel: str,
        role: str,
        content: str,
        *,
        conn: aiosqlite.Connection | None = None,
    ) -> Conversation:
        record = Conversation(
            id=str(uuid.uuid4()),
            channel=channel,             # type: ignore[arg-type]
            role=role,                   # type: ignore[arg-type]
            content=content,
            timestamp=datetime.now(timezone.utc),
        )
        async with _conn(conn) as (c, owns):
            await c.execute(
                "INSERT INTO conversations (id, channel, role, content, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (record.id, record.channel, record.role, record.content,
                 iso_utc_now()),
            )
            if owns:
                await c.commit()
        return record

    async def latest(
        self,
        limit: int = 20,
        *,
        channel: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> list[Conversation]:
        sql = "SELECT * FROM conversations"
        params: list[object] = []
        if channel:
            sql += " WHERE channel = ?"
            params.append(channel)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(sql, params)
            rows = await cur.fetchall()
        return [Conversation.model_validate(dict(r)) for r in rows]

    async def purge_older_than(
        self,
        cutoff: datetime,
        *,
        conn: aiosqlite.Connection | None = None,
    ) -> int:
        async with _conn(conn) as (c, owns):
            cur = await c.execute(
                "DELETE FROM conversations WHERE timestamp < ?",
                (cutoff.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),),
            )
            if owns:
                await c.commit()
            return max(cur.rowcount, 0)
```

### 6.4 TaskRepository

```python
# egon2/repositories/tasks.py
from __future__ import annotations

import uuid

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import Intent, Task, TaskStatus
from egon2.repositories._base import _conn


class TaskRepository:
    async def create(
        self,
        title: str,
        description: str | None,
        source_channel: str | None,
        *,
        intent: Intent | None = None,
        parent_task_id: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> Task:
        now_iso = iso_utc_now()
        task_id = str(uuid.uuid4())
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO tasks (id, title, description, intent, source_channel,
                                      status, parent_task_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (task_id, title, description, intent, source_channel,
                 parent_task_id, now_iso, now_iso),
            )
            if owns:
                await c.commit()
            cur = await c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cur.fetchone()
        return Task.model_validate(dict(row))

    async def get(
        self, task_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> Task | None:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cur.fetchone()
        return Task.model_validate(dict(row)) if row else None

    async def list_by_status(
        self,
        status: TaskStatus,
        *,
        limit: int = 50,
        conn: aiosqlite.Connection | None = None,
    ) -> list[Task]:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
            rows = await cur.fetchall()
        return [Task.model_validate(dict(r)) for r in rows]

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        result: str | None = None,
        assigned_agent: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """WICHTIG: Wird im Multi-Repo-Transaktions-Pattern (§7) mit conn= gerufen
        und committet dann NICHT — der äußere BEGIN/COMMIT regelt die Atomarität.
        """
        async with _conn(conn) as (c, owns):
            await c.execute(
                """UPDATE tasks
                       SET status = ?, result = COALESCE(?, result),
                           assigned_agent = COALESCE(?, assigned_agent),
                           updated_at = ?
                       WHERE id = ?""",
                (status, result, assigned_agent, iso_utc_now(), task_id),
            )
            if owns:
                await c.commit()

    async def delete(
        self, task_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if owns:
                await c.commit()
```

### 6.5 NoteRepository

```python
# egon2/repositories/notes.py
from __future__ import annotations

import json
import uuid

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import Note
from egon2.repositories._base import _conn


class NoteRepository:
    async def create(
        self,
        content: str,
        *,
        title: str | None = None,
        tags: list[str] | None = None,
        source_channel: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> Note:
        note_id = str(uuid.uuid4())
        now_iso = iso_utc_now()
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO notes (id, title, content, tags, source_channel, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (note_id, title, content, json.dumps(tags or []),
                 source_channel, now_iso),
            )
            if owns:
                await c.commit()
            cur = await c.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = await cur.fetchone()
        d = dict(row)
        d["tags"] = json.loads(d.get("tags") or "[]")
        return Note.model_validate(d)

    async def get(
        self, note_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> Note | None:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = await cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["tags"] = json.loads(data.get("tags") or "[]")
        return Note.model_validate(data)

    async def list_pending_sync(
        self,
        target: str,
        *,
        limit: int = 50,
        conn: aiosqlite.Connection | None = None,
    ) -> list[Note]:
        """Liefert Notizen mit Sync-Status 0 (pending) ODER 2 (error) für erneuten Versuch."""
        col = {"knowledge": "synced_knowledge",
               "bookstack": "synced_bookstack",
               "github":    "synced_github"}[target]
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(
                # 0=pending, 2=error — beide werden erneut versucht
                f"SELECT * FROM notes WHERE {col} IN (0, 2) ORDER BY created_at LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
        out: list[Note] = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.get("tags") or "[]")
            out.append(Note.model_validate(d))
        return out

    async def mark_synced(
        self,
        note_id: str,
        target: str,
        *,
        bookstack_page_id: int | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Setzt Sync-Status auf 1 (synced). Bei BookStack optional page_id mitschreiben."""
        col = {"knowledge": "synced_knowledge",
               "bookstack": "synced_bookstack",
               "github":    "synced_github"}[target]
        async with _conn(conn) as (c, owns):
            if target == "bookstack" and bookstack_page_id is not None:
                await c.execute(
                    f"UPDATE notes SET {col} = 1, bookstack_page_id = ? WHERE id = ?",
                    (bookstack_page_id, note_id),
                )
            else:
                await c.execute(f"UPDATE notes SET {col} = 1 WHERE id = ?", (note_id,))
            if owns:
                await c.commit()

    async def mark_sync_error(
        self,
        note_id: str,
        target: str,
        *,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Setzt Sync-Status auf 2 (error) — wird beim nächsten Sync-Job erneut versucht."""
        col = {"knowledge": "synced_knowledge",
               "bookstack": "synced_bookstack",
               "github":    "synced_github"}[target]
        async with _conn(conn) as (c, owns):
            await c.execute(f"UPDATE notes SET {col} = 2 WHERE id = ?", (note_id,))
            if owns:
                await c.commit()

    async def delete(
        self, note_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            if owns:
                await c.commit()
```

### 6.6 AgentRepository

```python
# egon2/repositories/agents.py
from __future__ import annotations

import json
import uuid

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import Agent
from egon2.repositories._base import _conn


class AgentRepository:
    async def get(
        self, agent_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> Agent | None:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
            row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["capabilities"] = json.loads(d.get("capabilities") or "[]")
        d["is_active"] = bool(d["is_active"])
        return Agent.model_validate(d)

    async def list_active(
        self, *, conn: aiosqlite.Connection | None = None,
    ) -> list[Agent]:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(
                "SELECT * FROM agents WHERE is_active = 1 ORDER BY id"
            )
            rows = await cur.fetchall()
        out: list[Agent] = []
        for r in rows:
            d = dict(r)
            d["capabilities"] = json.loads(d.get("capabilities") or "[]")
            d["is_active"] = bool(d["is_active"])
            out.append(Agent.model_validate(d))
        return out

    async def upsert(
        self, agent: Agent, *, conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO agents (id, name, description, system_prompt,
                                       capabilities, work_location, prompt_version,
                                       is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       name = excluded.name,
                       description = excluded.description,
                       system_prompt = excluded.system_prompt,
                       capabilities = excluded.capabilities,
                       work_location = excluded.work_location,
                       prompt_version = excluded.prompt_version,
                       is_active = excluded.is_active,
                       updated_at = excluded.updated_at""",
                (agent.id, agent.name, agent.description, agent.system_prompt,
                 json.dumps(agent.capabilities), agent.work_location,
                 agent.prompt_version, int(agent.is_active),
                 iso_utc_now(), iso_utc_now()),
            )
            if owns:
                await c.commit()

    async def set_active(
        self, agent_id: str, active: bool, *, conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute(
                "UPDATE agents SET is_active = ?, updated_at = ? WHERE id = ?",
                (int(active), iso_utc_now(), agent_id),
            )
            if owns:
                await c.commit()

    async def bump_prompt_version(
        self,
        agent_id: str,
        new_prompt: str,
        *,
        changed_by: str = "system",
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        """Erhöht prompt_version, schreibt new_prompt und legt einen
        agent_prompt_history-Eintrag mit der NEUEN Version an.

        Atomarität: wenn extern conn übergeben → kein commit; sonst eigene Transaktion.
        """
        async with _conn(conn) as (c, owns):
            if owns:
                await c.execute("BEGIN")
            try:
                await c.execute(
                    """UPDATE agents
                           SET system_prompt = ?,
                               prompt_version = prompt_version + 1,
                               updated_at = ?
                           WHERE id = ?""",
                    (new_prompt, iso_utc_now(), agent_id),
                )
                cur = await c.execute(
                    "SELECT prompt_version FROM agents WHERE id = ?", (agent_id,),
                )
                row = await cur.fetchone()
                new_version = row[0] if row else None
                await c.execute(
                    """INSERT INTO agent_prompt_history
                           (id, agent_id, prompt_version, system_prompt, created_at, changed_by)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), agent_id, new_version, new_prompt, iso_utc_now(), changed_by),
                )
                if owns:
                    await c.execute("COMMIT")
            except Exception:
                if owns:
                    await c.execute("ROLLBACK")
                raise
```

### 6.7 AgentAssignmentRepository

```python
# egon2/repositories/agent_assignments.py
from __future__ import annotations

import json
import uuid

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import AgentAssignment, AssignmentStatus
from egon2.repositories._base import _conn


class AgentAssignmentRepository:
    async def create_assignment(
        self,
        agent_id: str,
        task_id: str,
        brief: dict,
        *,
        conn: aiosqlite.Connection | None = None,
    ) -> AgentAssignment:
        """Legt ein neues Assignment an.

        WICHTIG: Im Multi-Repo-Transaktions-Pattern (§7) wird diese Methode mit
        conn= aufgerufen und committet NICHT — der äußere BEGIN/COMMIT regelt das.
        """
        record_id = str(uuid.uuid4())
        now_iso = iso_utc_now()
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO agent_assignments
                       (id, agent_id, task_id, brief, status, assigned_at)
                   VALUES (?, ?, ?, ?, 'running', ?)""",
                (record_id, agent_id, task_id, json.dumps(brief), now_iso),
            )
            if owns:
                await c.commit()
            cur = await c.execute(
                "SELECT * FROM agent_assignments WHERE id = ?", (record_id,),
            )
            row = await cur.fetchone()
        d = dict(row)
        d["brief"] = json.loads(d.get("brief") or "{}")
        return AgentAssignment.model_validate(d)

    async def complete(
        self,
        assignment_id: str,
        *,
        status: AssignmentStatus,
        result: str | None,
        tokens_input: int | None,
        tokens_output: int | None,
        cost_estimate: float | None,
        duration_ms: int | None,
        quality_score: int | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute(
                """UPDATE agent_assignments
                       SET status = ?, result = ?, tokens_input = ?,
                           tokens_output = ?, cost_estimate = ?, duration_ms = ?,
                           quality_score = ?, completed_at = ?
                       WHERE id = ?""",
                (status, result, tokens_input, tokens_output, cost_estimate,
                 duration_ms, quality_score, iso_utc_now(), assignment_id),
            )
            if owns:
                await c.commit()

    async def cost_sum_last_n_days(
        self, days: int = 7, *, conn: aiosqlite.Connection | None = None,
    ) -> float:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(
                """SELECT COALESCE(SUM(cost_estimate), 0.0)
                       FROM agent_assignments
                       WHERE assigned_at >= strftime('%Y-%m-%dT%H:%M:%S.000000Z', 'now', ?)""",
                (f"-{days} days",),
            )
            row = await cur.fetchone()
        return float(row[0]) if row else 0.0

    async def list_for_task(
        self, task_id: str, *, conn: aiosqlite.Connection | None = None,
    ) -> list[AgentAssignment]:
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(
                "SELECT * FROM agent_assignments WHERE task_id = ? "
                "ORDER BY assigned_at DESC",
                (task_id,),
            )
            rows = await cur.fetchall()
        out: list[AgentAssignment] = []
        for r in rows:
            d = dict(r)
            d["brief"] = json.loads(d.get("brief") or "{}")
            out.append(AgentAssignment.model_validate(d))
        return out
```

### 6.8 HealthCheckRepository

```python
# egon2/repositories/health_checks.py
from __future__ import annotations

import json
import uuid

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import HealthCheck, HealthCheckType, HealthStatus
from egon2.repositories._base import _conn


class HealthCheckRepository:
    async def record(
        self,
        check_type: HealthCheckType,
        target: str,
        status: HealthStatus,
        *,
        findings: list[str] | None = None,
        action_taken: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> HealthCheck:
        record_id = str(uuid.uuid4())
        now_iso = iso_utc_now()
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO health_checks
                       (id, check_type, target, status, findings, action_taken, checked_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (record_id, check_type, target, status,
                 json.dumps(findings or []), action_taken, now_iso),
            )
            if owns:
                await c.commit()
            cur = await c.execute(
                "SELECT * FROM health_checks WHERE id = ?", (record_id,),
            )
            row = await cur.fetchone()
        d = dict(row)
        d["findings"] = json.loads(d.get("findings") or "[]")
        return HealthCheck.model_validate(d)

    async def latest(
        self,
        check_type: HealthCheckType | None = None,
        *,
        limit: int = 50,
        conn: aiosqlite.Connection | None = None,
    ) -> list[HealthCheck]:
        sql = "SELECT * FROM health_checks"
        params: list[object] = []
        if check_type:
            sql += " WHERE check_type = ?"
            params.append(check_type)
        sql += " ORDER BY checked_at DESC LIMIT ?"
        params.append(limit)
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(sql, params)
            rows = await cur.fetchall()
        out: list[HealthCheck] = []
        for r in rows:
            d = dict(r)
            d["findings"] = json.loads(d.get("findings") or "[]")
            out.append(HealthCheck.model_validate(d))
        return out
```

### 6.9 SchedulerLogRepository

```python
# egon2/repositories/scheduler_log.py
from __future__ import annotations

import uuid
from typing import Literal

import aiosqlite

from egon2.database import iso_utc_now
from egon2.models import SchedulerLogEntry
from egon2.repositories._base import _conn

JobStatus = Literal["ok", "failed", "skipped"]


class SchedulerLogRepository:
    async def start(
        self, job_name: str, *, conn: aiosqlite.Connection | None = None,
    ) -> str:
        entry_id = str(uuid.uuid4())
        async with _conn(conn) as (c, owns):
            await c.execute(
                """INSERT INTO scheduler_log (id, job_name, started_at, status)
                   VALUES (?, ?, ?, 'ok')""",
                (entry_id, job_name, iso_utc_now()),
            )
            if owns:
                await c.commit()
        return entry_id

    async def finish(
        self,
        entry_id: str,
        status: JobStatus,
        *,
        output: str | None = None,
        conn: aiosqlite.Connection | None = None,
    ) -> None:
        async with _conn(conn) as (c, owns):
            await c.execute(
                """UPDATE scheduler_log
                       SET finished_at = ?, status = ?, output = ?
                       WHERE id = ?""",
                (iso_utc_now(), status, output, entry_id),
            )
            if owns:
                await c.commit()

    async def latest(
        self,
        job_name: str | None = None,
        *,
        limit: int = 50,
        conn: aiosqlite.Connection | None = None,
    ) -> list[SchedulerLogEntry]:
        sql = "SELECT * FROM scheduler_log"
        params: list[object] = []
        if job_name:
            sql += " WHERE job_name = ?"
            params.append(job_name)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        async with _conn(conn) as (c, _owns):
            cur = await c.execute(sql, params)
            rows = await cur.fetchall()
        return [SchedulerLogEntry.model_validate(dict(r)) for r in rows]
```

---

## 7. Transaktion über mehrere Repositories

Der Agent-Dispatcher (HLD §7.2) verlangt: **Task-Update + agent_assignment** in **einer** Transaktion. Dies wird über das `conn=`-Parameter-Pattern gelöst (siehe §6.1).

**Verbindliche Regel:** Die Repository-Methoden `task_repo.update_status()` und `assignment_repo.create_assignment()` / `assignment_repo.complete()` MÜSSEN atomar in einer Transaktion laufen. Ohne diese Atomarität entsteht inkonsistenter Zustand (Task ist `done`, aber kein Assignment-Record — oder umgekehrt).

```python
# egon2/core/agent_dispatcher.py (Auszug)
from egon2.database import db
from egon2.repositories.tasks import TaskRepository
from egon2.repositories.agent_assignments import AgentAssignmentRepository

tasks = TaskRepository()
assignments = AgentAssignmentRepository()


async def dispatch_assignment(
    task_id: str, agent_id: str, brief: dict,
) -> str:
    """Atomare Operation: Task auf 'running' setzen + Assignment anlegen."""
    async with db.connection() as conn:
        await conn.execute("BEGIN")
        try:
            await tasks.update_status(
                task_id, "running", assigned_agent=agent_id, conn=conn,
            )
            assignment = await assignments.create_assignment(
                agent_id=agent_id, task_id=task_id, brief=brief, conn=conn,
            )
            await conn.execute("COMMIT")
            return assignment.id
        except Exception:
            await conn.execute("ROLLBACK")
            raise


async def finalise_assignment(
    task_id: str, assignment_id: str, status, result: str, **metrics,
) -> None:
    """Atomare Operation: Assignment komplettieren + Task finalisieren."""
    async with db.connection() as conn:
        await conn.execute("BEGIN")
        try:
            await assignments.complete(
                assignment_id, status=status, result=result, conn=conn, **metrics,
            )
            await tasks.update_status(
                task_id,
                "done" if status == "done" else "failed",
                result=result,
                conn=conn,
            )
            await conn.execute("COMMIT")
        except Exception:
            await conn.execute("ROLLBACK")
            raise
```

Weil die Repository-Methoden `conn` extern erhalten, rufen sie kein eigenes `commit()` auf — der äußere `BEGIN`/`COMMIT` umschließt beide Statements. Bei einem Fehler im zweiten Statement wird auch das erste zurückgerollt.

---

## 8. Test-Strategie (Kurzfassung)

| Ebene | Tool | Was |
|---|---|---|
| Unit | `pytest` + `pytest-asyncio` | Repository-Methoden gegen `:memory:`-DB |
| Migration | dedizierter Test | Migration zweimal hintereinander → keine Duplikate; absichtlicher Fehler in Statement N → Rollback verifizieren |
| Multi-Repo-TX | dedizierter Test | `dispatch_assignment` mit Mock-Fehler im 2. Statement → kein Task-Update sichtbar |
| Pragma-Persistenz | dedizierter Test | Mehrere Connections öffnen, jede prüft `PRAGMA foreign_keys`, `synchronous`, `busy_timeout` |
| DATETIME-Format | dedizierter Test | Insert ohne explicit timestamp → DB-Default matcht Regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$` |
| Knowledge-Migration | dedizierter Test | Idempotenz: zweite Ausführung ist No-Op; SQLite-Versions-Gate löst aus bei < 3.35 |
| Backup | Shell-Test | Skript erzeugt valide DB für egon2.db UND scheduler.db, Rotation behält genau 7 (mit `touch -d`-Mock) |
| Integration | echte DB-Datei in `tmp_path` | End-to-End Task → Assignment → Completion |

---

## 9. Offene Punkte

- **Volltext-Suche im Knowledge Store**: SQLite FTS5 — Entscheidung beim MCP-Server-Team auf LXC 107. Bis dahin wird `/search` als Tag-/`LIKE`-Suche dokumentiert (sinnvoll bis ~10k Einträge). Bei FTS5-Einführung: Schema mit `tokenize='unicode61 remove_diacritics 2'` (deutsche Umlaute) plus Initial-Backfill — siehe Audit §2.2/2.3.
- **Backup off-site**: aktuell nur lokal auf LXC 128 — Einschränkungen dokumentiert in §9.1. Disaster-Recovery zusätzlich über GitHub-Sync (`egon2-knowledge`, HLD §8.2) möglich.
- **`agent_assignments.executed_at`** (Audit §10.3): tatsächlicher Ausführungs-Ort für `lxc_any`-Routing — als HOCH-MITTEL eingestuft, später ergänzen.
- **`updated_at`-Trigger** (Audit §1.6): aktuell setzt der Repository-Code `updated_at` — als Belt-and-Suspenders ggf. später Trigger ergänzen.
