# Zabbix → osTicket → AI Integration

## Übersicht

Die Integration verbindet Zabbix-Monitoring mit osTicket für automatisches Ticket-Management und AI-gestützter Problemlösung.

## Workflow-Architektur

### 1. Zabbix Problems Monitor (Hauptworkflow)
- **ID**: fD6G3VprEXpWUALk
- **Funktion**: Überwacht Zabbix auf neue Probleme alle 5 Minuten
- **Erweiterung**: Ruft jetzt osTicket-Integration auf

### 2. Zabbix Sub-6: osTicket Integration
- **ID**: osticket-integration
- **Funktion**: Erstellt automatisch Tickets in osTicket
- **Account**: n8n@doehlercomputing.de
- **API**: http://10.1.1.182/api/tickets.json

### 3. Zabbix Sub-7: AI Ticket Handler
- **ID**: ai-ticket-handler
- **Funktion**:
  - Analysiert Tickets mit Claude AI
  - Erstellt Diagnoseplan
  - Führt bei Bedarf Device-Zugriffe durch
  - Dokumentiert Lösungen im Ticket

## Installation

### Schritt 1: API Credentials konfigurieren

**osTicket API Key**: `283044493a2dd53d43b8b454a64bbc53`

In n8n Web-UI (http://10.1.1.180:5678):

1. Gehe zu **Settings → Credentials**
2. Klicke **Add Credential**
3. Wähle **HTTP Header Auth**
4. Name: `osTicket API`
5. Header Name: `X-API-Key`
6. Header Value: `283044493a2dd53d43b8b454a64bbc53`
7. **Save**

### Schritt 2: Workflows aktivieren

1. **Zabbix Sub-6: osTicket Integration**
   - Öffne Workflow in n8n
   - Node "Create osTicket" öffnen
   - Bei Authentication: "osTicket API" Credential auswählen
   - Workflow **Save** und **Activate**

2. **Zabbix Sub-7: AI Ticket Handler**
   - Öffne Workflow in n8n
   - Stelle sicher, dass Claude API konfiguriert ist
   - Bei den HTTP Request Nodes: osTicket API auswählen
   - Workflow **Save** und **Activate**

### Schritt 3: Hauptworkflow erweitern

Im Workflow "Zabbix Problems Monitor" (fD6G3VprEXpWUALk):

1. Nach dem Node "Root Cause Analyse" einen neuen **Execute Workflow** Node hinzufügen
2. Workflow auswählen: `Zabbix Sub-6: osTicket Integration`
3. Input-Daten mappen:
   ```json
   {
     "problem_name": "{{ $json.problem_name }}",
     "host_name": "{{ $json.host }}",
     "problem_description": "{{ $json.description }}",
     "severity": "{{ $json.severity }}",
     "event_time": "{{ $json.clock }}",
     "root_cause": "{{ $('Root Cause Analyse').item.json.analysis }}"
   }
   ```

4. Danach einen weiteren **Execute Workflow** Node:
5. Workflow: `Zabbix Sub-7: AI Ticket Handler`
6. Input: `{ "ticket_id": "{{ $json.ticket_number }}" }`

## Workflow-Ablauf

```
[Zabbix Alert]
    ↓
[Root Cause Analyse] (Sub-2)
    ↓
[osTicket Integration] (Sub-6)
    → Erstellt Ticket mit n8n Account
    → Ticket enthält: Problem + Root Cause
    ↓
[AI Ticket Handler] (Sub-7)
    → AI analysiert das Problem
    → Erstellt Diagnoseplan
    ↓
[Device Access benötigt?]
    ├─ JA → SSH/API Zugriff auf Device
    │        → Sammelt Diagnosedaten
    │        → AI wertet Daten aus
    │        → Erstellt Lösung
    └─ NEIN → AI erstellt direkt Lösung
    ↓
[Ticket Update]
    → Lösung wird ins Ticket geschrieben
    → Ticket bleibt offen für Review
```

## Ticket-Struktur

### Automatisch erstellte Tickets

**Von**: n8n Automation (n8n@doehlercomputing.de)

**Betreff**: [Zabbix Alert] {Problem Name}

**Inhalt**:
```
Host: server-name
Problem: Problem description
Severity: High/Average/Warning
Time: 2025-10-24 20:00:00

Root Cause Analysis:
[Analyse aus Zabbix Sub-2]
```

### AI-generierte Updates

**Von**: AI Ticket Handler

**Inhalt**:
```
=== Problem-Analyse ===
[Detaillierte Analyse]

=== Diagnose-Ergebnisse ===
[Falls Device-Zugriff erfolgt]

=== Lösungsvorschlag ===
1. Schritt 1
2. Schritt 2
3. Schritt 3

=== Status ===
[Wartend auf Review / Gelöst / Eskalation nötig]
```

## Device-Zugriff

Die AI kann auf folgende Geräte zugreifen:

### Verfügbare Aktionen:
- **Netzwerk-Devices**: Status-Checks, Config-Review
- **Server**: Service-Status, Logs, Ressourcen
- **Zabbix**: Historische Daten, Trends

### Sicherheit:
- Zugriffe werden geloggt
- Nur lesende Operationen (außer explizit freigegeben)
- Alle Aktionen werden im Ticket dokumentiert

## Mail-Benachrichtigungen

Tickets werden an folgende Adressen gesendet:
- mdoehler@doehlercomputing.de (Admin)
- Zugewiesene Techniker

osTicket-Regeln:
- High Priority → Sofort-Benachrichtigung
- Average → Standard-Queue
- Low → Info-Queue

## Monitoring

### n8n Workflow-Executions

Prüfe Workflow-Ausführungen:
```bash
ssh root@10.1.1.100 "pct exec 117 -- n8n list:executions"
```

### osTicket Queue

Check Ticket-Status:
- Web: http://10.1.1.182/scp/tickets.php
- API: `curl -H "X-API-Key: 283044493a2dd53d43b8b454a64bbc53" http://10.1.1.182/api/tickets.json`

### Logs

```bash
# n8n Logs
ssh root@10.1.1.100 "pct exec 117 -- journalctl -u n8n -f"

# osTicket Logs
ssh root@10.1.1.100 "pct exec 118 -- tail -f /var/log/apache2/osticket_error.log"
```

## Troubleshooting

### Tickets werden nicht erstellt

1. **API Key prüfen**:
   ```bash
   ssh root@10.1.1.100 "pct exec 118 -- mysql osticket -e 'SELECT * FROM ost_api_key;'"
   ```

2. **n8n Credentials prüfen**:
   - n8n UI → Settings → Credentials
   - osTicket API Key muss konfiguriert sein

3. **Workflow-Logs**:
   ```bash
   ssh root@10.1.1.100 "pct exec 117 -- n8n list:executions --status=error"
   ```

### AI antwortet nicht

1. **Claude API Key prüfen**:
   - n8n UI → Settings → Credentials
   - Anthropic API muss konfiguriert sein

2. **API-Limits**:
   - Prüfe Anthropic Dashboard auf Rate Limits

### Device-Zugriff fehlgeschlagen

1. **Netzwerk-Konnektivität**:
   ```bash
   ssh root@10.1.1.100 "pct exec 117 -- ping 10.1.1.XXX"
   ```

2. **SSH-Keys**:
   - n8n Server muss SSH-Keys für Geräte haben

## Best Practices

### Ticket-Management

- **Nicht automatisch schließen**: Tickets bleiben offen für manuelles Review
- **Prioritäten nutzen**: AI setzt Priorität basierend auf Severity
- **Tags verwenden**: Zabbix-Alerts werden automatisch getaggt

### AI-Optimierung

- **Context**: Gib der AI relevante Infos (Netzwerk-Topologie, bekannte Issues)
- **Feedback**: Markiere gute/schlechte Lösungen für Training
- **Eskalation**: Komplexe Probleme manuell übernehmen

### Workflow-Wartung

- **Regelmäßige Updates**: Workflows anpassen basierend auf Erfahrungen
- **Monitoring**: Execution-Rate und Error-Rate überwachen
- **Backup**: Workflows regelmäßig exportieren

## Erweiterungen

### Geplante Features

1. **Automatische Ticket-Zuordnung** basierend auf Problem-Typ
2. **SLA-Tracking** mit Eskalation
3. **Knowledge Base Integration** für wiederkehrende Probleme
4. **Slack/Teams Notifications** für kritische Tickets
5. **Self-Healing** für bekannte Probleme

### Custom Workflows

Weitere Sub-Workflows erstellen für:
- Backup-Checks
- Capacity Planning
- Patch Management
- Change Management

## Kontakt

- **n8n Server**: http://10.1.1.180:5678
- **osTicket**: http://10.1.1.182/
- **Dokumentation**: /opt/Projekte/n8n/

---

**Erstellt**: 2025-10-24
**Version**: 1.0
**Status**: Ready for Testing
