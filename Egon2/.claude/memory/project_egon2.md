---
name: Egon2 Projektkontext
description: Persönlicher KI-Assistent — Architektur, Stack, Deployment, Status, Grundentscheidungen
type: project
---

Egon2 ist ein persönlicher KI-Assistent (kein Chatbot, sondern Handlungsträger) mit Matrix- und Telegram-Anbindung.

## Grundentscheidungen (unveränderlich)
- **Privates Hobbyprojekt, Einzelnutzer (Marco)**
- **Keine Hochverfügbarkeit** — single-instance, `Restart=on-failure` reicht
- **Kein Anwendungs-Backup** — LXC wird bei Bedarf auf Hypervisor-Ebene (Proxmox) gesichert
- **Kein Docker** — systemd direkt
- **Autonomes Handlungsmandat:** Egon handelt eigenständig, kein Approval-Workflow für pct oder andere Admin-Ops
- **Dynamische Agenten:** LLM erzeugt System-Prompts vollständig frei — kein Template, kein Approval

## Stack
- Python 3.13 / FastAPI / aiosqlite / matrix-nio / python-telegram-bot v21.11.1
- APScheduler **3.10.x** (NICHT 4.x!) / asyncssh / uv
- **LLM-Backend:** Claude Code API `http://10.1.1.105:3001/v1/chat/completions` (OpenAI-kompatibel)
- **Deployment:** LXC 128 (`Egon2`), IP `10.1.1.202`, 6C/6GB/20GB, `/opt/egon2/`
- **Quellcode:** `/opt/Projekte/Egon2/` (Monorepo auf LXC 126)
- **Docs:** `/opt/Projekte/Egon2/docs/`

## Persönlichkeit
"Egon der 2." / kurz "Egon" — britisch-satirischer Humor (Douglas Adams / Blackadder), Deutsch, gelegentliche englische Einwürfe, direkt, nie servil

## Kernfunktionen
- Matrix-Bot (@egon:doehlercomputing.de) + Telegram-Bot (@Egon)
- Task-Manager (pending→running→done|failed|cancelled|waiting_approval)
- Scheduler: täglich 07:30 News-Report via SearXNG (10.1.1.204)
- SSH-Executor via User `egon` — Argv-basiert (kein Shell-String), Argument-Allowlist je Binary, pct Vollzugriff
- Knowledge Store: LXC 107 (10.1.1.107:8080, MCP-Server, `mcp_knowledge_v5.db`)
- Spiegel: BookStack + GitHub-Repo `egon2-knowledge` (privat)

## Spezialisten-System (10 Builtin + dynamisch erweiterbar)
- researcher, journalist, it_admin, developer (→ LXC 126), analyst, controller, archivist (→ LXC 107), designer, secretary, inspector
- **Dynamische Agenten:** Egon erzeugt neue Spezialisten eigenständig wenn kein Builtin passt; LLM generiert System-Prompt frei; max. 20 dynamische Agenten aktiv
- IDs immer mit Underscore: `it_admin`, `dynamic_legal_analyst` etc.
- Buchhaltung: `agent_assignments` (Brief, Ergebnis, Token, Kosten, Qualität, prompt_version_used)
- Prompt-Versionshistorie: `agent_prompt_history` (Rollback möglich via `/agenten rollback <id>`)

## Datenbank-Schema (egon2.db, SQLite WAL)
- conversations, tasks (+ request_id, cancelled_reason, parent_task_id), notes (3-state sync-flags, bookstack_page_id)
- agents (+ created_by, last_used_at, use_count, deactivated_reason, promoted_to_builtin)
- agent_assignments (+ prompt_version_used), agent_prompt_history, health_checks, scheduler_log
- DATETIME: immer ISO8601-UTC `datetime.now(timezone.utc)` — niemals `datetime.utcnow()`
- Sync-Flags: 0=pending / 1=synced / 2=error (kein Boolean)

## Technische Invarianten
- APScheduler immer 3.10.x pinnen (nicht 4.x)
- PTB v21: `stop_signals` NICHT auf `Updater.start_polling()` — nur auf `run_polling()` (nicht verwendet)
- Kein `Application.run_polling()` im Lifespan
- Consumer: `create_task` statt `await` im Hot-Path
- Retry: nur bei ConnectError/Timeout, kein Circuit Breaker
- Sub-Tasks: max. Tiefe 2
- claude-code-api LXC 105: `--bare` Flag in claude-executor.js entfernt (unterbricht OAuth-Auth in v2.1.126)

## Bekannte Bugfixes / Eigenheiten
- **PTB 21.11**: `stop_signals` existiert NICHT auf `Updater.start_polling()` → entfernt
- **claude-code-api**: `--bare` Flag in `/home/claude/claude-code-api/claude-executor.js` Zeile 127 auskommentiert — unterbricht OAuth-Auth in CLI v2.1.126. Bei Update der API prüfen!
- **LLM-Ping**: `max_tokens=10` (nicht 1 — zu restriktiv für den Wrapper)

## Credentials & Zugänge
- **Matrix**: @egon:doehlercomputing.de, Passwort aus Vaultwarden "Matrix - Egon", Homeserver https://matrix.doehlercomputing.de
- **Telegram**: Bot @Egon, Token in `/opt/egon2/.env` (noch NICHT in Vaultwarden — Admin-TODO)
- **Telegram Whitelist**: [6124084259] (Marco)
- **SSH-Key**: `/opt/egon2/.ssh/id_ed25519` (Public Key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOh/rdT+bchs7lF6iF2ufNkGdTWtEqaqMaA3YNXH2XAA egon2@doehlercomputing.de`)
- **User `egon`**: lokal angelegt auf Proxmox-Host + LXC 104/107/109/110/117/118/121/122/125/126/127/130, Key-Auth bestätigt

## Status (2026-05-02) — LIVE, VOLLSTÄNDIG IMPLEMENTIERT ✅

### Vollständig implementiert ✅
- Alle Grundmodule: database, llm_client, personality, message_queue, task_manager, context_manager
- agent_registry (10 Builtin-Agenten + dynamische Agenten via `create_dynamic_agent()`), agent_dispatcher
- matrix_bot, telegram_bot, scheduler (APScheduler WAL-Modus + 2 Jobs registriert)
- SSH-Executor (Argv-Allowlist, 18 Binaries, pct Vollzugriff) + Shell-Executor
- main.py (9-stufiger Lifespan, 7-stufiger Shutdown)
- egon2.service: active/running, autostart enabled
- **`/stats`** — echte DB-Abfragen (Tasks-per-Status, Top-3-Agenten, Kosten, Tokens)
- **`/agenten`** — Listing aller Agenten + `/agenten rollback <id>`
- **`/suche <query>`** — SearXNG-HTTP-Client → researcher-Spezialist
- **Dynamische Agenten** — `create_dynamic_agent()`, Limit 20, Duplikat-Check (Jaccard ≥ 0.4), `rollback_prompt()`
- **Sub-Tasks** — `_handle_subtasks()` + `_run_subtask()` (max Tiefe 2, asyncio.gather parallel)
- **Knowledge-Client** (`egon2/knowledge/client.py`) — HTTP gegen LXC 107, graceful degradation
- **News-Report-Job** — täglich 07:30 Europe/Berlin, SearXNG → journalist → Matrix+Telegram
- **BookStack-Sync** (`egon2/sync/bookstack.py`) — alle 30 min, notes.synced_bookstack 0→1

### Admin-TODOs 🟢
1. Telegram-Token in Vaultwarden Org "Bots" ablegen
2. GitHub-Repo `egon2-knowledge` (privat) anlegen
3. `BOOKSTACK_TOKEN_ID` + `BOOKSTACK_TOKEN_SECRET` in `/opt/egon2/.env` setzen (für BookStack-Sync)
4. `NEWS_REPORT_MATRIX_ROOM` + `NEWS_REPORT_TELEGRAM_CHAT` in `.env` setzen (für News-Versand)

## Neue Module (2026-05-02)
- `egon2/jobs/news_report.py` — `news_report_job()` (no-kwarg, Modul-Global `_app`)
- `egon2/jobs/bookstack_sync.py` — `bookstack_sync_job()` (no-kwarg, Modul-Global `_app`)
- `egon2/knowledge/client.py` — `KnowledgeClient` + `KnowledgeEntry`
- `egon2/sync/bookstack.py` — `BookStackSync`

## APScheduler-Pickle-Pattern (WICHTIG K1)
Jobs DÜRFEN keine non-picklable kwargs erhalten (FastAPI, httpx-Client, asyncio.Lock nicht picklebar!).
Muster: Modul-Level `_app: FastAPI | None = None`, `register_*()` setzt `_app = app`, Job greift auf `_app.state.egon` zu.

## Behobene Findings (Audit-Runde 1+2 — nicht mehr offen)
- LLD-Core: SYNONYM_BOOST, task_done() Timing, join(), sender_id
- LLD-Agenten: Syntax-Fehler, _slug() Separator
- LLD-Persistenz: bump_prompt_version(), DDL-Spalten, AssignmentStatus, cost_sum datetime
- LLD-Interfaces: Startup-Reihenfolge, pct Vollzugriff, safe_wrap(), AgentDispatcher keyword-args
- LLD-Architektur: datetime.utcnow()→UTC, AgentDispatcher API
