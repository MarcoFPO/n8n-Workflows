---
name: n8n MASTER Workflows - Vollständige Übersicht
description: Alle MASTER-Workflows mit ID, Trigger, Ablauf und Status (Stand 2026-03-30)
type: project
---

## MASTER: Incident Response
- **ID**: `EcSZAPiPhhekDwXd`
- **Trigger**: Webhook `POST /webhook/znuny-new-ticket`
- **Nodes**: 73
- **Ablauf**: Webhook → Znuny Reader → NetBox → **🛡️ IF: n8n Self-Host?** → 2-Zyklus (RCA→Guide→Execute→Verify) → Ticket schließen + BookStack Störungsbericht
- **Reboot-Detection**: Status `pausiert` wenn reboot erkannt
- **n8n Self-Host Guard (2026-03-29)**: IF-Node nach Initialize Context – wenn system_ip=10.1.1.180, sofortiger Exit mit Note (verhindert OOM durch n8n-eigene Logs + Self-Restart-Loop)
- **_skip in Build Execute Prompt**: `_skip: true` wenn system_ip=10.1.1.180 (redundante Schutzebene)

## MASTER: Pausiert Check
- **ID**: `ieZs0tmJO0Z5kVHo`
- **Trigger**: Cron `0 8 * * *` (täglich 08:00) + Manual
- **Nodes**: 20
- **Ablauf**: Alle `pausiert`-Tickets suchen → SSH-Health-Check via Claude → wenn RESUME + Confidence≥70 → Status `in Arbeit` + Webhook-Retrigger

## MASTER: Log Analyser
- **ID**: `pPJ4lVht3s3I0816`
- **Trigger**: Cron `0 2 * * 0` (Sonntag 02:00) + Manual
- **Nodes**: 23
- **Ablauf**: Phase 1 NetBox-Devices (mit IP) + Phase 2 LXC/VMs (außer n8n/claude) → SSH-Log-Analyse via Claude → Znuny Ticket → Matrix-Notification
- **Ticket-Prio**: CRITICAL=1, ERROR=2, WARNING=3

## MASTER: GitHub Management
- **ID**: `SZC3eAyFeRxAnApg`
- **Trigger**: Webhook `https://n8n.doehlercomputing.de/webhook/github-events`
- **Nodes**: 28
- **Events**: issues/opened → Labels+Comment | PR merged → CHANGELOG+Release | PR opened → Review | Comment → Reply
- **SUB**: GitHub API Executor `X21mf2hTEAz3r2XH`

## MASTER: Update Management
- **ID**: `G0ZjR26Ow8FQ9p6D`
- **Trigger**: Cron `0 2 * * 5` (Freitag 02:00) + Manual
- **Nodes**: 27
- **Ablauf**: NetBox Loader → Loop über alle Systeme → OS-Update via Claude → Reboot-Check → App-Update → bei Fehler Znuny-Ticket → Report + BookStack + Matrix
- **Ausgeschlossen**: IPs `10.1.1.100, 10.1.1.105, 10.1.1.180` + Namen `n8n, claude`
- **Reboot**: `reboot_handling: auto`, 90s Wartezeit
- **Letzte Execution**: noch keine (noch nie gelaufen)

## MASTER: Auto-Ticket-Processor
- **ID**: `U9IJAwuzasHVscgY`
- **Trigger**: Cron `*/30 * * * *` (alle 30 Min) + Manual
- **Nodes**: 12
- **Ablauf**: TicketSearch (state=new, älter als 5 Min, max 20) → max 2 älteste → splitInBatches:1 → Webhook-Trigger je Ticket
- **Datei**: `master/master-auto-ticket-processor.json`
- **Hinweis**: `TicketCreateTimeOlderDate` sendet UTC-Zeit an Znuny — funktioniert wenn Znuny in UTC läuft

## ~~MASTER: System Analyser~~ — GELÖSCHT (2026-03-29)
- Veraltet, am 2026-03-29 aus n8n gelöscht (ID war `ArruwHMyY6eCXbeE`)
- Datei `master/master-analyser.json` aus Git entfernt
