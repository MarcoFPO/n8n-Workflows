# LLD — Egon2: Low-Level Design Architektur

**Version:** 1.4
**Stand:** 2026-05-02
**Basis:** HLD-Egon2.md v1.5
**Autor:** Marco Doehler / Claude
**Letzte Änderung:** Sicherheits-Patches (Knowledge-Store Firewall-Empfehlung in §3.2, Tool-Use-Limitation des LXC 105 Wrappers in §2.6 dokumentiert).

**Änderungen v1.4 (2026-05-02):**
- Add: Firewall-Empfehlung für Knowledge-Store (LXC 107:8080 auf Egon2-LXC einschränken) in §3.2 — verhindert Manipulation der System-Message-Inhalte durch andere LXCs.
- Add: Tool-Use-Hinweis in §2.6 LLM Client — Claude Code API Wrapper (LXC 105) unterstützt keine `tool_calls`-Schnittstelle; strukturierte Outputs via JSON-im-`user`-Format. Migrationspfad: `it_admin` zuerst, sobald Tool-Use verfügbar.
- Neu: `docs/LLD-Tests.md` v1.0 — Test-Strategie (pytest + pytest-asyncio, Unit/Integration/Async/Bot-Tests, Fixtures, Coverage-Ziele).

**Änderungen v1.3 (Audit-Runde-2-Findings 2026-05-02):**
- Fix: `datetime.utcnow()` → `lambda: datetime.now(UTC)` in `AgentAssignmentRecord` und `HealthCheckRecord`; `UTC` zu Imports ergänzt (§2.1 models.py).
- Fix: `AgentDispatcher.process_message()` → `handle()`, `dispatch_task()` → `dispatch()` — Methodennamen an kanonische LLD-Core §4.4 API angeglichen (§2.3).

---

## 1. Komponentendiagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LXC 128 — Egon2-App  (10.1.1.202)                                          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  INTERFACE LAYER                                                      │   │
│  │                                                                       │   │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────────┐  │   │
│  │  │  matrix_bot.py       │    │  telegram_bot.py                     │  │   │
│  │  │  matrix-nio (async) │    │  python-telegram-bot v21 (async)    │  │   │
│  │  │  @egon2:doehlercmp. │    │  Whitelist: Telegram-User-IDs       │  │   │
│  │  └──────────┬──────────┘    └──────────────────┬──────────────────┘  │   │
│  │             │  IncomingMessage                  │  IncomingMessage     │   │
│  │             └──────────────────┬────────────────┘                     │   │
│  │                                ▼                                       │   │
│  │                  ┌─────────────────────────┐                          │   │
│  │                  │  message_queue.py         │                          │   │
│  │                  │  asyncio.Queue[IncomingMessage]                    │   │
│  │                  │  maxsize=100              │                          │   │
│  │                  └────────────┬────────────┘                          │   │
│  └───────────────────────────────┼───────────────────────────────────────┘   │
│                                  │                                            │
│  ┌───────────────────────────────▼───────────────────────────────────────┐   │
│  │  CORE ENGINE                                                           │   │
│  │                                                                        │   │
│  │  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐  │   │
│  │  │  context_manager │   │  task_manager.py  │   │  scheduler.py    │  │   │
│  │  │  .py             │   │  CRUD + Status-   │   │  AsyncIOScheduler│  │   │
│  │  │  System-Prompt   │◄──│  Transitions      │   │  5 Jobs (Cron)   │  │   │
│  │  │  Rolling Window  │   │  pending→running  │   │  SQLite JobStore │  │   │
│  │  │  Knowledge Top-5 │   │  →done/failed     │   └────────┬─────────┘  │   │
│  │  └────────┬─────────┘   └──────────────────┘            │             │   │
│  │           │                       ▲                       │             │   │
│  │           │  ContextBundle        │ TaskRecord            │ JobEvent    │   │
│  │           └───────────────────────┼───────────────────────┘             │   │
│  │                                   ▼                                     │   │
│  │                    ┌──────────────────────────┐                         │   │
│  │                    │  agent_dispatcher.py      │                         │   │
│  │                    │  Intent-Klassifikation    │                         │   │
│  │                    │  Capabilities-Matching    │                         │   │
│  │                    │  Brief erstellen          │                         │   │
│  │                    │  LLM-Call orchestrieren   │                         │   │
│  │                    │  Buchhaltung (Transaktion)│                         │   │
│  │                    └────────────┬─────────────┘                         │   │
│  └─────────────────────────────────┼─────────────────────────────────────┘   │
│                                    │                                           │
│  ┌─────────────────────────────────▼─────────────────────────────────────┐   │
│  │  AGENTEN-SCHICHT  (agents/)                                            │   │
│  │                                                                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │researcher│ │journalist│ │ it_admin │ │developer │ │ analyst  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │controller│ │archivist │ │ designer │ │secretary │ │inspector │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │                                                                        │   │
│  │  Alle via: llm_client.py → http://10.1.1.105:3001                     │   │
│  └───────────┬───────────────────────────────────────────────────────────┘   │
│              │                                                                 │
│  ┌───────────▼───────────────────────────────────────────────────────────┐   │
│  │  EXECUTOR LAYER  (executors/)                                          │   │
│  │                                                                        │   │
│  │  ┌───────────────────────┐    ┌───────────────────────────────────┐  │   │
│  │  │  ssh_executor.py       │    │  shell_executor.py                  │  │   │
│  │  │  asyncssh              │    │  Whitelist: ls,cat,grep,find,      │  │   │
│  │  │  User: egon            │    │  echo,curl,python3                 │  │   │
│  │  │  Key: /opt/egon2/      │    │  Bestätigung für destruktive Ops   │  │   │
│  │  │  .ssh/id_ed25519       │    └───────────────────────────────────┘  │   │
│  │  │  Timeout: 120s         │                                            │   │
│  │  └───────────────────────┘                                            │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │  PERSISTENZ (lokal)                                                   │     │
│  │  aiosqlite WAL-Modus → /opt/egon2/data/egon2.db                      │     │
│  │  APScheduler SQLiteJobStore → /opt/egon2/data/scheduler.db           │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌──────────────┐
  │ LXC 105     │   │ LXC 107      │   │ LXC 125          │   │ LXC 126      │
  │ claude      │   │ mcp-sequen.  │   │ SearXNG          │   │ egon-werkst. │
  │ :3001       │   │ :8080        │   │ :80              │   │ SSH :22      │
  │ Claude Code │   │ Knowledge    │   │ Metasuchmaschine │   │ Werkstatt-   │
  │ API         │   │ MCP Store    │   │                  │   │ Verzeichnis  │
  │ OpenAI-komp │   │ SQLite       │   │                  │   │ /opt/Proj.   │
  └─────────────┘   └──────────────┘   └─────────────────┘   └──────────────┘
```

**Kommunikationswege:**

| Von | Nach | Protokoll | Library |
|---|---|---|---|
| matrix_bot | message_queue | asyncio.Queue.put() | intern |
| telegram_bot | message_queue | asyncio.Queue.put() | intern |
| agent_dispatcher | llm_client | HTTP/1.1 POST | httpx async |
| llm_client | LXC 105:3001 | HTTP/1.1 | httpx async |
| knowledge/mcp_client | LXC 107:8080 | HTTP/1.1 | httpx async (Pool 5) |
| agents/researcher | LXC 125:80 | HTTP/1.1 | httpx async |
| ssh_executor | LXC 126:22 | SSH | asyncssh |
| sync/bookstack_sync | BookStack | HTTPS | httpx async |
| sync/github_sync | GitHub API | HTTPS | httpx async |

---

## 2. Interne API-Schnittstellen

### 2.1 Datenmodelle (Pydantic)

> **Hinweis C1 (Audit-Finding 1.1):** Die frühere Pydantic-Definition von `IncomingMessage` in diesem LLD wurde entfernt.
> Kanonische Definition: `egon2.core.message_queue.IncomingMessage` — siehe LLD-Core.md § 1.2.
> Dieses LLD referenziert `IncomingMessage` nur noch über diesen Import.

```python
# egon2/models.py
from __future__ import annotations
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid

# IncomingMessage wird aus egon2.core.message_queue importiert — Definition dort.
# Hier NICHT neu definieren.
from egon2.core.message_queue import IncomingMessage  # noqa: F401 (re-export für Kompatibilität)


class Channel(str, Enum):
    MATRIX = "matrix"
    TELEGRAM = "telegram"
    SCHEDULER = "scheduler"   # interner Kanal für scheduler-getriggerte Pseudo-Messages


class IntentType(str, Enum):
    TASK = "task"
    NOTE = "note"
    QUESTION = "question"
    CONVERSATION = "conversation"
    COMMAND = "command"      # /status, /stats, /suche etc.


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"
    CANCELLED = "cancelled"      # F7 — User-Abbruch (terminal)


class AssignmentStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"      # F7 — Buchhaltung wird auch bei Cancel geschrieben


class WorkLocation(str, Enum):
    LOCAL = "local"
    LXC126 = "lxc126"
    LXC_ANY = "lxc_any"


class HealthStatus(str, Enum):
    OK = "ok"
    REPAIRED = "repaired"
    WARNING = "warning"
    DEGRADED = "degraded"


class OutgoingMessage(BaseModel):
    """Ausgehende Antwort an einen Kanal."""
    channel: Channel
    room_id: str                    # Ziel: Room-ID (Matrix) oder Chat-ID (Telegram)
    content: str
    reply_to_event_id: str | None = None   # Matrix: thread reply
    parse_mode: str = "Markdown"           # Telegram: "Markdown" | "HTML"


# --- Intent & Kontext ---

class ClassifiedIntent(BaseModel):
    """Ergebnis der LLM-basierten Intent-Klassifikation."""
    intent_type: IntentType
    confidence: float               # 0.0–1.0
    extracted_task: str | None = None       # Bei TASK: extrahierte Aufgabenbeschreibung
    extracted_note: str | None = None       # Bei NOTE: Notiz-Inhalt
    requires_clarification: bool = False
    clarification_question: str | None = None


class ConversationEntry(BaseModel):
    """Ein Eintrag im Rolling Window."""
    id: str
    channel: Channel
    role: str                       # "user" | "assistant"
    content: str
    timestamp: datetime


class KnowledgeEntry(BaseModel):
    """Ein Treffer aus dem Knowledge Store."""
    id: str
    title: str
    content: str
    domain: str
    importance: int
    relevance_score: float          # 0.0–1.0, berechnet durch mcp_client


class ContextBundle(BaseModel):
    """Vollständiger Kontext für einen LLM-Call."""
    system_prompt: str              # Egon-Persönlichkeit + Fähigkeiten + Datum/Uhrzeit
    conversation_history: list[ConversationEntry]   # letzte 20 Einträge
    knowledge_entries: list[KnowledgeEntry]          # Top-5 nach Relevanz
    incoming_message: IncomingMessage
    current_task_id: str | None = None


# --- Tasks ---

class TaskRecord(BaseModel):
    """Task-Datensatz aus der DB."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str | None = None
    source_channel: Channel
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    result: str | None = None
    parent_task_id: str | None = None
    request_id: str | None = None             # F5 — Korrelations-ID, übernommen aus IncomingMessage
    cancelled_reason: str | None = None       # F7 — User-Wortlaut der Abbruch-Anweisung
    cancel_requested: bool = False            # F7 — transientes Flag für laufende Tasks
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    source_channel: Channel


class TaskUpdateRequest(BaseModel):
    status: TaskStatus | None = None
    result: str | None = None
    assigned_agent: str | None = None


# --- Agenten ---

class AgentRecord(BaseModel):
    """Spezialist aus der agents-Tabelle."""
    id: str                         # z.B. "researcher"
    name: str
    description: str | None = None
    system_prompt: str
    capabilities: list[str]         # z.B. ["web_search", "fact_check", "summarize"]
    work_location: WorkLocation
    prompt_version: int = 1
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class AgentBrief(BaseModel):
    """Auftrag an einen Spezialisten."""
    task_id: str
    specialist: str                 # Agent-ID
    objective: str
    context: str
    constraints: list[str] = Field(default_factory=list)
    expected_output: str
    work_location: WorkLocation


class AgentResult(BaseModel):
    """Ergebnis eines Spezialisten-Runs."""
    assignment_id: str
    task_id: str
    agent_id: str
    result: str
    status: AssignmentStatus
    tokens_input: int
    tokens_output: int
    cost_estimate: float            # USD
    duration_ms: int
    quality_score: int | None = None   # 1–5, optional manuell


class AgentAssignmentRecord(BaseModel):
    """agent_assignments-Tabelleneintrag."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    task_id: str
    brief: AgentBrief
    result: str | None = None
    status: AssignmentStatus = AssignmentStatus.RUNNING
    tokens_input: int = 0
    tokens_output: int = 0
    cost_estimate: float = 0.0
    duration_ms: int = 0
    quality_score: int | None = None
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


# --- LLM ---

class LLMMessage(BaseModel):
    role: str                       # "system" | "user" | "assistant"
    content: str


class LLMRequest(BaseModel):
    model: str = "claude-sonnet-4-6"
    messages: list[LLMMessage]
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str              # "stop" | "length" | "tool_calls"


# --- Gesundheitschecks ---

class HealthCheckRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    check_type: str                 # "system" | "data" | "agent"
    target: str
    status: HealthStatus
    findings: list[str] = Field(default_factory=list)
    action_taken: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# --- SSH ---

class SSHCommandResult(BaseModel):
    host: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
```

---

### 2.2 Interface Layer → Message Queue

**Schnittstelle:** `message_queue.py`

```python
# egon2/core/message_queue.py
import asyncio
from egon2.models import IncomingMessage


class MessageQueue:
    """Async FIFO-Queue zwischen Interface Layer und Core Engine."""

    def __init__(self, maxsize: int = 100) -> None:
        self._queue: asyncio.Queue[IncomingMessage] = asyncio.Queue(maxsize=maxsize)

    async def put(self, message: IncomingMessage) -> None:
        """Nachricht einreihen. Bei voller Queue: BlockingError nach 5s.

        Raises:
            asyncio.QueueFull: Wenn Queue nach 5s noch voll (über asyncio.wait_for).
        """
        await asyncio.wait_for(self._queue.put(message), timeout=5.0)

    async def get(self) -> IncomingMessage:
        """Nächste Nachricht abholen. Blockiert bis Nachricht verfügbar.

        Returns:
            IncomingMessage: Nächste zu verarbeitende Nachricht.
        """
        return await self._queue.get()

    def task_done(self) -> None:
        """Nach Verarbeitung aufrufen (für join()-Kompatibilität)."""
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()
```

**Fehlerfälle:**
- `asyncio.TimeoutError` — Queue voll für > 5s: Matrix/Telegram-Bot loggt als WARNING, Nachricht wird verworfen
- Queue leer: `get()` blockiert — kein Fehler, normaler Betrieb

---

### 2.3 Message Queue → Agent Dispatcher

**Schnittstelle:** `agent_dispatcher.py`

```python
# egon2/core/agent_dispatcher.py
from egon2.models import (
    IncomingMessage, OutgoingMessage, ContextBundle,
    ClassifiedIntent, AgentBrief, AgentResult, TaskRecord
)


class AgentDispatcher:

    async def handle(
        self,
        message: IncomingMessage,
    ) -> str:
        """Einstiegspunkt aus dem Consumer-Loop (kanonisch: LLD-Core §4.4).

        Ablauf:
            1. Task aus Message erzeugen
            2. classify_intent()
            3. Routing je nach IntentType
            4. Antwort formulieren und zurückgeben

        Args:
            message: Eingehende Nachricht aus der Queue.

        Returns:
            str: Fertige Antwort für Interface Layer.

        Raises:
            LLMClientError: Bei LLM-API-Fehler (nach Retries erschöpft).
            DatabaseError: Bei SQLite-Fehler beim Schreiben.
        """
        ...

    async def classify_intent(
        self,
        message: IncomingMessage,
        context: ContextBundle,
    ) -> ClassifiedIntent:
        """Klassifiziert den Intent via LLM-Call.

        Nutzt einen dedizierten, kurzen System-Prompt für die Klassifikation.
        Kein Spezialist-System-Prompt hier — nur Egon's Klassifikations-Logik.

        Args:
            message: Die zu klassifizierende Nachricht.
            context: Aktueller Kontext (für rolling window).

        Returns:
            ClassifiedIntent: Klassifiziertes Intent mit Confidence.

        Raises:
            LLMClientError: Bei LLM-Fehler.
        """
        ...

    async def dispatch(
        self,
        task: TaskRecord,
    ) -> str:
        """Wählt Spezialisten, erstellt Brief und führt LLM-Call aus.

        Ablauf (atomar in einer SQLite-Transaktion am Ende):
            1. capabilities_match() → AgentRecord
            2. build_brief() → AgentBrief
            3. Task-Status → 'running' (sofort, außerhalb Transaktion)
            4. LLM-Call mit Spezialist-System-Prompt
            5. Task-Status + agent_assignment in einer Transaktion

        Args:
            task: Der angelegte TaskRecord.

        Returns:
            str: Ergebnis-Text des Spezialisten.

        Raises:
            NoAgentFoundError: Kein passender Spezialist (löst Agent-Anlage aus).
            LLMClientError: Bei LLM-Fehler.
            DatabaseError: Bei Transaktionsfehler.
        """
        ...

    async def capabilities_match(
        self,
        intent: ClassifiedIntent,
        context: ContextBundle,
    ) -> AgentRecord:
        """Wählt den optimalen Spezialisten per LLM-Reasoning.

        Lädt alle aktiven Agenten aus der Registry.
        Bei eindeutigem Match: direkt zurückgeben.
        Bei mehreren Matches: kurzer LLM-Call zum Auswählen.
        Bei keinem Match: NoAgentFoundError.

        Args:
            intent: Klassifiziertes Intent mit extrahierter Aufgabe.
            context: Kontext für LLM-Reasoning.

        Returns:
            AgentRecord: Ausgewählter Spezialist.

        Raises:
            NoAgentFoundError: Kein aktiver Spezialist gefunden.
        """
        ...

    async def build_brief(
        self,
        task: TaskRecord,
        agent: AgentRecord,
        intent: ClassifiedIntent,
        context: ContextBundle,
    ) -> AgentBrief:
        """Erstellt den strukturierten Auftrag (Brief) für den Spezialisten.

        Returns:
            AgentBrief: Vollständig befüllter Brief.
        """
        ...

    async def record_assignment(
        self,
        task: TaskRecord,
        brief: AgentBrief,
        result: AgentResult,
    ) -> None:
        """Schreibt Task-Update + agent_assignment in einer SQLite-Transaktion.

        Raises:
            DatabaseError: Bei Fehler — Task bleibt auf 'running', muss manuell bereinigt werden.
        """
        ...
```

**Fehlerfälle:**

| Fehler | Typ | Verhalten |
|---|---|---|
| LLM nicht erreichbar (nach Retries) | `LLMClientError` | Task → 'failed', User-Meldung |
| Kein Spezialist gefunden | `NoAgentFoundError` | Egon legt neuen Agenten an und wiederholt |
| SQLite Transaktionsfehler | `DatabaseError` | Task bleibt 'running' → Health-Check bereinigt |
| Spezialist-LLM-Call Timeout | `asyncio.TimeoutError` | AgentResult.status = 'failed', Egon meldet Grund |

---

### 2.4 Agent Dispatcher → Context Manager

```python
# egon2/core/context_manager.py
from egon2.models import IncomingMessage, ContextBundle, ConversationEntry, KnowledgeEntry


class ContextManager:

    async def build_context(
        self,
        message: IncomingMessage,
        current_task_id: str | None = None,
    ) -> ContextBundle:
        """Baut den vollständigen Kontext für einen LLM-Call auf.

        Lädt parallel:
            - build_system_prompt() → str
            - get_rolling_window() → list[ConversationEntry]
            - get_relevant_knowledge() → list[KnowledgeEntry]

        Args:
            message: Eingehende Nachricht als Relevanz-Anker.
            current_task_id: Optionale Task-ID für Kontext-Anreicherung.

        Returns:
            ContextBundle: Vollständiger Kontext.

        Raises:
            KnowledgeClientError: Bei LXC 107 nicht erreichbar (non-fatal: leere Liste).
            DatabaseError: Bei SQLite-Fehler beim Rolling Window.
        """
        ...

    def build_system_prompt(self) -> str:
        """Baut den aktuellen System-Prompt inkl. Datum/Uhrzeit.

        Format:
            [Egon's Persönlichkeit aus personality.py]
            Aktuelles Datum: {date} Uhrzeit: {time} (Europe/Berlin)
            [Spezialist-Registry-Kurzübersicht]

        Returns:
            str: Fertiger System-Prompt.
        """
        ...

    async def get_rolling_window(
        self,
        limit: int = 20,
    ) -> list[ConversationEntry]:
        """Liest die letzten `limit` Nachrichten aus conversations (kanalunabhängig).

        Args:
            limit: Anzahl Nachrichten (Standard: 20).

        Returns:
            list[ConversationEntry]: Chronologisch aufsteigend.

        Raises:
            DatabaseError: Bei SQLite-Fehler.
        """
        ...

    async def get_relevant_knowledge(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[KnowledgeEntry]:
        """Holt Top-k relevante Knowledge-Einträge von LXC 107.

        Args:
            query: Suchbegriff (aus message.content extrahiert).
            top_k: Anzahl Ergebnisse (Standard: 5).

        Returns:
            list[KnowledgeEntry]: Nach Relevanz absteigend. Bei Fehler: leere Liste.
        """
        ...

    async def save_conversation_entry(
        self,
        channel: Channel,
        role: str,
        content: str,
    ) -> str:
        """Speichert einen Gesprächseintrag in conversations.

        Returns:
            str: ID des gespeicherten Eintrags.

        Raises:
            DatabaseError: Bei SQLite-Fehler.
        """
        ...
```

---

### 2.5 Task Manager

```python
# egon2/core/task_manager.py
from egon2.models import TaskRecord, TaskCreateRequest, TaskUpdateRequest, TaskStatus


class TaskManager:

    async def create(
        self,
        request: TaskCreateRequest,
    ) -> TaskRecord:
        """Legt neuen Task in der DB an (Status: 'pending').

        Returns:
            TaskRecord: Gespeicherter Task mit generierter UUID.

        Raises:
            DatabaseError: Bei SQLite-Fehler.
        """
        ...

    async def update(
        self,
        task_id: str,
        request: TaskUpdateRequest,
    ) -> TaskRecord:
        """Aktualisiert Task-Felder. Setzt updated_at = now().

        Args:
            task_id: UUID des Tasks.
            request: Felder die aktualisiert werden sollen.

        Returns:
            TaskRecord: Aktualisierter Task.

        Raises:
            TaskNotFoundError: Task-ID nicht in DB.
            DatabaseError: Bei SQLite-Fehler.
        """
        ...

    async def get(self, task_id: str) -> TaskRecord:
        """Lädt einen Task aus der DB.

        Raises:
            TaskNotFoundError: Task-ID nicht in DB.
        """
        ...

    async def list_active(self) -> list[TaskRecord]:
        """Alle Tasks mit Status 'pending' oder 'running'.

        Returns:
            list[TaskRecord]: Chronologisch aufsteigend nach created_at.
        """
        ...

    async def list_recent(
        self,
        limit: int = 10,
        status: TaskStatus | None = None,
    ) -> list[TaskRecord]:
        """Letzte `limit` Tasks, optional nach Status gefiltert.

        Returns:
            list[TaskRecord]: Chronologisch absteigend.
        """
        ...

    async def get_stale_running(
        self,
        older_than_minutes: int = 60,
    ) -> list[TaskRecord]:
        """Tasks mit Status 'running' die älter als N Minuten sind.

        Wird vom Health-Check zur Bereinigung genutzt.
        """
        ...
```

---

### 2.6 LLM Client

```python
# egon2/llm_client.py
from egon2.models import LLMRequest, LLMResponse, ContextBundle, AgentBrief


class LLMClient:
    """HTTP-Client gegen Claude Code API (LXC 105:3001, OpenAI-kompatibel).

    Retry-Strategie: Exponential Backoff (s. Abschnitt 5).
    Connection Pool: httpx.AsyncClient, limits=httpx.Limits(max_connections=10).
    """

    BASE_URL: str = "http://10.1.1.105:3001"
    DEFAULT_MODEL: str = "claude-sonnet-4-6"
    CONNECT_TIMEOUT: float = 10.0
    READ_TIMEOUT: float = 120.0

    async def complete(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Sendet einen Chat-Completion-Request.

        Args:
            request: Vollständiger LLM-Request.

        Returns:
            LLMResponse: Antwort des Modells.

        Raises:
            LLMClientError: Bei HTTP-Fehler, Timeout oder Parse-Fehler (nach Retries).
            LLMRateLimitError: Bei HTTP 429 (mit Retry-After-Header).
        """
        ...

    async def complete_with_context(
        self,
        context: ContextBundle,
        user_content: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Convenience-Methode: Baut LLMRequest aus ContextBundle.

        Konvertiert:
            context.system_prompt → messages[0] (role=system)
            context.conversation_history → messages[1..n]
            user_content → messages[-1] (role=user)

        Returns:
            LLMResponse: Antwort.
        """
        ...

    async def run_specialist(
        self,
        agent: AgentRecord,
        brief: AgentBrief,
        context: ContextBundle,
    ) -> LLMResponse:
        """Führt einen Spezialisten-Call aus.

        System-Prompt = agent.system_prompt
        User-Message  = JSON-serialisierter Brief + relevanter Kontext

        Returns:
            LLMResponse: Spezialisten-Antwort.
        """
        ...
```

> **Tool-Use:** Der Claude Code API Wrapper auf LXC 105 (OpenAI-kompatibler Proxy) unterstützt keine `tool_calls`-Schnittstelle. Alle strukturierten Outputs erfolgen via JSON-im-`user`-Message-Format. Sobald Tool-Use verfügbar: `it_admin`-Spezialist sollte als erstes umgestellt werden.

---

### 2.7 SSH Executor

> **C9 — Sicherheits-Notiz (Security-Audit Finding 3.1): sudo-Scope**
>
> Aktuell konfigurierter sudo-Umfang auf Ziel-LXCs:
> `egon NOPASSWD: /usr/bin/apt, /bin/systemctl, /usr/sbin/pct`
>
> **Risiko:** `pct` erlaubt effektiv root-Zugriff auf alle LXCs (inkl. Vaultwarden LXC 127,
> Mailserver LXC 121). Eine Kompromittierung von LXC 128 wäre cluster-weit terminal.
>
> **Akzeptiert:** Privates Heimnetz, Single-User, kein externer Angriffvektor auf LXC 128.
>
> **Empfehlung für Production-Härtung:** pct-Zugriff auf whitelist-LXCs beschränken via
> sudoers-Alias (nur `pct list`, `pct status *`, `pct config *` — keine `pct exec`/`pct push`).
> Schreibende pct-Operationen über `waiting_approval`-Workflow (Marco bestätigt im Chat).
>
> Vollständige Sudoers-Vorlage: siehe Security-Audit Finding 3.1.

#### Sicherheitsprofil LXC 126 (Werkstatt)

> **C9 — Security-Audit Finding 3.4: LXC 126 Sandbox-Status**
>
> - Developer-Spezialist führt Code via SSH aus — LXC 126 ist per Design ein Code-Execution-Primitive.
> - LXC 126 ist **privilegierter Container** (by design, kein unprivilegierter Container).
> - **Akzeptiertes Risiko im Heimnetz:** kein seccomp/cgroup-Filter aktiv, kein AppArmor-Profil.
> - **Mitigierende Maßnahmen:**
>   - SSH-Zugang nur von LXC 128 (`from="10.1.1.202"` in authorized_keys der Ziel-LXCs)
>   - Pfad-Beschränkung im Developer-Prompt: Spezialisten dürfen nur in `/opt/Projekte/Egon2/werkstatt/<task-id>/` schreiben
>   - Kein Egon2-DB-Zugriff von LXC 126 aus (keine DB-Credentials auf LXC 126)
>   - task_id wird als UUID validiert (Regex `^[0-9a-f-]{32,36}$`) **vor** jeder Pfad-Interpolation
>   - Output-Truncation: 1 MiB hard cap in `_truncate()`
> - **Empfehlung Phase 3+:** `systemd-run --scope -p MemoryMax=1G -p CPUQuota=200%` für
>   Developer-Kommandos; Network-Egress-Filter: LXC 126 darf nur 10.1.1.105 (LLM) und 10.1.1.107 (Knowledge) erreichen.

```python
# egon2/executors/ssh_executor.py
from egon2.models import SSHCommandResult


class SSHExecutor:
    """asyncssh-basierter SSH-Executor für LXC 126 und andere Hosts."""

    SSH_USER: str = "egon"
    SSH_KEY_PATH: str = "/opt/egon2/.ssh/id_ed25519"
    COMMAND_TIMEOUT: float = 120.0

    async def run(
        self,
        host: str,
        command: str,
        timeout: float | None = None,
    ) -> SSHCommandResult:
        """Führt ein Kommando auf einem Remote-Host aus.

        Args:
            host: Hostname oder IP (z.B. "10.1.1.203").
            command: Shell-Kommando.
            timeout: Überschreibt Standard-Timeout (120s).

        Returns:
            SSHCommandResult: stdout, stderr, exit_code, duration_ms.

        Raises:
            SSHConnectionError: Bei Verbindungsfehler (Host nicht erreichbar, Auth fehlgeschlagen).
            SSHTimeoutError: Bei Überschreitung des Timeouts.
        """
        ...

    async def run_werkstatt(
        self,
        task_id: str,
        command: str,
    ) -> SSHCommandResult:
        """Führt Kommando im task-spezifischen Werkstatt-Verzeichnis auf LXC 126 aus.

        Arbeitsverzeichnis: /opt/Projekte/Egon2/werkstatt/{task_id}/

        Raises:
            SSHConnectionError: Bei Verbindungsfehler.
            SSHTimeoutError: Bei Timeout.
        """
        ...

    async def ensure_werkstatt_dir(self, task_id: str) -> SSHCommandResult:
        """Legt Werkstatt-Verzeichnis für task_id an falls nicht vorhanden.

        Kommando: mkdir -p /opt/Projekte/Egon2/werkstatt/{task_id}
        """
        ...

    async def cleanup_werkstatt(self, task_id: str) -> SSHCommandResult:
        """Löscht Werkstatt-Verzeichnis nach 24h.

        Kommando: rm -rf /opt/Projekte/Egon2/werkstatt/{task_id}
        """
        ...
```

---

### 2.8 Shell Executor

```python
# egon2/executors/shell_executor.py
from egon2.models import SSHCommandResult


ALLOWED_COMMANDS: frozenset[str] = frozenset([
    "ls", "cat", "grep", "find", "echo", "curl", "python3",
])

DESTRUCTIVE_COMMANDS: frozenset[str] = frozenset([
    "rm", "mv", "systemctl stop", "systemctl disable",
    "apt remove", "apt purge", "kill", "pkill",
])


class ShellExecutor:
    """Lokaler Shell-Executor mit Whitelist-Enforcement."""

    COMMAND_TIMEOUT: float = 30.0

    async def run(
        self,
        command: str,
        working_dir: str = "/opt/egon2",
    ) -> SSHCommandResult:
        """Führt Whitelist-geprüftes Kommando lokal aus.

        Args:
            command: Shell-Kommando. Wird gegen ALLOWED_COMMANDS geprüft.
            working_dir: Arbeitsverzeichnis.

        Returns:
            SSHCommandResult: stdout, stderr, exit_code, duration_ms.

        Raises:
            CommandNotAllowedError: Kommando nicht in Whitelist.
            ShellTimeoutError: Timeout nach 30s.
        """
        ...

    async def run_destructive(
        self,
        command: str,
        confirmation_token: str,
    ) -> SSHCommandResult:
        """Führt destruktives Kommando nach Bestätigung aus.

        Args:
            command: Destruktives Kommando.
            confirmation_token: UUID aus vorheriger User-Bestätigung im Chat.

        Raises:
            ConfirmationRequiredError: confirmation_token ungültig oder abgelaufen.
            CommandNotAllowedError: Kommando nicht in DESTRUCTIVE_COMMANDS.
        """
        ...
```

---

## 3. Externe API-Schnittstellen

### 3.1 Claude Code API — LXC 105:3001

**Basis-URL:** `http://10.1.1.105:3001`
**Protokoll:** HTTP/1.1 (kein TLS intern)
**Kompatibilität:** OpenAI Chat Completions API

**Request-Format:**

```http
POST /v1/chat/completions HTTP/1.1
Host: 10.1.1.105:3001
Content-Type: application/json
Authorization: Bearer dummy   (API-Key wird vom lokalen Server nicht geprüft)

{
  "model": "claude-sonnet-4-6",
  "messages": [
    {
      "role": "system",
      "content": "Du bist Egon der 2. ..."
    },
    {
      "role": "user",
      "content": "Recherchiere was sich bei Python 3.14 getan hat."
    }
  ],
  "max_tokens": 4096,
  "temperature": 0.7,
  "stream": false
}
```

**Response-Format (Success, HTTP 200):**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "claude-sonnet-4-6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Python 3.14 bringt vor allem ..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 312,
    "completion_tokens": 87,
    "total_tokens": 399
  }
}
```

**Response-Format (Error):**

```json
{
  "error": {
    "message": "Rate limit exceeded",
    "type": "rate_limit_error",
    "code": 429
  }
}
```

**Response-Parsing in `llm_client.py`:**

```python
def _parse_response(self, raw: dict) -> LLMResponse:
    """Parsed OpenAI-kompatible Response zu LLMResponse.

    Raises:
        LLMParseError: Wenn 'choices' fehlt oder leer ist.
        LLMParseError: Wenn 'usage' fehlt.
    """
    if not raw.get("choices"):
        raise LLMParseError(f"Unexpected response shape: {raw}")
    return LLMResponse(
        content=raw["choices"][0]["message"]["content"],
        model=raw.get("model", "unknown"),
        tokens_input=raw["usage"]["prompt_tokens"],
        tokens_output=raw["usage"]["completion_tokens"],
        finish_reason=raw["choices"][0]["finish_reason"],
    )
```

**Retry-Logik für LLM-Client:**

```python
# Exponential Backoff Parameter
RETRY_MAX_ATTEMPTS: int = 3
RETRY_BASE_DELAY: float = 1.0          # Sekunden
RETRY_MAX_DELAY: float = 30.0          # Sekunden
RETRY_JITTER: float = 0.5              # Random [0, 0.5] addiert
RETRY_ON_STATUS: tuple[int, ...] = (429, 500, 502, 503, 504)

# Delay-Formel:
# delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, JITTER), MAX_DELAY)
# attempt 0 → 1.0-1.5s
# attempt 1 → 2.0-2.5s
# attempt 2 → 4.0-4.5s

# Bei HTTP 429: Retry-After-Header auslesen falls vorhanden
# Bei HTTP 500+: sofort retry (Backoff)
# Bei HTTP 400, 401, 404: kein Retry → LLMClientError direkt
# Bei asyncio.TimeoutError (READ_TIMEOUT=120s): retry bis MAX_ATTEMPTS
```

**Timeout-Konfiguration:**

```python
import httpx

timeout = httpx.Timeout(
    connect=10.0,    # TCP-Verbindungsaufbau
    read=120.0,      # Warten auf Response-Body
    write=10.0,      # Request senden
    pool=5.0,        # Warten auf freien Connection aus Pool
)
limits = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=30.0,
)
```

---

### 3.2 Knowledge MCP API — LXC 107:8080

**Basis-URL:** `http://10.1.1.107:8080`
**Protokoll:** HTTP/1.1
**Datenbasis:** `mcp_knowledge_v5.db` (SQLite, per Migration erweitert)

> **Sicherheitshinweis (Heimnetz):** Da Knowledge-Inhalte in den System-Message-Slot des LLM injiziert werden, sollte LXC 107 Port 8080 per iptables auf Egon2-LXC (10.1.1.202) beschränkt werden: `iptables -A INPUT -p tcp --dport 8080 ! -s 10.1.1.202 -j DROP`. Verhindert dass andere LXCs im Subnetz den Knowledge-Store manipulieren können.

**Genutzte Endpoints:**

```
GET    /search?q={query}&limit={n}&domain={domain}   → Suchanfrage
GET    /entries/{id}                                  → Einzelner Eintrag
POST   /entries                                       → Neuer Eintrag
PUT    /entries/{id}                                  → Eintrag aktualisieren
DELETE /entries/{id}                                  → Eintrag löschen (is_active=0)
GET    /health                                        → Health-Check
```

**Search-Request:**

```http
GET /search?q=Python+asyncio&limit=5&domain=it HTTP/1.1
Host: 10.1.1.107:8080
```

**Search-Response (HTTP 200):**

```json
{
  "results": [
    {
      "id": "ke-abc123",
      "title": "asyncio Event-Loop Konzepte",
      "content": "...",
      "domain": "it",
      "knowledge_type": "general",
      "importance": 7,
      "source": "user/matrix",
      "references": [],
      "expires_at": null,
      "relevance_score": 0.87
    }
  ],
  "total": 1,
  "query": "Python asyncio"
}
```

**Create-Entry Request (POST /entries):**

```json
{
  "title": "Python 3.14 No-GIL Update",
  "content": "...",
  "domain": "it",
  "knowledge_type": "news",
  "importance": 5,
  "source": "egon2/news-report",
  "references": [],
  "expires_at": "2026-06-01T00:00:00Z"
}
```

**Response bei Fehler (HTTP 404):**

```json
{"detail": "Entry ke-xyz not found"}
```

**Client-Implementierung:**

```python
# egon2/knowledge/mcp_client.py
class MCPKnowledgeClient:

    BASE_URL: str = "http://10.1.1.107:8080"
    CONNECT_TIMEOUT: float = 5.0
    READ_TIMEOUT: float = 15.0
    # Connection Pool: max_connections=5 (im HLD spezifiziert)

    RETRY_MAX_ATTEMPTS: int = 2
    RETRY_BASE_DELAY: float = 0.5
    RETRY_ON_STATUS: tuple[int, ...] = (500, 502, 503)
    # Bei 404: kein Retry → KnowledgeEntryNotFoundError
    # Bei Timeout: 1 Retry, dann KnowledgeClientError

    async def search(
        self,
        query: str,
        limit: int = 5,
        domain: str | None = None,
    ) -> list[KnowledgeEntry]:
        """Sucht im Knowledge Store.

        Bei Verbindungsfehler: gibt leere Liste zurück (non-fatal).
        Loggt WARNING.
        """
        ...

    async def create_entry(
        self,
        title: str,
        content: str,
        domain: str,
        knowledge_type: str,
        importance: int,
        source: str,
        expires_at: datetime | None = None,
        references: list[dict] | None = None,
    ) -> str:
        """Erstellt neuen Knowledge-Eintrag.

        Returns:
            str: ID des erstellten Eintrags.

        Raises:
            KnowledgeClientError: Bei HTTP-Fehler oder Timeout.
        """
        ...

    async def update_entry(
        self,
        entry_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Aktualisiert einen bestehenden Eintrag.

        Raises:
            KnowledgeEntryNotFoundError: Entry-ID nicht gefunden.
            KnowledgeClientError: Bei HTTP-Fehler.
        """
        ...

    async def deactivate_expired(self) -> int:
        """Deaktiviert abgelaufene Einträge (expires_at < now).

        Aufgerufen vom Health-Check täglich.

        Returns:
            int: Anzahl deaktivierter Einträge.
        """
        ...

    async def health_check(self) -> bool:
        """Prüft Erreichbarkeit. Timeout: 5s.

        Returns:
            bool: True = erreichbar, False = nicht erreichbar.
        """
        ...
```

---

### 3.3 SearXNG API — LXC 125:80

**Basis-URL:** `http://10.1.1.204` (Port 80 via Nginx)
**Protokoll:** HTTP/1.1, kein Auth (internes Netz)

**Request-Format:**

```http
GET /search?q=Python+3.14+news&format=json&categories=general,news&language=de&time_range=week HTTP/1.1
Host: 10.1.1.204
```

**Query-Parameter:**

| Parameter | Wert | Bedeutung |
|---|---|---|
| `q` | URL-encoded String | Suchbegriff |
| `format` | `json` | JSON-Response |
| `categories` | `general`, `news`, `it` | Suchkategorien |
| `language` | `de`, `en` | Sprache |
| `time_range` | `day`, `week`, `month` | Zeitbereich |
| `pageno` | `1` | Ergebnisseite (Standard: 1) |

**Response (HTTP 200):**

```json
{
  "query": "Python 3.14 news",
  "number_of_results": 42,
  "results": [
    {
      "title": "Python 3.14 Released",
      "url": "https://python.org/downloads/...",
      "content": "Zusammenfassung des Artikels...",
      "publishedDate": "2026-04-30T12:00:00",
      "engine": "bing",
      "score": 0.95,
      "category": "general"
    }
  ],
  "answers": [],
  "corrections": [],
  "infoboxes": []
}
```

**Response-Parsing:**

```python
def _parse_searxng_results(self, raw: dict) -> list[SearchResult]:
    """Parsed SearXNG-Response.

    Raises:
        SearXNGParseError: Wenn 'results' fehlt im Response.

    Gibt leere Liste zurück wenn results = [].
    Filtert Ergebnisse ohne 'content' heraus.
    Limit: max. 10 Ergebnisse werden verarbeitet.
    """
    ...
```

**Fehlerbehandlung SearXNG:**

```python
RETRY_MAX_ATTEMPTS: int = 2
RETRY_BASE_DELAY: float = 2.0
CONNECT_TIMEOUT: float = 10.0
READ_TIMEOUT: float = 30.0
# Bei 0 Ergebnissen: SearXNGNoResultsError (non-fatal, Journalist berichtet "keine Nachrichten")
# Bei HTTP 5xx: retry, dann SearXNGClientError
# Mindest-Ergebnis: ≥ 1 Result für Health-Check (s. Abschnitt 12.1 HLD)
```

---

### 3.4 Matrix Homeserver API

**Homeserver:** `matrix.doehlercomputing.de`
**Protokoll:** HTTPS (matrix-nio managed)
**Account:** `@egon2:doehlercomputing.de`
**Library:** `matrix-nio` (async, Credentials via Vaultwarden)

**Empfangen — Event-Typen die verarbeitet werden:**

```python
# Relevante Event-Callbacks in matrix_bot.py

async def on_message(
    room: nio.MatrixRoom,
    event: nio.RoomMessageText,
) -> None:
    """Verarbeitet eingehende Textnachrichten.

    Filtert:
        - Eigene Nachrichten (event.sender == BOT_MXID): ignoriert
        - Nicht-whitelistete Räume: ignoriert (nur autorisierter 1:1-Raum)
        - event.body.startswith("!"): Matrix-System-Events: ignoriert

    Konvertiert zu IncomingMessage und pusht in MessageQueue.
    """
    ...

async def on_invite(
    room: nio.MatrixRoom,
    event: nio.InviteNameEvent,
) -> None:
    """Einladungsbehandlung: Auto-Join nur für autorisierte User-IDs.

    Nicht autorisierte Einladungen werden abgelehnt (room.leave()).
    """
    ...
```

**Senden:**

```python
async def send_message(
    room_id: str,
    content: str,
    reply_to_event_id: str | None = None,
) -> None:
    """Sendet Textnachricht in einen Raum.

    Formatierung: Markdown → Matrix HTML via markdown2
    Länge: > 4000 Zeichen → aufteilen in mehrere Messages (Chunk-Größe: 3900)

    Raises:
        MatrixSendError: Bei API-Fehler (loggt, nicht re-raised — best effort).
    """
    ...
```

**Konfiguration:**

```python
MATRIX_HOMESERVER: str = "https://matrix.doehlercomputing.de"
MATRIX_BOT_MXID: str = "@egon2:doehlercomputing.de"
MATRIX_PASSWORD: str   # aus Vaultwarden
MATRIX_STORE_PATH: str = "/opt/egon2/data/matrix_store/"   # E2E-Schlüsselmaterial
AUTHORIZED_ROOM_IDS: list[str]   # aus Config, !roomid:doehlercomputing.de
RECONNECT_DELAY: float = 5.0     # Sekunden zwischen Reconnect-Versuchen
RECONNECT_MAX_DELAY: float = 300.0   # Max 5 Minuten
```

---

### 3.5 Telegram Bot API

**API-URL:** `https://api.telegram.org/bot{token}/`
**Library:** `python-telegram-bot` v21 (async, webhooks oder long-polling)
**Modus:** Long-Polling (kein Webhook, keine externe URL nötig)

**Empfangen — Update-Typen:**

```python
# telegram_bot.py — Handler-Registrierung

from telegram.ext import Application, MessageHandler, CommandHandler, filters

# Nur Text-Messages von authorisierten User-IDs:
app.add_handler(
    MessageHandler(
        filters.TEXT & filters.User(user_ids=AUTHORIZED_TELEGRAM_IDS),
        handle_message,
    )
)

# Slash-Kommandos (werden auch als IncomingMessage mit /prefix weitergeleitet):
app.add_handler(CommandHandler("status", handle_command))
app.add_handler(CommandHandler("stats", handle_command))
app.add_handler(CommandHandler("suche", handle_command))
app.add_handler(CommandHandler("hilfe", handle_command))
```

**Senden:**

```python
async def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = "Markdown",
) -> None:
    """Sendet Textnachricht via Telegram API.

    Länge: > 4096 Zeichen → aufteilen (Telegram-Limit)
    Chunk-Größe: 4000 Zeichen (Puffer für Markdown-Tags)

    Bei MarkdownParseError: Retry mit parse_mode=None (Plain-Text).

    Raises:
        TelegramSendError: Bei API-Fehler nach 2 Retries (loggt, best effort).
    """
    ...
```

**Konfiguration:**

```python
TELEGRAM_BOT_TOKEN: str   # aus Vaultwarden
AUTHORIZED_TELEGRAM_IDS: list[int]   # Marco's User-ID (aus Vaultwarden/Config)
TELEGRAM_POLLING_INTERVAL: float = 0.0   # sofort (library-default)
TELEGRAM_ALLOWED_UPDATES: list[str] = ["message", "edited_message"]
```

---

## 4. Datenflüsse — Sequenzdiagramme

### 4.1 Flow 1: User-Anfrage (Task)

```
User (Matrix/Telegram)    Interface Layer      MessageQueue    CoreEngine/Dispatcher    LLM Client     DB (SQLite)    LXC107 KnowledgeStore
         │                      │                    │                │                    │               │                  │
         │── "Recherchiere Python 3.14" ──►           │                │                    │               │                  │
         │                      │                    │                │                    │               │                  │
         │                 parse Event               │                │                    │               │                  │
         │                 create IncomingMessage    │                │                    │               │                  │
         │                      │─── queue.put() ──►│                │                    │               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │─── get() ─────►│                    │               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         build_context():            │               │                  │
         │                      │                    │          ├─ system_prompt()         │               │                  │
         │                      │                    │          ├────────────────────────────────────────►│                  │
         │                      │                    │          │  SELECT last 20 from conversations       │                  │
         │                      │                    │          │◄────────────────────────────────────────│                  │
         │                      │                    │          ├─────────────────────────────────────────────────────────►│
         │                      │                    │          │  GET /search?q=Python+3.14&limit=5                        │
         │                      │                    │          │◄─────────────────────────────────────────────────────────│
         │                      │                    │                │                    │               │                  │
         │                      │                    │         classify_intent() LLM:     │               │                  │
         │                      │                    │                │────── POST /v1/chat/completions ──►│               │                  │
         │                      │                    │                │◄───── IntentType.TASK ─────────────│               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         task_manager.create()       │               │                  │
         │                      │                    │                │──────────────────────────────────►│                  │
         │                      │                    │                │  INSERT INTO tasks (status=pending)│                  │
         │                      │                    │                │◄─────────────────────────────────│                  │
         │                      │                    │                │                    │               │                  │
         │  ◄── "Verstanden. Researcher kümmert sich." ──────────────│                    │               │                  │
         │       (< 2s nach Eingang)                 │                │                    │               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         capabilities_match()         │               │                  │
         │                      │                    │          → agent: researcher        │               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         task → status=running       │               │                  │
         │                      │                    │                │──────────────────────────────────►│                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         run_specialist(researcher, brief):          │                  │
         │                      │                    │                │────── POST /v1/chat/completions ──►│               │                  │
         │                      │                    │                │       (researcher system-prompt    │               │                  │
         │                      │                    │                │        + brief als JSON)           │               │                  │
         │                      │                    │                │       [max 120s]                   │               │                  │
         │                      │                    │                │◄───── AgentResult ─────────────────│               │                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         record_assignment()  [Transaktion]:         │                  │
         │                      │                    │                │──────────────────────────────────►│                  │
         │                      │                    │                │  UPDATE tasks SET status=done      │                  │
         │                      │                    │                │  INSERT agent_assignments          │                  │
         │                      │                    │                │◄─────────────────────────────────│                  │
         │                      │                    │                │                    │               │                  │
         │                      │                    │         formuliere User-Antwort via LLM:           │                  │
         │                      │                    │                │────── POST /v1/chat/completions ──►│               │                  │
         │                      │                    │                │◄───── kompakte Zusammenfassung ────│               │                  │
         │                      │                    │                │                    │               │                  │
         │  ◄── "Python 3.14 bringt vor allem..." ──│                │                    │               │                  │
         │                      │                    │                │                    │               │                  │
```

**Timing-Ziele:**

| Schritt | Ziel |
|---|---|
| Bestätigungs-Nachricht | < 2s nach Eingang |
| Zwischen-Update (bei > 30s) | alle 30s |
| Gesamt (einfache Recherche) | < 60s |
| Gesamt (SSH-basierter Task) | < 180s |

---

### 4.2 Flow 2: Scheduler-Job (News-Report, täglich 07:30)

```
APScheduler          Agent Dispatcher       LLM (researcher)    SearXNG              LLM (journalist)   Matrix Bot    LXC107 Knowledge
     │                      │                    │                  │                       │                │               │
     │─ news_report_job() ─►│                    │                  │                       │                │               │
     │                      │                    │                  │                       │                │               │
     │                 scheduler_log:            │                  │                       │                │               │
     │                 INSERT (started_at)       │                  │                       │                │               │
     │                      │                    │                  │                       │                │               │
     │                 build researcher brief:   │                  │                       │                │               │
     │                 categories=["tech","ki","allgemein"]         │                       │                │               │
     │                      │─── run_specialist(researcher) ───────►│                      │                │               │
     │                      │                    │─── GET /search?q=KI+news&time_range=day►│               │               │
     │                      │                    │◄───────────── results (≥1) ─────────────│               │               │
     │                      │                    │─── GET /search?q=Tech+news&... ─────────►│              │               │
     │                      │                    │◄───────────── results ──────────────────│               │               │
     │                      │                    │─── GET /search?q=Allgemein+news&... ────►│              │               │
     │                      │                    │◄───────────── results ──────────────────│               │               │
     │                      │◄────── researcher_result (aggregierte Artikel) ──────────────│               │               │
     │                      │                    │                  │                       │                │               │
     │                 build journalist brief:   │                  │                       │                │               │
     │                      │──────────────────────────────────────────── run_specialist(journalist) ─────►│              │
     │                      │◄───────────────────────────────────────────── news_report_text ─────────────│               │
     │                      │                    │                  │                       │                │               │
     │                      │──────────────────────────────────────────────────────────────── send_message ►│              │
     │                      │◄──────────────────────────────────────────────────────────────── ok ──────────│              │
     │                      │                    │                  │                       │                │               │
     │                 build archivist brief:    │                  │                       │                │               │
     │                      │────────────────────────────────────────────────────────────────────── POST /entries ─────────►│
     │                      │                    │                  │                       │                │  channel=news  │
     │                      │                    │                  │                       │                │  expires=+30d  │
     │                      │◄───────────────────────────────────────────────────────────────────── entry_id ──────────────│
     │                      │                    │                  │                       │                │               │
     │                 scheduler_log:            │                  │                       │                │               │
     │                 UPDATE (finished_at, ok)  │                  │                       │                │               │
     │◄─ done ──────────────│                    │                  │                       │                │               │
```

**Fehlerfall News-Report:**

```
SearXNG nicht erreichbar:
    → researcher liefert leeres Ergebnis
    → journalist schreibt "Heute keine Nachrichten verfügbar."
    → Nachricht wird trotzdem gesendet
    → scheduler_log status = 'ok' (degraded, aber ausgeführt)

LLM nicht erreichbar (nach 3 Retries):
    → LLMClientError wird in news_report_job() gefangen
    → scheduler_log status = 'failed', output = Fehlermeldung
    → KEINE User-Benachrichtigung (03:00 Health-Check meldet)
    → APScheduler misfire_grace_time = 3600: kein Re-Trigger
```

---

### 4.3 Flow 3: Health-Check (täglich 03:00)

```
APScheduler    Inspector Agent    LLM Client    LXC105:3001    LXC107:8080    LXC126 SSH    SearXNG    SQLite    Matrix Bot
     │               │               │              │               │              │            │           │          │
     │─ health_check_job() ─────────►│              │               │              │            │           │          │
     │               │               │              │               │              │            │           │          │
     │          [PARALLEL HEALTH CHECKS]             │               │              │            │           │          │
     │               │──── GET /health ─────────────►│              │               │            │           │          │
     │               │──── GET /health ──────────────────────────────►             │            │           │          │
     │               │──── echo ok (SSH) ────────────────────────────────────────►│            │           │          │
     │               │──── GET /search?q=health ──────────────────────────────────────────────►│           │          │
     │               │──── SELECT 1 FROM tasks ──────────────────────────────────────────────────────────►│          │
     │               │◄─── results (alle parallel) ─────────────────────────────────────────────────────────────────│          │
     │               │               │              │               │              │            │           │          │
     │          [DATEN-AKTUALITÄTSPRÜFUNG]           │               │              │            │           │          │
     │               │──── deactivate_expired() ──────────────────────────────────────────────────────────►│          │
     │               │◄─── n_deactivated ──────────────────────────────────────────────────────────────────│          │
     │               │──── get_stale_running() ───────────────────────────────────────────────────────────►│          │
     │               │◄─── stale_tasks ────────────────────────────────────────────────────────────────────│          │
     │               │     [für jeden stale Task: UPDATE status=failed]                                     │          │
     │               │               │              │               │              │            │           │          │
     │          [SPEZIALIST-REVIEWS — sequenziell]  │               │              │            │           │          │
     │               │  für jeden aktiven Spezialisten:             │               │            │           │          │
     │               │──── run_specialist(test_task) ──────────────►│              │            │           │          │
     │               │◄─── test_result ────────────────────────────│              │            │           │          │
     │               │  evaluate_test_result()       │              │               │            │           │          │
     │               │  [falls failed: auto_repair() → retry]       │              │            │           │          │
     │               │               │              │               │              │            │           │          │
     │          INSERT health_checks (alle Ergebnisse)              │               │            │           │          │
     │               │──────────────────────────────────────────────────────────────────────────────────────────────►│          │
     │               │               │              │               │              │            │           │          │
     │          [BENACHRICHTIGUNG — nur bei degraded/critical]      │               │            │           │          │
     │               │──────────────────────────────────────────────────────────────────────────────────────────────────────────►│
     │               │               │              │               │              │            │           │          │
     │◄─ done ────────│              │              │               │              │            │           │          │
```

---

## 5. Error-Handling-Strategie

### 5.1 Exception-Hierarchie

```python
# egon2/exceptions.py

class Egon2Error(Exception):
    """Basis-Exception für alle Egon2-Fehler."""
    pass


# --- LLM ---
class LLMError(Egon2Error):
    pass

class LLMClientError(LLMError):
    """HTTP-Fehler, Connection-Error oder Parse-Fehler vom LLM-Backend.

    Attribute:
        status_code: int | None — HTTP-Status wenn verfügbar
        attempt: int — Retry-Versuch bei dem der Fehler aufgetreten ist
    """
    def __init__(self, message: str, status_code: int | None = None, attempt: int = 0):
        super().__init__(message)
        self.status_code = status_code
        self.attempt = attempt

class LLMRateLimitError(LLMClientError):
    """HTTP 429 — Rate limit.

    Attribute:
        retry_after: float | None — Sekunden aus Retry-After-Header
    """
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after

class LLMParseError(LLMError):
    """Response-Format unbekannt oder leer."""
    pass

class LLMTimeoutError(LLMError):
    """READ_TIMEOUT (120s) überschritten."""
    pass


# --- Datenbank ---
class DatabaseError(Egon2Error):
    """SQLite-Fehler (aiosqlite)."""
    pass

class TaskNotFoundError(DatabaseError):
    """Task-ID nicht in DB."""
    pass


# --- Agenten ---
class AgentError(Egon2Error):
    pass

class NoAgentFoundError(AgentError):
    """Kein aktiver Spezialist für die Capabilities gefunden."""
    pass

class AgentTimeoutError(AgentError):
    """Spezialist-LLM-Call hat Timeout überschritten."""
    pass


# --- SSH ---
class SSHError(Egon2Error):
    pass

class SSHConnectionError(SSHError):
    """Host nicht erreichbar oder Auth fehlgeschlagen."""
    pass

class SSHTimeoutError(SSHError):
    """COMMAND_TIMEOUT (120s) überschritten."""
    pass


# --- Shell ---
class ShellError(Egon2Error):
    pass

class CommandNotAllowedError(ShellError):
    """Kommando nicht in Whitelist."""
    pass

class ConfirmationRequiredError(ShellError):
    """Bestätigung für destruktives Kommando fehlt oder abgelaufen."""
    pass


# --- Knowledge ---
class KnowledgeError(Egon2Error):
    pass

class KnowledgeClientError(KnowledgeError):
    """HTTP-Fehler oder Timeout bei LXC 107."""
    pass

class KnowledgeEntryNotFoundError(KnowledgeError):
    """Entry-ID nicht im Knowledge Store."""
    pass


# --- Interface ---
class InterfaceError(Egon2Error):
    pass

class MatrixSendError(InterfaceError):
    pass

class TelegramSendError(InterfaceError):
    pass


# --- SearXNG ---
class SearXNGError(Egon2Error):
    pass

class SearXNGClientError(SearXNGError):
    pass

class SearXNGNoResultsError(SearXNGError):
    pass
```

---

### 5.2 Fehler-Matrix: Was wird wo gefangen

| Fehler | Geworfen in | Gefangen in | Verhalten |
|---|---|---|---|
| `LLMClientError` | `llm_client.py` | `agent_dispatcher.py` | Task → 'failed', User-Antwort mit Fehlergrund |
| `LLMRateLimitError` | `llm_client.py` | `llm_client.py` (retry) | Warte `retry_after` Sekunden, dann retry |
| `LLMTimeoutError` | `llm_client.py` | `agent_dispatcher.py` | Task → 'failed', "Timeout" als Grund |
| `NoAgentFoundError` | `agent_dispatcher.py` | `agent_dispatcher.py` | Neuen Agenten anlegen, dann wiederholen |
| `AgentTimeoutError` | `agent_dispatcher.py` | `agent_dispatcher.py` | Task → 'failed', User informieren |
| `SSHConnectionError` | `ssh_executor.py` | `agents/it_admin.py`, `developer.py` | AgentResult.status = 'failed', Fehler im Ergebnis |
| `SSHTimeoutError` | `ssh_executor.py` | jeweiliger Agent | AgentResult.status = 'failed' |
| `CommandNotAllowedError` | `shell_executor.py` | `agents/*.py` | Sofort mit Fehlermeldung zurück |
| `KnowledgeClientError` | `mcp_client.py` | `context_manager.py` | Leere Knowledge-Liste (non-fatal), WARNING log |
| `KnowledgeClientError` | `mcp_client.py` | `agents/archivist.py` | AgentResult.status = 'failed', Egon meldet |
| `MatrixSendError` | `matrix_bot.py` | `matrix_bot.py` | ERROR log, best effort (kein Re-raise) |
| `TelegramSendError` | `telegram_bot.py` | `telegram_bot.py` | ERROR log, best effort |
| `DatabaseError` | `database.py` | `task_manager.py`, `context_manager.py` | Je nach Kontext: fatal (startup) oder ERROR log |
| `asyncio.TimeoutError` | message_queue | `matrix_bot.py`, `telegram_bot.py` | WARNING log, Nachricht verworfen |
| `SearXNGNoResultsError` | `mcp_client.py` | `agents/researcher.py` | Researcher gibt "keine Ergebnisse" zurück |

---

### 5.3 Retry-Implementierung (Exponential Backoff)

> **Spec-Finding F4 (Heimnetz-Pragmatik):** Für die drei externen HTTP-Clients
> (LLM, Knowledge-MCP, SearXNG) gilt: **kein Circuit Breaker, kein Bulkhead.**
> Einfaches Retry mit fixem Backoff `[1s, 2s, 4s]`, max. 3 Versuche, ist ausreichend.
> Retried wird **nur bei transienten Netzwerkfehlern** (`httpx.ConnectError`,
> `httpx.TimeoutException`) — nicht bei HTTP 4xx (echte Fehler). HTTP 5xx wird
> retried, aber das Wrapping in Egon2-eigene Exceptions (`LLMTimeoutError`,
> `KnowledgeClientError`, `SearXNGClientError`) erfolgt **erst nach** dem letzten
> erschöpften Versuch — sonst feuert das `retry_on=(...,)`-Tuple unten nicht
> auf die ursprünglichen httpx-Exceptions.
>
> Die untenstehende `retry_with_backoff`-Implementierung bleibt erhalten (sie ist
> die generischere Variante). Für die drei Clients darf alternativ die schlankere
> `simple_retry.retry()` aus LLD-Core §6.0 verwendet werden — beide sind erlaubt.
> Kanonische Anpassung der `retry_on`-Tupel:
> - `LLM_RETRY_CONFIG.retry_on = (httpx.ConnectError, httpx.TimeoutException, LLMRateLimitError)` — die Status-5xx-Behandlung erfolgt im `LLMClient.complete()` durch erneutes Werfen einer transienten Exception.
> - `KNOWLEDGE_RETRY_CONFIG.retry_on = (httpx.ConnectError, httpx.TimeoutException)`
> - `SEARXNG_RETRY_CONFIG.retry_on = (httpx.ConnectError, httpx.TimeoutException)`
>
> **Begründung:** Egon2-Wrapper-Exceptions wie `LLMTimeoutError` werden in der alten
> Variante VOR dem Retry geworfen — das Retry kann sie zwar fangen, aber das
> Mapping-Layer ist doppelt. Mit der neuen Variante propagieren httpx-Native bis
> zum Retry-Decorator; erst nach Erschöpfung der Versuche werden sie in Egon2-
> Exceptions umgewandelt (in `LLMClient.complete()` als `try/except` um den
> Retry-Aufruf herum).

```python
# egon2/utils/retry.py
import asyncio
import random
import logging
from collections.abc import Callable, Awaitable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_attempts: int,
    base_delay: float,
    max_delay: float,
    jitter: float,
    retry_on: tuple[type[Exception], ...],
    label: str = "operation",
) -> T:
    """Führt `func` mit Exponential Backoff aus.

    Args:
        func: Async-Funktion ohne Argumente (via functools.partial oder lambda).
        max_attempts: Maximale Versuche (1 = kein Retry).
        base_delay: Basis-Wartezeit in Sekunden.
        max_delay: Maximale Wartezeit in Sekunden.
        jitter: Maximale zufällige Zusatz-Wartezeit.
        retry_on: Exception-Typen die einen Retry auslösen.
        label: Beschreibung für Logging.

    Returns:
        T: Ergebnis von func().

    Raises:
        Exception: Letzte aufgetretene Exception nach Erschöpfung aller Versuche.
    """
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except retry_on as e:
            last_exception = e
            if attempt == max_attempts - 1:
                break

            delay = min(base_delay * (2 ** attempt) + random.uniform(0, jitter), max_delay)

            # Sonderfall: LLMRateLimitError mit Retry-After
            if hasattr(e, "retry_after") and e.retry_after is not None:
                delay = max(delay, e.retry_after)

            logger.warning(
                f"{label}: attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

    raise last_exception


# --- Vorkonfigurierte Retry-Profile ---

import httpx

# F4: retry_on enthält httpx-native Exceptions, NICHT die Egon2-Wrapper.
# Wrapper werden erst nach erschöpften Retries im Client-Code geworfen.
# Kein Retry bei HTTP 4xx (echte Fehler — der Client wirft dann kein
# httpx.HTTPStatusError sondern direkt eine semantische Exception).

LLM_RETRY_CONFIG = dict(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    jitter=0.5,
    retry_on=(httpx.ConnectError, httpx.TimeoutException, LLMRateLimitError),
)

KNOWLEDGE_RETRY_CONFIG = dict(
    max_attempts=2,
    base_delay=0.5,
    max_delay=10.0,
    jitter=0.2,
    retry_on=(httpx.ConnectError, httpx.TimeoutException),
)

SEARXNG_RETRY_CONFIG = dict(
    max_attempts=2,
    base_delay=2.0,
    max_delay=15.0,
    jitter=1.0,
    retry_on=(httpx.ConnectError, httpx.TimeoutException),
)

SSH_RETRY_CONFIG = dict(
    max_attempts=2,
    base_delay=3.0,
    max_delay=10.0,
    jitter=0.5,
    retry_on=(SSHConnectionError,),
    # SSHTimeoutError wird NICHT retried — Timeout ist Fehler, kein Transient
)
```

---

### 5.4 Timeout-Tabelle (alle Werte)

| Komponente | Timeout-Typ | Wert | Verhalten bei Überschreitung |
|---|---|---|---|
| LLM-Client connect | TCP-Connect | 10s | `LLMClientError` → Retry |
| LLM-Client read | Response-Body | 120s | `LLMTimeoutError` → Retry |
| LLM-Client pool | Free-Connection-Wait | 5s | `LLMClientError` (kein Retry) |
| SSH-Executor command | Kommando-Ausführung | 120s | `SSHTimeoutError`, Task → 'failed' |
| Shell-Executor command | Lokales Kommando | 30s | `ShellTimeoutError` |
| Knowledge-Client connect | TCP-Connect | 5s | non-fatal, leere Liste |
| Knowledge-Client read | Response-Body | 15s | non-fatal, leere Liste |
| SearXNG connect | TCP-Connect | 10s | `SearXNGClientError` → Retry |
| SearXNG read | Response-Body | 30s | `SearXNGClientError` → Retry |
| MessageQueue put | Einreihen | 5s | WARNING, Nachricht verworfen |
| Matrix reconnect initial | Reconnect-Delay | 5s | exponentiell bis 300s |
| APScheduler misfire_grace | Verpasster Job | 3600s | 1× Nachhol-Run |
| Werkstatt-Cleanup | Nach Task-Abschluss | 24h | `ssh_executor.cleanup_werkstatt()` |

---

### 5.5 Logging-Konvention & Correlation-ID (F5)

> **Spec-Finding F5 — pragmatisch für Einzelnutzer:** Kein Distributed Tracing
> (kein Jaeger/Tempo, kein W3C-Trace-Context). Statt dessen wird die
> `request_id` (8-Hex-Chars) der `IncomingMessage` (LLD-Core §1.2) durch
> alle Schichten als Log-Präfix mitgeführt. Reicht für „warum ist Task X
> fehlgeschlagen?"-Debugging im Heimnetz.

**Mechanismus:**

- `structlog.contextvars.bind_contextvars(req=msg.request_id)` wird im
  `MessageConsumer._handle_with_semaphore` (LLD-Core §1.6) für die Dauer
  einer Nachricht-Verarbeitung gesetzt. Alle `log.info(...)`-Aufrufe in
  Dispatcher, LLM-Client, SSH-Executor, DB-Layer etc. tragen automatisch das
  Feld `req=<id>`.
- Im strukturierten JSON-Output: `{"event":"llm.request","req":"a1b2c3d4",...}`.
- Im Plain-Text-Format (Debug-Mode): `[req=a1b2c3d4] llm.request model=claude-sonnet-4-6`.
- Bei Sub-Tasks (LLD-Core §4.10): die `request_id` wird vom Parent-Task übernommen
  und beim Spawn der Sub-Task in deren `tasks.request_id`-Spalte geschrieben.
  Damit gehört die gesamte Sub-Task-Historie zum gleichen `req=…`-Faden.
- Scheduler-Jobs (News-Report, Health-Check etc.) erzeugen ihre Pseudo-`IncomingMessage`
  mit Channel `SCHEDULER` und einer eigenen `request_id` → Log-Faden pro Job-Lauf.

**Was NICHT gemacht wird:**

- Keine externen Trace-Backends, keine OpenTelemetry-Instrumentierung.
- Keine `traceparent`-HTTP-Header an LXC 105 / 107 / 125 (die Backends könnten sie eh nicht auswerten).
- Kein Sampling — bei < 100 Tasks/Tag im Heimnetz loggen wir alles.

---

## 6. Startup- und Shutdown-Sequenz

### 6.1 Startup-Sequenz

```
main.py → uvicorn starts → FastAPI lifespan() begins
```

> **HOCH (Audit-Finding 4.1 + Spec-Finding F2):** Kanonische 9-stufige Startup-Reihenfolge.
> Alle LLDs müssen übereinstimmen. Interfaces dürfen erst Nachrichten annehmen wenn Queue +
> Dispatcher + Consumer bereit sind — sonst landen Nachrichten in einer nicht existenten Queue.
>
> **F2 — Scheduler MUSS NACH Matrix und Telegram starten:** Bei Restart nach längerer Downtime
> feuern dank `misfire_grace_time=3600` Nachhol-Runs sofort beim Scheduler-Start. Wenn der
> Scheduler vor den Bots startet (alte Reihenfolge: Stage 6), versucht z. B. der News-Report-Job
> Matrix-Nachrichten zu senden, obwohl der Matrix-Bot noch nicht initialisiert ist —
> `MatrixSendError` und Job läuft auf failed. Korrektur: Scheduler in **neuer Stage 9** —
> nach Matrix (7) und Telegram (8). Damit ist garantiert, dass Nachhol-Runs einen funktionsfähigen
> Output-Kanal vorfinden.

**Kanonische 9-stufige Reihenfolge:**

```python
# Reihenfolge in lifespan() — async with lifespan(app):

# STUFE 1: DB init + WAL pragmas + Migrationen
# ─────────────────────────────────────────────
# 1.1  config.py: Alle Umgebungsvariablen und Secrets laden
#      - LLM_API_URL, MATRIX_PASSWORD, TELEGRAM_TOKEN, etc.
#      - Fehlende Pflicht-Config → SystemExit(1) mit Fehlermeldung
#      - Timeout: sofort (kein Netzwerk)
# 1.2  Logging konfigurieren (Structured JSON via structlog, Level: INFO | DEBUG)
# 1.3  aiosqlite: Verbindung zu /opt/egon2/data/egon2.db öffnen
#      PRAGMA journal_mode=WAL
#      PRAGMA foreign_keys=ON
#      PRAGMA synchronous=NORMAL
#      Bei Fehler → SystemExit(1)
# 1.4  database.py: Schema-Migrations ausführen
#      - Prüfe schema_migrations-Tabelle
#      - Führe ausstehende Migrations aus
#      - agents/registry.py: Alle 10 Spezialisten INSERT OR IGNORE
#      - Bei Fehler → SystemExit(1)

# STUFE 2: recover_orphaned() → running→pending
# ──────────────────────────────────────────────
# 2.1  TaskManager: recover_orphaned()
#      UPDATE tasks SET status='pending' WHERE status='running'
#      Alle running-Tasks aus vorherigem Run werden als pending wiederhergestellt
#      (nicht 'failed' — Core-LLD § 3.5 definiert das korrekt)
#      log.info("startup.recovered", count=n)

# STUFE 3: Knowledge Store Client init (soft-fail ok)
# ─────────────────────────────────────────────────────
# 3.1  MCPKnowledgeClient: httpx.AsyncClient() init (Pool max_connections=5)
#      Health-Check: GET /health, Timeout: 5s
#      Bei Fehler → WARNING (non-fatal, Egon startet ohne Knowledge)

# STUFE 4: LLM Client init + Verbindungstest
# ───────────────────────────────────────────
# 4.1  LLMClient: httpx.AsyncClient() init
#      Health-Check: POST /v1/chat/completions (Mini-Prompt "ping"), Timeout: 15s
#      Bei Fehler → WARNING (Egon startet degraded, kein SystemExit)

# STUFE 5: Externe HTTP-Clients + Persistenz-Wrapper
# ────────────────────────────────────────────────────
# (umbenannt von alt-5; Inhalt unverändert — siehe Stufen 3+4 für die einzelnen
#  Clients; diese Stufe ist nur ein "alle Clients sind initialisiert"-Marker.)

# STUFE 6: Message Queue + AgentDispatcher + Consumer
# ─────────────────────────────────────────────────────
# 6.1  MessageQueue init (asyncio.Queue, maxsize=100; siehe LLD-Core §1.3)
# 6.2  TaskManager init (DB-Referenz)
# 6.3  ContextManager init
# 6.4  AgentDispatcher init (kanonischer Konstruktor — LLD-Core §4.4)
# 6.5  MessageConsumer init + start() — siehe LLD-Core §1.6
#      Konsument läuft als asyncio.Task(name="message-consumer") mit
#      Semaphore(MAX_CONCURRENT_LLM_CALLS=3) für gleichzeitige LLM-Calls (F1).
#      Die Queue ist ab hier bereit, Nachrichten anzunehmen — die Bots
#      (Stufe 7+8) können also sicher pushen.

# STUFE 7: Matrix Bot init (sync → dann callbacks)
# ──────────────────────────────────────────────────
# 7.1  matrix-nio: Login mit gespeichertem Session-Token oder Passwort
#      Initial-Sync (full_state=True), Timeout: 10s
#      Callbacks registrieren (on_message, on_invite) NACH Initial-Sync (K2-Fix)
#      Sync-Loop als asyncio.Task starten
#      Bei Auth-Fehler → ERROR + WARNING (Egon startet ohne Matrix)
#      Adapter setzt request_id auf jeder eingehenden IncomingMessage (F5,
#      Default-Factory in IncomingMessage erledigt das automatisch).

# STUFE 8: Telegram Bot init
# ───────────────────────────
# 8.1  python-telegram-bot: Application.initialize() + start() + updater.start_polling()
#      stop_signals=None (uvicorn behält Signal-Handler)
#      Bei Auth-Fehler → ERROR + WARNING (Egon startet ohne Telegram)
#      Falls BEIDE Kanäle fehlschlagen → SystemExit(1) — kein nutzbarer Start
#      Adapter setzt request_id (s. Stage 7-Hinweis).

# STUFE 9: Scheduler init + Jobs registrieren + start  (F2 — NEU, ehem. Stage 6)
# ───────────────────────────────────────────────────────────────────────────────
# WARUM nach den Bots? Bei Restart nach Downtime feuern Nachhol-Runs (misfire_grace_time
# = 3600) sofort beim Scheduler-Start. Würde der Scheduler vor den Bots starten, würde
# z. B. der News-Report seinen Output an einen nicht existierenden Matrix-Adapter
# senden → MatrixSendError, Job verloren. Reihenfolge "erst Output-Kanäle, dann Trigger"
# verhindert das.
#
# 9.1  AsyncIOScheduler(timezone="Europe/Berlin")  — APScheduler 3.x (NICHT 4.x, s. Warnung)
#      JobStore: SQLAlchemyJobStore(url="sqlite:////opt/egon2/data/scheduler.db")
#      ExecutorPool: AsyncIOExecutor
# 9.2  Kanonisch 5 Jobs (HLD §7.4), replace_existing=True:
#      - news_report_job:     CronTrigger(hour=7, minute=30)
#      - health_check_job:    CronTrigger(hour=3, minute=0)
#      - weekly_audit_job:    CronTrigger(day_of_week="mon", hour=4, minute=0)
#      - weekly_summary_job:  CronTrigger(day_of_week="sat", hour=20, minute=0)
#      - backup_job:          CronTrigger(hour=2, minute=0)
#      BookStack/GitHub-Sync sind KEIN eigenständiger Scheduler-Job; Sync läuft als Teil
#      von weekly_summary_job bzw. wird vom archivist-Spezialisten getriggert (HLD §8.4).
#      misfire_grace_time=3600 (global, für alle Jobs)
# 9.3  scheduler.start()

# ─── lifespan yield ───
# App ist bereit, uvicorn akzeptiert Requests

# ONBOARDING-CHECK (lazy, nicht im Startup):
# Beim ersten eingehenden User-Event prüfen ob conversations leer (role='assistant' COUNT=0)
# Falls ja: Onboarding-Nachricht senden. Flag im AppState: state.onboarding_pending = True
```

> **HOCH — APScheduler-Versionswarnung:**
> APScheduler 3.x verwenden (NICHT 4.x — 4.x ist noch Beta und hat eine andere API).
> `AsyncIOScheduler` aus `apscheduler.schedulers.asyncio` läuft im FastAPI-Event-Loop.
> Scheduler-Listener (`_on_event`) darf KEINE `asyncio.create_task()` aufrufen —
> APScheduler-Listener werden synchron im Loop-Thread aufgerufen. Korrekte Variante:
> ```python
> # FALSCH — kann Task leaken oder bei Shutdown auf geschlossene DB zugreifen:
> def _on_event(self, event): asyncio.create_task(self._db.scheduler_log_insert(...))
>
> # RICHTIG — loop-sicher:
> def _on_event(self, event):
>     loop = asyncio.get_event_loop()
>     loop.call_soon_threadsafe(
>         lambda: asyncio.ensure_future(self._db.scheduler_log_insert(...))
>     )
> # Oder: Listener stellt Event in eine asyncio.Queue, ein dedizierter Background-Task
> # verarbeitet sie geordnet (bevorzugte Variante für Shutdown-Safety).
> ```

**Startup-Fehlerstrategie:**

| Stufe | Fehler | Verhalten |
|---|---|---|
| Stufe 1 (Config/DB) | Pflicht-Variable fehlt / DB nicht öffenbar | `SystemExit(1)` — kein Start |
| Stufe 2 (Recovery) | recover_orphaned() schlägt fehl | `SystemExit(1)` — DB-Fehler ist fatal |
| Stufe 3 (Knowledge) | LXC 107 nicht erreichbar | WARNING, nicht-fatal |
| Stufe 4 (LLM) | LLM nicht erreichbar | WARNING, Egon startet degraded |
| Stufe 6 (Queue/Consumer) | asyncio.Queue/Semaphore-Init schlägt fehl | `SystemExit(1)` — Core ohne Consumer ist sinnlos |
| Stufe 7 (Matrix) | Auth-Fehler | ERROR, Egon startet ohne Matrix |
| Stufe 8 (Telegram) | Auth-Fehler | ERROR, Egon startet ohne Telegram |
| Stufe 7+8 (beide) | Beide Kanäle fehlschlagen | `SystemExit(1)` — kein nutzbarer Start |
| Stufe 9 (Scheduler) | JobStore nicht öffenbar / Cron-Parse-Fehler | ERROR, Egon startet ohne Scheduler (nur Live-Chat funktioniert) |

---

### 6.2 Shutdown-Sequenz

```
SIGTERM → uvicorn → FastAPI lifespan() exits yield → cleanup begins
```

> **HOCH (Audit-Finding 4.2 + Spec-Finding F3):** Kanonische 7-stufige Shutdown-Reihenfolge.
> Scheduler VOR den Bots stoppen — andernfalls kann ein laufender Job (z.B. News-Report)
> versuchen Matrix-Nachrichten zu senden, obwohl Matrix bereits gestoppt ist.
> Consumer + alle laufenden handler-Tasks NACH den Bots stoppen — sonst kann eine
> Antwort an einen bereits gestoppten Bot gesendet werden.
> SSHExecutor.aclose() ist Pflicht (Audit-Finding 4.4).
>
> **F3 — Reihenfolge ist umgekehrt zu Startup, mit Queue-Drain dazwischen:**
> Startup ging Input→Output (Queue→Bots→Scheduler), Shutdown geht Trigger→Input→Drain→Output.
> Der explizite Queue-Drain (neue Stage 4) sorgt dafür, dass eingereihte Nachrichten —
> auch die, die kurz vor Bot-Stop noch durchrutschten — noch verarbeitet werden, bevor
> der Consumer abgebaut wird.

**Kanonische 7-stufige Reihenfolge (Graceful Shutdown, max. 30s gesamt):**

```python
# Nach dem yield in lifespan():

# STUFE 1: Scheduler shutdown (keine neuen Jobs)
# ────────────────────────────────────────────────
# 1.1  scheduler.shutdown(wait=True)
#      Wartet auf alle laufenden Jobs (misfire_grace_time greift nicht mehr).
#      APScheduler 3.x: wait=True blockiert bis Jobs fertig oder timeout.
#      Hard-Limit: scheduler.shutdown(wait=False) nach 30s als Fallback.
#      Damit ist garantiert: keine NEUEN Scheduler-Messages mehr in der Queue.

# STUFE 2: Matrix Bot stop (kein neuer Input)
# ─────────────────────────────────────────────
# 2.1  matrix_sync_task.cancel()    — beendet sync_forever-Loop
# 2.2  await asyncio.gather(matrix_sync_task, return_exceptions=True)
#      Damit nimmt der Adapter keine NEUEN IncomingMessages mehr an.
#      Hinweis: Ausgehender Send-Pfad bleibt noch offen — wir brauchen ihn
#      bis Stufe 5 (Consumer-Drain), damit gerade laufende Tasks ihre Antwort
#      noch ausliefern können. Der Bot wird in Stufe 6 final entladen.

# STUFE 3: Telegram Bot stop (kein neuer Input)
# ──────────────────────────────────────────────
# 3.1  await application.updater.stop()   — beendet long-polling
#      stop_signals=None ist gesetzt; updater.stop() ist idempotent.
#      Send-API von PTB bleibt für ausgehende Antworten verfügbar bis Stufe 6.

# STUFE 4: MessageQueue drain (max 30s)  ← F3 NEU
# ─────────────────────────────────────────────────
# 4.1  Bereits eingereihte Nachrichten verarbeiten oder Timeout abwarten.
#      try:
#          await asyncio.wait_for(message_queue.join(), timeout=30.0)
#      except asyncio.TimeoutError:
#          log.warning("shutdown.queue_drain_timeout", qsize=message_queue.qsize())
#      Damit gehen keine Nachrichten verloren, die noch in der Queue lagen,
#      als die Bots gestoppt wurden.

# STUFE 5: Consumer stoppen + alle laufenden handler-Tasks awaiten
# ──────────────────────────────────────────────────────────────────
# 5.1  await consumer.stop(drain_timeout=30.0)   — siehe LLD-Core §1.6
#      Der Consumer-Loop wird gecancelt, dann werden ALLE noch laufenden
#      handle_message-Tasks via asyncio.gather(*_running_tasks) awaited.
#      Bei laufenden LLM-Calls (bis 120s): nach drain_timeout=30s harter Cancel.
#      Antworten dieser Tasks gehen noch über die NOCH offenen Bot-Send-APIs raus
#      (Bots erst in Stage 6 final geschlossen).
#      Tasks, die durch Cancel sterben, werden beim nächsten Startup via
#      recover_orphaned() auf 'pending' gesetzt (LLD-Core §3.5).

# STUFE 6: SSHExecutor + httpx-Clients + Bots final schließen
# ─────────────────────────────────────────────────────────────
# 6.1  await application.stop()         — Telegram: PTB final stop
# 6.2  await application.shutdown()     — Telegram: PTB final shutdown
# 6.3  await matrix_client.close()      — Matrix-nio HTTP-Client schließen
# 6.4  await state.ssh.aclose()         — schließt asyncssh connection pool
# 6.5  await state.llm.aclose()         — httpx AsyncClient (LLM)
# 6.6  await state.knowledge.aclose()   — httpx AsyncClient (Knowledge)
# 6.7  await state.searxng.aclose()     — httpx AsyncClient (SearXNG)
# 6.8  [PARALLEL für 6.4-6.7] — keine Reihenfolge-Abhängigkeit
#      6.1-6.3 müssen vor 6.4-6.7 fertig sein (Bots brauchen ggf. ihren Pool).

# STUFE 7: DB — WAL checkpoint + close
# ──────────────────────────────────────
# 7.1  PRAGMA wal_checkpoint(TRUNCATE)   — WAL aufräumen
# 7.2  await db.aclose()                 — aiosqlite connection schließen
# 7.3  log.info("egon2.shutdown.complete")
```

**Zustand nach unerwarteten Absturz (kein Graceful Shutdown):**

- Tasks mit `status='running'` werden beim nächsten Startup in Stufe 2 via `recover_orphaned()` auf `'pending'` gesetzt (nicht 'failed' — Core-LLD § 3.5)
- APScheduler SQLite-JobStore: Jobs bleiben erhalten, `misfire_grace_time=3600` behandelt Nachhol-Runs
- Matrix-Session-Token bleibt gültig (matrix-nio persistiert in `/opt/egon2/data/matrix_store/`)
- SQLite WAL-Modus: kein Datenverlust bei Absturz (WAL wird beim nächsten Open recovered)

---

## Anhang: Custom Exceptions — Vollständige Referenz

```
Egon2Error
├── LLMError
│   ├── LLMClientError(status_code, attempt)
│   │   └── LLMRateLimitError(retry_after)
│   ├── LLMParseError
│   └── LLMTimeoutError
├── DatabaseError
│   └── TaskNotFoundError
├── AgentError
│   ├── NoAgentFoundError
│   └── AgentTimeoutError
├── SSHError
│   ├── SSHConnectionError
│   └── SSHTimeoutError
├── ShellError
│   ├── CommandNotAllowedError
│   └── ConfirmationRequiredError
├── KnowledgeError
│   ├── KnowledgeClientError
│   └── KnowledgeEntryNotFoundError
├── InterfaceError
│   ├── MatrixSendError
│   └── TelegramSendError
└── SearXNGError
    ├── SearXNGClientError
    └── SearXNGNoResultsError
```
