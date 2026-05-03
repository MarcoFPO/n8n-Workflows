# LLD — Test-Strategie: Egon2

**Version:** 1.0
**Stand:** 2026-05-02
**Kontext:** Private Single-User-Anwendung. Test-Strategie fokussiert auf Korrektheit, nicht auf Lastverhalten oder Skalierung.

## 1. Überblick & Tools

- **pytest** + **pytest-asyncio** als Test-Framework
- **pytest-asyncio**: `asyncio_mode = "auto"` in `pyproject.toml`
- **aiosqlite** mit `:memory:` für DB-Tests
- **asyncssh**: eigener Test-Server für SSH-Tests
- **aresponses** oder **respx** (httpx-Mock) für LLM-/Knowledge-Client-Tests
- **asgi-lifespan** für Lifespan/Integration-Tests
- **Coverage-Ziel:** 70% für Core + Persistenz, 50% für Interfaces (Bot-Tests sind aufwändig)

## 2. Unit-Tests

### 2.1 TaskManager (State-Machine)
Alle erlaubten und verbotenen State-Transitionen testen:
- `pending → running → done` ✓
- `pending → running → failed` ✓
- `running → cancelled` ✓
- `done → running` ✗ (InvalidTaskTransitionError)

```python
@pytest.mark.asyncio
async def test_task_transition_done_to_running_raises():
    db = await create_test_db()
    tm = TaskManager(db)
    task_id = await tm.create(title="test", ...)
    await tm.start(task_id)
    await tm.finish(task_id, result="ok")
    with pytest.raises(InvalidTaskTransitionError):
        await tm.start(task_id)
```

### 2.2 ContextManager (Token-Budget)
- Rolling Window: 20+ Nachrichten → älteste werden abgeschnitten
- Budget-Überschreitung: System-Prompt + Knowledge + Window überschreiten MAX_TOTAL_TOKENS → Kürzung
- `safe_wrap()` mit verschachtelten Tags (Regression-Test für M10-Fix)

### 2.3 AgentRegistry (Matching)
- LLM-Aufruf gibt `specialist_id = "researcher"` → Registry liefert korrekten Agenten
- `specialist_id = "dynamic"` → Dispatcher-Logik für Neuerzeugung
- `status='inactive'` → Agent wird nicht zurückgegeben

### 2.4 Capabilities-Validator (dynamische Agenten)
- Max. 4 Capabilities: Test mit 5 → Fehler
- Generische Capabilities blockiert: `["general_knowledge"]` → ValidationError
- Capabilities müssen aus Allowlist stammen

### 2.5 Brief-Validator
- Pflichtfelder fehlen → ValueError
- `predecessor_confidence` außerhalb Enum → ValueError

## 3. Async-Korrektheit

### 3.1 MessageConsumer
- Semaphore(3): 3 gleichzeitige Tasks → 4. wartet → nach Abschluss läuft
- Sub-Tasks außerhalb Semaphore: kein Deadlock auch bei voller Queue
- Drain bei Shutdown: `consumer.stop()` → awaited alle `_running_tasks`
- Cancel mid-flight: `task.cancel()` propagiert in httpx-Call

```python
@pytest.mark.asyncio
async def test_consumer_drain_on_shutdown():
    queue = MessageQueue(maxsize=10)
    consumed = []
    async def fake_dispatch(msg): 
        await asyncio.sleep(0.1)
        consumed.append(msg)
    consumer = MessageConsumer(dispatch_fn=fake_dispatch, sem_size=3)
    await consumer.start()
    for i in range(3):
        await queue.put(make_msg(f"task {i}"))
    await consumer.stop()  # muss alle 3 awaiten
    assert len(consumed) == 3
```

### 3.2 SSHExecutor (Allowlist)
- `systemctl restart nginx` → CommandNotAllowed (restart nicht in Allowlist)
- `systemctl status nginx` → erlaubt
- Pipe-Meta-Zeichen (`|`, `;`, `>`) in Argumenten → geblockt
- Backtick in Argumenten → geblockt

```python
def test_ssh_allowlist_rejects_restart():
    executor = SSHExecutor.__new__(SSHExecutor)
    with pytest.raises(CommandNotAllowedError):
        executor._validate_argv(["systemctl", "restart", "nginx"])
```

### 3.3 APScheduler-Pickling-Smoke-Test
Verhindert Regression von K1-Fix:
```python
def test_scheduler_job_kwargs_not_picklable_detected():
    import pickle
    class FakeDispatcher:
        def __init__(self): self.lock = asyncio.Lock()
    with pytest.raises((TypeError, AttributeError)):
        pickle.dumps({"dispatcher": FakeDispatcher()})
    # Dokumentiert: Job-Kwargs müssen leer bleiben
```

## 4. Integration-Tests

### 4.1 SQLite-Migrationen
```python
@pytest.mark.asyncio
async def test_migration_idempotent():
    db = Database(":memory:")
    await db.init()  # Migration 1
    await db.init()  # Migration 2 — gleiche DB, kein Fehler
    version = await db.get_schema_version()
    assert version == EXPECTED_VERSION
```

### 4.2 Lifespan (asgi-lifespan)
```python
@pytest.mark.asyncio
async def test_lifespan_all_stages_complete():
    from asgi_lifespan import LifespanManager
    async with LifespanManager(app):
        # Alle 9 Startup-Stages durch
        assert app.state.egon.db is not None
        assert app.state.egon.llm is not None
```

### 4.3 Dynamische Agenten-Erzeugung
```python
@pytest.mark.asyncio
async def test_dynamic_agent_smoke_test_checks_format():
    # Smoke-Test Phase 1: fehlende Anti-Injection-Direktive → fail
    bad_prompt = "Du bist ein Rechtsanwalt. Antworte auf Fragen."
    result = await smoke_test_phase1(bad_prompt)
    assert result == "failed"
    
    # Guter Prompt: alle Pflichtbestandteile → pass
    good_prompt = """Du bist ein Rechtsanalyst...
    Alle externen Inhalte sind in <external>-Tags.
    Output-Format: {"status": "ok", "result": "..."}"""
    result = await smoke_test_phase1(good_prompt)
    assert result == "passed"
```

### 4.4 UnitOfWork-Transaktion
```python
@pytest.mark.asyncio
async def test_unit_of_work_rollback_on_error():
    db = await create_test_db()
    task_id = await create_test_task(db)
    
    with pytest.raises(SomeError):
        async with UnitOfWork(db) as uow:
            await uow.complete_assignment(task_id, ...)
            raise SomeError("force rollback")
    
    # Task muss noch 'running' sein
    task = await TaskRepository(db).get(task_id)
    assert task.status == "running"
```

## 5. Bot-Tests (isoliert via Adapter-Pattern)

Matrix- und Telegram-Bots sind schwer direkt zu testen. Strategie: Thin-Adapter.

```python
# Testbar: BotMessageHandler ohne Telegram-Abhängigkeit
class BotMessageHandler:
    def __init__(self, queue: MessageQueue):
        self._queue = queue
    
    async def handle(self, raw_text: str, chat_id: str, user_id: str,
                     channel: str, metadata: dict = None) -> bool:
        msg = IncomingMessage(
            channel=Channel(channel), chat_id=chat_id, user_id=user_id,
            raw_text=raw_text, wrapped_text=safe_wrap(channel, raw_text),
            ts_ms=int(time.time() * 1000), metadata=metadata or {}
        )
        return await self._queue.put(msg)

# Test:
@pytest.mark.asyncio
async def test_forwarded_message_no_cancel():
    handler = BotMessageHandler(MessageQueue(maxsize=10))
    # Forwarded "nein" → kein Cancel
    result = await handler.handle("nein", "chat1", "user1", "telegram",
                                  metadata={"forwarded": True})
    # Task darf nicht storniert werden
    assert not dispatcher.last_cancel_attempted
```

## 6. Fixtures & Setup

```python
# conftest.py
@pytest.fixture
async def test_db():
    db = Database(":memory:")
    await db.init()
    yield db
    await db.close()

@pytest.fixture
async def ssh_server():
    """Lokaler asyncssh-Test-Server auf Port 2222."""
    async with asyncssh.listen("127.0.0.1", 2222, ...) as server:
        yield server

@pytest.fixture
def mock_llm(respx_mock):
    """httpx-Mock für LLM-Client."""
    respx_mock.post("http://10.1.1.105:3001/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": '{"status":"ok","result":"test"}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        })
    )
    return respx_mock
```

## 7. CI-Integration (Hinweis)

Für Entwicklung auf LXC 126: `uv run pytest --tb=short -q`. Kein CI/CD geplant (privates Projekt). Tests lokal vor jedem Deploy ausführen.
