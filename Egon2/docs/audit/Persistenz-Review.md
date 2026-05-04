# Technisches Review — LLD-Persistenz.md (Egon2)

**Reviewer:** Claude (Python/SQLite-Expert)
**Stand:** 2026-05-02
**Bezug:** `docs/LLD-Persistenz.md` v1.0, abgeglichen mit `docs/HLD-Egon2.md` v1.5 §8 und `docs/LLD-Core.md`
**Bewertung gesamt:** Solide, produktionsreif strukturiert. Mehrere KRITISCHE Punkte beim Migrations-Rollback, beim FTS5-Thema (offen gelassen), bei der Knowledge-Migration auf laufendem MCP-Server und beim Backup-Skript. Eine handvoll HOCH-priorisierte Defekte rund um Pydantic-Aliasing, BEGIN/COMMIT-Doppelung und 7-Tage-Off-by-One.

Schweregrade: **KRITISCH** (blockiert Inbetriebnahme oder verursacht Datenverlust) · **HOCH** (Bug, Race oder Designfehler — vor Go-live fixen) · **MITTEL** (sollte vor Hardening behoben werden) · **NIEDRIG** (Polish, Dokumentation).

---

## 1. SQLite Schema-Korrektheit

### KRITISCH-1.1 — `agents`-Tabelle vor `tasks` anlegen lassen
In `MIGRATIONS[1]` (Zeile 158-175) ist die Reihenfolge:
```
SQL_CREATE_CONVERSATIONS,
SQL_CREATE_TASKS,        ← referenziert agents(id) per FK!
SQL_CREATE_NOTES,
SQL_CREATE_AGENTS,
…
```
Mit `PRAGMA foreign_keys = ON` zieht SQLite die Constraint-Prüfung beim Insert, **das CREATE TABLE selbst ist tolerant** — formal lauffähig, aber sehr fehleranfällig. Sobald `_seed_agents()` greift bevor die FK-Tabelle existiert (sie tut es nicht, weil im selben Lauf), oder wenn eine spätere Migration FK-Validierung erzwingt (`PRAGMA foreign_key_check`), kippt der Setup. Reihenfolge fixen: **erst `agents`, dann `tasks`/`agent_assignments`**.

### HOCH-1.2 — Redundanter Unique-Index auf `agents.id`
```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_id_unique ON agents (id);
```
`id` ist bereits `PRIMARY KEY` → SQLite legt automatisch einen Unique-Index an. Der zusätzliche Index ist tot, kostet Schreib-IO und Speicher. **Entfernen.**

### HOCH-1.3 — Fehlender Index auf `agent_assignments(status, assigned_at)`
Der Controller-Job (HLD §11.2: „Summe der letzten 7 `agent_assignments.cost_estimate`") läuft täglich und filtert nach `assigned_at >= datetime('now', '-7 days')`. Ohne Index Full-Scan. Empfehlung:
```sql
CREATE INDEX IF NOT EXISTS idx_assignments_assigned_at
    ON agent_assignments (assigned_at DESC);
```

### HOCH-1.4 — `tasks.assigned_agent` Index fehlt
TaskManager `list_active()` und Recovery filtern u.a. nach `status` — abgedeckt — aber das Inspector-/Analyst-Reporting will Tasks pro Spezialist sehen. Joins über `assigned_agent` ohne Index. Empfehlung:
```sql
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent
    ON tasks (assigned_agent) WHERE assigned_agent IS NOT NULL;
```

### MITTEL-1.5 — `notes` ohne Sync-Status-Index
`list_pending_sync()` (Zeile 1083) macht `WHERE synced_knowledge = 0`. Ohne Index Full-Scan. Empfehlung Partial Index:
```sql
CREATE INDEX IF NOT EXISTS idx_notes_pending_knowledge
    ON notes (created_at) WHERE synced_knowledge = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_bookstack
    ON notes (created_at) WHERE synced_bookstack = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_github
    ON notes (created_at) WHERE synced_github = 0;
```

### MITTEL-1.6 — `updated_at` wird nicht automatisch aktualisiert
Die Tabellen `tasks` und `agents` haben `updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP`, aber kein Trigger. Repository-Methoden setzen das manuell — ok, aber ein vergessener Pfad führt zu stale `updated_at`. Empfehlung Belt-and-Suspenders:
```sql
CREATE TRIGGER IF NOT EXISTS trg_tasks_updated
AFTER UPDATE ON tasks FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```
Analog für `agents`.

### NIEDRIG-1.7 — `conversations.role` vs HLD
HLD §8.1 listet nur `'user'|'assistant'`, das LLD ergänzt `'system'` im CHECK. Bewusst, aber Diff zum HLD dokumentieren.

### NIEDRIG-1.8 — `health_checks.status` Enum unterscheidet sich zum HLD
LLD: `'ok','repaired','warning','degraded','critical'` — HLD listet nur 4 Werte (ohne `critical`). Akzeptabel, sollte aber im HLD nachgezogen werden.

---

## 2. FTS5-Integration

### KRITISCH-2.1 — FTS5 für Knowledge Store: ungeklärt, aber bereits gebraucht
Abschnitt 9 sagt: „Volltext-Suche im Knowledge Store: SQLite FTS5 — wird vom MCP-Server-Team auf LXC 107 entschieden, nicht Bestandteil dieses LLD." Gleichzeitig spezifiziert §4.4 den Endpoint `POST /search` mit Query-Feld → der Client erwartet semantische/Volltext-Suche. **Inkonsistenz**. Entweder:
- (a) Entscheidung eskalieren und FTS5 in dieses LLD aufnehmen,
- (b) `/search` als reine Tag-/`LIKE`-Suche dokumentieren mit einer expliziten Performance-Grenze („nur sinnvoll bis ~10k Einträge").

### HOCH-2.2 — Empfohlenes FTS5-Schema (falls (a))
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_entries_fts USING fts5(
    title,
    content,
    tags,
    content='knowledge_entries',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

-- Sync-Trigger (contentless table braucht das nicht, content-rowid table aber doch)
CREATE TRIGGER IF NOT EXISTS ke_ai AFTER INSERT ON knowledge_entries BEGIN
    INSERT INTO knowledge_entries_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS ke_ad AFTER DELETE ON knowledge_entries BEGIN
    INSERT INTO knowledge_entries_fts(knowledge_entries_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS ke_au AFTER UPDATE ON knowledge_entries BEGIN
    INSERT INTO knowledge_entries_fts(knowledge_entries_fts, rowid, title, content, tags)
    VALUES ('delete', old.id, old.title, old.content, old.tags);
    INSERT INTO knowledge_entries_fts(rowid, title, content, tags)
    VALUES (new.id, new.title, new.content, new.tags);
END;
```
Wichtig: **`tokenize='unicode61 remove_diacritics 2'`** ist für deutsche Texte mit Umlauten essenziell — ohne wird „Mütze" nicht von „mutze" gefunden. `porter` würde zwar stemmen, ist aber nur englisch.

### MITTEL-2.3 — Initial-Backfill bei bestehenden Einträgen
Die Knowledge-DB existiert bereits. Wenn FTS5 nachgerüstet wird, muss ein einmaliger Backfill laufen:
```sql
INSERT INTO knowledge_entries_fts(rowid, title, content, tags)
SELECT id, title, content, tags FROM knowledge_entries;
```
In der Migration unbedingt nach Trigger-Anlage und vor dem ersten Query.

---

## 3. Migrations-System

### KRITISCH-3.1 — Keine Atomarität pro Migration
`_run_migrations()` (Zeile 96-114) ruft `await conn.commit()` **nur am Ende** der Schleife pro Version. Bei einem Fehler in Statement N würde der `INSERT INTO schema_version` nie geschrieben — gut. **Aber:** die bisherigen `await conn.execute(stmt)` werden bei aiosqlite ohne explizites BEGIN automatisch in eigenen Mini-Transaktionen committet (autocommit). Das heißt: bricht Statement 7 von 14 ab, sind 1-6 schon dauerhaft drin, `schema_version` ist nicht aktualisiert → beim nächsten Start läuft die ganze Migration wieder, Statement 1-6 gehen via `IF NOT EXISTS` durch, aber jedes `ALTER TABLE ADD COLUMN` ohne `IF NOT EXISTS`-Check (wie in v2+) crasht.

**Fix:** Migration in expliziter Transaktion ausführen:
```python
for version, statements in MIGRATIONS.items():
    if version <= current:
        continue
    logger.info("Applying migration v%d", version)
    await conn.execute("BEGIN")
    try:
        for stmt in statements:
            await conn.execute(stmt)
        await conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
```
**Achtung:** SQLite kann `CREATE TABLE` und `CREATE INDEX` in einer Transaktion zurückrollen. **`ALTER TABLE ADD COLUMN` ist seit SQLite 3.25 ebenfalls transaktional sicher** — passt für unsere Version (Debian 12 → 3.40+).

### HOCH-3.2 — Rollback einer fehlgeschlagenen Migration
Es gibt **keinen Down-Pfad**. Das ist für ein Singleton-Service akzeptabel, sollte aber dokumentiert werden: „Recovery = Backup vor Migration einspielen". Empfehlung: vor jeder Migration > 1 automatisch `egon2.db` → `egon2.db.pre-vN.bak` kopieren (per `VACUUM INTO` während des laufenden Service unsicher, daher in `initialise()` **vor** `_run_migrations()`).

### MITTEL-3.3 — Migration-Reihenfolge
`MIGRATIONS: dict[int, tuple[str, ...]]` — `dict` ist seit Python 3.7 insertion-ordered, aber Versionssprünge (z.B. {1, 3} ohne 2) wären stille Fehler. Empfehlung: explizit sortieren und Lückencheck:
```python
versions = sorted(MIGRATIONS.keys())
assert versions == list(range(1, max(versions) + 1)), "Migration gaps"
for version in versions:
    if version <= current:
        continue
    ...
```

### NIEDRIG-3.4 — `schema_version.version` als PRIMARY KEY
PK auf einer monoton wachsenden Versionsnummer ist ok, aber für die Audit-History wäre `(version, applied_at)`-Composite sinnvoller — und `applied_at` als `TEXT` mit ISO8601 (siehe §9 unten).

---

## 4. WAL-Modus Pragmas

### HOCH-4.1 — Pragmas werden in `initialise()` einmalig gesetzt, in `connection()` nur `foreign_keys`
Reihenfolge in `initialise()` (Zeile 84-94) ist korrekt: `journal_mode=WAL` zuerst (persistent in der DB-Datei → bleibt gesetzt), dann `synchronous`, `foreign_keys`, etc. **`journal_mode` ist persistent**, `foreign_keys` und `synchronous` sind **per-connection** und müssen bei jeder neuen Connection gesetzt werden. Der Context-Manager `connection()` setzt nur `foreign_keys = ON` — `synchronous=NORMAL`, `temp_store`, `mmap_size`, `cache_size`, `busy_timeout` fallen für jede neue Connection auf den Default zurück.

**Fix:** Per-Connection-Pragmas in den Context-Manager verschieben:
```python
PER_CONNECTION_PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA temp_store = MEMORY",
    "PRAGMA cache_size = -16384",
    "PRAGMA busy_timeout = 5000",
)

@asynccontextmanager
async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(self.path)
    conn.row_factory = aiosqlite.Row
    try:
        for pragma in PER_CONNECTION_PRAGMAS:
            await conn.execute(pragma)
        yield conn
    finally:
        await conn.close()
```
`mmap_size` und `journal_mode` muss man nicht pro Connection setzen.

### MITTEL-4.2 — `busy_timeout` zu niedrig?
5000 ms ist Standard-OK für ein lokales Service mit geringer Concurrency. Bei längeren Backup-/Migrations-Operationen reicht es nicht — der Backup öffnet die DB exklusiv via `.backup`-API, kann aber bei einer gleichzeitigen Schreib-Operation > 5 s blockieren. Empfehlung: `busy_timeout = 15000` für den Backup-Pfad (oder Backup-Job pausiert kurz Schreibverkehr).

### NIEDRIG-4.3 — `mmap_size = 128 MiB`
Auf einem LXC mit 6 GB RAM unkritisch. OK.

---

## 5. aiosqlite Repository Pattern

### HOCH-5.1 — Doppeltes BEGIN/COMMIT in Multi-Repo-Transaktion (Abschnitt 7)
```python
async with db.connection() as conn:
    await conn.execute("BEGIN")
    try:
        await assignments.complete(..., conn=conn, ...)   # ruft await c.commit()!
        await tasks.update_status(..., conn=conn)         # ruft await c.commit()!
        await conn.execute("COMMIT")
```
**KRITISCH-Bug:** Jede Repository-Methode (z.B. `AgentAssignmentRepository.complete`, Zeile 1283-1285) endet mit `await c.commit()`. Wird sie mit übergebenem `conn` aufgerufen, committet sie die laufende Transaktion **mittendrin**. Das BEGIN/COMMIT in `finalise_assignment` ist Schein.

**Fix:** Repository-Methoden dürfen **nur dann** committen, wenn sie die Connection selbst geöffnet haben. Pattern:
```python
async def complete(self, ..., conn: aiosqlite.Connection | None = None) -> None:
    async with _conn(conn) as c:
        await c.execute(...)
        if conn is None:           # nur eigenen Cycle committen
            await c.commit()
```
Den `_conn`-Helper entsprechend erweitern, z.B. zweites yield-Tupel `(c, owns)`.

### HOCH-5.2 — Connection wird nicht in einer Transaktion geöffnet
aiosqlite/Python sqlite3 startet im **Default isolation_level="" (deferred)**. Das bedeutet: das erste `INSERT/UPDATE` startet implizit eine Transaktion, die durch `commit()` geschlossen wird. Alles ok für die Single-Statement-Repository-Methoden — aber für Lese-Pfade (`SELECT`) **wird ebenfalls eine Transaktion gestartet**, die nie commit'tet wird. Mehrere serielle SELECTs auf derselben Connection sehen dann einen festgefrorenen Snapshot. Da wir die Connection sofort schließen, harmlos — aber `isolation_level=None` (autocommit) wäre semantisch klarer:
```python
conn = await aiosqlite.connect(self.path, isolation_level=None)
```
Dann muss man Multi-Statement-Transaktionen explizit mit `BEGIN`/`COMMIT` umrahmen — das passiert in §7 ohnehin.

### MITTEL-5.3 — `_conn`-Helper verschluckt Doppel-Yield-Risiko
```python
@asynccontextmanager
async def _conn(conn: aiosqlite.Connection | None) -> AsyncIterator[aiosqlite.Connection]:
    if conn is not None:
        yield conn
        return
    async with db.connection() as c:
        yield c
```
Funktional korrekt, aber wenn ein Aufrufer den Context betritt und in `aiosqlite.Row` ein Pickling-Problem hat, kann `aclose` doppelt aufgerufen werden. Empfehlung: `try/finally` mit explizitem `pass` im if-Zweig — defensiver Stil.

### MITTEL-5.4 — `cur.rowcount` bei `aiosqlite`
`ConversationRepository.purge_older_than` returnt `cur.rowcount or 0`. aiosqlite's Cursor kann `rowcount = -1` zurückgeben, wenn der Wert nicht bekannt ist. Bei einfachem DELETE funktioniert das, aber `or 0` würde -1 nicht abfangen → falscher Returnwert. Sicherer:
```python
return max(cur.rowcount, 0)
```

### NIEDRIG-5.5 — `Conversation.timestamp` Konvertierung
Pydantic-Validierung schlägt fehl, wenn aus SQLite ein TEXT zurückkommt, der nicht ISO8601 ist. Da wir per `isoformat()` schreiben und über die Default-Spalte `CURRENT_TIMESTAMP` (Format `YYYY-MM-DD HH:MM:SS`) auch andere Werte landen können — kann **inkonsistent** werden. Siehe §9.

---

## 6. Knowledge Store Migration

### KRITISCH-6.1 — Migration auf laufendem MCP-Server
`ALTER TABLE … ADD COLUMN` mit `NOT NULL DEFAULT 'general'` ist seit SQLite 3.35+ schnell (constant-time), aber:
- Wenn der MCP-Server eine **offene WAL-Connection** hält, sieht er die neuen Spalten **erst nach der nächsten Transaktion**.
- Wenn der MCP-Server `SELECT *` macht und die Spaltenanzahl cacht, crasht er bei Schemawechsel zur Laufzeit.

**Empfehlung:** Migration **niemals** bei laufendem Server fahren. Procedure:
1. MCP-Server stoppen (`systemctl stop mcp-knowledge`),
2. Backup der DB (`cp` reicht — Server ist down),
3. `migrate(db_path)` ausführen,
4. `PRAGMA integrity_check`,
5. Server starten.

Das LLD muss diesen Ablauf dokumentieren — derzeit suggeriert §4.3, dass die Migration „beliebig oft" zur Laufzeit läuft.

### HOCH-6.2 — `ALTER TABLE … ADD COLUMN NOT NULL DEFAULT` für bestehende Zeilen
SQLite 3.35+ unterstützt das, aber **nur mit konstantem Default**. `'general'` und `5` sind konstant — passt. **Aber:** wenn eine ältere SQLite-Version auf LXC 107 läuft (< 3.35), schlägt das fehl. Empfehlung:
```python
async def migrate(...):
    async with aiosqlite.connect(db_path) as conn:
        cur = await conn.execute("SELECT sqlite_version()")
        version = (await cur.fetchone())[0]
        major, minor, *_ = map(int, version.split("."))
        if (major, minor) < (3, 35):
            raise RuntimeError(f"SQLite >= 3.35 needed, got {version}")
```

### HOCH-6.3 — `refs` als Workaround statt `references`
Die Reservierung von `REFERENCES` als SQL-Keyword ist korrekt erkannt. Aber das Pydantic-Modell aliased nur in **eine** Richtung:
```python
references: list[KnowledgeReference] = Field(default_factory=list, alias="refs")
```
Mit `populate_by_name=True` akzeptiert das Modell beim Lesen sowohl `refs` als auch `references`. Beim Senden (`model_dump(mode="json")` ohne `by_alias=True`) wird `references` ausgegeben → **HTTP-Server bekommt `references`**, schreibt aber Spalte `refs`. **Inkonsistenz mit dem REST-Layer**. Fix: konsistent `by_alias=True`:
```python
r = await self._client.post("/entries", json=payload.model_dump(mode="json", by_alias=True))
```
Plus: bei `KnowledgeEntryCreate` denselben Alias setzen (fehlt aktuell):
```python
class KnowledgeEntryCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ...
    references: list[KnowledgeReference] = Field(default_factory=list, alias="refs")
```

### MITTEL-6.4 — `_existing_columns` ohne Quoting
```python
cur = await conn.execute(f"PRAGMA table_info({table})")
```
F-string mit Tabellennamen → SQL-Injection-Vektor. Hier nicht ausnutzbar (intern), aber in OSS-Code mit fixiertem Wert besser:
```python
cur = await conn.execute("SELECT name FROM pragma_table_info(?)", (table,))
```

---

## 7. mcp_client.py HTTP-Endpunkte

### HOCH-7.1 — Pagination fehlt
`GET /entries?limit=50` ohne `offset` oder `cursor`. Bei wachsendem Knowledge Store (mehrere tausend Einträge) ist das ein Problem. Empfehlung Cursor-Pagination:
```
GET /entries?limit=50&after_id=12345
Response: { "items":[...], "next_cursor":"12395" }
```
Oder offset-basiert, falls einfacher.

### MITTEL-7.2 — `POST /search` ohne Pagination
Gleicher Punkt — Search sollte auch Cursor unterstützen.

### MITTEL-7.3 — `DELETE` ist Soft-Delete, aber kein Hard-Delete-Endpoint
`is_active=0` ist sinnvoll, aber für DSGVO-Anforderungen oder GitHub-Sync-Cleanup fehlt ein expliziter Hard-Delete (`DELETE /entries/{id}?hard=true` oder eigener Endpoint).

### MITTEL-7.4 — `httpx` Limits
```python
limits = httpx.Limits(max_connections=5, max_keepalive_connections=5)
```
Keine Retry-Strategie. Für einen lokalen Service ok, aber `httpx` hat eingebautes Retry über `transport=httpx.AsyncHTTPTransport(retries=3)` — empfohlen für transiente Netzfehler.

### NIEDRIG-7.5 — `health()` schluckt Exceptions nicht
Wenn der MCP-Server down ist, wirft `_client.get("/health")` `ConnectError` — `health()` returnt nicht `False`, sondern wirft. Wenn das Absicht ist (Fail-Loud) — dokumentieren. Sonst:
```python
async def health(self) -> bool:
    try:
        r = await self._client.get("/health")
    except httpx.HTTPError:
        return False
    return r.status_code == 200 and r.json().get("status") == "ok"
```

### NIEDRIG-7.6 — `Self` aus `typing` braucht Python 3.11+
Im Modul `from typing import Self`. Das LLD geht von Python 3.12+ aus (siehe HLD §10) — passt, aber explizit erwähnen.

---

## 8. Backup-Skript

### KRITISCH-8.1 — `find -mtime +7` löscht erst Dateien älter als **7 vollen Tagen** (~ 8 Tage alt)
`find -mtime +7` matcht Dateien mit `mtime > 7*24h`. Bei täglichem Backup um 02:00 wird das 8. Backup also erst gelöscht, **nachdem es 8 Tage alt ist**. Praxis: 8 Backups statt 7. Mehr Storage, kein Datenverlust — aber Off-by-One.

**Fix-Optionen:**
- `-mtime +6` (löscht alles > 6 Tage alt = behält 7 jüngste Backups inkl. heute),
- oder besser deterministisch: Liste mit `ls -1t backup/egon2-*.db | tail -n +8 | xargs -r rm`.

### HOCH-8.2 — `sqlite3 .backup` und WAL: korrekt, aber WAL-Cleanup
Die `.backup`-API kopiert Page für Page und ist **WAL-safe** — die WAL-Datei wird mitberücksichtigt. **Aber** das Ziel-File hat keine WAL (Single-File Backup), was für ein Restore ausreichend ist. **Wichtig:** wenn jemand das Backup zurückspielt **und der Service noch läuft**, muss er vorher gestoppt sein, sonst überlagert die laufende WAL die Restore-DB.

### HOCH-8.3 — Subprocess-Approach im APScheduler-Hook
```python
proc = await asyncio.create_subprocess_exec("/opt/egon2/scripts/backup_egon2.sh", ...)
```
Funktioniert, aber das Skript läuft als gleicher User wie der Egon2-Service. Wenn der Service unter `egon2:egon2` läuft und `/var/log/egon2/` gehört `root:root` → **ENOENT/EACCES**. Setup-Hinweis im LLD ergänzen: `chown egon2:egon2 /var/log/egon2/` und Backup-Verzeichnis.

### MITTEL-8.4 — Pipe-Konstrukt im Find/Rotate kaputt
```bash
find … -mtime "+${RETENTION_DAYS}" -print -delete | while read -r removed; do
    log "Rotated out: ${removed}"
done
```
`-delete` löscht **bevor** der Print durch die Pipe kommt — funktioniert, aber `-print -delete` in dieser Reihenfolge ist trickreich. **Cleaner**:
```bash
mapfile -t removed < <(find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'egon2-*.db' -mtime "+${RETENTION_DAYS}")
for f in "${removed[@]}"; do
    rm -f "$f" && log "Rotated out: $f"
done
```

### MITTEL-8.5 — `PRAGMA integrity_check` nach `.backup`
Sinnvoll, **aber:** `integrity_check` läuft auf der **kopierten** Datei und ist langsam (sequentieller Scan über alle Pages). Bei wachsender DB (>500 MB) > 30 s. Akzeptabel als Tageslauf. Alternativ `PRAGMA quick_check` — schneller, weniger gründlich.

### NIEDRIG-8.6 — `set -euo pipefail` und ERR-Trap
Korrekt verwendet. Plus: `LANG=C` setzen, damit `date -Iseconds` und `stat -c` reproduzierbar sind.

---

## 9. Datentypen und Constraints — DATETIME-Konsistenz

### HOCH-9.1 — Mischung TEXT (ISO8601) vs `CURRENT_TIMESTAMP`
SQLite hat keinen echten DATETIME-Typ. Die Spalten sind als `TIMESTAMP` deklariert (=`NUMERIC` Affinität), gefüllt werden sie:
- per `DEFAULT CURRENT_TIMESTAMP` → `'2026-05-02 13:14:15'` (Space-getrennt, **kein 'T'**, **keine TZ**)
- per Repository-Methode → `datetime.now(timezone.utc).isoformat()` → `'2026-05-02T13:14:15.123456+00:00'`

**Inkonsistenz:** zwei Formate in derselben Spalte. Pydantic kann beides parsen, aber ORDER-BY-Vergleiche per String funktionieren nur, wenn beide ISO-konform sind — `'2026-05-02 13:00'` < `'2026-05-02T12:00'` ist **lexikografisch** anders als zeitlich.

**Fix-Optionen:**
- (a) **Strikt ISO8601-UTC im Code**: in allen `INSERT`s `datetime.now(timezone.utc).isoformat(sep=' ')` (mit Space) oder `'T'`-konsistent. Default `CURRENT_TIMESTAMP` aus DB-Schema entfernen, Repository setzt immer.
- (b) **Unix-Epoch (REAL)**: schneller zu vergleichen, aber Lesbarkeit leidet.

Empfehlung **(a)** mit `'T'`-Separator (ISO8601-strikt) — `CURRENT_TIMESTAMP` aus dem Schema entfernen, NULL-Default per Code setzen.

### MITTEL-9.2 — Pydantic V2 + Naive vs. Aware Datetime
`Conversation.timestamp: datetime` akzeptiert beide Varianten. Wenn aus DB ein naiver String kommt, wird das Pydantic-Modell ein **naives** `datetime`-Objekt liefern → später `astimezone()` crasht. Empfehlung: in den Repository-Methoden nach `model_validate` `tz=timezone.utc` setzen oder Validator:
```python
@field_validator("timestamp", mode="after")
@classmethod
def ensure_tz(cls, v: datetime) -> datetime:
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
```

---

## 10. Fehlende Tabellen / Spalten / Doku

### HOCH-10.1 — Scheduler-DB nicht beschrieben
LLD §1 erwähnt `scheduler.db` „separat — von APScheduler verwaltet". Aber:
- Wer legt das Verzeichnis an?
- Wer macht das Backup?
- Wer überwacht das Wachstum (APScheduler-Default ist 30 Tage Job-History)?
Mindestens ein Satz „Backup-Skript erweitern um `scheduler.db`" gehört rein, sonst ist im DR-Fall der ganze Cron weg.

### HOCH-10.2 — `tasks.intent` fehlt
HLD §6.3 nennt im Brief-Format ein `intent`-Feld („chat", „task", „note", „search", „question"). LLD-Core §2 verarbeitet das in der Conversation-Logik. Im Persistenz-Schema fehlt es jedoch — wenn der Intent persistiert werden soll (für Analyst-Stats), gehört eine Spalte `tasks.intent TEXT` rein.

### MITTEL-10.3 — `agent_assignments.work_location_actual` fehlt
HLD §6.5 unterscheidet `work_location` per Agent (`local|lxc126|lxc_any`). Für Auswertung „welcher Spezialist lief tatsächlich wo" wäre eine Spalte `executed_at TEXT` sinnvoll — sonst kann der Analyst Fehler bei `lxc_any`-Routing nicht aufdecken.

### MITTEL-10.4 — `agent_prompt_history`-Tabelle (im LLD §9 als „später" markiert)
Mit Versionssprüngen (`bump_prompt_version`) geht der alte Prompt-Text **verloren**. Für A/B-Tests und Rollback nötig. Empfehlung jetzt mit minimaler Tabelle:
```sql
CREATE TABLE IF NOT EXISTS agent_prompt_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE(agent_id, version)
);
```
Trigger oder Repository-Code legt bei jedem `bump_prompt_version` einen History-Eintrag an.

### NIEDRIG-10.5 — `health_checks.target` ohne Format-Constraint
Format-Konvention im LLD nicht festgelegt (z.B. `agent:archivist`, `system:backup`, `data:notes`). Für spätere Auswertung sinnvoll als CHECK oder zumindest Doku.

### NIEDRIG-10.6 — Connection-Lifecycle der `mcp_client`-Singleton
LLD instanziiert `McpClient` als Context-Manager. Wo wird er im Service-Lifecycle aufgemacht/geschlossen? Fehlt die Verknüpfung zu `lifespan`/Service-Start in `LLD-Architektur.md`.

---

## 11. Zusammenfassung — Top-10 vor Go-Live

| # | Schwere | Punkt |
|---|---|---|
| 1 | KRITISCH | §3.1 BEGIN/COMMIT pro Migration explizit (Atomarität) |
| 2 | KRITISCH | §5.1 Repository-Methoden dürfen mit übergebener `conn` **nicht** committen — Multi-Repo-Transaktion ist sonst kaputt |
| 3 | KRITISCH | §6.1 Knowledge-Migration darf nicht bei laufendem MCP-Server laufen — Procedure dokumentieren |
| 4 | KRITISCH | §1.1 Tabellen-Reihenfolge in MIGRATIONS[1]: agents vor tasks |
| 5 | KRITISCH | §2.1 FTS5 für `/search`-Endpoint klären (oder `LIKE`-Fallback dokumentieren) |
| 6 | KRITISCH | §8.1 Backup-Rotation: `-mtime +7` ist Off-by-One → `-mtime +6` |
| 7 | HOCH | §4.1 Per-Connection-Pragmas in `connection()` setzen (`synchronous`, `temp_store`, `cache_size`, `busy_timeout`) |
| 8 | HOCH | §6.3 Pydantic `by_alias=True` für refs/references — sonst inkonsistent zwischen Client und DB |
| 9 | HOCH | §9.1 DATETIME-Format-Konsistenz: ISO8601 strict, `CURRENT_TIMESTAMP`-Default raus oder `isoformat(sep=' ')` |
| 10 | HOCH | §1.3/1.4/1.5 fehlende Indizes für Cost-Sum, assigned_agent, Sync-Queue |

Behebung 1-6 ist Pflicht, 7-10 dringend empfohlen vor erstem Produktiv-Lauf.

---

## 12. Anhang — SQL-Korrekturen (kompakt)

```sql
-- Reihenfolge in MIGRATIONS[1]:
-- 1) agents
-- 2) tasks
-- 3) agent_assignments
-- 4) conversations / notes / health_checks / scheduler_log

-- Redundanten Index entfernen:
DROP INDEX IF EXISTS idx_agents_id_unique;

-- Fehlende Indizes:
CREATE INDEX IF NOT EXISTS idx_assignments_assigned_at
    ON agent_assignments (assigned_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent
    ON tasks (assigned_agent) WHERE assigned_agent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_pending_knowledge
    ON notes (created_at) WHERE synced_knowledge = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_bookstack
    ON notes (created_at) WHERE synced_bookstack = 0;
CREATE INDEX IF NOT EXISTS idx_notes_pending_github
    ON notes (created_at) WHERE synced_github = 0;

-- updated_at Trigger:
CREATE TRIGGER IF NOT EXISTS trg_tasks_updated
AFTER UPDATE ON tasks FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Prompt-History:
CREATE TABLE IF NOT EXISTS agent_prompt_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE(agent_id, version)
);

-- FTS5 (falls beschlossen):
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_entries_fts USING fts5(
    title, content, tags,
    content='knowledge_entries', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
-- + Trigger ke_ai/ke_ad/ke_au + Initial-Backfill (siehe §2.2)

-- Backup-Rotation:
-- vorher: -mtime "+${RETENTION_DAYS}"
-- nachher: -mtime "+$((RETENTION_DAYS - 1))"
```

---

**Ende des Reviews.** Das LLD ist fundiert, die Defekte sind durchweg lokal behebbar — das Gesamtdesign (Repository-Pattern + idempotente Migration + WAL + httpx-Client) trägt.
