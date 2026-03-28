# Quick Reference: Zabbix-osTicket Integration

## Schnelle Übersicht

### Die 4 Kernattribute

| Attribut | Wert | Zabbix-Quelle | osTicket-Ziel |
|----------|------|---------------|---------------|
| **WER** | Wer/Was löst den Alarm aus | `user`, `host_name` | `name` (Requester) |
| **WANN** | Zeitpunkt des Alarms | `event_time` | `created` (Ticket-Zeit) |
| **WAS** | Was ist das Problem | `trigger_name`, `trigger_description` | `subject`, `message` |
| **EVENTNUMMER** | Eindeutige Event-ID | `event_id` | Custom Field `zabbix_event_id` |

---

## Workflow-Fluss

```
┌─────────────────┐
│ Zabbix Trigger  │
│   (Alarm)       │
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│   Webhook POST   │
│ /api/v1/zabbix/  │
│     alerts       │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│ Daten transformieren     │
│ - Zeit-Format ändern     │
│ - Severity mappen        │
│ - Body generieren        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  osTicket API Call       │
│  POST /api/tickets.json  │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────┐
│ Neues Ticket in  │
│   osTicket       │
└──────────────────┘
```

---

## JSON-Struktur

### Request (Von Zabbix an Webhook)

```json
{
  "event_id": "12345678",        // EVENTNUMMER
  "event_time": "2025-10-26 14:32:15",  // WANN
  "trigger_name": "High CPU",    // WAS
  "trigger_severity": "High",    // Severity Level
  "trigger_description": "CPU > 90%",
  "host_name": "server-01",      // WAS (Host)
  "host_ip": "192.168.1.100",
  "item_name": "CPU utilization",
  "item_value": "95%",
  "trigger_url": "https://zabbix.../...",
  "event_tags": "service:web",
  "user": "zabbix-automation"    // WER
}
```

### Response (Vom Webhook an osTicket)

```json
{
  "name": "zabbix-automation (server-01)",        // WER
  "email": "zabbix@example.com",
  "subject": "[Zabbix] High CPU",                 // WAS
  "message": "HTML-formatierte Nachricht",         // WAS + Details
  "priority": 3,                                   // Basierend auf Severity
  "topicId": 1,
  "ip": "192.168.1.100",
  "zabbix_event_id": "12345678",                 // EVENTNUMMER
  "zabbix_trigger_id": "13926",
  "zabbix_event_time": "2025-10-26T14:32:15Z"   // WANN
}
```

---

## Severity → Priority Mapping

| Zabbix Severity | osTicket Priority | Beschreibung |
|-----------------|-------------------|--------------|
| Disaster | Emergency (4) | Sofortige Eskalation nötig |
| High | High (3) | Wichtig, zeitnah bearbeiten |
| Average | Medium (2) | Normale Priorität |
| Warning | Low (1) | Niedrige Priorität |
| Information | Low (1) | Informativ |
| Not classified | Normal (2) | Standard |

---

## Daten-Transformationen

### 1. Zeit-Format
```
Eingabe:  "2025-10-26 14:32:15"
Ausgabe:  "2025-10-26T14:32:15Z"
```

### 2. Requester-Name
```
Eingabe:  user="zabbix-automation", host_name="server-01"
Ausgabe:  "zabbix-automation (server-01)"
```

### 3. Ticket-Betreff
```
Eingabe:  trigger_name="High CPU usage"
Ausgabe:  "[Zabbix] High CPU usage"
```

### 4. Ticket-Body Template
```
Zabbix Alert Details
====================

Problem: {trigger_name}
Status: {trigger_status}
Severity: {trigger_severity}

Host Information:
- Hostname: {host_name}
- IP Address: {host_ip}

Event Details:
- Event ID: {event_id}
- Event Time: {event_time}
- Item: {item_name}
- Current Value: {item_value}

Description:
{trigger_description}

View in Zabbix: {trigger_url}

Tags: {event_tags}
```

---

## Implementierungs-Schritte (Kurzform)

### Phase 1: Zabbix Konfiguration
1. Neue Media Type "osTicket Webhook" anlegen
2. Action für Trigger-Events erstellen
3. Webhook URL und API-Key konfigurieren

### Phase 2: Webhook-Service
1. Webhook-Endpunkt `POST /api/v1/zabbix/alerts` implementieren
2. JSON-Validierung (Pflichtfelder prüfen)
3. Daten-Transformation (Zeit, Severity)
4. osTicket API aufrufen

### Phase 3: osTicket Integration
1. API-Key generieren
2. Custom Fields anlegen (`zabbix_event_id`, etc.)
3. Topic/Kategorie für Zabbix-Alerts konfigurieren

### Phase 4: Testing & Monitoring
1. Test-Payload senden (cURL)
2. Logs prüfen
3. Metriken überwachen (Success Rate, Latenz)

---

## Fehlerbehandlung (Kurz)

| Fehler | Handling |
|--------|----------|
| Ungültiges JSON | 400 - Fehler zurück, kein Retry |
| Fehlende Felder | 400 - Fehler zurück, kein Retry |
| osTicket offline | 502 - Retry 3x mit Backoff |
| Auth Error osTicket | 401 - Fehler, kein Retry |
| Rate Limit | 429 - Retry mit Backoff |

---

## Test-Befehl

```bash
curl -X POST http://localhost:8080/api/v1/zabbix/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "event_id": "99999999",
    "event_time": "2025-10-26 14:32:15",
    "trigger_name": "Test Alert",
    "trigger_severity": "High",
    "trigger_description": "This is a test alert",
    "host_name": "test-server",
    "host_ip": "192.168.1.99",
    "item_name": "Test Item",
    "item_value": "99",
    "trigger_url": "https://zabbix.example.com",
    "event_tags": "test",
    "user": "test-user"
  }'
```

---

## Monitoring-Metriken

- **Request Rate:** Requests/Min (Target: Normal-Level)
- **Success Rate:** % erfolgreiche Ticket-Erstellungen (Target: >99%)
- **Latenz P95:** Response-Zeit (Target: <2s)
- **Error Rate:** % Fehler (Target: <1%)

---

## Wichtige Dateien

- **LLD-Dokument:** `/docs/LLD-Zabbix-osTicket-Integration.md`
- **Workflow-Definition:** `/workflows/rBbxkgNzArvmkpBE-zabbix-alert-to-osticket.json`
- **Implementierungs-Skripte:** `/scripts/` (noch zu erstellen)

---

## Kontakt & Support

Bei Fragen zum Design oder zur Implementierung bitte im Projekt-Wiki nachschlagen oder mit dem DevOps-Team Rücksprache halten.

---

**Dokument Version:** 1.0
**Datum:** 2025-10-26
**Status:** Entwurf - Bereit für Review
