# Architektur-Review — Egon2 LLD

**Reviewer:** Claude (Master Software Architect)
**Stand:** 2026-05-02
**Geprüfte Dokumente:**
- `/opt/Projekte/Egon2/docs/HLD-Egon2.md` (v1.5, Referenz)
- `/opt/Projekte/Egon2/docs/LLD-Architektur.md` (v1.0)
- `/opt/Projekte/Egon2/docs/LLD-Core.md` (v1.0)
- `/opt/Projekte/Egon2/docs/LLD-Interfaces.md` (v1.0)

**Severity-Skala:** KRITISCH (blockiert Implementierung / Datenverlust / Deadlock-Risiko) · HOCH (funktionaler Bug zu erwarten) · MITTEL (Wartbarkeit, Robustheit) · NIEDRIG (Konsistenz, Doku)

---

## Executive Summary

Die LLD-Dokumente sind insgesamt von **hoher Qualität** und zeigen ein durchdachtes, async-natives Design. Stark sind: vollständige Exception-Hierarchie, klare DI-Struktur in `AppState`, expliziter Lifespan, sauberer SSH/Shell-Executor mit Output-Truncation, Whitelist via Binary-Name (nicht Pfad).

Es gibt jedoch **drei Inkonsistenzen zwischen den drei LLD-Dokumenten**, die vor Implementierungsbeginn aufgelöst werden müssen — sie führen sonst zu Code, der sich nicht zusammenfügt. Außerdem mehrere konkrete async-/Shutdown-Bugs.

**Top-Findings:**
1. KRITISCH — Drei verschiedene Datenmodelle für eingehende Nachrichten (`IncomingMessage` vs. `Message`) zwischen Architektur-LLD, Core-LLD und Interfaces-LLD.
2. KRITISCH — Queue-Maxsize-Inkonsistenz (100 vs. 256) zwischen Core-LLD und Interfaces-LLD.
3. KRITISCH — Scheduler-Job-Inventar weicht zwischen HLD (7 Jobs inkl. BookStack/GitHub-Sync) und Scheduler-LLD (5 Jobs) ab.
4. HOCH — `asyncio.create_task` aus synchronem APScheduler-Listener (`_on_event`) ist unsicher — kann ohne laufenden Loop fehlschlagen oder Tasks „leaken".
5. HOCH — `SSHExecutor.aclose()` fehlt im Shutdown-Inventar (Hinweis im Querverweis-Kapitel, aber nicht in der Stages-Tabelle).
6. HOCH — `recover_orphaned()` aus Core-LLD fehlt komplett in der Interfaces-LLD-Startup-Sequenz.

---

## 1. Konsistenz HLD ↔ LLD

### 1.1 [KRITISCH] Drei divergierende Message-Datenmodelle

LLD-Architektur §2.1 definiert `IncomingMessage` (Pydantic) mit Feldern `id, channel, user_id, room_id, content, timestamp, raw`.
LLD-Core §1.2 definiert `Message` (frozen dataclass) mit `channel, user_id, text, timestamp, message_id, metadata`.
LLD-Interfaces §2.4/3.3 nutzt eine dritte Variante `IncomingMessage(channel, chat_id, user_id, text, ts_ms)` — `chat_id` statt `room_id`, `text` statt `content`, `ts_ms` (int) statt `timestamp` (datetime).

**Auswirkung:** Beim Zusammensetzen lässt sich kein Modul gegen das andere bauen — Felder fehlen oder heißen anders.

**Vorschlag:** Eine kanonische Definition in `egon2/core/message_queue.py` (frozen dataclass mit `slots=True`, da dataclass + StrEnum hier passender als Pydantic ist und Allokationen reduziert):

```python
@dataclass(slots=True, frozen=True)
class IncomingMessage:
    channel: Channel
    chat_id: str           # Matrix room_id ODER Telegram chat_id (immer str)
    user_id: str
    text: str
    ts_ms: int             # ms seit epoch (UTC), kompatibel mit Matrix server_timestamp
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)
```

Pydantic-Variante in LLD-Architektur löschen, Architektur-LLD auf gemeinsamen Typ verweisen lassen.

### 1.2 [KRITISCH] Queue maxsize: 100 vs. 256

- HLD §7.1, LLD-Architektur §2.2 und LLD-Core §1.3 (`MAX_SIZE = 100`) sagen **100**.
- LLD-Interfaces §1.3 Stage 4: `MessageQueue(maxsize=256)`.

**Auswirkung:** Backpressure-Verhalten weicht ab. Soft-Limit bei 80% in Core-LLD setzt 100 voraus.

**Vorschlag:** Auf 100 vereinheitlichen (Single-User-System, 256 ist Overkill) oder beide Stellen auf 256 anheben — aber konsistent. LLD-Interfaces Stage 4 anpassen.

### 1.3 [KRITISCH] Scheduler-Job-Inventar weicht ab

| Quelle | Anzahl Jobs | Inhalt |
|---|---|---|
| HLD §7.4 (Tabelle) | 5 | News, Health, Wissens-Audit, Wochenzusammenfassung, DB-Backup |
| HLD §9 (Code-Beispiel) | 5 | wie oben, `bookstack_sync` und `github_sync` fehlen |
| LLD-Architektur §6.1 PHASE 6.2 | **7** | + `bookstack_sync_job` (23:00) + `github_sync_job` (23:30) |
| LLD-Interfaces §4.3 | 5 | wie HLD §7.4 |
| HLD §8.4 (Sync-Tabelle) | 2 zusätzliche | BookStack täglich 23:00, GitHub täglich 23:30 |

**Auswirkung:** BookStack-/GitHub-Sync-Jobs sind im Scheduler-LLD nicht registriert, obwohl HLD §8.4 sie fordert. Synchronisation würde nie laufen.

**Vorschlag:** LLD-Interfaces §4.3 um `bookstack_sync` und `github_sync` ergänzen; `_register_jobs()` auf 7 Jobs erweitern; Tabelle in §4.3 aktualisieren.

### 1.4 [HOCH] Scheduler-DB-Pfad inkonsistent

LLD-Interfaces nutzt `settings.scheduler_db_path`. HLD §9 nennt `/opt/egon2/data/scheduler.db`. LLD-Architektur §6.1 Phase 2: `egon2.db` plus `scheduler.db`. Pfad nicht im LLD-Architektur-Tabellenwerk dokumentiert. **Vorschlag:** In Settings explizit `scheduler_db_path: Path = Path("/opt/egon2/data/scheduler.db")` definieren.

### 1.5 [MITTEL] Telegram-Allowed-Updates inkonsistent

LLD-Architektur §3.5: `["message", "edited_message"]`. LLD-Interfaces §3.3: `allowed_updates=["message"]` — `edited_message` fehlt. Effekt: nachträglich editierte Telegram-Nachrichten werden ignoriert. **Vorschlag:** Bewusst entscheiden — für einen persönlichen Bot ist „edits ignorieren" akzeptabel, dann HLD/Architektur-LLD anpassen; sonst Interfaces-LLD ergänzen.

### 1.6 [MITTEL] Status `waiting_approval` nur partiell modelliert

HLD §8.1 listet `waiting_approval` als Task-Status. Core-LLD §3.2 modelliert die State-Machine korrekt mit Approval. Architektur-LLD §2.5 (`TaskManager`) und §6.1 (Recovery in Phase 5.2 setzt einfach „running → failed") berücksichtigen diesen Zustand nicht. **Vorschlag:** Recovery-Logik nur `status='running'`, NICHT `waiting_approval` zurücksetzen — Core-LLD hat das korrekt, Architektur-LLD muss präzisiert werden.

### 1.7 [NIEDRIG] Werkstatt-Cleanup ist nirgends Job-fähig

HLD §6.6 fordert „Cleanup 24h nach Task-Abschluss". LLD-Architektur listet `ssh_executor.cleanup_werkstatt(task_id)`. Aber: Kein Job triggert das. Es gibt keine Cleanup-Schleife. **Vorschlag:** Im Scheduler einen `werkstatt_cleanup`-Job (z. B. stündlich) ergänzen oder im Health-Check-Job als Teilschritt.

### 1.8 [NIEDRIG] `SCHEDULER` als Channel-Wert nur in Core-LLD

LLD-Core §1.2 definiert `Channel.SCHEDULER`, andere LLDs kennen nur `MATRIX`/`TELEGRAM`. **Vorschlag:** Architektur-LLD `Channel`-Enum ergänzen (gut, weil Scheduler-getriggerte Pseudo-Messages ohnehin durchs Dispatcher-System sollen).

---

## 2. Async-Korrektheit

### 2.1 [HOCH] `asyncio.create_task` aus APScheduler-Listener

LLD-Interfaces §4.4:

```python
def _on_event(self, event: JobExecutionEvent) -> None:
    ...
    import asyncio
    asyncio.create_task(self._db.scheduler_log_insert(...))
```

APScheduler-Listener werden synchron im Loop-Thread aufgerufen — `asyncio.create_task` benötigt einen laufenden Loop und gibt das Task-Handle weg, sodass Exceptions im Insert verschluckt werden („fire-and-forget"). Bei Shutdown kann der Task gerade laufen, während die DB schon geschlossen wird.

**Vorschlag:**
- Loop explizit holen: `loop = asyncio.get_running_loop(); loop.create_task(...)` und Task-Referenzen in Set sammeln, um GC zu verhindern (typischer asyncio-Bug).
- Besser: Listener nur setzen, die einen Trigger in eine `asyncio.Queue` stellen; ein Hintergrund-Task verarbeitet diese Events ordentlich.

### 2.2 [HOCH] `recover_orphaned` fehlt im Startup-Pfad

LLD-Core §3.5 verlangt: „Aufruf in `main.py` Lifespan **vor** dem Scheduler-Start". LLD-Interfaces §1.3 Stages enthält das nicht. LLD-Architektur §6.1 Phase 5.2 erwähnt es als kommentar, aber mit anderer Logik (`'running' AND updated_at < now()-5min` statt unbedingt alle).

**Auswirkung:** Tasks bleiben nach Crash auf `running` hängen, neue Sessions sehen sie als aktiv.

**Vorschlag:** In LLD-Interfaces Stage 4 (oder als neue Stage 4.5) einfügen:
```python
n = await state.dispatcher.tasks.recover_orphaned()
log.info("startup.recovered", count=n)
```

### 2.3 [HOCH] Matrix `_authenticate` ruft `client.load_store()` synchron

LLD-Interfaces §2.3: `self._client.load_store()` — in `nio` ist das synchron, kann aber File-I/O blockieren (Sync-Token-DB lesen). Bei kleinen Stores akzeptabel, bei wachsendem Store-Volume nicht. **Vorschlag:** Per `await asyncio.to_thread(self._client.load_store)` in Thread-Pool delegieren.

### 2.4 [MITTEL] `client.sync(timeout=10_000)` blockierender Initial-Sync

LLD-Interfaces §2.2 `start()`: erst `await self._client.sync(timeout=10_000, full_state=True)` (10s Initial), DANN Task starten. Das verzögert das gesamte Startup um bis zu 10 s. Bei `full_state=True` über Matrix-HS mit vielen Räumen kann es mehr werden. **Vorschlag:** Initial-Sync im Background-Task starten und `is_connected()` erst nach erstem erfolgreichem Sync auf `True` setzen — Startup blockiert nicht.

### 2.5 [MITTEL] AsyncIOExecutor + AsyncIOScheduler — Loop-Bindung

LLD-Interfaces §4.2 erzeugt `AsyncIOScheduler` im `start()`. Wichtig: Der Scheduler bindet sich an den Loop, der zu diesem Zeitpunkt läuft (FastAPI-Lifespan-Loop). Das ist korrekt. **Aber**: Bei `scheduler.shutdown(wait=True)` aus `stop()` kann APScheduler `RuntimeError: Cannot run the event loop while another loop is running` werfen, wenn der Shutdown im Lifespan-Cleanup passiert (gleicher Loop ist OK). Hier alles richtig — nur als Audit-Vermerk: **Tests sicherstellen** dass Scheduler nicht in eigenem Thread läuft.

### 2.6 [MITTEL] `httpx.AsyncClient` Lifecycle nicht durchgängig spezifiziert

LLD-Architektur erwähnt Connection-Pool-Limits, aber nirgends ist klar gesagt, dass `LLMClient` und `KnowledgeClient` einen langlebigen `httpx.AsyncClient` halten und in `aclose()` schließen. LLD-Interfaces ruft korrekt `state.llm.aclose()` und `state.knowledge.aclose()` — also geht das implizit aus dem Shutdown hervor. **Vorschlag:** In LLD-Architektur §2.6 / §3.2 explizit dokumentieren: „`AsyncClient` wird einmalig im Konstruktor erzeugt und in `aclose()` geschlossen — keine `async with`-Blöcke pro Request."

### 2.7 [NIEDRIG] `python-telegram-bot` und Signal-Handling

`Application.start()` registriert per Default Signal-Handler. Da Egon2 unter uvicorn läuft, will man die NICHT überschreiben lassen. **Vorschlag:** `ApplicationBuilder().updater(None).post_init(...)` ist die übliche Variante; alternativ `Application.start_polling(stop_signals=None)` setzen, damit uvicorn die Signale behält. Im LLD nicht erwähnt — Pflicht-Detail.

---

## 3. Error-Propagation

### 3.1 [HOCH] Doppelte Exception-Hierarchien

LLD-Architektur §5.1 definiert `Egon2Error` mit allen Subklassen. LLD-Core §3.7 definiert eigene `TaskError`, `TaskNotFoundError` etc. — **NICHT** als Subklassen von `Egon2Error`/`DatabaseError` aus Architektur-LLD.

**Auswirkung:** `try/except Egon2Error` fängt Task-Errors aus Core nicht. Logging-/Reporting-Pfade sehen sie als „unbekannte" Fehler.

**Vorschlag:** Alle Exceptions in `egon2/exceptions.py` zentralisieren. Core-LLD §3.7 ableiten lassen:
```python
class TaskError(DatabaseError): ...
class TaskNotFoundError(TaskError): ...   # Architektur-LLD definierte das schon — Duplikat entfernen
class InvalidTaskTransitionError(TaskError): ...
class ParentTaskNotFoundError(TaskError): ...
class ParentTerminalError(TaskError): ...
```
Außerdem `CommandNotAllowed` aus LLD-Interfaces §6.2 in `CommandNotAllowedError(ShellError)` umbenennen — sonst zwei Klassen mit demselben Zweck.

### 3.2 [MITTEL] Fehler-Matrix unvollständig für `LLMParseError`

LLD-Architektur §5.2 listet die meisten Fehler, aber `LLMParseError` (definiert in §5.1) hat keine Matrix-Zeile. **Vorschlag:** Ergänzen — vermutlich gleicher Pfad wie `LLMClientError` (Task → failed, kein Retry, da Format-Bug).

### 3.3 [MITTEL] „best effort" beim Senden — User merkt nichts

LLD-Architektur §3.4/§3.5 und §5.2: `MatrixSendError` und `TelegramSendError` werden nur geloggt, nicht re-raised. Bei beidseitigem Ausfall (Telegram down + Matrix down) bekommt der User keine Antwort und es gibt keinen Fallback. **Vorschlag:** Ein „pending replies"-Mechanismus: bei Send-Fehler in `tasks.result` notieren + `health_checks` Eintrag, sodass beim nächsten erfolgreichen Verbindungsaufbau zugestellt wird (HLD §5.2 verlangt das implizit: „Läuft eine Aufgabe noch wenn der User offline geht …").

### 3.4 [NIEDRIG] `SystemPromptTooLargeError` nicht in Hierarchie

Core-LLD §2.8 wirft `SystemPromptTooLargeError`, taucht aber nirgendwo in §5.1 (Architektur-Hierarchie) auf. **Vorschlag:** `class SystemPromptTooLargeError(Egon2Error): pass` ergänzen.

---

## 4. Startup/Shutdown-Sequenz

### 4.1 [HOCH] Reihenfolge widersprüchlich zwischen Architektur und Interfaces

LLD-Architektur §6.1: **Phase 4 = Interfaces (Matrix+Telegram), Phase 5 = Core, Phase 6 = Scheduler** — Interfaces VOR Core.
LLD-Interfaces §1.3: **Stage 4 = Queue+Dispatcher, Stage 5 = Scheduler, Stage 6 = Matrix, Stage 7 = Telegram, Stage 8 = Consumer** — Core/Scheduler VOR Interfaces.

LLD-Interfaces ist die richtige Reihenfolge: Interfaces dürfen erst Nachrichten annehmen, wenn Queue+Dispatcher+Consumer bereit sind. Andernfalls könnten Bots Nachrichten in eine nicht existente Queue legen.

**Vorschlag:** LLD-Architektur §6.1 anpassen. Phasen-Reihenfolge: Config → DB → Recovery (`recover_orphaned`) → externe Health-Pings → Queue → Dispatcher → Scheduler → Interfaces → Consumer-Task → yield.

### 4.2 [HOCH] Shutdown-Reihenfolge: Scheduler vor Bots ist riskant

LLD-Interfaces §1.4 Stage 4 stoppt den Scheduler **nach** den Bots. Das bedeutet: Wenn der Health-Check oder News-Report gerade läuft und Matrix-Nachrichten senden will, ist Matrix bereits gestoppt. **Vorschlag:** Scheduler vor den Bots stoppen (umgekehrte Reihenfolge der Stages 2-4). Oder: Jobs müssen `MatrixSendError` beim Shutdown tolerieren — sollte ohnehin der Fall sein (best-effort), aber das Risiko, dass Sync-Loop noch eine eingehende Antwort an einen gerade abreißenden Job verarbeitet, sinkt mit der vorgeschlagenen Reihenfolge.

### 4.3 [MITTEL] `consumer_task.cancel()` allein reicht nicht

LLD-Interfaces §1.4 Stage 1 cancelt den Consumer-Task. Was passiert mit der gerade in Bearbeitung befindlichen Nachricht? Wenn Dispatcher gerade einen 60-s LLM-Call macht, wird der nach 5 s gewaltsam beendet — Task bleibt auf `running` in der DB hängen, `recover_orphaned` repariert das aber beim nächsten Start. **Vorschlag:** Akzeptabel, ABER: Cancellation muss bis in den `httpx`-Call propagieren — `httpx.AsyncClient.aclose()` cancelt offene Requests. Stages 5/6 (`llm.aclose()` / `knowledge.aclose()`) kommen erst NACH Consumer-Cancel. Reihenfolge OK, aber im LLD klarstellen, dass `await httpx.AsyncClient.aclose()` aktiv den laufenden Request killt.

### 4.4 [HOCH] `SSHExecutor.aclose()` fehlt im Shutdown-Inventar

LLD-Interfaces §7 erwähnt: „Die Executors sind in `_shutdown` ebenfalls zu schließen (`await state.ssh.aclose()` als Stage 6.5)" — aber die Tabelle in §1.4 listet das nicht und `_shutdown()` enthält es nicht. **Vorschlag:** Tabelle in §1.4 ergänzen: `("ssh", lambda: state.ssh.aclose(), 5)` zwischen Stage 6 (LLM) und Stage 7 (DB). Außerdem `state.ssh = SSHExecutor(...)` in `_startup()` ergänzen — fehlt aktuell.

### 4.5 [MITTEL] Misfire-Run nach Crash kann zu Doppelarbeit führen

`misfire_grace_time=3600` in Kombination mit `coalesce=True` ist gut. Aber: Wenn der LXC um 07:25 abstürzt und um 07:35 wiederkommt, wird der News-Report-Job bei 07:30 als „missed" gewertet. Da `coalesce=True`, gibt es einen Run um 07:35. Bis dann ist der News-Topic schon „nicht mehr top of mind". **Vorschlag:** Akzeptabel für Single-User; im LLD nur explizit vermerken, dass dieser Catch-up-Run gewollt ist.

### 4.6 [NIEDRIG] Onboarding-Check fehlt in LLD-Interfaces

LLD-Architektur §6.1 PHASE 7 sieht Onboarding-Check (Anzahl `assistant`-Nachrichten in `conversations`). LLD-Interfaces hat keine entsprechende Stage. **Vorschlag:** Nicht im Startup, sondern beim ersten ankommenden User-Event prüfen — dafür braucht es nur ein Flag im AppState. Im LLD-Interfaces als Notiz ergänzen.

---

## 5. Message-Queue-Design

### 5.1 [MITTEL] Backpressure-Antwort-Sender-Kanal nicht definiert

LLD-Core §1.4: bei `put()=False` soll Interface Layer User-Antwort schicken („Bin gerade ausgelastet…"). Aber: Bei Drop ist nicht klar, **wer** antwortet. Der `MatrixBot._on_room_message`-Handler ruft `await self._queue.put(msg)` aber ignoriert den Boolean (LLD-Interfaces §2.4). **Vorschlag:**
```python
ok = await self._queue.put(msg)
if not ok:
    await self.send_message(room.room_id,
        "Gerade voll. Bitte gleich nochmal versuchen.")
```
Analog im Telegram-Bot.

### 5.2 [MITTEL] Single Consumer = sequenziell

`asyncio.create_task(_consume(state))` — ein Consumer-Task. Gleichzeitige Nachrichten beider Kanäle werden sequenziell verarbeitet. Das ist HLD-konform („verhindert Race Conditions"), aber: Ein langsamer LLM-Call (60 s) blockiert den Folgenachrichten-User. Da Single-User und beide Kanäle derselbe Mensch sind, ist das eigentlich OK. **Vorschlag:** Akzeptabel; im LLD klar dokumentieren, dass „Bestätigungs-Antwort < 2 s" (HLD §5.2) ein Sub-Coroutine-Pattern erfordert: Consumer feuert `confirmation` sofort ab, dann `dispatch` als Task, der bei Fertigstellung nochmal sendet.

### 5.3 [NIEDRIG] In-Memory-Queue verliert Nachrichten beim Restart

LLD-Core §1.4: „verlorene Messages werden über das Matrix/Telegram Sync (Read-Marker) wieder eingelesen". Telegram: `drop_pending_updates=True` (LLD-Interfaces §3.3) **verwirft** ausstehende Updates beim Start! Damit passt die Aussage in Core-LLD nicht zur Implementierung in Interfaces-LLD.

**Vorschlag:** Entweder `drop_pending_updates=False` setzen ODER Core-LLD korrigieren („Telegram-Nachrichten während Downtime gehen verloren — akzeptiert, da Single-User Egon einfach nochmal anstößt").

---

## 6. Context-Manager Token-Budget

### 6.1 [HOCH] Modell-Limit-Annahme stimmt für `claude-sonnet-4-6`, aber Buffer ist eng

Core-LLD §2.2:
- `MAX_TOTAL_TOKENS = 150_000`
- `RESERVED_OUTPUT_TOKENS = 8_000`
- Sum input budget = 142 000

Claude Sonnet 4.6 hat 200 000 Tokens Context-Fenster. Die 150 k sind also bewusst konservativ (Sicherheits-Marge ~25 %). OK.

**Aber:** LLM-Client (LLD-Architektur §2.6) hat `max_tokens: int = 4096` als Default. Wenn der Dispatcher 8 000 Output-Tokens reserviert, der LLM-Client aber nur 4096 anfordert, ist das ein Mismatch — 4 k Tokens werden „verschwendet" (kein Bug, aber überdimensionierter Budget).

**Vorschlag:**
- Default `max_tokens=4096` auf 8 000 anheben für Spezialisten-Calls (Researcher, Journalist liefern oft längere Texte).
- Oder `RESERVED_OUTPUT_TOKENS = 4_500` reduzieren und 4 k Output-Default beibehalten — vereinfacht.
- Klarstellen: Reserved-Budget muss `>=` `LLMRequest.max_tokens` aller geplanten Calls sein.

### 6.2 [MITTEL] Token-Schätzung 1 Token ≈ 3.5 Zeichen ist optimistisch für Deutsch

Core-LLD §2.8 nutzt `tokens ≈ ceil(len(text) / 3.5)`. Für deutschen Fließtext: realistisch 3.0–3.5. Für Code/JSON: 2.5–3.0. Brief-JSON ist relevant. **Vorschlag:** Konservativer auf `/3.0` setzen oder `tiktoken` (ist bereits im uv-Stack möglich) für Vorab-Schätzung verwenden — kostet einmalig wenige ms.

### 6.3 [NIEDRIG] FTS5-Migration auf LXC 107 nicht im Migrations-Pfad

Core-LLD §2.7 verweist auf FTS5-Index. Core-LLD §6.1 erwähnt: „Migration in `egon2/knowledge/migration.py` ergänzen". HLD §8.3 erwähnt den Index nicht. LLD-Architektur Phase 3 (Knowledge-Client-Init) führt keine Migrations aus auf LXC 107. **Vorschlag:** In Architektur-LLD §6.1 PHASE 3.2 ergänzen: einmalige Migration via `mcp_client.run_migration_v6()` falls FTS5-Tabelle fehlt. Idempotent.

### 6.4 [NIEDRIG] `KNOWLEDGE_BUDGET = 20_000` für Top-5

Top-5 Knowledge-Einträge mit 20 k Tokens-Budget = 4 k Tokens/Eintrag. Die LLD-Core §2.8 Cap auf 2 000 Zeichen ≈ 600 Tokens je Eintrag bedeutet: tatsächliche Nutzung ~3 000 Tokens, restliche 17 k bleiben ungenutzt. **Vorschlag:** Budget auf 8 000 reduzieren und ROLLING_BUDGET auf 130 000 anheben — Gespräche bekommen mehr Kontext.

---

## 7. Dependency-Injektion

### 7.1 [HOCH] `AppState` nicht typsicher bezüglich Initialisierungs-Reihenfolge

LLD-Interfaces §1.2 deklariert `AppState` als Class mit Klassenattributen — keine `__init__`. Vor `_startup` sind alle Felder „undeclared". `app.state.egon: AppState` wird zwar als Typ angegeben, Pylance/mypy würde aber erst bei ersten Zugriff Fehler werfen.

**Vorschlag:**
```python
@dataclass
class AppState:
    settings: Settings
    db: Database | None = None
    ...
```
Oder `AppState` zur ersten Phase mit „lazy" Pattern via `Optional` und Assertion.

### 7.2 [HOCH] `AgentDispatcher`-Konstruktor-Inkonsistenz

LLD-Core §4.4: `AgentDispatcher(db, llm, ctx, tasks, registry)` — 5 Argumente.
LLD-Interfaces §1.3 Stage 4: `AgentDispatcher(state.db, state.knowledge, state.llm)` — 3 Argumente.

**Auswirkung:** Fundamentaler Mismatch. Core-LLD vergisst `knowledge`, Interfaces-LLD vergisst `ctx`, `tasks`, `registry`.

**Vorschlag:** Konsolidieren auf:
```python
AgentDispatcher(
    db=state.db,
    llm=state.llm,
    knowledge=state.knowledge,
    queue=state.queue,
    context_manager=ContextManager(state.db, state.knowledge, personality_prompt),
    task_manager=TaskManager(state.db),
    registry=AgentRegistry(state.db),
)
```
Und in Interfaces §1.3 die DI-Konstruktion explizit zeigen.

### 7.3 [MITTEL] `ContextManager` und `TaskManager` werden nirgends instanziiert

In LLD-Interfaces §1.3 fehlen die Zeilen `state.task_manager = TaskManager(state.db)` und `state.context_manager = ContextManager(...)`. Sie tauchen nur als Konstruktor-Argumente in Core-LLD §4.4 auf. **Vorschlag:** Stage 4 explizit erweitern:

```python
state.task_manager = TaskManager(state.db)
state.registry = AgentRegistry(state.db)
state.context_manager = ContextManager(state.db, state.knowledge, render_system_prompt())
state.dispatcher = AgentDispatcher(
    db=state.db, llm=state.llm, knowledge=state.knowledge,
    ctx=state.context_manager, tasks=state.task_manager, registry=state.registry,
)
```

### 7.4 [NIEDRIG] Bot/Dispatcher-Antwort-Pfad nicht via DI

`_consume(state)` muss zurück an `state.matrix_bot.send_message()` oder `state.telegram_bot.send_message()` aufrufen. Wie? Über `IncomingMessage.channel`-Switch im Consumer. Das ist schon klar implizit — aber im LLD nicht ausgeschrieben. **Vorschlag:** `_consume` Pseudocode in LLD-Interfaces §1.3 ergänzen:
```python
async def _consume(state: AppState):
    while True:
        msg = await state.queue.get()
        try:
            reply = await state.dispatcher.handle(msg)
            bot = state.matrix_bot if msg.channel == "matrix" else state.telegram_bot
            await bot.send_message(msg.chat_id, reply)
        finally:
            state.queue.task_done()
```

---

## 8. Scheduler-Integration

### 8.1 [HOCH] Bereits in §2.1 erwähnt — Listener-Coroutine-Risiko

(Siehe Finding 2.1 — gleiches Problem; doppelt aufgeführt, weil sowohl Async- als auch Scheduler-relevant.)

### 8.2 [MITTEL] `replace_existing=True` + persistenter JobStore

LLD-Interfaces §4.3 nutzt `replace_existing=True`. Korrekt — Trigger-Änderungen propagieren. **Aber**: Ein bestehender, im JobStore persistierter, gerade laufender Job wird beim Restart nicht doppelt gestartet (Schutz durch `max_instances=1`), aber sein „letzter Run-State" geht verloren. Das ist akzeptabel.

**Vorschlag:** Doku-Hinweis in §4.3 ergänzen: „Trigger werden bei jedem Service-Start aktualisiert. Job-IDs sind stabil, sodass `scheduler_log` über Restarts hinweg konsistente Auswertungen erlaubt."

### 8.3 [MITTEL] `coalesce=True` + 7:30-Uhr-Job + Wochenend-Lücken

Wenn der LXC Freitag 21:00 ausfällt und Montag 09:00 zurückkommt, sind Health-Checks Sa+So+Mo um 03:00 verpasst. `coalesce=True` führt zu einem einzigen Catch-up-Run. Das kann irreführend sein, weil dann `scheduler_log` nur einen Eintrag hat statt drei. **Vorschlag:** Bei wichtigen Audit-Jobs (`weekly_audit` Mo 04:00) den `misfire_grace_time` reduzieren auf `7200` (2h) — verpasste Wochenend-Audit-Jobs würden dann „skipped" geloggt statt unsichtbar zu verschmelzen.

### 8.4 [NIEDRIG] APScheduler 4.x-Hinweis im HLD widerspricht Code

HLD §9 sagt „APScheduler 4.x". 4.x ist noch beta und hat eine andere API als das in den LLDs gezeigte 3.x-Muster (`AsyncIOScheduler`, `SQLAlchemyJobStore`, `add_job(...)`). Der Code in LLD-Interfaces §4 ist klar 3.x. **Vorschlag:** HLD §9 auf „APScheduler 3.10+ (`AsyncIOScheduler`)" korrigieren.

---

## 9. Fehlende Komponenten / Lücken

### 9.1 [HOCH] `AgentDispatcher.handle()` ist im Code nirgends definiert

Core-LLD §4.4 nennt `dispatch(task: Task)`. Interfaces-LLD §1.3 Stage 8: „liest aus Queue, übergibt an `dispatcher.handle()`". `handle` taucht nicht im Core-LLD auf.

**Vorschlag:** Methode `async def handle(self, msg: IncomingMessage) -> str` als öffentlichen Einstiegspunkt definieren — Core-LLD §4.4 ergänzen. Sie macht: `task = await self.tasks.create(title=msg.text[:80], description=msg.text, source_channel=msg.channel)` → `await self.dispatch(task)`.

### 9.2 [HOCH] `AgentRegistry` ist nirgends spezifiziert

Core-LLD §4.4 erwartet `registry: AgentRegistry`. Core-LLD §6.3 sagt: „nicht in diesem LLD". Architektur-LLD enthält keine Spezifikation. HLD §6.5 zeigt nur das Datenmodell.

**Vorschlag:** Eigenes `LLD-Agenten.md` (existiert in `docs/` lt. `ls`) muss prüfen — falls nicht abgedeckt, dort Spezifikation ergänzen: `class AgentRegistry`-API mit `all_active()`, `get(id)`, `create_specialist_via_llm(task)`, `update_prompt(id, new_prompt)`, `deactivate(id)`.

### 9.3 [MITTEL] `Database`-API ist Black-Box

`Database.connect()`, `Database.run_migrations()`, `Database.is_ready()`, `Database.aclose()`, `Database.transaction()` werden alle benutzt, aber nirgends spezifiziert (kein eigenes LLD ausgewiesen außer LLD-Persistenz, das nicht reviewed wurde). **Vorschlag:** Sicherstellen dass `LLD-Persistenz.md` diese API exakt definiert — sonst wird `Database` zu einem GodObject ohne Vertrag.

### 9.4 [MITTEL] Job-Funktionen `news_report.run`, `health_check.run` etc.

LLD-Interfaces §4.3 importiert `from egon2.jobs import backup, health_check, news_report, weekly_audit, weekly_summary`. Module sind erwähnt, Inhalte nirgendwo spezifiziert. HLD §7.4 beschreibt den Ablauf, aber nicht die Signaturen. **Vorschlag:** Mini-LLD oder Anhang in LLD-Interfaces: `async def run(*, dispatcher: AgentDispatcher, db: Database) -> None`.

### 9.5 [MITTEL] Sync-Module `bookstack_sync`, `github_sync` nicht spezifiziert

Erwähnt in HLD §8.4 und LLD-Architektur §6.1 PHASE 6, aber kein LLD. **Vorschlag:** Mindestens API-Signaturen + Auth-Quellen (Vaultwarden) in LLD-Architektur §3 oder eigenem Dokument ergänzen.

### 9.6 [NIEDRIG] Health-Check-Job-Inhalt fehlt

HLD §12 beschreibt es ausführlich, aber kein LLD legt fest, welche Methoden auf welchen Clients aufgerufen werden. **Vorschlag:** Tabelle in LLD-Interfaces §4 ergänzen — was tut `health_check.run` konkret.

---

## 10. Skalierbarkeits-Overkill vs. Unter-Engineering

### 10.1 [MITTEL] Overkill: SQLAlchemy für Single-File-SQLite-JobStore

LLD-Interfaces §4.2 nutzt `SQLAlchemyJobStore`. Das zieht SQLAlchemy als Abhängigkeit nur für 7 Cron-Jobs. APScheduler hat auch einen `MemoryJobStore` und einen reinen `SQLiteJobStore` ist möglich — aber `SQLAlchemyJobStore` ist tatsächlich die offizielle SQLite-Variante in APScheduler 3.x. Akzeptabel.

**Vorschlag:** Akzeptieren, aber dokumentieren: „SQLAlchemy ist Transitive-Dep für JobStore-Persistenz. Bei reinem In-Memory wäre `MemoryJobStore` möglich, dann gehen verpasste Jobs nach Crash verloren — gegen HLD §7.4 Anforderung."

### 10.2 [MITTEL] Overkill: Optimistic Locking in TaskManager

Core-LLD §3.6: optimistic locking via `WHERE status = ?` im UPDATE. Macht Sinn in Multi-Worker-Setups. Hier: ein Consumer-Task, ein Scheduler-Loop, beide im selben Event-Loop, also serialisiert auf Async-Ebene. **Vorschlag:** Pattern beibehalten — kostet nichts, schützt vor künftigen Race Conditions falls Sub-Tasks parallel via `asyncio.gather` dispatched werden.

### 10.3 [HOCH] Unter-Engineering: Keine Idempotenz bei Scheduler-Jobs

Wenn `news_report` mitten im Run abstürzt (LLM-Antwort kam, BookStack-Sync schlug fehl), beim nächsten Run wird der Eintrag im Knowledge Store doppelt angelegt. **Vorschlag:** Pro Job einen „Idempotency-Key" generieren (`f"news_report_{date.today().isoformat()}"`) und vor INSERT prüfen.

### 10.4 [MITTEL] Unter-Engineering: Kein Rate-Limit im LLM-Client

Marco kann durch schnelle Eingaben theoretisch 100 Nachrichten/min an Egon schicken — Queue=100, jede löst 2-3 LLM-Calls aus. Claude Code API auf LXC 105 ist Single-User, aber upstream gibt es Anthropic-Rate-Limits. **Vorschlag:** Token-Bucket-Rate-Limiter in `LLMClient` (z. B. via `aiolimiter`) — z. B. 30 Calls/min hard cap. Aktiviert dass `LLMRateLimitError` realistisch wird und der Retry-Pfad getestet wird.

### 10.5 [MITTEL] Overkill: Pydantic v2 Modelle vs. dataclass — beides genutzt

LLD-Architektur nutzt durchgehend Pydantic. LLD-Core nutzt `@dataclass(slots=True, frozen=True)`. Beides nebeneinander erhöht kognitiven Overhead und Validierungs-Inkonsistenzen.

**Vorschlag:** Entscheidung treffen:
- **Empfehlung Pydantic** für externe Schnittstellen (Matrix/Telegram-Events, LLM-Responses, MCP-Responses) — automatische Validierung von Untrusted Input.
- **Empfehlung dataclass slots=True** für interne Domain-Objekte (Task, Brief, ContextBundle) — geringere Allokation, kein Validierungs-Overhead bei jedem Konstruktor-Call.

Im LLD klare Konvention dokumentieren: „Pydantic an System-Grenzen, dataclass intern."

### 10.6 [NIEDRIG] Unter-Engineering: Keine Migration-Versionierung dokumentiert

LLD-Interfaces §1.3 Stage 1: „prüft Schema-Version, führt fehlende Migrationen aus". Wo wird Schema-Version gespeichert? Wie? **Vorschlag:** `schema_migrations(version INT PRIMARY KEY, applied_at TIMESTAMP)`-Tabelle plus Liste in `egon2/database.py` als Konstante. Sollte in LLD-Persistenz stehen.

### 10.7 [NIEDRIG] Single-User: Whitelist mit `frozenset[int]` ist gut, aber Reload?

Wenn Marco eine zweite Telegram-ID hinzufügen will (z. B. Tablet), muss Service neugestartet werden. Akzeptabel für Single-User-Tool — nur als Hinweis dokumentieren.

---

## Zusammenfassung & Empfohlene Aktionen

### Vor Implementierungsbeginn (KRITISCH/HOCH zwingend):

1. **Datenmodell konsolidieren** (1.1): Eine kanonische `IncomingMessage`-Definition.
2. **Queue-Maxsize einigen** (1.2): 100 oder 256, einheitlich.
3. **Scheduler-Job-Inventar** (1.3): BookStack/GitHub-Sync-Jobs ergänzen oder aus HLD streichen.
4. **Exception-Hierarchie zentralisieren** (3.1): Eine Hierarchie, alle Module ableiten.
5. **Startup-Reihenfolge harmonisieren** (4.1): Interfaces-LLD-Reihenfolge in Architektur-LLD übernehmen.
6. **Shutdown ergänzen** (4.4): `SSHExecutor.aclose()`, Reihenfolge Scheduler-vor-Bots.
7. **`AgentDispatcher`-Konstruktor harmonisieren** (7.2): Auf gemeinsamen Vertrag bringen.
8. **`AgentDispatcher.handle()` definieren** (9.1).
9. **`recover_orphaned()` in Startup** (2.2).
10. **APScheduler-Listener `create_task` absichern** (2.1).

### Vor Phase 4 (Scheduler):

- Job-Module (`egon2/jobs/*`) spezifizieren (9.4).
- Idempotency-Keys in Scheduler-Jobs (10.3).
- BookStack/GitHub-Sync-Module spezifizieren (9.5).

### Wartbarkeit / Qualität (MITTEL):

- Pydantic-vs.-dataclass-Konvention dokumentieren (10.5).
- Token-Schätzung konservativer (6.2).
- LLM-Rate-Limit (10.4).
- Pending-Replies-Mechanismus bei Send-Fehlern (3.3).

### Doku-Anpassungen (NIEDRIG):

- HLD §9 APScheduler-Version präzisieren (8.4).
- Telegram `drop_pending_updates`-Diskrepanz (5.3).
- Onboarding-Check-Logik (4.6).

---

## Gesamteinschätzung

Das LLD-Set ist **deployment-fähig nach Behebung der KRITISCH/HOCH-Findings**. Die Architektur ist für ein Single-User-System angemessen dimensioniert (kein Microservice-Overkill, keine Message-Brokers wie Kafka — gut), aber durchdacht in Bezug auf Crash-Recovery, Backpressure und Persistenz.

Stärken:
- Sauberes async-only Design.
- Gute Trennung Interface / Core / Executor / Persistence.
- Realistische Timeout- und Retry-Profile.
- Ehrliche Fehlerbehandlung (Soft-Fail bei Knowledge-Store, Hard-Fail bei DB).

Schwächen:
- Drei LLD-Dokumente unterscheiden sich in Detailtypen — entstanden aus paralleler Erarbeitung, jetzt Konsolidierung nötig.
- Einige „Brücken-Module" (`AgentRegistry`, `Database`, `egon2/jobs/*`) sind nur referenziert, nicht spezifiziert.

Mit den oben genannten ~10 Klarstellungen ist das System sauber implementierbar.
