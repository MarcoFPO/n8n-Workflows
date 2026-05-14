---
name: n8n Incident Pipeline - Aktueller Stand
description: Stand der n8n Incident Response Pipeline und Znuny-Ticket-Abarbeitung (März 2026)
type: project
---

## n8n MASTER Incident Response Workflow

- **ID**: `EcSZAPiPhhekDwXd`
- **Status**: Aktiv, produktiv
- **Nodes**: 62 (2-Zyklus-Aufbau + Statusübergänge + Pause-Detection-Branches)
- **Timeout**: 1800s (erhöht von 600s in `/etc/systemd/system/n8n.service.d/override.conf` auf LXC 117)
- **Webhook**: `http://10.1.1.180:80/webhook/znuny-new-ticket` (POST: ticket_id, wer, system_ip, severity, problem, zabbix_event_id)
- **Aktueller API-Key** (public-api, Stand 2026-03-27): `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDk0ZDFhYy1jMmZmLTQ5YTItOTFlMC1hMTRmOGU0ZDc2MjYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMDM3MzAxfQ.tZ72KsjUc6EuuWm5ZeTz1loMPmcMtMjO2B7ABA5dsiA`
- **Trigger**: Wird von Znuny automatisch via ZabbixIntegration-Webservice ausgelöst

**Why:** Timeout-Erhöhung war nötig wegen 2-Retry-Zyklus (~20-25 min Laufzeit bei Eskalation)
**How to apply:** Bei n8n-Workflow-Änderungen immer Timeout beachten

## Ablauf (kein Orchestrator-Aufruf)

1. Webhook → Ticket einlesen
2. Zyklus 1: RCA → Guide → Execute → Verify
3. Wenn gelöst: Ticket schließen + BookStack-Bericht
4. Wenn nicht gelöst: Retry → Zyklus 2 identischer Ablauf
5. Wenn nach Zyklus 2 noch nicht gelöst: Eskalations-Notiz + **Telegram-Alarm** (TODO: noch zu entwickeln)

## Ticket-Lifecycle

`neu` → `in Arbeit` (bei Start Execute-Phase) → `geschlossen` (erfolgreich) ODER `eskaliert` (beide Zyklen gescheitert) ODER `pausiert` (Reboot/Wartung erkannt)

**Znuny Custom States (müssen in Znuny Admin → Tickets → States manuell angelegt werden!):**
- `in Arbeit` — Typ: open
- `geschlossen` — Typ: closed
- `eskaliert` — Typ: pending reminder
- `pausiert` — Typ: pending reminder

**Reboot-Detection**: Regex in `Parse Execute Result` und `Parse Execute Result 2`:
- Pattern: `/\breboot\b|\bshutdown\b|\bpct reboot\b|\bsystemctl reboot\b/i`
- IF reboot_pending → Status `pausiert` + Notiz → Workflow endet (kein Verify)
- Pausiert-Check (täglich 08:00) reaktiviert ggf. in `in Arbeit`

## Znuny API

- **Webservice-Name**: `GenericTicketConnectorREST` (nicht ZnunyRestAPI!)
- **URL-Muster**: `https://10.1.1.182/znuny/nph-genericinterface.pl/Webservice/GenericTicketConnectorREST/<Operation>`
- **Direkter DB-Zugang**: `mysql -uznuny '-p15hx34DreMsb2VhYWgDa' znuny` (auf LXC 118)
- **State-ID**: `closed successful` = ID 2
- **Wichtig**: Externe HTTPS-Verbindung von außen (10.1.1.182) zeitweise instabil → lieber via DB oder n8n-Workflow

## SUB: Workflows (vollständige Liste mit Live-IDs)

| Name | Live-ID | Datei | Funktion |
|------|---------|-------|----------|
| SUB: Znuny Ticket Reader | `LpMuYNBncZNbIoZo` | sub-znuny-ticket-reader.json | Ticket aus Znuny lesen |
| SUB: Znuny Ticket Closer | `LELSswgLWlmtIais` | sub-znuny-ticket-closer.json | Ticket schließen |
| SUB: Znuny Note Adder | `0k5NM7V2p1dkvMSG` | sub-znuny-note-adder.json | Notiz hinzufügen |
| SUB: Claude AI Executor | `l4ee6BahShsiEXjI` | sub-claude-executor.json | Claude-Aufruf (RCA/Guide/Execute/Verify) |
| SUB: BookStack Reporter | `ugPeuIa1KJXX9xqC` | sub-bookstack-reporter.json | Incident-Bericht in BookStack |
| SUB: Notification Dispatcher | `TmyAkITcb41Ti3Ev` | sub-notification.json | Matrix/Telegram-Benachrichtigungen |
| SUB: NetBox Loader | `Sp6DiNXwi5pfRjA7` | sub-netbox-loader.json | NetBox-Inventar-Abfrage |
| SUB: System Health Check | (name-basiert) | sub-health-check.json | Health-Check per Claude |
| SUB: System Log Analyser | (name-basiert) | sub-log-analyser.json | Log-Analyse per Claude |
| SUB: Report Generator | (name-basiert) | sub-report-generator.json | Zusammenfassung erstellen |
| SUB: Safety Check | (name-basiert) | sub-safety-check.json | Befehle vor Ausführung validieren |
| SUB: SSH Command Executor | (name-basiert) | sub-ssh-executor.json | SSH-Befehl ausführen |
| SUB: System Update Executor | (name-basiert) | sub-update-executor.json | System-Update via Claude |
| SUB: Znuny Status Updater | `Ly3pTphrckI23Bda` | sub-znuny-status-updater.json | Reiner Statuswechsel ohne Notiz |
| SUB: Znuny Ticket Search | `XtpJW0B4twnclvtk` | sub-znuny-ticket-search.json | Tickets nach Status suchen |
| SUB: Znuny Ticket Creator | `NMxFaLwPpq39MSCF` | sub-znuny-ticket-creator.json | Neues Znuny-Ticket erstellen |

## MASTER: Pausiert-Check Workflow

- **Datei**: `master/master-pausiert-check.json`
- **Live-ID**: `ieZs0tmJO0Z5kVHo`
- **Status**: Aktiv, deployed
- **Nodes**: 20
- **Trigger**: Cron täglich 08:00 + Manual Trigger
- **Ablauf**: Suche alle `pausiert`-Tickets → SSH-Health-Check via Claude → wenn RESUME + Confidence≥70 → Status `in Arbeit` + Notiz + Webhook-Retrigger
- **Webhook-Retrigger**: POST `http://10.1.1.180:80/webhook/znuny-new-ticket` mit `{ ticket_id: X }`
- **Referenzierte Live-IDs**: Ticket Reader (`LpMuYNBncZNbIoZo`), Claude Executor (`l4ee6BahShsiEXjI`), Note Adder (`0k5NM7V2p1dkvMSG`), Ticket Search (name-basiert: "SUB: Znuny Ticket Search")

## lib-* Workflows (VERALTET)

Nur noch in 2 INAKTIVEN Workflows genutzt:
- `strbRBJXLZww36or` — Alter Incident Response Master (INACTIVE)
- `wSGRDgZuFG2RedeP` — Infrastructure Update Scheduler (INACTIVE)

**Empfehlung**: lib-* Workflows können nach Löschen der inaktiven MASTERs deaktiviert/gelöscht werden

## n8n Concurrency

`N8N_CONCURRENCY_PRODUCTION_LIMIT=5` (max 5 gleichzeitige MASTER-Instances)
Vorsicht: 5 parallele MASTERs → ~50 Znuny-API-Calls → LXC 118 Last-Peak bis 4.3 → Zabbix-Alarm-Loop

## MASTER: Log Analyser Workflow

- **Datei**: `master/master-log-analyser.json`
- **Live-ID**: `pPJ4lVht3s3I0816`
- **Status**: Aktiv, deployed (2026-03-23)
- **Nodes**: 23
- **Trigger**: Cron `0 2 * * 0` (Sonntag 02:00) + Manual Trigger
- **Ablauf**:
  - **Phase 1**: NetBox Devices (mit IP) → SSH via Claude Code (10.1.1.105:3001) → Log-Analyse → Znuny Ticket erstellen
  - **Phase 2**: NetBox LXC+VM (außer `n8n`/`claude`) → SSH via Claude Code → Log-Analyse → Znuny Ticket erstellen
  - **Abschluss**: Aggregate + Matrix-Notification
- **Tickets**: Queue `Raw`, State `neu`, Priority basierend auf max. Severity (CRITICAL=1, ERROR=2, WARNING=3)
- **executionTimeout**: 3600s
- **Ausschluss**: LXC 105 (claude), LXC 117 (n8n) via `exclude_names: ['n8n','claude']`

## Offene Aufgaben

1. **Ticket #16 manuell lösen**: Disk-Bereinigung Werkstatt LXC 126 (10.1.1.203)
2. **lib-* Workflows aufräumen**: Inaktive MASTERs löschen, dann lib-* Workflows deaktivieren/löschen
3. **SUB: Telegram Escalation entwickeln**: Neuer SUB-Workflow für Eskalations-Alarm (noch nicht implementiert)
4. ~~**Znuny Custom States anlegen**~~ — ERLEDIGT (2026-03-23): `in Arbeit`, `geschlossen`, `eskaliert`, `pausiert`
5. ~~**Neue Workflows in n8n importieren**~~ — ERLEDIGT (2026-03-23): IDs `XtpJW0B4twnclvtk`, `Ly3pTphrckI23Bda`, `ieZs0tmJO0Z5kVHo`
6. ~~**master-incident-response.json re-importieren**~~ — ERLEDIGT (2026-03-23): 62 Nodes, aktiv
7. ~~**MASTER: Log Analyser + SUB: Znuny Ticket Creator deployen**~~ — ERLEDIGT (2026-03-23): IDs `pPJ4lVht3s3I0816`, `NMxFaLwPpq39MSCF`

## MASTER: GitHub Management Workflow

- **Datei**: `master/master-github-management.json`
- **Live-ID**: `SZC3eAyFeRxAnApg`
- **Status**: Aktiv, deployed (2026-03-28)
- **Nodes**: 28
- **Webhook**: `https://n8n.doehlercomputing.de/webhook/github-events` (POST, IPv6)
- **Events**: issues/opened, pull_request/merged+opened, issue_comment/created
- **Flows**: Issue-Klassifizierung → Labels+Comment | PR Merge → CHANGELOG+Release | PR Opened → Review | Comment → Reply
- **SUB: GitHub API Executor**: ID `X21mf2hTEAz3r2XH`

### Ausstehende Konfiguration
- `GITHUB_TOKEN` + `GITHUB_WEBHOOK_SECRET` in `/etc/systemd/system/n8n.service.d/override.conf` auf LXC 117 setzen
- GitHub Webhook unter `https://n8n.doehlercomputing.de/webhook/github-events` anlegen
