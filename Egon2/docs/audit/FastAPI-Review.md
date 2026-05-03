# FastAPI / Async / Pydantic V2 — Implementierungs-Review

**Projekt:** Egon2
**Reviewer-Profil:** FastAPI-Experte (async-first, Pydantic V2, Python 3.12)
**Stand:** 2026-05-02
**Geprüfte Dokumente:**
- `docs/LLD-Interfaces.md`
- `docs/LLD-Core.md`
- `docs/LLD-Architektur.md`

**Gesamteinschätzung:** Die LLDs sind insgesamt sehr solide und implementierbar. Die Lifespan-Architektur ist sauber, Reihenfolge und Timeouts sind durchdacht. Es gibt jedoch mehrere konkrete Bugs in Code-Snippets (v.a. `python-telegram-bot` v21 Polling, `matrix-nio` Doppel-Sync, deprecated Pydantic-Patterns, modell-Inkonsistenzen Core ↔ Architektur), die vor der Implementierung adressiert werden müssen.

---

## Schweregrad-Übersicht

| Severity | Anzahl | Bereiche |
|---|---|---|
| KRITISCH | 4 | python-telegram-bot polling, matrix sync, Pydantic V2 deprecation, Modell-Drift |
| HOCH | 6 | aiosqlite Threading, Listener-Crosstalk, datetime.utcnow, Token-Datei chmod-Window, Brief-JSON, Recovery-Inkonsistenz |
| MITTEL | 7 | Connection-Pool-Defaults, Backoff-Edges, frozenset-Whitelist Telegram, Knowledge-Pool-Param, Auth-Header dummy, Konstanten-Drift, Logging |
| NIEDRIG | 5 | dataclass json, Cosmetics, Doppel-Imports, frozen-dataclass mutation pitfalls, Doku-Lücken |

---

## KRITISCH

### K1. `python-telegram-bot` v21 — `start_polling()` Lifecycle ist unvollständig dokumentiert, aber im Code korrekt

`LLD-Interfaces.md` §3.3 nutzt das richtige PTB-21-Muster:
```
await app.initialize()
await app.start()
await app.updater.start_polling(...)
```
Dies blockiert den Loop NICHT (im Gegensatz zu `app.run_polling()`, was selbst `asyncio.run()` aufruft und den Lifespan zerstören würde). Das ist korrekt — **Falle vermieden**.

ABER: Die im Diagramm-Abschnitt §3.5 von `LLD-Architektur.md` erwähnte Abkürzung
> `app.add_handler(...)` … `Application.initialize() + start_polling()`

ist missverständlich, da `start_polling` ohne `start()` den Updater zwar startet, aber Handler nicht ausgeliefert werden. **Korrektur:** Sequenz in §3.5 explizit auf `initialize → start → updater.start_polling` festlegen, kongruent zu `LLD-Interfaces.md` §3.3.

Zusätzlich KRITISCH: **`drop_pending_updates=True` in Kombination mit Crash-Recovery**: Bei Restart nach Crash gehen alle Updates verloren, die zwischen Last-Offset und Restart eingegangen sind. Das HLD verlässt sich auf "Read-Marker" zur Wiederherstellung, aber Telegram hat KEINEN Read-Marker im PTB — nur den Update-Offset. Der Kommentar in `LLD-Core.md` §1.4 ("über Matrix/Telegram Sync (Read-Marker) wieder eingelesen") ist für Telegram **unzutreffend**.

**Fix:**
```python
# Empfehlung: drop_pending_updates=False im Produktionsbetrieb
await self._app.updater.start_polling(
    poll_interval=1.0, timeout=30,
    drop_pending_updates=False,    # Crash-Resilienz
    allowed_updates=["message"],
)
```
Dazu dokumentieren, dass das `getUpdates`-Offset von PTB persistent in `Application.persistence` (z. B. `PicklePersistence`) gehalten werden muss, sonst macht auch `=False` keinen Sinn — out of the box ist das **In-Memory** und überlebt keinen Restart.

### K2. `matrix-nio`: Doppelter Sync in `start()` — Initial-Sync + `sync_forever()` überlappen

`LLD-Interfaces.md` §2.2:
```python
await self._client.sync(timeout=10_000, full_state=not self._token_file.exists())
self._sync_task = asyncio.create_task(self._sync_forever(), ...)
```
und in §2.5:
```python
resp = await self._client.sync_forever(timeout=30_000, full_state=False, loop_sleep_time=1_000)
```

**Problem:**
1. `loop_sleep_time` ist in matrix-nio in **Millisekunden** dokumentiert — der Wert `1_000` (= 1s) ist OK, aber der Kommentar `# ms` ist redundant; wichtiger: `sync_forever` läuft selbst in einer Endlosschleife. Die äußere `while self._running`-Schleife ist nur dafür da, Backoff bei Exceptions zu machen — das ist OK.
2. Bei `event.server_timestamp`: Der erste manuelle `sync(...)` löst Callbacks aus für Events, die im First-Sync-Range sind. Bei `full_state=True` (Erststart) bedeutet das: alle historischen Events der Räume können neu in die Queue laufen. Empfehlung: Im Erststart `since`-Token speichern, danach in `sync_forever` weitergeben — oder Callbacks erst NACH dem Initial-Sync registrieren.

**Fix:**
```python
# Reihenfolge umdrehen:
await self._client.sync(timeout=10_000, full_state=not self._token_file.exists())
# Jetzt erst Callbacks setzen, damit Initial-Sync nicht in die Queue läuft
self._client.add_event_callback(self._on_room_message, RoomMessageText)
self._client.add_event_callback(self._on_invite, InviteMemberEvent)
self._running = True
self._sync_task = asyncio.create_task(self._sync_forever(), name="matrix-sync")
```

Außerdem: `client.load_store()` (§2.3) ist in nio nur bei `encryption_enabled=True` sinnvoll. Bei deaktivierter E2EE sollte er weggelassen werden, sonst wirft er bei leerem Store eine Warnung.

### K3. Pydantic V2 — `datetime.utcnow` ist deprecated und liefert naive datetimes

In `LLD-Architektur.md` §2.1 verwenden alle Pydantic-Modelle:
```python
timestamp: datetime = Field(default_factory=datetime.utcnow)
```
- `datetime.utcnow()` ist seit **Python 3.12 deprecated** (`DeprecationWarning`, Entfernung in 3.14 vorgesehen).
- Liefert ein naives `datetime` ohne tzinfo → in DB persistiert als naive Zeit, nicht eindeutig vergleichbar mit `datetime.now(UTC)` aus `LLD-Core.md` §1.2.

**Fix (zwingend):**
```python
from datetime import datetime, UTC
timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

Außerdem fehlt in den Pydantic-Modellen `model_config`. Empfehlung für robuste DB-Roundtrips:
```python
from pydantic import BaseModel, ConfigDict
class IncomingMessage(BaseModel):
    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        ser_json_timedelta="iso8601",
        validate_assignment=True,
    )
```

### K4. Massiver Drift zwischen `LLD-Architektur.md` (Pydantic) und `LLD-Core.md` (dataclasses)

Es gibt ZWEI parallele, unterschiedlich definierte Datenmodelle:

| Modell | LLD-Architektur (§2.1) | LLD-Core (§1.2 / §3.3 / §4.3) |
|---|---|---|
| Message | `IncomingMessage` (Pydantic, `room_id`, `content`, `timestamp`, `raw`) | `Message` (dataclass, `chat_id`/`metadata`, `text`, `timestamp`, `message_id`) |
| Channel | `MATRIX/TELEGRAM` | `MATRIX/TELEGRAM/SCHEDULER` |
| Task | `TaskRecord` (Pydantic) | `Task` (dataclass) |
| Brief | `AgentBrief` (Pydantic) | `Brief` (dataclass) |
| Intent | `ClassifiedIntent` mit `confidence`, `extracted_task` | `Intent` StrEnum ohne Confidence |
| TaskStatus | enthält `WAITING_APPROVAL` | enthält `WAITING_APPROVAL` ✓ |

Außerdem in `LLD-Interfaces.md` §2.2 **noch ein dritter `IncomingMessage`** (mit `chat_id`, `user_id`, `ts_ms` int, ohne Pydantic).

**Aktion: KRITISCH — Single-Source-of-Truth festlegen, bevor implementiert wird.**
Empfehlung: Pydantic V2 BaseModels in `egon2/models.py` zentral, dataclasses in den Core-LLDs durch Verweis auf `egon2.models` ersetzen. Konkret:
- `Message` (Core) und `IncomingMessage` (Architektur, Interfaces) zusammenführen.
- `ts_ms` (int) vs. `timestamp` (datetime) — ein Format wählen, idealerweise `datetime` mit UTC.
- `Brief.to_json()` nicht hand-rollen, sondern `model_dump_json(by_alias=True)` aus Pydantic V2.

---

## HOCH

### H1. `aiosqlite` und Cross-Thread-Listener im Scheduler

`LLD-Interfaces.md` §4.4:
```python
def _on_event(self, event: JobExecutionEvent) -> None:
    ...
    asyncio.create_task(self._db.scheduler_log_insert(...))
```
Listener-Callbacks von APScheduler 3.x (`AsyncIOScheduler`) werden im **selben Loop** ausgeführt, also sollte `create_task` funktionieren. ABER: Es gibt kein `loop`-Argument, falls APScheduler in einer früheren Version oder Konfiguration den Listener im Scheduler-Thread ausführt, würde `asyncio.create_task` **mit `RuntimeError: no running event loop`** scheitern.

**Fix:** Sicherer Pattern:
```python
def _on_event(self, event: JobExecutionEvent) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(self._db.scheduler_log_insert(...))
    except RuntimeError:
        # Listener läuft außerhalb des Loops → asyncio.run_coroutine_threadsafe
        asyncio.run_coroutine_threadsafe(
            self._db.scheduler_log_insert(...), self._loop
        )
```
Dazu im `start()`: `self._loop = asyncio.get_running_loop()` als Fallback merken.

Zusätzlich: `aiosqlite`-Verbindungen sind **nicht thread-safe** (SQLite generell nicht). Wenn das Modul aus einem Listener im falschen Thread aufgerufen wird, bekommt man `sqlite3.ProgrammingError`. WAL-Modus mildert das nur für mehrere Prozesse — innerhalb einer Connection gilt: ein Thread, eine Coroutine zur Zeit.

### H2. APScheduler Version — 3.x vs. 4.x

`LLD-Interfaces.md` §4 verwendet:
- `from apscheduler.schedulers.asyncio import AsyncIOScheduler`
- `from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore`
- `scheduler.add_listener(...)`, `scheduler.add_job(...)`, `scheduler.shutdown(wait=True)`

Das ist **APScheduler 3.x**. APScheduler 4.x hat einen komplett anderen API-Stil (`AsyncScheduler` als Context-Manager, `data_store=` statt `jobstores=`, kein Listener-Pattern; siehe https://apscheduler.readthedocs.io/en/4.0/migration_3to4.html).

**Aktion:** In `pyproject.toml` explizit `apscheduler>=3.10,<4` pinnen. Dokument ergänzen:
> APScheduler **3.x** API. Bei späterem Upgrade auf 4.x ist das gesamte Scheduler-LLD neu zu schreiben.

### H3. Token-Datei `session.json` — chmod-Race

`LLD-Interfaces.md` §2.3:
```python
self._token_file.write_text(json.dumps({...}))
self._token_file.chmod(0o600)
```
Zwischen `write_text` und `chmod` ist die Datei kurzzeitig mit Default-Umask (typisch `0644`) lesbar. Der Token leakt in dem Zeitfenster theoretisch.

**Fix:**
```python
import os
fd = os.open(str(self._token_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump({...}, f)
```
Oder vor dem Write `umask`-temporär setzen.

### H4. `Application.add_error_handler` Signatur in PTB v21

`LLD-Interfaces.md` §3.3:
```python
async def _on_error(self, update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("telegram.error", error=str(ctx.error))
```
PTB v21: Error-Handler ist `async def(update: object, context: CallbackContext)` — passt. ABER: `update: object` ist seit PTB 20 explizit als `object`, weil bei manchen Fehlern `update=None` ist. In `_authorized` wird das nicht behandelt — okay, da Error-Handler `_authorized` nicht aufruft.

Nicht-kritisch, aber: `frozenset[int]` für Whitelist ist unproblematisch — `frozenset(settings.telegram_whitelist)` aus `list[int]` ist O(1)-Lookup.

### H5. `recover_orphaned` — semantischer Konflikt zwischen Core und Architektur

- `LLD-Core.md` §3.5: alle `running` → **`pending`** (zur Wiederaufnahme).
- `LLD-Architektur.md` §6.1 Phase 5.2: alle `running` AND `updated_at < now()-5min` → **`failed`**.

Das sind unterschiedliche Recovery-Strategien. Ein Task, der vor 4 Minuten `running` wurde und der Service abstürzt: Architektur lässt ihn auf `running`, Core setzt ihn auf `pending`. Inkonsistent.

**Aktion:** Eine Strategie wählen. Empfehlung: **Architektur-Variante** (zeitbasiert auf `failed` → User wird informiert, kein endloser Geistlauf). `LLD-Core.md` §3.5 entsprechend anpassen.

### H6. `Brief.to_json()` und Pydantic-Doppelverwendung

`LLD-Interfaces.md` und `LLD-Core.md` §4.3 definieren `Brief` als dataclass mit handgeschriebenem `to_json()`. `LLD-Architektur.md` §2.1 definiert `AgentBrief` als Pydantic `BaseModel`. In `agent_dispatcher.py` §4.8 wird `brief.to_json()` aufgerufen, was bei BaseModel `model_dump_json()` heißen müsste.

**Fix:** Auf Pydantic standardisieren:
```python
brief_payload = brief.model_dump_json()
await db.execute("INSERT INTO agent_assignments(... brief, ...) VALUES (..., ?, ...)", (brief_payload, ...))
```

---

## MITTEL

### M1. `httpx.AsyncClient` Konfiguration nicht durchgängig in den Klassen sichtbar

`LLD-Architektur.md` §2.6 zeigt `LLMClient` mit `BASE_URL`, `CONNECT_TIMEOUT`, `READ_TIMEOUT` als Klassen-Konstanten, aber **kein `__init__` mit `httpx.AsyncClient(...)`-Erzeugung**. Der Zeitpunkt der Pool-Erstellung ist nicht spezifiziert (eager im `__init__` vs. lazy beim ersten Call). Das LLD-Interfaces (§1.3) sagt zudem explizit *"Pool wird lazy beim ersten Call angelegt"* — das widerspricht der Best-Practice "AsyncClient im Lifespan erzeugen, im Lifespan schließen".

**Fix:**
```python
class LLMClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=30.0),
            headers={"Authorization": f"Bearer {token}"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()
```
Damit ist `aclose` symmetrisch zu Lifespan-Stop und der Pool wird nicht erst im Hot-Path erzeugt (Latenz-Spike beim ersten Call).

### M2. SSH-Connection-Pool: Race in `_connect`

`LLD-Interfaces.md` §5.2:
```python
async def _connect(self, host, user, port):
    target = f"{user}@{host}:{port}"
    async with self._lock:
        conn = self._conns.get(target)
        if conn is not None and not conn.is_closed():
            return conn
        conn = await asyncssh.connect(...)   # << blocking innerhalb des locks!
        self._conns[target] = conn
        return conn
```
Der `await asyncssh.connect(...)` läuft INNERHALB von `self._lock` — andere Hosts blockieren während des Connect (15s connect_timeout). Bei mehreren parallelen Anfragen an verschiedene Hosts wird der Pool seriell.

**Fix:** Per-Target-Lock:
```python
self._target_locks: dict[str, asyncio.Lock] = {}
self._dict_lock = asyncio.Lock()

async def _connect(self, host, user, port):
    target = f"{user}@{host}:{port}"
    async with self._dict_lock:
        lock = self._target_locks.setdefault(target, asyncio.Lock())
    async with lock:
        conn = self._conns.get(target)
        if conn is not None and not conn.is_closed():
            return conn
        conn = await asyncssh.connect(...)
        self._conns[target] = conn
        return conn
```

Außerdem: `conn.is_closed()` gibt es in asyncssh als `_conn._closing` Flag, aber öffentliche API ist `conn._transport is None` oder `conn.is_closed()` (verfügbar ab asyncssh 2.13+). In `pyproject.toml` minimum-Version pinnen.

### M3. SSH max output cap — encoded-bytes vs. str-len

`_truncate(s: str)` in `LLD-Interfaces.md` §5.2 encoded explizit nach UTF-8 vor dem Cap. Das ist korrekt für 1-MiB-Byte-Limit. ABER: `_truncate_bytes` für ShellExecutor §6.2 arbeitet auf `bytes` direkt — saubere Asymmetrie. Inkonsistenz: `proc.stdout` von asyncssh ist `str`, von asyncio.subprocess `bytes`. Ist eigentlich okay, aber die Unicode-Escape-Kante (Zeichen, das durch das Cap zerrissen wird) ist nur über `errors="replace"` adressiert — ein 4-Byte-UTF8-Sequenzschnitt produziert ggf. einen Replacement-Char am Ende. Vertretbar; sollte im LLD als bekanntes Verhalten dokumentiert werden.

### M4. `Authorization: Bearer dummy` für Claude Code API

`LLD-Architektur.md` §3.1 stellt fest, dass der API-Key nicht geprüft wird. Trotzdem: Header weglassen (oder leeren String) wäre semantisch sauberer. **Aktion:** Im `LLMClient.__init__` `Authorization` nur setzen, wenn Token != `"dummy"` ist. Sonst landen `"Bearer dummy"`-Strings in Logs.

### M5. Knowledge-Pool-Größe nicht im LLD-Architektur-Schnittstellenbeschrieb

`LLD-Architektur.md` §3.2 sagt im Kommentar `# Connection Pool: max_connections=5 (im HLD spezifiziert)`, aber der Code ist `...`. Der `MCPKnowledgeClient.__init__` braucht expliziten `httpx.Limits`-Block analog zu M1.

### M6. Rolling-Window-Format-Drift

`LLD-Core.md` §2.5 sagt: "Reihenfolge im Ergebnis: aufsteigend nach `timestamp` → ältestes zuerst." OK. ABER: SELECT lautet `ORDER BY timestamp DESC LIMIT ?` — das gibt absteigend zurück. Es fehlt der Hinweis "danach im Code reverten" oder "über Subquery `SELECT * FROM (... DESC LIMIT N) ORDER BY timestamp ASC`".

**Fix:**
```sql
SELECT role, content, channel, timestamp FROM (
  SELECT role, content, channel, timestamp FROM conversations
  ORDER BY timestamp DESC LIMIT ?
) ORDER BY timestamp ASC;
```

### M7. `ContextManager` API-Drift Core ↔ Architektur

`LLD-Core.md` §2.3: `build_context(task: str, channel: str, user_id: str, intent: str | None, extra_system: str | None)`.
`LLD-Architektur.md` §2.4: `build_context(message: IncomingMessage, current_task_id: str | None)`.

Zwei unterschiedliche Signaturen. Eine wählen (vorzugsweise die Architektur-Version, weil typed via Pydantic) und Core anpassen.

---

## NIEDRIG

### N1. `MessageQueue.MAX_SIZE` Drift
- Core §1.3: `MAX_SIZE = 100`
- Interfaces §1 (Lifespan): `MessageQueue(maxsize=256)`
- Architektur §2.2: `maxsize=100`

→ einheitlich auf 256 oder 100 setzen.

### N2. `frozen=True` dataclass und `frozenset`-Whitelists
`ExecResult` ist `frozen=True, slots=True` — gut. Aber: `dataclass(slots=True, frozen=True)` mit `field(default_factory=...)` wirft bei `__init__` keine Warnung, aber Mutation ist gesperrt. Passt.

### N3. `Telegram` `MarkdownV2` — `disable_web_page_preview` ist deprecated
PTB v21: `disable_web_page_preview` ist deprecated zugunsten von `link_preview_options=LinkPreviewOptions(is_disabled=True)`. Nicht-kritisch, aber bei strict-deprecation-Warnings im Test wäre es ein Issue.

### N4. `LLM_RETRY_CONFIG.retry_on` enthält `LLMTimeoutError`, aber im Codepfad wird `httpx.ReadTimeout` geworfen

`LLD-Architektur.md` §5.3: `retry_on=(LLMClientError, LLMRateLimitError, LLMTimeoutError)`. Der httpx-Client wirft jedoch `httpx.TimeoutException` / `httpx.ReadTimeout`, nicht den eigenen `LLMTimeoutError`. Es muss ein Wrapper im `LLMClient.complete()` her, der `httpx.TimeoutException → LLMTimeoutError` konvertiert. Das ist im LLD impliziert, aber nicht spezifiziert.

### N5. Pydantic V2 `field_validator` / `model_validator` werden nirgendwo genutzt
Kein Validator z.B. für `Channel`, `confidence in [0,1]`, `quality_score in [1,5]`. Das ist nicht falsch, aber ungenutzte Pydantic-Stärke. Empfehlung in einem späteren Iteration:
```python
from pydantic import field_validator
class AgentResult(BaseModel):
    quality_score: int | None = None

    @field_validator("quality_score")
    @classmethod
    def _q(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError("quality_score must be 1..5 or None")
        return v
```

---

## Konkrete Fix-Liste (priorisiert)

1. **K3** Alle `datetime.utcnow` → `lambda: datetime.now(UTC)` (sed in `models.py`).
2. **K4** Modell-Drift auflösen: Pydantic V2 als SoT in `egon2/models.py`, dataclasses in Core-LLDs entfernen oder als Aliases dokumentieren.
3. **K1** `drop_pending_updates=False` + `PicklePersistence` für PTB.
4. **K2** Matrix Callback-Registrierung NACH Initial-Sync; `load_store` nur wenn E2EE aktiv.
5. **H1** Listener-Pattern mit `loop.call_soon_threadsafe`/`run_coroutine_threadsafe` absichern.
6. **H2** `apscheduler>=3.10,<4` in `pyproject.toml`; LLD-Hinweis ergänzen.
7. **H3** Atomares `os.open(... 0o600)` für `session.json`.
8. **H5** Recovery-Strategie vereinheitlichen (Empfehlung: `running` älter 5 min → `failed`).
9. **H6** `brief.model_dump_json()` statt `to_json()`.
10. **M1/M5** `httpx.AsyncClient` eager im `__init__`, `aclose` im Lifespan.
11. **M2** Per-Target-Lock im SSH-Pool.
12. **M6** Rolling-Window-SELECT per Subquery, Reihenfolge garantieren.
13. **M7** `ContextManager.build_context` Signatur auf Architektur-Variante vereinheitlichen.
14. **N1** `MessageQueue` maxsize konsistent setzen.

---

## Implementierbarkeit

| Bereich | Verdict |
|---|---|
| Lifespan-Pattern | **Implementierbar** mit kleinen Anpassungen (K1, K2). Reihenfolge sauber, Timeouts plausibel. |
| Pydantic V2 | **Nach K3/K4 implementierbar.** Kein Blocker, aber zwingender Cleanup. |
| asyncssh Pool | **Implementierbar**, M2 sollte vor Produktion behoben sein, sonst Latenz-Bug. |
| matrix-nio | **Implementierbar** mit K2-Fix. `sync_forever` + Backoff-Loop ist idiomatisch. |
| python-telegram-bot v21 | **Implementierbar** — Lifecycle wie spezifiziert ist korrekt. K1 ist eher Robustness. |
| APScheduler 3.x | **Implementierbar** — exakt das Standard-Pattern. H2 (Pinning) sicherstellen. |
| aiosqlite + Repository | **Implementierbar** unter Beachtung von H1 (Single-Connection / Single-Loop-Affinität). |
| httpx Pool | **Implementierbar** — M1/M5 als Code-Zentrierung. |

**Empfehlung:** Vor Coding-Beginn die Modell-Drift (K4) und das Pydantic-Date-Issue (K3) auflösen — beides sind 30-Minuten-Aufwand und sparen tagelange Folgekosten.
