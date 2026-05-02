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
- Python 3.12 / FastAPI / aiosqlite / matrix-nio / python-telegram-bot v21
- APScheduler **3.10.x** (NICHT 4.x!) / asyncssh / uv
- **LLM-Backend:** Claude Code API `http://10.1.1.105:3001/v1/chat/completions` (OpenAI-kompatibel)
- **Deployment:** LXC 128 (`Egon2`), IP `10.1.1.202`, 6C/6GB/20GB, `/opt/egon2/`
- **Quellcode:** `/opt/Projekte/Egon2/` (Monorepo, auf LXC 126)
- **Docs:** `/opt/Projekte/Egon2/docs/`

## Persönlichkeit
"Egon der 2." / kurz "Egon" — britisch-satirischer Humor (Douglas Adams / Blackadder), Deutsch, gelegentliche englische Einwürfe, direkt, nie servil

## Kernfunktionen
- Matrix-Bot (@egon2:doehlercomputing.de) + Telegram-Bot
- Task-Manager (pending→running→done|failed|cancelled|waiting_approval)
- Scheduler: täglich 07:30 News-Report via SearXNG (10.1.1.204)
- SSH-Executor via User `egon` — Argv-basiert (kein Shell-String), Argument-Allowlist je Binary, pct Vollzugriff
- Knowledge Store: LXC 107 (10.1.1.107:8080, MCP-Server, `mcp_knowledge_v5.db`)
- Spiegel: BookStack + GitHub-Repo `egon2-knowledge` (privat)

## Spezialisten-System (10 Builtin + dynamisch erweiterbar)
- researcher, journalist, it_admin, developer (→ LXC 126), analyst, controller, archivist (→ LXC 107), designer, secretary, inspector
- **Dynamische Agenten:** Egon erzeugt neue Spezialisten eigenständig wenn kein Builtin passt (Confidence < 0.6); LLM generiert System-Prompt frei; max. 20 dynamische Agenten aktiv
- Confidence-Score normiert: `keyword_matches / len(capabilities)`, Schwelle 0.6 (Builtin) / 0.4 (Dynamic-Reuse)
- IDs immer mit Underscore: `it_admin`, `dynamic_legal_analyst` etc.
- Buchhaltung: `agent_assignments` (Brief, Ergebnis, Token, Kosten, Qualität, prompt_version_used)
- Prompt-Versionshistorie: `agent_prompt_history` (Rollback möglich via `/agenten rollback <id>`)

## Datenbank-Schema (egon2.db, SQLite WAL)
- conversations, tasks (+ request_id, cancelled_reason, parent_task_id), notes (3-state sync-flags, bookstack_page_id)
- agents (+ created_by, last_used_at, use_count, deactivated_reason, promoted_to_builtin)
- agent_assignments (+ prompt_version_used), agent_prompt_history, health_checks, scheduler_log
- DATETIME: immer ISO8601-UTC `datetime.now(timezone.utc)` — niemals `datetime.utcnow()`
- Sync-Flags: 0=pending / 1=synced / 2=error (kein Boolean)

## Startup-Reihenfolge (kanonisch, 9 Stufen)
1. DB init + WAL + Migrationen
2. recover_orphaned() → running→pending
3. Knowledge Store Client (soft-fail)
4. LLM Client + Verbindungstest (retry 3×, backoff [1,2,4]s)
5. MessageConsumer (create_task + Semaphore(3)) + AgentDispatcher
6. Matrix Bot (sync → dann callbacks)
7. Telegram Bot (initialize→start→start_polling, stop_signals=None!)
8. **Scheduler zuletzt** — nach beiden Interfaces (verhindert misfire-Runs ohne Bot)

## Shutdown-Reihenfolge (kanonisch, 7 Stufen)
1. Scheduler shutdown
2. Matrix Bot stop
3. Telegram Bot stop
4. Message Queue drain (join, 30s Timeout)
5. Consumer stop + alle laufenden Tasks awaiten
6. SSHExecutor.aclose()
7. DB WAL-checkpoint + close

## Security-Entscheidungen (alle akzeptiert, Heimnetz)
- SSH-Executor: Argv-Übergabe (kein Shell-String), Argument-Allowlist je Binary
- **pct: Vollzugriff** (lesen + schreiben) — autonomes Handlungsmandat, kein Approval
- **Dynamische Agenten: freier LLM-generierter System-Prompt** — kein Template-Zwang
- safe_wrap() für alle externen Inputs (Matrix/Telegram/SearXNG/Knowledge) → `<external source="…">`
- Internes HTTP ohne TLS (LLM/Knowledge/SearXNG): akzeptiertes Risiko
- LXC 126 kein seccomp/cgroup: akzeptiertes Risiko

## Slash-Kommandos
/task /note /wissen /status /stats /suche /agenten /hilfe

## Technische Invarianten
- APScheduler immer 3.10.x pinnen (nicht 4.x)
- PTB v21: `stop_signals=None` zwingend
- Kein `Application.run_polling()` im Lifespan
- Consumer: `create_task` statt `await` im Hot-Path
- Retry: nur bei ConnectError/Timeout, kein Circuit Breaker
- Sub-Tasks: max. Tiefe 2

## System-Account
User `egon`, sudo NOPASSWD für apt/systemctl/pct, SSH Key Ed25519
Bot-Tokens: beim Start aus Vaultwarden geladen (nicht aus .env)

## Vorbereitungsaufgaben (ausstehend)
- Matrix-Account @egon2:doehlercomputing.de einrichten
- Telegram-Bot via @BotFather → Token in Vaultwarden (Org "Bots")
- GitHub-Repo `egon2-knowledge` anlegen (privat)
- User `egon` auf Proxmox + alle LXCs anlegen (sudo, SSH-Key)
- Marco's Telegram User-ID für Whitelist ermitteln

## Status (2026-05-02)
- HLD **v1.7** ✅
- LLD-Architektur **v1.3** ✅, LLD-Core **v1.3** ✅, LLD-Agenten **v1.3** ✅
- LLD-Persistenz **v1.3** ✅, LLD-Interfaces **v1.3** ✅, Spec-UX v1.1 ✅
- Security-Audit + 4 Fachreviews ✅ + alle Findings eingearbeitet (Runde 1 + Runde 2)
- **Audit-Runde-2-Findings vollständig behoben** ✅ (2026-05-02)
- **Nächster Schritt: Phase 1 Implementierung**

## Behobene Findings (Audit-Runde 2 — nicht mehr offen)
- LLD-Core: SYNONYM_BOOST `it-admin`→`it_admin`, `task_done()` Timing, `join()`, `sender_id`
- LLD-Agenten: Syntax-Fehler (fehlende ` ``` `), `_slug()` Separator `-`→`_`
- LLD-Persistenz: `bump_prompt_version()` (changed_at→created_at + id), DDL-Spalten (use_count/last_used_at/sender_id), AssignmentStatus+CHECK 'cancelled', cost_sum datetime-Format
- LLD-Interfaces: Startup-Reihenfolge (Scheduler Stage 8, nach beiden Bots), pct Vollzugriff in Allowlist, systemctl/apt Schreibzugriff, safe_wrap() in Bots, AgentDispatcher keyword-args
- LLD-Architektur: datetime.utcnow()→UTC, AgentDispatcher API (handle/dispatch)
