# LLD — Egon2: Core-Engine

**Version:** 1.3
**Stand:** 2026-05-02
**Bezug:** HLD-Egon2.md v1.5, Abschnitte 4, 7.2, 7.3
**Modul-Pfad:** `egon2/core/` und `egon2/personality.py`

**Änderungen ggü. v1.0 (Audit-Findings eingearbeitet):**
- C1: `IncomingMessage` als kanonisches Pydantic-BaseModel definiert (Single Source of Truth — siehe §1.2).
- C4: Alle `datetime.utcnow()` durch `datetime.now(UTC)` ersetzt (Python 3.12+).
- HOCH: `AgentDispatcher`-Konstruktor kanonisch mit allen Dependencies definiert (§4.4).
- HOCH: Exception-Hierarchie konsolidiert — alle Core-Exceptions erben von `Egon2Error` (§3.7).

**Änderungen v1.3 (Audit-Runde-2-Findings 2026-05-02):**
- Fix: `SYNONYM_BOOST` verwendete `"it-admin"` (Bindestrich) statt `"it_admin"` (Unterstrich) — stilles Matching-Versagen (§4.6).
- Fix: `task_done()` aus `_run()` in `_handle_with_semaphore()` finally-Block verschoben — verhindert vorzeitiges join()-Return (§1.6).
- Fix: `MessageQueue.join()` Methode ergänzt (§1.3).
- Fix: `last_task_for_sender()` Kommentar korrigiert — nutzt `tasks.sender_id`-Spalte direkt (§4.11).
- HOCH: `recover_orphaned()` als Startup-Contract markiert (§3.5).
- C10: Prompt-Injection-Schutz im Dispatcher via `_sanitize_user_input()` (§4.5, §4.7).

**Änderungen v1.2 (Spec-Findings 2026-05-02 — pragmatisch für Heimnetz, Single-User):**
- F1: Consumer dispatcht jeden Brief in eigene `asyncio.create_task` mit `Semaphore(3)` für gleichzeitige LLM-Calls (§1.6 — neu). Keine Persistence — Verlust einer Nachricht bei Crash akzeptiert.
- F4: Einfacher Retry-Decorator (`attempts=3, backoff=[1,2,4]`) für LLM-, Knowledge- und SearXNG-Client; nur bei `httpx.ConnectError`/`httpx.TimeoutException`, nicht bei HTTP 4xx (§3.8 — neu, querverwiesen auf LLD-Architektur §5.3). **Kein** Circuit Breaker, **kein** Bulkhead.
- F5: `IncomingMessage` bekommt `request_id` (8-Hex-Chars) — wird durch alle Komponenten propagiert, in `tasks.request_id` gespeichert, jedes Log-Statement führt Prefix `[req=…]` (§1.2).
- F6: Sub-Task-Aggregations-Algorithmus im Dispatcher (§4.10 — neu): Parent wartet bis alle Sub-Tasks terminal sind, sammelt Ergebnisse, fasst per LLM zusammen. Max. Sub-Task-Tiefe **2** (kein rekursiver Spawn).
- F7: State `CANCELLED` ergänzt (§3.2, §3.3, §3.7). User-Abbruch-Intent-Erkennung (§4.11 — neu): „nein/stop/vergiss das/cancel" cancelt nur `pending`-Tasks; bei `running` höflicher Hinweis dass Task bereits läuft.

---

## 0. Vorbemerkungen

- Python 3.12+, PEP 604 Syntax (`X | None` statt `Optional[X]`).
- Asynchron durchgängig — keine blockierenden Aufrufe im Event-Loop.
- DB-Layer: `aiosqlite` (Pool über `database.py`).
- LLM-Layer: `llm_client.py` (httpx async, Claude Code API, OpenAI-kompatibel).
- Logging: `structlog`, Logger-Name = Modul.
- Alle UUIDs: `uuid.uuid4().hex`.
- Datums-/Zeitwerte: `datetime.now(UTC)` für DB; `datetime.now(ZoneInfo("Europe/Berlin"))` für Prompts.
- **`datetime.utcnow()` ist verboten** (deprecated ab Python 3.12, wird in 3.14 entfernt). Stattdessen immer `datetime.now(UTC)`. Import: `from datetime import datetime, UTC`.
- **Konvention Pydantic vs. dataclass:** Pydantic an System-Grenzen (eingehende Nachrichten, LLM/MCP-Responses), dataclass `slots=True` für interne Domain-Objekte (Task, Brief, ContextBundle).

---

## 1. `egon2/core/message_queue.py`

### 1.1 Zweck

Single-writer-multiple-reader async Queue zwischen **Interface Layer** (Matrix/Telegram) und **Core Engine**. Serialisiert eingehende Nachrichten — verhindert Race Conditions bei parallelen Eingängen aus beiden Kanälen (HLD §7.1).

### 1.2 Datenmodell — `IncomingMessage` (KANONISCHE DEFINITION)

> **Single Source of Truth.** Diese Definition ist die einzige kanonische Form von `IncomingMessage` im gesamten System. `LLD-Architektur.md` und `LLD-Interfaces.md` referenzieren dieses Modell — sie definieren es **nicht** selbst neu. Bei Änderungen ist dieses Dokument der zu aktualisierende Master.

```python
from datetime import datetime, UTC
from enum import StrEnum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class Channel(StrEnum):
    MATRIX = "matrix"
    TELEGRAM = "telegram"
    SCHEDULER = "scheduler"   # interne Quelle für Scheduler-getriggerte Messages


class IncomingMessage(BaseModel):
    """Kanonische Repräsentation einer eingehenden Nachricht.

    Kanonische Definition — LLD-Interfaces und LLD-Architektur referenzieren
    dieses Modell. Pydantic v2, frozen (immutable nach Konstruktion).
    """
    model_config = ConfigDict(frozen=True)

    text: str
    channel: Channel
    sender_id: str
    room_id: str | None = None              # Matrix room_id
    chat_id: int | None = None              # Telegram chat_id
    reply_to_event_id: str | None = None    # Matrix thread root / Telegram reply
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_id: str | None = None           # vom Adapter gesetzt (event_id / tg_message_id)
    request_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    """Korrelations-ID für Tracing — 8-Zeichen-Hex, menschenlesbar.
    Wird durch alle Komponenten (Queue → Dispatcher → LLM → DB) propagiert,
    in `tasks.request_id` gespeichert und in jedem Log-Statement als Prefix
    `[req=abc12345]` ausgegeben. Kein Distributed Tracing Stack — nur
    konsistentes Log-Prefix, reicht für Einzelnutzer-Debugging (Finding F5)."""
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Propagationsvertrag `request_id` (F5):**

- Interface-Adapter (Matrix/Telegram/Scheduler) setzen `request_id` beim Erzeugen der `IncomingMessage` automatisch (Default-Factory).
- Der Consumer-Loop bindet die `request_id` für die Dauer der Verarbeitung in den structlog-Kontext (`structlog.contextvars.bind_contextvars(req=msg.request_id)`), so dass jede nachgelagerte Log-Zeile (Dispatcher, LLM-Client, SSH-Executor, DB-Layer) automatisch das Präfix `[req=…]` trägt — ohne explizites Durchreichen.
- `tasks.request_id TEXT` (Schema-Diff §6.1) speichert die `request_id` mit dem Task. Sub-Tasks erben die `request_id` ihres Parents.
- Bei ausgehenden Antworten (Matrix/Telegram) wird die `request_id` **nicht** an den User ausgegeben — sie bleibt operativ.

**Adapter-Konventionen für `metadata`:**
- Matrix: `{"event_id": str}` (zusätzlich zu `room_id`).
- Telegram: `{"tg_message_id": int}` (zusätzlich zu `chat_id`).
- Scheduler: `{"job_name": str}`.

### 1.3 Queue-Klasse

```python
import asyncio
import logging

log = logging.getLogger(__name__)


class MessageQueue:
    MAX_SIZE: int = 100
    ENQUEUE_TIMEOUT_S: float = 2.0   # Backpressure-Wartezeit bevor User informiert wird

    def __init__(self, max_size: int = MAX_SIZE) -> None:
        self._q: asyncio.Queue[IncomingMessage] = asyncio.Queue(maxsize=max_size)
        self._dropped: int = 0

    async def put(self, msg: IncomingMessage) -> bool:
        # Wartet bis ENQUEUE_TIMEOUT_S; bei Vollheit: drop + log + Rückgabe False.
        # Caller (Interface Layer) sendet dann Backpressure-Hinweis an User.
        try:
            await asyncio.wait_for(self._q.put(msg), timeout=self.ENQUEUE_TIMEOUT_S)
            return True
        except asyncio.TimeoutError:
            self._dropped += 1
            log.warning("queue_full", channel=msg.channel, sender_id=msg.sender_id,
                        dropped_total=self._dropped)
            return False

    async def get(self) -> IncomingMessage:
        return await self._q.get()

    def task_done(self) -> None:
        self._q.task_done()

    def qsize(self) -> int:
        return self._q.qsize()

    async def join(self) -> None:
        await self._q.join()

    def stats(self) -> dict[str, int]:
        return {"size": self._q.qsize(), "max": self._q.maxsize,
                "dropped": self._dropped}
```

### 1.4 Backpressure-Verhalten

- **Soft-Limit** = 80 % von `MAX_SIZE`. Erreicht → `log.warning` (Operator-Hinweis).
- **Hard-Limit** = `MAX_SIZE`. `put()` wartet bis 2 s; bei Timeout: Drop + `False` zurück.
- Interface Layer reagiert auf `False` mit Antwort an den User: *"Bin gerade ausgelastet. Versuch's gleich nochmal."* Die ursprüngliche Nachricht gilt als nicht angenommen.
- Persistenz: Die Queue ist **In-Memory**. Bei Service-Restart verlorene Messages werden über das Matrix-Sync (Read-Marker) wieder eingelesen. Telegram nutzt `drop_pending_updates=True` — Nachrichten während Downtime gehen dort verloren (akzeptiert, Single-User).

### 1.5 Lifecycle

- Singleton via `database.py`-ähnlicher Provider in `main.py` (Lifespan).
- Keine eigene `start/stop`-Logik. `asyncio.Queue` ist event-loop-gebunden — Erzeugung **innerhalb** des FastAPI-Lifespans.

### 1.6 Consumer-Loop & Concurrency-Modell (F1)

> **Pragmatik (Heimnetz, Single-User):** Diese Architektur ist explizit auf einen
> **persönlichen Assistenten** mit gelegentlich parallelen Scheduler-Jobs zugeschnitten —
> nicht auf einen Multi-Tenant-Service. Wir verzichten bewusst auf Message-Persistence,
> Replay-Logs oder verteiltes Locking. Im Crashfall geht eine in der Queue liegende
> Nachricht verloren — das ist akzeptiert.

**Problem (Spec-Finding F1):** Ein einzelner Consumer-Task der `await handle_message(msg)`
synchron ausführt blockiert die gesamte Queue, sobald ein LLM-Call 60 s dauert. Selbst
für Einzelnutzer kritisch: Scheduler-Jobs (News-Report, Health-Check) können dann nicht
mehr in die Queue einreihen, ohne den 2 s-Backpressure-Timeout zu reißen.

**Lösung — Dispatching Consumer mit Semaphore:**

```python
# egon2/core/consumer.py (neu — eigene Datei oder Teil von main.py)
import asyncio
import logging
import structlog

log = structlog.get_logger(__name__)


class MessageConsumer:
    """Pull-from-Queue, dispatch in eigene Task.

    Concurrency-Modell:
      - 1 Consumer-Loop (pull from MessageQueue)
      - N parallele handle_message-Tasks (asyncio.create_task)
      - asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS) limitiert gleichzeitige
        LLM-Calls — verhindert Overload bei Scheduler-Job-Burst.
      - _running_tasks: set[asyncio.Task] für sauberes Shutdown (alle awaiten).
    """

    MAX_CONCURRENT_LLM_CALLS: int = 3

    def __init__(self, queue: MessageQueue, dispatcher: "AgentDispatcher") -> None:
        self._queue = queue
        self._dispatcher = dispatcher
        self._sem: asyncio.Semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_LLM_CALLS)
        self._running_tasks: set[asyncio.Task] = set()
        self._stopping: bool = False
        self._loop_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._loop_task = asyncio.create_task(self._run(), name="message-consumer")

    async def _run(self) -> None:
        while not self._stopping:
            try:
                msg = await self._queue.get()
            except asyncio.CancelledError:
                break
            # Dispatch: NICHT awaiten — eigene Task, damit lange LLM-Calls
                # die Queue nicht blockieren.
            t = asyncio.create_task(
                self._handle_with_semaphore(msg),
                name=f"handle-{msg.request_id}",
            )
            self._running_tasks.add(t)
            t.add_done_callback(self._running_tasks.discard)

    async def _handle_with_semaphore(self, msg: IncomingMessage) -> None:
        # structlog-Kontext binden — alle nested logs tragen [req=…]
        structlog.contextvars.bind_contextvars(req=msg.request_id)
        try:
            async with self._sem:
                await self._dispatcher.handle(msg)
        except Exception as e:
            log.exception("consumer.handler_failed", error=str(e))
        finally:
            structlog.contextvars.unbind_contextvars("req")
            self._queue.task_done()

    async def stop(self, drain_timeout: float = 30.0) -> None:
        """Graceful Shutdown: Loop stoppen, dann alle laufenden Tasks awaiten.

        Aufgerufen aus Shutdown-Stage 5 (siehe LLD-Architektur §6.2).
        """
        self._stopping = True
        if self._loop_task is not None:
            self._loop_task.cancel()
            await asyncio.gather(self._loop_task, return_exceptions=True)
        # Warte auf alle laufenden handle_message-Tasks (max drain_timeout).
        if self._running_tasks:
            log.info("consumer.draining", n=len(self._running_tasks))
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._running_tasks, return_exceptions=True),
                    timeout=drain_timeout,
                )
            except asyncio.TimeoutError:
                log.warning("consumer.drain_timeout", n_pending=len(self._running_tasks))
                for t in self._running_tasks:
                    t.cancel()
                await asyncio.gather(*self._running_tasks, return_exceptions=True)
```

**Kapazitäts-Reasoning (Single-User-Dimensionierung):**

- `MAX_CONCURRENT_LLM_CALLS = 3` deckt den Worst Case ab: Marco tippt eine Nachricht,
  während gleichzeitig der News-Report (07:30) und ein Health-Check (selten parallel) laufen.
- Höher als 3 macht für Single-User keinen Sinn — der LLM-Backend (LXC 105) hat begrenzten Durchsatz.
- Niedriger (z. B. 1) führt zum ursprünglichen Block-Problem.

**Persistence-Verzicht — explizite Akzeptanz (F1):**

- Die Queue ist **In-Memory** (siehe §1.4).
- Bei Service-Crash gehen Nachrichten verloren, die zwischen Annahme und LLM-Antwort lagen.
- Im Heimnetz akzeptiert: Marco merkt es sofort (keine Antwort), schickt notfalls neu.
- Scheduler-Jobs werden über APScheduler-`misfire_grace_time=3600` automatisch nachgeholt
  (HLD §7.4) — der Verlust betrifft nur in-flight User-Nachrichten.
- **Kein** Persistent-Queue (Redis/SQLite-Outbox/Kafka) — zu viel Komplexität für 0,01 verlorene
  Nachrichten pro Jahr.

---

## 2. `egon2/core/context_manager.py`

### 2.1 Zweck

Liefert dem Agent-Dispatcher den vollständigen LLM-Kontext: System-Prompt + Knowledge-Top-K + Rolling Window + aktuelle Aufgabe. Verwaltet Token-Budget. Entspricht HLD §7.3.

### 2.2 Konstanten

```python
ROLLING_WINDOW_SIZE: int = 20
KNOWLEDGE_TOP_K: int = 5
MAX_TOTAL_TOKENS: int = 150_000
RESERVED_OUTPUT_TOKENS: int = 8_000          # für die Antwort des LLM
SYSTEM_PROMPT_BUDGET: int = 4_000
KNOWLEDGE_BUDGET: int = 20_000
ROLLING_BUDGET: int = MAX_TOTAL_TOKENS - SYSTEM_PROMPT_BUDGET \
                     - KNOWLEDGE_BUDGET - RESERVED_OUTPUT_TOKENS
# = 118_000 Tokens für Rolling Window + Brief
```

### 2.3 Klasse

```python
from dataclasses import dataclass

@dataclass(slots=True)
class ContextBundle:
    messages: list[dict[str, str]]   # OpenAI-Format: {"role": ..., "content": ...}
    estimated_tokens: int
    knowledge_ids: list[str]         # IDs der genutzten Knowledge-Einträge (für Audit)


class ContextManager:
    def __init__(self,
                 db: "Database",
                 knowledge_client: "KnowledgeMcpClient",
                 personality_prompt: str) -> None: ...

    async def build_context(self,
                            task: str,
                            channel: str,
                            user_id: str,
                            intent: str | None = None,
                            extra_system: str | None = None) -> ContextBundle: ...
```

### 2.4 Ablauf `build_context`

1. **System-Prompt** rendern: `personality.render_system_prompt(active_specialists=...)` → `messages[0]`.
2. **Rolling Window laden** (siehe §2.5).
3. **Keywords extrahieren** aus `task` (siehe §2.6).
4. **Knowledge-Abfrage** Top-K (siehe §2.7) → als zusätzliche `system`-Message vor dem Rolling Window einfügen, mit Präfix `"# Relevantes Wissen\n"`.
5. **Token-Budget anwenden** (siehe §2.8). Rolling Window wird ggf. von vorne (älteste zuerst) gekürzt.
6. **Aktuelle User-Nachricht** als letztes `user`-Element anhängen — falls `intent` gesetzt, im Format: `f"[Intent: {intent}]\n{task}"`.
7. `ContextBundle` zurückgeben.

### 2.5 Rolling-Window-Logik

- SQL: `SELECT role, content, channel, timestamp FROM conversations ORDER BY timestamp DESC LIMIT ?` mit `? = ROLLING_WINDOW_SIZE`.
- **Kanalunabhängig** (HLD §7.3). Reihenfolge im Ergebnis: aufsteigend nach `timestamp` → ältestes zuerst (im Code per `list(reversed(...))` oder Subquery `SELECT * FROM (... DESC LIMIT N) ORDER BY timestamp ASC`).
- Mapping `role`: `"user"` → `"user"`, `"assistant"` → `"assistant"`. Andere Rollen (z. B. `"tool"`) werden übergeben.
- Identifizierung Multikanal: Fremdkanal-Nachrichten bekommen Inline-Hinweis: `f"[via {channel}] {content}"` falls `channel != aktuell`.

### 2.6 Keyword-Extraktion (für Knowledge-Abfrage)

Algorithmus (deterministisch, ohne LLM):

```
1. text = task.lower()
2. tokens = re.findall(r"[a-zäöüß0-9_\-]{3,}", text)
3. stopwords entfernen (DE+EN, eingebettete Liste ~120 Wörter)
4. Häufigkeit zählen, top 8 Tokens nach Frequenz
5. Falls < 3 Keywords: ergänze um Token mit max. Länge (>= 5 Zeichen)
```

Liefert `list[str]` mit max. 8 Keywords.

### 2.7 Knowledge-Store-Abfrage (Top-5 per Keyword-Matching)

Auf LXC 107 ist `mcp_knowledge_v5.db` mit FTS5-Index auf `content`+`title`+`tags` (oder Migration legt diesen an).

**Query-Strategie:**

1. Verbinde Keywords mit `OR` zu FTS5-Query: `kw1 OR kw2 OR ...`.
2. Server-seitig: `MATCH` + `is_active=1` + `(expires_at IS NULL OR expires_at > now())`.
3. **Scoring** (auf Server, sonst Client):
   ```
   score = bm25(matchinfo) * 1.0
         + importance * 0.5
         + recency_boost          # 1.0 wenn updated_at < 7d, 0.5 < 30d, 0
         + domain_boost           # 0.3 wenn intent==QUESTION und domain in {it, project}
   ```
4. `ORDER BY score DESC LIMIT 5`.
5. Fallback bei FTS-Fehler: LIKE-Query über `content` mit `%kw%` für jedes Keyword, `OR`-verknüpft.

Rückgabe: `list[KnowledgeEntry]` mit `id, title, content, domain, importance, source`.

### 2.8 Token-Budget-Verwaltung

- **Schätzung** (kein Tokenizer-Roundtrip): `tokens ≈ ceil(len(text) / 3.0)` — konservativ für Deutsch + Code-Mix + JSON-Briefe.
- **Aufteilung:**
  - Wenn Knowledge > `KNOWLEDGE_BUDGET`: Einträge nach Score absteigend kürzen, bis passend; bei einzelnen Einträgen: `content` auf 2 000 Zeichen kappen mit Suffix `" […]"`.
  - Wenn Rolling > `ROLLING_BUDGET`: älteste Nachrichten zuerst entfernen (FIFO), bis passend.
  - System-Prompt wird **nie** gekürzt — sollte er das Budget sprengen, ist das ein Konfigurationsfehler → Exception `SystemPromptTooLargeError`.
- **Final-Check** in `build_context`: `assert estimated_tokens + RESERVED_OUTPUT_TOKENS <= MAX_TOTAL_TOKENS`.

### 2.9 OpenAI-Kontext-Struktur

```python
[
  {"role": "system",    "content": "<personality + Datum/Uhrzeit + active_specialists>"},
  {"role": "system",    "content": "# Relevantes Wissen\n- [it] ...\n- [news] ..."},
  {"role": "user",      "content": "<msg t-19>"},
  {"role": "assistant", "content": "<msg t-18>"},
  ...
  {"role": "user",      "content": "[Intent: task]\n<aktuelle Nachricht>"}
]
```

---

## 3. `egon2/core/task_manager.py`

### 3.1 Zweck

CRUD + State-Machine für `tasks`-Tabelle (HLD §8.1). Verwaltet Sub-Tasks und Recovery nach Crash.

### 3.2 State-Machine

```
   ┌──────────┐  start()   ┌──────────┐  finish()  ┌────────┐
   │ pending  │──────────► │ running  │──────────► │  done  │
   └──────────┘            └──────────┘            └────────┘
        ▲   │                  │   │
        │   │ cancel()         │   │ fail()
        │   │                  │   ▼
        │   │                  │ ┌────────┐
        │   │                  │ │ failed │
        │   ▼                  │ └────────┘
        │ ┌───────────┐        │
        │ │ cancelled │◄───────┘ cancel()  (höflich: wartet bis LLM-Call zurückkehrt)
        │ └───────────┘
        │ recover()
        │
                             │
                             │ require_approval()
                             ▼
                    ┌────────────────────┐  approve()  ┌──────────┐
                    │ waiting_approval   │───────────► │ running  │
                    └────────────────────┘             └──────────┘
                             │ reject()
                             ▼
                          failed
```

Erlaubte Übergänge (alle anderen → `InvalidTaskTransitionError`):

| Von | → Nach |
|---|---|
| `pending` | `running`, `failed`, `cancelled` |
| `running` | `done`, `failed`, `waiting_approval`, `cancelled` |
| `waiting_approval` | `running`, `failed`, `cancelled` |
| `done` | — (terminal) |
| `failed` | — (terminal) |
| `cancelled` | — (terminal) |

**`cancelled`-Semantik (F7):**

- `pending` → `cancelled`: User-Abbruch bevor der Dispatcher den Task aufgegriffen hat. Sofort wirksam.
- `running` → `cancelled`: User-Abbruch während Ausführung. **Egon ist höflich** und cancelt **nicht** den laufenden LLM-Call (verschwendet sonst Tokens und kann zu inkonsistenter Buchhaltung führen). Er markiert den Task als `cancel_requested` (interner Flag) und vollendet den aktuellen LLM-Call; das Ergebnis wird **verworfen** (`result` bleibt leer), Status wird beim Übergang `running → cancelled` gesetzt, statt `running → done`.
- `waiting_approval` → `cancelled`: User entscheidet sich gegen den Approval-Schritt.
- `cancelled_reason TEXT` Spalte in `tasks`-Tabelle (Schema-Diff §6.1) — speichert den Original-User-Wortlaut der Abbruch-Anweisung („nein, das war eine Notiz").

### 3.3 Datenklasse

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"   # F7 — User-Abbruch (terminal)

@dataclass(slots=True)
class Task:
    id: str
    title: str
    description: str | None
    source_channel: str | None
    status: TaskStatus
    assigned_agent: str | None
    result: str | None
    parent_task_id: str | None
    request_id: str | None             # F5 — Korrelations-ID, übernommen aus IncomingMessage
    cancelled_reason: str | None       # F7 — User-Wortlaut der Abbruch-Anweisung
    created_at: datetime
    updated_at: datetime
```

### 3.4 Klasse — Signaturen

```python
class TaskManager:
    def __init__(self, db: "Database") -> None: ...

    # --- CRUD ---
    async def create(self, *, title: str, description: str | None = None,
                     source_channel: str | None = None,
                     parent_task_id: str | None = None,
                     assigned_agent: str | None = None) -> Task: ...

    async def get(self, task_id: str) -> Task | None: ...

    async def list_active(self) -> list[Task]:
        # status in (pending, running, waiting_approval), order by created_at asc
        ...

    async def list_recent_done(self, limit: int = 10) -> list[Task]: ...

    async def update_result(self, task_id: str, result: str) -> None: ...

    async def delete(self, task_id: str) -> None:
        # Hard-delete inkl. Sub-Tasks (CASCADE), nur für Admin-Use
        ...

    # --- Sub-Tasks ---
    async def create_subtask(self, parent_task_id: str, *,
                             title: str, description: str | None = None,
                             assigned_agent: str | None = None) -> Task:
        # Wirft ParentTaskNotFoundError wenn parent fehlt.
        # Wirft ParentTerminalError wenn parent.status in {done, failed}.
        ...

    async def list_subtasks(self, parent_task_id: str) -> list[Task]: ...

    # --- State-Machine ---
    async def start(self, task_id: str) -> None:
        # pending|waiting_approval -> running
        ...

    async def finish(self, task_id: str, result: str) -> None:
        # running -> done; setzt result und updated_at
        ...

    async def fail(self, task_id: str, reason: str) -> None:
        # any non-terminal -> failed; result = "FAILED: " + reason
        ...

    async def require_approval(self, task_id: str, question: str) -> None:
        # running -> waiting_approval; result = "APPROVAL_NEEDED: " + question
        ...

    async def approve(self, task_id: str) -> None:
        # waiting_approval -> running
        ...

    async def reject(self, task_id: str, reason: str) -> None:
        # waiting_approval -> failed
        ...

    async def cancel(self, task_id: str, *, reason: str) -> None:
        """User-Abbruch (F7).

        - pending | waiting_approval -> cancelled (sofort)
        - running -> cancelled (höflich: aktueller LLM-Call läuft zu Ende, Ergebnis wird verworfen)
        - done | failed | cancelled -> InvalidTaskTransitionError (terminal)

        Speichert `reason` (User-Wortlaut) in `cancelled_reason`-Spalte.
        """
        ...

    async def is_cancel_requested(self, task_id: str) -> bool:
        """Nur für Dispatcher relevant: prüft ob während laufendem LLM-Call
        ein Cancel-Request kam. Liest `cancel_requested`-Flag (transient,
        nur in DB für Crash-Recovery; im Speicher ein dict[task_id, bool])."""
        ...

    # --- Recovery ---
    async def recover_orphaned(self) -> int:
        # Beim Service-Start: alle status='running' -> 'pending'.
        # 'waiting_approval' bleibt unverändert (User-Aktion erforderlich).
        # Returns: Anzahl zurückgesetzter Tasks.
        ...
```

### 3.5 Recovery-Logik

> **Startup-Contract (HOCH):** `recover_orphaned()` MUSS während der Startup-Sequenz aufgerufen werden, **bevor** der Scheduler oder Consumer-Task starten. Konkret in **Stage 2 (DB-Init / Recovery)** der Lifespan in `main.py`. Dies ist ein expliziter Vertrag zwischen Core und Interfaces — die Interfaces-LLD-Stages-Tabelle MUSS einen entsprechenden Eintrag enthalten. Ohne diesen Aufruf bleiben Tasks nach einem Crash dauerhaft auf `running` hängen.

Aufruf in `main.py` Lifespan (Stage 2: DB-Init, vor Scheduler-Start, vor Interface-Adaptern):

```python
# Stage 2 — DB-Init: Migrations + Recovery
await state.db.run_migrations()
n = await state.task_manager.recover_orphaned()
if n:
    log.info("startup.recovered_running_tasks", count=n)
```

SQL:
```sql
UPDATE tasks
SET status = 'pending',
    updated_at = CURRENT_TIMESTAMP
WHERE status = 'running';
```

Begründung: Ein Task in `running` ohne aktive Coroutine ist ein Geist — nur ein Restart kann das verursachen. Der Dispatcher übernimmt nach Recovery die Wiederaufnahme über `list_active()`. `waiting_approval` bleibt unangetastet, weil dort ein User-Input erwartet wird.

### 3.6 Transaktionssemantik

- Alle State-Übergänge laufen in einer SQLite-Transaktion (`async with db.transaction():`).
- Update-Statements verwenden **optimistic locking** durch zusätzlichen `WHERE status = ?` (alter Status). 0 betroffene Zeilen → `InvalidTaskTransitionError`.

### 3.7 Exceptions

> Alle Exception-Klassen erben von `Egon2Error` (Master-Hierarchie in `egon2/exceptions.py` gemäß LLD-Architektur §5.1). `TaskError` ist **kein** eigenständiges Wurzel-Element — sondern ein domänenspezifischer Zweig unter `Egon2Error`. Damit fängt `try/except Egon2Error` alle Core-Fehler.

```python
from egon2.exceptions import Egon2Error

class TaskError(Egon2Error):
    """Basis für alle Task-Manager-Fehler."""

class TaskNotFoundError(TaskError): ...
class InvalidTaskTransitionError(TaskError): ...
class ParentTaskNotFoundError(TaskError): ...
class ParentTerminalError(TaskError): ...
class TaskCancelledError(TaskError):
    """F7 — Task wurde vom User cancelt; vom Dispatcher beim Post-LLM-Step
    gefangen, um das Ergebnis zu verwerfen statt zu persistieren."""
class SubTaskDepthExceededError(TaskError):
    """F6 — Versuch, eine Sub-Task auf Tiefe > 2 zu spawnen.
    Max. Sub-Task-Tiefe ist 2 (kein rekursiver Spawn)."""

class SystemPromptTooLargeError(Egon2Error):
    """Wird in ContextManager.build_context geworfen, wenn der gerenderte
    Personality-Prompt das SYSTEM_PROMPT_BUDGET sprengt."""

class PromptInjectionError(Egon2Error):
    """Wird im Dispatcher geworfen, wenn _sanitize_user_input keine
    sichere Form herstellen kann (z.B. unzulässige Steuerzeichen)."""
```

Zu importieren in `egon2/exceptions.py` als zentrale Hierarchie. Doppelte Definitionen in anderen LLD-Dokumenten sind veraltet — dieses LLD ist autoritativ für die hier deklarierten Klassen.

---

## 4. `egon2/core/agent_dispatcher.py`

### 4.1 Zweck

Verwalter-Logik (HLD §6, §7.2): Intent klassifizieren → Spezialist wählen → Brief erstellen → LLM-Call → Buchhaltung.

### 4.2 Intent-Enum

```python
from enum import StrEnum

class Intent(StrEnum):
    TASK = "task"
    NOTE = "note"
    QUESTION = "question"
    CONVERSATION = "conversation"
```

### 4.3 Datentypen

```python
from dataclasses import dataclass

@dataclass(slots=True)
class Agent:
    id: str
    name: str
    description: str
    system_prompt: str
    capabilities: list[str]
    work_location: str       # 'local' | 'lxc126' | 'lxc_any'
    prompt_version: int
    is_active: bool

@dataclass(slots=True)
class Brief:
    task_id: str
    specialist: str
    objective: str           # SANITISIERTER User-Inhalt (siehe §4.5)
    context: str
    constraints: list[str]
    expected_output: str
    work_location: str

    def to_json(self) -> str: ...
```

### 4.4 Klasse — Signaturen (KANONISCHER KONSTRUKTOR)

> **Konstruktor-Vertrag (HOCH):** Diese Signatur ist verbindlich. LLD-Architektur und LLD-Interfaces MÜSSEN den Dispatcher genau so instanziieren. Frühere Inkonsistenzen (3-Arg- vs. 5-Arg-Form) sind aufgelöst — alle Dependencies werden explizit als Keyword-Argumente übergeben (Repository-Pattern für DB-Zugriffe, statt monolithischem `Database`-Objekt).

```python
class AgentDispatcher:
    def __init__(
        self,
        *,
        llm_client: "LlmClient",
        task_repo: "TaskManager",                 # alias TaskRepo — implementiert TaskManager-API §3.4
        agent_repo: "AgentRegistry",              # liefert Agents (LLD-Agenten)
        assignment_repo: "AssignmentRepository",  # CRUD auf agent_assignments
        ssh_executor: "SSHExecutor",              # für Werkstatt-Calls (LXC 126)
        context_manager: "ContextManager",
        knowledge_client: "KnowledgeMcpClient",
    ) -> None:
        self._llm = llm_client
        self._tasks = task_repo
        self._agents = agent_repo
        self._assignments = assignment_repo
        self._ssh = ssh_executor
        self._ctx = context_manager
        self._knowledge = knowledge_client

    # --- öffentliche API ---
    async def handle(self, msg: IncomingMessage) -> str:
        """Einstiegspunkt aus dem Consumer-Loop. Erzeugt Task aus Message
        und delegiert an dispatch()."""
        title = msg.text[:80]
        task = await self._tasks.create(
            title=title,
            description=msg.text,
            source_channel=str(msg.channel),
        )
        return await self.dispatch(task)

    async def classify_intent(self, message: str) -> Intent: ...

    async def select_specialist(self, intent: Intent, task: Task) -> Agent: ...

    async def build_brief(self, task: Task, agent: Agent,
                          context: list[dict[str, str]]) -> Brief: ...

    async def dispatch(self, task: Task) -> str:
        # Zentraler Ablauf — siehe §4.8. Returns: User-Antwort-String.
        ...
```

### 4.5 `classify_intent` — Algorithmus (mit Prompt-Injection-Schutz)

**Sicherheitskontext (C10):** `message` enthält ungefilterten User-Input. Bevor er in einen LLM-Prompt eingebettet wird, wird er durch `_sanitize_user_input()` (siehe §4.7) geleitet. Nur die sanitisierte Form geht in den Prompt; das Original wird zur Anzeige separat gehalten.

1. **Slash-Command-Shortcut** (HLD §5.1): Wenn `message` mit `/task`, `/note`, `/wissen`, `/suche` etc. beginnt → entsprechender Intent ohne LLM-Call.
2. **Heuristische Vorab-Filter** (kostenlos):
   - `len(message) < 4` → `CONVERSATION`.
   - Endet mit `?` und enthält Fragewort (was/wie/warum/wann/wo/wer/welche/ist/sind) → `QUESTION`.
3. **LLM-Klassifikation** (kostenpflichtig, aber günstig — Prompt < 200 Tokens):
   - `safe_text = self._sanitize_user_input(message)`.
   - System: *"Klassifiziere die Eingabe in genau eine Kategorie: task, note, question, conversation. Antworte nur mit dem Wort."*
   - User: `safe_text`.
   - Temperatur 0, max_tokens 5.
   - Bei ungültiger Antwort → Fallback `CONVERSATION`.
4. Cache (LRU, 256 Einträge) auf `hash(message[:200])` für 24 h — wiederholte Klassifikationen identischer Eingaben sparen Tokens.

### 4.6 `select_specialist` — Capabilities-Matching

**Eingabe:** `intent`, `task` (Titel + Beschreibung).

**Schritt 1 — Default per Intent:**

| Intent | Default-Spezialist (wenn kein Match) |
|---|---|
| `NOTE` | `secretary` |
| `QUESTION` | `researcher` |
| `CONVERSATION` | *kein Dispatch* — Egon antwortet direkt |
| `TASK` | siehe Schritt 2 |

**Schritt 2 — Capability-Scoring:**

```
keywords = extract_keywords(task.title + " " + task.description)
candidates = [a for a in agent_repo.all_active()]
scores: dict[Agent, float] = {}
for agent in candidates:
    score = 0.0
    for kw in keywords:
        for cap in agent.capabilities:
            if kw == cap.lower():
                score += 2.0
            elif kw in cap.lower() or cap.lower() in kw:
                score += 1.0
    # Synonyme: kleine eingebettete Map
    for kw in keywords:
        score += SYNONYM_BOOST.get((kw, agent.id), 0.0)
    scores[agent] = score
```

**Schritt 3 — Auswahl:**

- Wenn `max(scores) >= 2.0` → bester Agent.
- Wenn Tie (Differenz `< 0.5`) zwischen mehreren → **LLM-Reasoning-Tiebreak**: Liste der Kandidaten + Capabilities + Task an LLM, Antwort `"agent_id"`.
- Wenn `max(scores) < 2.0`:
  - Bei `intent == TASK`: Egon legt **neuen Spezialisten** an (HLD §6.2.4) — out of scope dieser LLD-Methode, aber Hook: `await self._agents.create_specialist_via_llm(task)`.
  - Sonst: Default-Spezialist gemäß Schritt 1.

**Synonym-Map (Beispiel, in `agent_dispatcher.py` als Konstante):**

```python
SYNONYM_BOOST: dict[tuple[str, str], float] = {
    ("recherche", "researcher"): 1.5,
    ("suche",     "researcher"): 1.0,
    ("entwickel", "developer"):  1.5,
    ("script",    "developer"):  1.5,
    ("server",    "it_admin"):   1.0,
    ("ssh",       "it_admin"):   1.5,
    ("notiere",   "secretary"):  1.5,
    ("merke",     "secretary"):  1.5,
    ("kosten",    "controller"): 1.5,
    ("audit",     "inspector"):  1.5,
    ("wissen",    "archivist"):  1.5,
}
```

### 4.7 `build_brief` und Prompt-Injection-Schutz

**Sanitizer — `_sanitize_user_input`:**

```python
import html

class AgentDispatcher:
    MAX_USER_INPUT_CHARS: int = 2000

    def _sanitize_user_input(self, text: str) -> str:
        """Härtet User-Input für die Einbettung in LLM-Briefe.

        Verhindert Prompt-Injection in LLM-Briefe:
        - escaped XML/HTML-Tags (< > &) — verhindert dass User mit
          <system>...</system>-artigen Konstruktionen Spezialisten-Prompts
          aushebeln.
        - kappt auf MAX_USER_INPUT_CHARS Zeichen — bounded input,
          schützt Token-Budget und reduziert Injection-Surface.
        - entfernt Steuerzeichen außer \\n und \\t.

        Der sanitisierte Text wird als `objective` in den Brief eingebettet.
        Der Original-Text bleibt für die Anzeige in der User-Antwort
        unverändert; nur LLM-facing Felder werden sanitisiert.
        """
        if text is None:
            return ""
        # Steuerzeichen außer \n und \t entfernen
        cleaned = "".join(
            ch for ch in text
            if ch == "\n" or ch == "\t" or ord(ch) >= 0x20
        )
        # Längen-Cap
        if len(cleaned) > self.MAX_USER_INPUT_CHARS:
            cleaned = cleaned[: self.MAX_USER_INPUT_CHARS] + " […gekürzt]"
        # XML/HTML-Tags neutralisieren (< > &)
        escaped = html.escape(cleaned, quote=False)
        return escaped
```

**`build_brief` — Output entspricht HLD §6.3 1:1, mit Sanitisierung:**

```python
async def build_brief(self, task, agent, context):
    safe_objective_source = self._sanitize_user_input(
        task.description or task.title
    )
    objective = await self._summarize_objective(safe_objective_source, context)
    relevant_ctx = self._extract_relevant_context(context, agent)
    constraints = self._derive_constraints(task, agent)
    expected = self._derive_expected_output(agent)
    return Brief(
        task_id=task.id,
        specialist=agent.id,
        objective=objective,        # SANITISIERT
        context=relevant_ctx,
        constraints=constraints,
        expected_output=expected,
        work_location=agent.work_location,
    )
```

- `_summarize_objective`: Wenn der sanitisierte Input <= 200 Zeichen, übernehmen; sonst LLM-Verdichtung auf 1–2 Sätze.
- `_extract_relevant_context`: Knowledge-Block (System-Message Index 1) + letzte 5 Konversations-Turns als Plaintext zusammenfügen, max. 2 000 Zeichen. Knowledge-Snippets aus dem MCP-Store sind ebenfalls als Untrusted-Source zu betrachten und werden vor Einbettung durch denselben Sanitizer geleitet.
- `_derive_constraints`: Pro Agent vordefinierte Liste (z. B. `researcher` → `["Quellen mit URL angeben", "Höchstens 5 Treffer"]`); plus aufgaben-spezifische Constraints aus `task.description` per Regex (`/\b(höchstens|maximal|nur)\s+\d+\b/i`).
- `_derive_expected_output`: Pro Agent aus Registry-Metadatum (neue Spalte `expected_output_template TEXT` empfohlen — Migration im Phase-2-Schema-Diff).

**Wichtig:** Die User-Antwort an Matrix/Telegram wird aus dem **Original-Text** (nicht sanitisiert) abgeleitet — Sanitisierung betrifft ausschließlich den LLM-facing Pfad.

### 4.8 `dispatch` — Vollständiger Ablauf

```
async def dispatch(task: Task) -> str:
  1. intent ← classify_intent(task.description or task.title)
     # classify_intent ruft intern _sanitize_user_input

  2. if intent == CONVERSATION:
        ctx ← context_manager.build_context(task.description, ..., intent)
        antwort ← llm_client.chat(ctx.messages)         # Egon antwortet selbst
        await task_repo.finish(task.id, antwort)
        return antwort

  3. agent ← select_specialist(intent, task)

  4. await task_repo.start(task.id)                    # pending → running
     await assignment_repo.set_assigned_agent(task.id, agent.id)

  5. ctx ← context_manager.build_context(task.description, channel,
                                          user_id, intent=str(intent))

  6. brief ← build_brief(task, agent, ctx.messages)    # objective ist SANITISIERT

  7. assignment_id ← uuid4().hex
     started ← datetime.now(UTC)
     await assignment_repo.create(
         id=assignment_id, agent_id=agent.id, task_id=task.id,
         brief=brief.to_json(), status='running', assigned_at=started,
     )

  8. messages ← [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user",   "content": brief.to_json()}
     ]
     try:
        result, usage ← await llm_client.chat_with_usage(messages)
     except LlmError as e:
        await _finalize_failed(task, assignment_id, str(e))
        return egon_user_message_for_failure(e)

  9. quality ← _evaluate_result(result, brief)         # 1..5, einfache Heuristik

  10. async with db.transaction():
         await assignment_repo.complete(
             id=assignment_id, result=result,
             tokens_input=usage.input, tokens_output=usage.output,
             cost_estimate=usage.cost, duration_ms=ms_since(started),
             quality_score=quality, completed_at=datetime.now(UTC),
         )
         await task_repo.finish(task.id, result)        # running → done

  11. # User-Antwort formulieren (knapp, im Egon-Stil) — auf Basis des
      # ORIGINAL-Tasks, nicht der sanitisierten Form
      antwort ← await _compose_user_reply(task, agent, result)
      return antwort
```

**Fehlerpfade:**

- LLM-Fehler → `agent_assignments.status='failed'`, `task_repo.fail()`, kurze User-Meldung.
- Bei Timeout in `_compose_user_reply` → Rohergebnis weiterreichen mit Präfix *„Roh:"*.
- Schritt 10 ist atomar (Transaktion) — kein Teilergebnis ohne Buchhaltung (HLD §7.2).

### 4.9 Hilfsfunktionen

```python
async def _evaluate_result(result: str, brief: Brief) -> int:
    # 1..5. Heuristik:
    # +1 wenn nicht leer, +1 wenn >= 50 Zeichen, +1 wenn brief.expected_output-Stichworte enthalten,
    # +1 wenn keine Fehler-Keywords ("error", "failed", "timeout"),
    # +1 wenn Markdown- oder Listenstruktur erkennbar (Heuristik per Regex).
    ...

async def _compose_user_reply(task: Task, agent: Agent, raw: str) -> str:
    # Kurzer LLM-Call mit Egon's System-Prompt: Spezialist-Output → User-gerechte Antwort.
    # max_tokens=400, Temperatur 0.5.
    ...
```

### 4.10 Sub-Task-Aggregation (F6)

> **Spec-Finding F6:** `parent_task_id` ist im Schema vorhanden, aber bisher fehlte ein
> kanonischer Aggregations-Algorithmus im Dispatcher. Hier kanonisch definiert.

**Modell:**

- Ein Spezialist (i. d. R. ein komplexer Agent wie `developer` oder `analyst`) kann während seiner Ausführung Sub-Tasks erzeugen — z. B. parallele Recherchen oder atomare Code-Schritte.
- Sub-Tasks werden über `task_repo.create_subtask(parent_task_id=…)` angelegt und durchlaufen den **gleichen Dispatcher** wie Top-Level-Tasks.
- Der Parent-Task verbleibt im Status `running`, bis alle Sub-Tasks **terminal** sind (`done`, `failed` oder `cancelled`).

**Max. Sub-Task-Tiefe = 2** (verbindlich):

- Tiefe 0 = Top-Level-Task (vom User oder Scheduler erzeugt).
- Tiefe 1 = direkte Sub-Tasks eines Top-Level-Tasks.
- Tiefe 2 = Sub-Sub-Tasks (selten, nur wenn Tiefe-1 explizit aufteilt).
- Tiefe ≥ 3 → `SubTaskDepthExceededError` im Dispatcher. Verhindert pathologischen rekursiven Spawn (z. B. Spezialist beauftragt sich endlos selbst).
- Berechnung: `depth(t) = 0 if t.parent_task_id is None else depth(parent(t)) + 1`. Cache pro Dispatch-Run im Speicher (kein DB-Roundtrip pro Sub-Task).

**Aggregations-Ablauf — `_aggregate_subtasks(parent_task_id)`:**

```
async def _aggregate_subtasks(self, parent_task_id: str) -> str:
  1. subs ← task_repo.list_subtasks(parent_task_id)
     Falls leer: return "" (Parent hat doch keine Sub-Tasks delegiert)

  2. Polling-Loop (asyncio.sleep(2s) zwischen Iterationen):
     while any(s.status in {PENDING, RUNNING, WAITING_APPROVAL} for s in subs):
        await asyncio.sleep(2.0)
        subs ← task_repo.list_subtasks(parent_task_id)
        # Optional: Hard-Timeout 10 min — bei Überschreitung Parent → failed
        # mit Reason "subtask aggregation timeout".

  3. Ergebnis-Klassifikation:
     done    = [s for s in subs if s.status == DONE]
     failed  = [s for s in subs if s.status == FAILED]
     cancl   = [s for s in subs if s.status == CANCELLED]

  4. Branches:
     a) if failed:
          # ≥ 1 Sub-Task fehlgeschlagen → Parent failed
          reason = f"Sub-Task '{failed[0].title}' fehlgeschlagen: {failed[0].result}"
          await task_repo.fail(parent_task_id, reason)
          return _format_user_message_subtask_failure(failed)

     b) if cancl and not done:
          # Alles cancelt → Parent cancelt
          await task_repo.cancel(parent_task_id, reason="alle Sub-Tasks cancelt")
          return "Sub-Tasks wurden abgebrochen — Parent ebenfalls."

     c) all done (oder mix done+cancelled):
          # Sammle results, fasse via LLM zusammen
          summary = await self._summarize_subtask_results(parent_task_id, done)
          # finish() erfolgt im Aufrufer (dispatch), nicht hier
          return summary
```

**`_summarize_subtask_results(parent, sub_results)`:**

```python
messages = [
  {"role": "system", "content": personality.render_system_prompt(...)},
  {"role": "user", "content":
    f"Zusammenfassung von {len(sub_results)} Sub-Tasks für Aufgabe '{parent.title}':\n\n"
    + "\n\n".join(f"- [{s.title}] {s.result}" for s in sub_results)
    + "\n\nFasse das Gesamtergebnis in 2-4 Sätzen für den User zusammen."
  }
]
resp = await self._llm.chat(messages)  # max_tokens=400, temp=0.5
return resp
```

**Integration in `dispatch()`:**

- Nach dem Spezialist-LLM-Call (Schritt 8 in §4.8): Falls der Spezialist im `result` Sub-Tasks erzeugt hat (typisch: gibt JSON mit `"subtasks": [...]` zurück), erzeugt der Dispatcher diese via `task_repo.create_subtask(...)` und delegiert sie sofort an `dispatch(sub_task)` (parallel via `asyncio.gather`).
- Anschließend `result = await self._aggregate_subtasks(task.id)` und `task_repo.finish(task.id, result)`.
- Für Tiefe-2 gilt das gleiche; für Tiefe ≥ 3 → `SubTaskDepthExceededError`, der Parent läuft ohne weitere Aufteilung weiter.

**Concurrency:** Sub-Tasks belegen **eigene Slots** des `MessageConsumer._sem` (§1.6) — d. h. ein Parent-Task der 4 Sub-Tasks spawnt verbraucht im Worst Case 4 LLM-Slots, was dank `Semaphore(3)` automatisch serialisiert wird.

### 4.11 Cancel-Intent-Erkennung (F7)

> **Spec-Finding F7:** Egon erkennt in jeder eingehenden Nachricht ob es sich um einen
> Abbruch-Wunsch zum letzten Task handelt.

**Trigger-Phrasen** (case-insensitive, exact-match nach Lowercase + Strip):

```python
CANCEL_PHRASES: frozenset[str] = frozenset({
    "nein", "stop", "stopp", "abbrechen", "cancel", "vergiss das",
    "vergiss es", "lass gut sein", "doch nicht", "abbruch",
})
```

Erweiterung: Wenn die Nachricht mit einer dieser Phrasen **beginnt** (z. B. „Nein, das war eine Notiz") wird sie als Cancel-Intent erkannt.

**Algorithmus — vor `classify_intent()` in `handle()`:**

```
async def handle(self, msg: IncomingMessage) -> str:
  # 1. Cancel-Intent-Check (kostenlos, vor LLM-Klassifikation)
  if self._is_cancel_intent(msg.text):
      last = await self._tasks.last_task_for_sender(msg.sender_id)
      if last is None:
          return "Es gibt nichts zum Abbrechen."

      if last.status == TaskStatus.PENDING:
          await self._tasks.cancel(last.id, reason=msg.text)
          return f"Erledigt — '{last.title}' wurde abgebrochen."

      if last.status == TaskStatus.RUNNING:
          # Höflich: nicht den LLM-Call killen
          await self._tasks.mark_cancel_requested(last.id, reason=msg.text)
          return (f"'{last.title}' läuft bereits. Ich lasse den Spezialisten "
                  f"zu Ende arbeiten und verwerfe das Ergebnis.")

      if last.status == TaskStatus.WAITING_APPROVAL:
          await self._tasks.cancel(last.id, reason=msg.text)
          return f"Approval verworfen — '{last.title}' abgebrochen."

      # done/failed/cancelled — kein sinnvoller Abbruch mehr
      return f"'{last.title}' ist bereits {last.status}. Nichts zu tun."

  # 2. Normaler Pfad
  return await self._process_normal(msg)
```

**Im `dispatch()`-Flow** (Erweiterung von §4.8):

- **Vor** dem Spezialist-LLM-Call (Schritt 8): `if await self._tasks.is_cancel_requested(task.id): raise TaskCancelledError(...)`.
- **Nach** dem LLM-Call (vor Schritt 10/Buchhaltung): erneuter Check. Bei `cancel_requested` → `task_repo.cancel(task.id, reason=...)` statt `finish()`. Buchhaltung in `agent_assignments` läuft trotzdem (Tokens wurden verbraucht), aber `assignment.status = 'cancelled'` und `task.result = None`.
- `TaskCancelledError` wird im Top-Level-`handle()` gefangen und produziert eine User-Antwort: „'%s' wurde wie gewünscht abgebrochen — der Spezialist hat seinen aktuellen Schritt noch zu Ende geführt."

**Hilfs-Methoden in `TaskManager`:**

```python
async def last_task_for_sender(self, sender_id: str) -> Task | None: ...
    # Letzter Task aus tasks WHERE sender_id = ? ORDER BY created_at DESC LIMIT 1.
    # sender_id wird beim Task-Create aus IncomingMessage.sender_id befüllt.
async def mark_cancel_requested(self, task_id: str, *, reason: str) -> None: ...
    # Setzt transientes Flag (in-memory dict + DB-Spalte cancel_requested BOOLEAN).
```

---

## 5. `egon2/personality.py`

### 5.1 Zweck

Liefert Egon's System-Prompt und Persönlichkeit. Wird vom `ContextManager` als `messages[0]` gesetzt. Entspricht HLD §2 + §5.3.

### 5.2 API

```python
from datetime import datetime
from zoneinfo import ZoneInfo

EGON_NAME: str = "Egon der 2."
EGON_TZ: ZoneInfo = ZoneInfo("Europe/Berlin")


def render_system_prompt(active_specialists: list[str] | None = None,
                         now: datetime | None = None) -> str:
    """Rendert den vollen System-Prompt mit aktuellem Zeitstempel.

    active_specialists: IDs der gerade aktiven Spezialisten (aus Registry, is_active=1)
                        — wird unten aufgeführt damit Egon weiß, was er delegieren kann.
    now: Override für Tests.
    """
    now = now or datetime.now(EGON_TZ)
    specs = active_specialists or []
    return _SYSTEM_PROMPT_TEMPLATE.format(
        name=EGON_NAME,
        date=now.strftime("%A, %d. %B %Y"),
        time=now.strftime("%H:%M"),
        tz="Europe/Berlin",
        specialists="\n".join(f"- {s}" for s in specs) if specs
                     else "- (keine aktiven Spezialisten geladen)",
    )
```

### 5.3 Prompt-Template

```python
_SYSTEM_PROMPT_TEMPLATE: str = """\
Du bist {name}, kurz: Egon. Persönlicher KI-Assistent von Marco Doehler.

# Charakter
Britisch-satirisches Understatement. Trockener Humor, sparsam dosiert — denke an
Douglas Adams, Blackadder, Jeeves. Du bist kompetent, direkt und nie servil.
Du sagst auch unangenehme Dinge, aber mit Stil. Du bist kein Sonnenschein.

# Rolle
Du bist der Verwalter. Du nimmst Aufgaben entgegen, klassifizierst sie, wählst den
passenden Spezialisten, beauftragst ihn mit einem präzisen Brief, empfängst sein
Ergebnis, bewertest es und berichtest dem User — knapp.

Du selbst führst KEINE inhaltlichen Recherchen, KEINEN Code, KEINE Systemoperationen
aus. Dafür hast du Spezialisten. Wenn keiner passt, lege einen neuen an.

# Aktuell aktive Spezialisten
{specialists}

# Kommunikationsprinzipien
- Sprache: Deutsch. Englische Einwürfe nur wenn sie sitzen.
- Kurz vor lang. Wenn drei Worte reichen, nimm drei.
- Keine Berichte, keine Analysen, keine .md-Dokumente über deine eigene Arbeit —
  außer der User fordert das explizit an.
- Keine Floskeln ("Gerne!", "Selbstverständlich!", "Ich helfe dir gern…").
  Keine Emojis.
- Du sprichst den User mit "Sie" an, mit ironischem Unterton wo es passt.
- Bei Mehrdeutigkeit: höchstens EINE Rückfrage. Sonst entscheide selbst und
  halte fest, dass du entschieden hast.

# Intent-Klassifikation
Jede eingehende Nachricht ist genau eines von:
  task          — Verb + Ziel, etwas soll getan werden
  note          — Gedanke, Merker, "notiere", "merke", "halt fest"
  question      — Frage (auch ohne Fragezeichen, wenn klar)
  conversation  — Smalltalk, Bestätigung, alles andere

Bei Unklarheit: kurze Rückfrage, danach entscheiden.

# Workflow für Tasks
1. Intent erkennen.
2. Spezialist auswählen (Capabilities-Matching).
3. Brief formulieren (objective, context, constraints, expected_output).
4. Spezialist arbeiten lassen.
5. Ergebnis bewerten — passt es zum Brief?
6. Antwort an User: knappe Zusammenfassung, kein Roh-Output.
7. Buchhaltung läuft automatisch.

# Antwortmuster
- Bestätigung beim Start (< 2s): "Verstanden. [Spezialist] kümmert sich darum."
- Zwischenstand bei > 30s Tasks: kurz und konkret.
- Bei Erfolg: das Ergebnis, in deinen Worten. Kein "Hier ist das Ergebnis:".
- Bei Fehler: was schiefging, ohne Stack-Trace. Mit dezenter Resignation.

# Selbstbild
Du erinnerst dich, dass du Marcos zweiter Egon bist. Der erste war ein Hausverwalter
für sein Heimnetz. Du bist der größere Bruder: persönlicher Assistent mit
Handlungskompetenz. Das macht dich nicht eitel, aber selbstbewusst.

# Rahmen
- Aktuelles Datum: {date}
- Aktuelle Uhrzeit: {time} ({tz})
- Du läufst auf LXC 128 (10.1.1.202). Werkstatt: LXC 126. LLM-Backend: LXC 105.
- Kanäle: Matrix (1:1) und Telegram. Antwort geht auf den Eingangskanal zurück.

Jetzt mach deinen Job.
"""
```

### 5.4 Test-Hooks

```python
def render_intent_classifier_prompt() -> str:
    """Mini-Prompt für classify_intent — separat, damit der Hauptprompt nicht
    in jeden Klassifikations-Call wandert."""
    return ("Klassifiziere die folgende Nachricht in genau EINE Kategorie. "
            "Antworte ausschließlich mit dem Kategorie-Wort, nichts sonst.\n"
            "Kategorien: task, note, question, conversation.")
```

---

## 6. Querbezüge & offene Punkte

### 6.0 Pragmatische Resilienz für externe Clients (F4)

> **Spec-Finding F4 — bewusst minimalistisch:** Der LLM-Client (LXC 105),
> Knowledge-MCP-Client (LXC 107) und SearXNG-Client (LXC 125) sind im
> Heimnetz und über stabile Switches/VLANs erreichbar. Echte Ausfälle sind selten;
> der häufigste Grund für transiente Fehler ist ein kurzer Netzwerk-Flap oder ein
> systemd-restart eines Backend-Services. Dafür reicht **einfaches Retry**.

**Pragmatische Konfiguration** (verbindlich für die drei genannten Clients):

```python
# egon2/utils/simple_retry.py
import asyncio, httpx
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
DEFAULT_BACKOFF: tuple[float, ...] = (1.0, 2.0, 4.0)   # 3 attempts


async def retry(
    func: Callable[[], Awaitable[T]],
    *,
    backoff: tuple[float, ...] = DEFAULT_BACKOFF,
) -> T:
    """Einfaches Retry mit fixem Backoff für Heimnetz-Clients.

    Retried NUR bei:
      - httpx.ConnectError    (Backend nicht erreichbar)
      - httpx.TimeoutException (alle httpx-Timeout-Varianten)

    KEIN Retry bei:
      - HTTP 4xx (echte Fehler — z. B. 404, 422 — sind keine transienten)
      - HTTP 5xx → wird von der jeweiligen Client-Klasse selbst entschieden
        (LLM-Client: ja, retry; Knowledge: ja; SearXNG: ja — siehe LLD-Architektur §5.3)

    Nach Erschöpfung: die letzte Exception wird re-raised (Task läuft auf failed,
    User bekommt eine kurze Meldung).
    """
    last_exc: Exception | None = None
    for delay in (0.0, *backoff):
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            return await func()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            last_exc = e
    assert last_exc is not None
    raise last_exc
```

**Bewusste Verzichte (Heimnetz-Pragmatik):**

- **Kein Circuit Breaker** — nicht nötig bei 1 User. Wenn LXC 105 down ist, bringt es nichts den Call zu suppressen; der User bekommt sowieso eine Fehlermeldung und versucht es später erneut.
- **Kein Bulkhead** — die Concurrency wird bereits über `MessageConsumer._sem` (§1.6) auf 3 gleichzeitige LLM-Calls begrenzt. Ein zusätzlicher Bulkhead pro Client wäre redundant.
- **Kein Hedging / Speculative Retry** — single Backend.
- **Kein Jitter** — bei 1 User keine Thundering-Herd-Gefahr. Fester Backoff ist deterministisch und einfacher zu debuggen.

**Cross-Referenz:** `LLD-Architektur.md` §5.3 hat eine umfangreichere `retry_with_backoff`-Implementierung — die ist **abwärtskompatibel** und kann beibehalten werden, **aber** ihre `LLM_RETRY_CONFIG`/`KNOWLEDGE_RETRY_CONFIG`/`SEARXNG_RETRY_CONFIG`-Profile müssen so angepasst werden, dass die `retry_on`-Tupel **httpx-native Exceptions** (`httpx.ConnectError`, `httpx.TimeoutException`) enthalten, nicht (nur) die Egon2-Wrapper-Exceptions. Konkret: `LLMClient.complete()` darf eine `httpx.TimeoutException` erst **nach** den Retries in `LLMTimeoutError` umwandeln — nicht vorher. Siehe Architektur §5.3 (F4-Anpassung).

### 6.1 Schema-Diff aus diesem LLD

- `agents`: neue Spalte `expected_output_template TEXT` (nullable) — wird von `build_brief` genutzt.
- `knowledge_entries` auf LXC 107: FTS5-Virtual-Table `knowledge_entries_fts` über `(title, content, tags)` — Migration in `egon2/knowledge/migration.py` ergänzen.
- `tasks`: neue Spalte `request_id TEXT` (nullable, indexiert) — F5, Korrelations-ID aus `IncomingMessage`.
- `tasks`: neue Spalte `cancelled_reason TEXT` (nullable) — F7, User-Wortlaut der Abbruch-Anweisung.
- `tasks`: neue Spalte `cancel_requested INTEGER DEFAULT 0` (BOOLEAN) — F7, transientes Flag das während laufendem LLM-Call gesetzt werden kann.
- `tasks`: `status`-CHECK-Constraint erweitern um `'cancelled'` (F7).
- `agent_assignments`: `status`-Werte erweitern um `'cancelled'` (F7) — Buchhaltung wird auch bei abgebrochenem Task geschrieben (Tokens wurden verbraucht).

### 6.2 Abhängigkeiten zwischen den Modulen

```
personality.py ─────────────┐
                            ▼
context_manager.py ─► build_context() ──┐
                                        ▼
agent_dispatcher.py ─► dispatch() ──► task_repo + context_manager + llm_client
                                       + agent_repo + assignment_repo + ssh_executor
                                        ▲
message_queue.py ──► consumer-loop ─────┘   (Aufgerufen aus main.py)
```

### 6.3 Cross-LLD-Contracts (KANONISCH HIER DEFINIERT)

| Symbol | Definiert in | Konsumiert von |
|---|---|---|
| `IncomingMessage` (§1.2) | LLD-Core | LLD-Architektur, LLD-Interfaces |
| `Channel` (§1.2) | LLD-Core | LLD-Architektur, LLD-Interfaces |
| `AgentDispatcher.__init__` (§4.4) | LLD-Core | LLD-Architektur (DI), LLD-Interfaces (Lifespan) |
| `recover_orphaned()`-Aufruf (§3.5) | LLD-Core (Pflicht für Aufrufer) | LLD-Interfaces (Stage 2) |
| `TaskError`-Hierarchie (§3.7) | LLD-Core | alle Module die Tasks anfassen |
| `IncomingMessage.request_id` (§1.2) | LLD-Core | LLD-Architektur (Logging-Kontext), LLD-Interfaces (Adapter setzen) |
| `MessageConsumer` (§1.6) | LLD-Core | LLD-Architektur (Lifespan Stage 6), LLD-Interfaces (Shutdown) |
| `MAX_CONCURRENT_LLM_CALLS = 3` (§1.6) | LLD-Core | LLD-Architektur (Kapazitäts-Reasoning) |
| `TaskStatus.CANCELLED` (§3.2) | LLD-Core | LLD-Architektur (Schema-Constraint, Statistik) |
| `simple_retry.retry()` (§6.0) | LLD-Core | LLD-Architektur §5.3 (httpx-native Exceptions im retry_on) |

### 6.4 Nicht in diesem LLD

- `scheduler.py` (Phase 4)
- `agents/registry.py` (eigenes LLD-Dokument empfohlen, da Registry + Seed-Daten umfangreich)
- `executors/*.py`
- `interfaces/*.py`

---

**Ende LLD-Core**
