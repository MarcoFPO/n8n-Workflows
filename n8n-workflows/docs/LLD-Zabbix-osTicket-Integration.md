# Low Level Design: Zabbix-to-osTicket Webhook Integration

**Version:** 1.0
**Datum:** 2025-10-26
**Status:** Entwurf

---

## 1. Übersicht

Diese Integration ermöglicht die automatische Erstellung von osTicket-Tickets bei Zabbix-Alarmen durch einen Webhook-Mechanismus.

**Datenfluss:**
```
Zabbix Trigger → Zabbix Webhook Action → Webhook-Endpunkt → osTicket API → Neues Ticket
```

---

## 2. Webhook-Schnittstelle

### 2.1 Endpunkt-Definition

**URL:** `POST https://<webhook-host>/api/v1/zabbix/alerts`

**Content-Type:** `application/json`

**Authentication:**
- API-Key im Header: `X-API-Key: <webhook-api-key>`
- Oder Basic Auth (zu definieren)

### 2.2 Request-Body JSON-Schema

```json
{
  "event_id": "12345678",
  "event_date": "2025-10-26",
  "event_time": "14:32:15",
  "event_timestamp": "1729952535",
  "event_status": "1",
  "event_severity": "High",
  "event_nseverity": "4",
  "event_age": "3600",
  "event_tags": "service:web,priority:high",

  "trigger_id": "13926",
  "trigger_name": "High CPU usage on webserver-01",
  "trigger_status": "PROBLEM",
  "trigger_description": "CPU usage exceeded 90% threshold",
  "trigger_url": "https://zabbix.example.com/tr_events.php?triggerid=13926&eventid=12345678",
  "trigger_priority": "4",
  "trigger_priority_name": "High",

  "host_id": "10001",
  "host_name": "webserver-01",
  "host_ip": "192.168.1.100",
  "host_dns": "web01.example.com",
  "host_description": "Production Web Server",

  "item_id": "23456",
  "item_name": "CPU utilization",
  "item_key": "system.cpu.load.avg(1m)",
  "item_value": "0.95",
  "item_units": "%",

  "user": "zabbix-automation"
}
```

**Zabbix-Makro zu JSON-Feld Mapping:**
- `{EVENT.ID}` → `event_id`
- `{EVENT.DATE}` → `event_date`
- `{EVENT.TIME}` → `event_time`
- `{EVENT.TIMESTAMP}` → `event_timestamp`
- `{EVENT.STATUS}` → `event_status`
- `{EVENT.SEVERITY}` → `event_severity`
- `{EVENT.NSEVERITY}` → `event_nseverity`
- `{EVENT.AGE}` → `event_age`
- `{EVENT.TAGS}` → `event_tags`
- `{TRIGGER.ID}` → `trigger_id`
- `{TRIGGER.NAME}` → `trigger_name`
- `{TRIGGER.STATUS}` → `trigger_status`
- `{TRIGGER.DESCRIPTION}` → `trigger_description`
- `{TRIGGER.URL}` → `trigger_url`
- `{TRIGGER.PRIORITY}` → `trigger_priority`
- `{TRIGGER.PRIORITY.NAME}` → `trigger_priority_name`
- `{HOST.ID}` → `host_id`
- `{HOST.NAME}` → `host_name`
- `{HOST.IP}` → `host_ip`
- `{HOST.DNS}` → `host_dns`
- `{HOST.DESCRIPTION}` → `host_description`
- `{ITEM.ID}` → `item_id`
- `{ITEM.NAME}` → `item_name`
- `{ITEM.KEY}` → `item_key`
- `{ITEM.VALUE}` → `item_value`
- `{ITEM.UNITS}` → `item_units`

**Pflichtfelder (Must-Have):**
- `event_id` - **EVENTNUMMER** (eindeutige Event-ID von Zabbix)
- `event_date` + `event_time` - **WANN** (Zeitpunkt des Alarms)
- `trigger_name` - **WAS** (Problem-Beschreibung)
- `host_name` - **WER** (betroffener Host/System)

**Empfohlene Felder (Should-Have):**
- `event_severity` / `event_nseverity` - Severity-Level für Priority-Mapping
- `trigger_description` - Detaillierte Problem-Beschreibung
- `host_ip` - IP-Adresse des Hosts
- `item_value` + `item_units` - Aktueller Messwert
- `trigger_url` - Link zurück zu Zabbix
- `event_tags` - Tags für Kategorisierung/Routing
- `trigger_priority_name` - Human-readable Priorität

### 2.3 Response-Schema

**Erfolg (HTTP 201):**
```json
{
  "status": "success",
  "ticket_id": "123456",
  "ticket_number": "OST-123456",
  "message": "Ticket created successfully",
  "zabbix_event_id": "12345678"
}
```

**Fehler (HTTP 4xx/5xx):**
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Missing required field: event_id",
  "details": {
    "field": "event_id",
    "reason": "Field is required but not provided"
  }
}
```

---

## 3. Attribute-Definitionen und Mapping

### 3.1 Anforderungs-Attribute (4 Kernattribute)

| Attribut | Bedeutung | Zabbix-Makro | JSON-Feld | Beispielwert |
|----------|-----------|--------------|-----------|--------------|
| **WER** | Wer/Was hat den Alarm ausgelöst | `{HOST.NAME}` | `host_name` | "webserver-01" |
| **WANN** | Zeitpunkt des Alarms | `{EVENT.DATE}` `{EVENT.TIME}` | `event_date`, `event_time` | "2025-10-26", "14:32:15" |
| **WAS** | Beschreibung des Problems | `{TRIGGER.NAME}` `{TRIGGER.DESCRIPTION}` | `trigger_name`, `trigger_description` | "High CPU usage on webserver-01" |
| **EVENTNUMMER** | Eindeutige Event-ID | `{EVENT.ID}` | `event_id` | "12345678" |

### 3.2 Mapping: Zabbix-Makro → JSON → osTicket

| Zabbix-Makro | JSON-Feld | osTicket-Feld | Transformation | Beispiel |
|--------------|-----------|---------------|----------------|----------|
| `{EVENT.ID}` | `event_id` | Custom Field: `zabbix_event_id` | Direkt | "12345678" |
| `{EVENT.DATE}` + `{EVENT.TIME}` | `event_date`, `event_time` | `created` | ISO 8601: `event_dateTevent_timeZ` | "2025-10-26T14:32:15Z" |
| `{HOST.NAME}` | `host_name` | `name` (Requester Name) | Direkt oder mit `{HOST.IP}` | "webserver-01" oder "webserver-01 (192.168.1.100)" |
| `{TRIGGER.NAME}` | `trigger_name` | `subject` (Ticket Subject) | Prefix: "[Zabbix] " + trigger_name | "[Zabbix] High CPU usage on webserver-01" |
| `{TRIGGER.DESCRIPTION}` | `trigger_description` | `message` (Ticket Body) | Template mit allen Details (siehe 3.3) | "CPU usage exceeded 90% threshold" |
| `{EVENT.SEVERITY}` oder `{EVENT.NSEVERITY}` | `event_severity`, `event_nseverity` | `priority` | Severity-Mapping (siehe 3.4) | "High" / "4" → Priority 3 |
| `{EVENT.TAGS}` | `event_tags` | `topic` oder Tags | Tag-Parsing für Kategorisierung | "service:web,priority:high" |
| `{TRIGGER.URL}` | `trigger_url` | Eingebettet in `message` | URL im Body als Link | "https://zabbix.../...?triggerid=13926" |
| `{HOST.IP}` | `host_ip` | Im Body | Kontextinformation | "192.168.1.100" |
| `{ITEM.NAME}` + `{ITEM.VALUE}` + `{ITEM.UNITS}` | `item_name`, `item_value`, `item_units` | Im Body | Messwert Darstellung | "CPU utilization = 0.95 %" |

### 3.3 Ticket-Body Template

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

### 3.6 Severity-Mapping

| Zabbix Severity | Zabbix NSEVERITY | osTicket Priority | Bedeutung |
|----------------|------------------|-------------------|-----------|
| Disaster | 5 | 4 | Emergency (Höchste) |
| High | 4 | 3 | High |
| Average | 3 | 2 | Medium |
| Warning | 2 | 1 | Low |
| Information | 1 | 1 | Low |
| Not classified | 0 | 2 | Normal |

### 3.5 osTicket Standard-Felder Mapping

Die Integration verwendet **NUR die 4 Standard-osTicket-Felder**. Keine Custom Fields notwendig!

| Zabbix Attribut | osTicket-Feld | Datentyp | Länge | Zabbix-Quelle | Format |
|-----------------|---------------|----------|-------|---------------|--------|
| **WER** | `name` (Requester Name) | Text | 20 | `{HOST.NAME}` | Hostname (z.B. "webserver-01") |
| **WANN** | `date_created` | DateTime | - | `{EVENT.DATE}` `{EVENT.TIME}` | Deutsches Format: DD.MM.YYYY HH:MM:SS |
| **WAS** | `subject` | Text | 256 | `{EVENT.ID}` + `{TRIGGER.NAME}` | "EVENT_ID: 12345678\nHigh CPU usage..." |
| **Priorität** | `priority` | Integer | 1-4 | `{EVENT.SEVERITY}` | Severity-Mapping (siehe 3.6) |

**Hinweise:**
- **Keine Custom Fields notwendig** - alle Daten passen in Standard-Felder
- `name` ist limitiert auf 20 Zeichen (Hostname-Länge beachten!)
- `subject` (256 Zeichen) enthält: Event-ID (1. Zeile) + Trigger-Name (2. Zeile)
- `date_created` wird im osTicket-UI im lokalen Datumsformat angezeigt
- `priority` ist numerisch (1=Low, 2=Normal, 3=High, 4=Emergency)

---

## 4. osTicket API Integration

### 4.1 API-Endpunkt

**URL:** `POST https://<osticket-host>/api/tickets.json`

**Authentication:**
- Header: `X-API-Key: <osticket-api-key>`
- API-Key muss in osTicket unter Admin Panel → Manage → API Keys konfiguriert sein

### 4.2 Ticket-Create Request

```json
{
  "alert": true,
  "autorespond": true,
  "source": "API",
  "name": "webserver-01",
  "email": "zabbix@example.com",
  "subject": "EVENT_ID: 12345678\nHigh CPU usage on webserver-01",
  "message": "Zabbix Alert",
  "priority": 3
}
```

**Feld-Beschreibung:**

| Feld | Wert | Quelle | Beschreibung |
|------|------|--------|-------------|
| `name` | "webserver-01" | `{HOST.NAME}` | **WER** - Hostname (max. 20 Zeichen) |
| `subject` | "EVENT_ID: 12345678\nHigh CPU usage..." | `{EVENT.ID}` + `{TRIGGER.NAME}` | **WAS + EVENTNUMMER** - Event-ID (Zeile 1) + Trigger-Name (Zeile 2) |
| `priority` | 3 | `{EVENT.SEVERITY}` | **PRIORITÄT** - Severity-gemappt (1-4) |
| `email` | "zabbix@example.com" | Fest | System-User für Tickets von Zabbix |
| `message` | "Zabbix Alert" | Fest | Einfacher Nachrichtentext |
| `alert` | true | Fest | Alert-Flag für osTicket |
| `autorespond` | true | Fest | Auto-Response aktiviert |
| `source` | "API" | Fest | Zeigt API-Origin an |

**Hinweise:**
- **Keine Custom Fields** - alle Daten in Standard-Feldern
- `name` ist auf 20 Zeichen begrenzt (Hostname-Länge beachten!)
- `subject` enthält Zeilenumbruch (`\n`) nach Event-ID
- `priority` ist Integer 1-4 (Severity-Mapping)

### 4.3 osTicket Response

**Erfolg (HTTP 201):**
```json
{
  "ticket_id": 123456,
  "number": "OST-123456"
}
```

**Fehler:**
```json
{
  "error": "Error message description"
}
```

---

## 5. Transformations-Logik

### 5.1 Datum/Zeit-Konvertierung

**Input:** `"2025-10-26 14:32:15"` (Zabbix Format)
**Output:** `"2025-10-26T14:32:15Z"` (ISO 8601)

```python
from datetime import datetime

def convert_zabbix_time(zabbix_time: str) -> str:
    """Konvertiert Zabbix Timestamp zu ISO 8601"""
    dt = datetime.strptime(zabbix_time, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
```

### 5.2 Severity zu Priority Mapping

```python
SEVERITY_MAP = {
    "Disaster": 4,
    "High": 3,
    "Average": 2,
    "Warning": 1,
    "Information": 1,
    "Not classified": 2
}

def map_severity(severity: str) -> int:
    return SEVERITY_MAP.get(severity, 2)  # Default: Normal
```

### 5.3 Message-Body Generierung

```python
def generate_ticket_body(zabbix_data: dict) -> str:
    """Generiert HTML-formatierten Ticket-Body"""
    template = """
    <h2>Zabbix Alert Details</h2>
    <p><strong>Problem:</strong> {trigger_name}</p>
    <p><strong>Status:</strong> {trigger_status}</p>
    <p><strong>Severity:</strong> {trigger_severity}</p>

    <h3>Host Information</h3>
    <ul>
        <li>Hostname: {host_name}</li>
        <li>IP Address: {host_ip}</li>
    </ul>

    <h3>Event Details</h3>
    <ul>
        <li>Event ID: {event_id}</li>
        <li>Event Time: {event_time}</li>
        <li>Item: {item_name}</li>
        <li>Current Value: {item_value}</li>
    </ul>

    <p><strong>Description:</strong><br>{trigger_description}</p>

    <p><a href="{trigger_url}">View in Zabbix</a></p>

    <p><strong>Tags:</strong> {event_tags}</p>
    """

    body = template.format(**zabbix_data)
    return f"data:text/html,{body}"
```

---

## 6. Implementierungs-Workflow

```
1. Webhook empfängt POST Request
   ↓
2. Validiere JSON-Schema (Pflichtfelder prüfen)
   ↓
3. Extrahiere und transformiere Daten
   - Zeit-Konvertierung
   - Severity-Mapping
   - Body-Generierung
   ↓
4. Erstelle osTicket API Request
   ↓
5. Sende Request an osTicket
   ↓
6. Verarbeite Response
   ↓
7. Logge Transaktion
   ↓
8. Sende Response an Zabbix
```

---

## 7. Fehlerbehandlung

### 7.1 Fehler-Szenarien

| Fehler | HTTP Code | Action | Retry? |
|--------|-----------|--------|--------|
| Ungültiges JSON | 400 | Log + Error Response | Nein |
| Fehlende Pflichtfelder | 400 | Log + Error Response mit Details | Nein |
| osTicket API nicht erreichbar | 502 | Log + Retry | Ja (3x) |
| osTicket Authentication Error | 401 | Log + Alert Admin | Nein |
| osTicket Rate Limit | 429 | Warte + Retry | Ja (mit Backoff) |
| Unbekannter Fehler | 500 | Log + Generic Error | Nein |

### 7.2 Retry-Logik

```python
import time
from typing import Optional

def create_ticket_with_retry(
    ticket_data: dict,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Optional[dict]:
    """
    Erstellt Ticket mit Retry-Logik
    """
    for attempt in range(max_retries):
        try:
            response = osticket_api.create_ticket(ticket_data)
            return response
        except OSTicketConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                time.sleep(wait_time)
                continue
            raise
        except OSTicketAuthError:
            # Keine Retries bei Auth-Fehlern
            raise

    return None
```

---

## 8. Logging und Audit-Trail

### 8.1 Log-Struktur

Jede Transaktion wird mit folgenden Informationen geloggt:

```json
{
  "timestamp": "2025-10-26T14:32:16Z",
  "transaction_id": "uuid-v4",
  "event_type": "zabbix_webhook_received",
  "zabbix_event_id": "12345678",
  "status": "success|error",
  "request": {
    "source_ip": "192.168.1.50",
    "headers": {"X-API-Key": "***"},
    "body_size": 1024
  },
  "processing": {
    "duration_ms": 245,
    "transformations_applied": ["time_conversion", "severity_mapping"],
    "validation_passed": true
  },
  "osticket": {
    "api_call_duration_ms": 180,
    "ticket_id": "123456",
    "ticket_number": "OST-123456",
    "response_code": 201
  },
  "error": null
}
```

### 8.2 Log-Level

- **DEBUG:** Detaillierte Request/Response Daten
- **INFO:** Erfolgreiche Ticket-Erstellungen
- **WARNING:** Retries, Rate Limits
- **ERROR:** Fehlgeschlagene Requests, Validierungsfehler
- **CRITICAL:** osTicket API dauerhaft nicht erreichbar

### 8.3 Persistierung

- Logs in strukturiertem Format (JSON Lines)
- Rotation: Täglich, Aufbewahrung: 90 Tage
- Optional: Zusätzliche Persistierung in Datenbank für Audit-Zwecke

**Datenbank-Schema (optional):**
```sql
CREATE TABLE webhook_audit_log (
    id BIGSERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL,
    zabbix_event_id VARCHAR(50) NOT NULL,
    osticket_ticket_id VARCHAR(50),
    osticket_ticket_number VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    request_json JSONB,
    response_json JSONB,
    error_message TEXT,
    processing_duration_ms INTEGER,
    INDEX idx_zabbix_event_id (zabbix_event_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
);
```

---

## 9. Konfiguration

### 9.1 Umgebungsvariablen

```bash
# Webhook Server
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8080
WEBHOOK_API_KEY=<generated-secret>

# osTicket API
OSTICKET_URL=https://osticket.example.com
OSTICKET_API_KEY=<osticket-api-key>
OSTICKET_DEFAULT_TOPIC_ID=1
OSTICKET_DEFAULT_EMAIL=zabbix@example.com

# Retry Configuration
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/zabbix-webhook/webhook.log
LOG_RETENTION_DAYS=90
```

### 9.2 Zabbix Webhook Action Konfiguration

**Media Type: Webhook**

**Name:** osTicket Integration

**Script Parameters (in dieser Reihenfolge):**

Minimal (4 Parameter - Pflichtfelder):
1. `{EVENT.ID}`
2. `{EVENT.DATE}`
3. `{EVENT.TIME}`
4. `{TRIGGER.NAME}`

Empfohlen (14 Parameter):
1. `{EVENT.ID}`
2. `{EVENT.DATE}`
3. `{EVENT.TIME}`
4. `{EVENT.TIMESTAMP}`
5. `{EVENT.STATUS}`
6. `{EVENT.SEVERITY}`
7. `{EVENT.NSEVERITY}`
8. `{EVENT.AGE}`
9. `{EVENT.TAGS}`
10. `{TRIGGER.ID}`
11. `{TRIGGER.NAME}`
12. `{TRIGGER.STATUS}`
13. `{TRIGGER.DESCRIPTION}`
14. `{TRIGGER.URL}`
15. `{TRIGGER.PRIORITY}`
16. `{TRIGGER.PRIORITY.NAME}`
17. `{HOST.ID}`
18. `{HOST.NAME}`
19. `{HOST.IP}`
20. `{HOST.DNS}`
21. `{ITEM.NAME}`
22. `{ITEM.VALUE}`
23. `{ITEM.UNITS}`

**JavaScript Webhook Script:**
```javascript
var params = JSON.parse(value);

var request = new HttpRequest();
request.addHeader('Content-Type: application/json');
request.addHeader('X-API-Key: <webhook-api-key>');

var payload = {
    // Event Information
    event_id: params.event_id,                  // {EVENT.ID}
    event_date: params.event_date,              // {EVENT.DATE}
    event_time: params.event_time,              // {EVENT.TIME}
    event_timestamp: params.event_timestamp,    // {EVENT.TIMESTAMP}
    event_status: params.event_status,          // {EVENT.STATUS}
    event_severity: params.event_severity,      // {EVENT.SEVERITY}
    event_nseverity: params.event_nseverity,    // {EVENT.NSEVERITY}
    event_age: params.event_age,                // {EVENT.AGE}
    event_tags: params.event_tags,              // {EVENT.TAGS}

    // Trigger Information
    trigger_id: params.trigger_id,              // {TRIGGER.ID}
    trigger_name: params.trigger_name,          // {TRIGGER.NAME}
    trigger_status: params.trigger_status,      // {TRIGGER.STATUS}
    trigger_description: params.trigger_description,  // {TRIGGER.DESCRIPTION}
    trigger_url: params.trigger_url,            // {TRIGGER.URL}
    trigger_priority: params.trigger_priority,  // {TRIGGER.PRIORITY}
    trigger_priority_name: params.trigger_priority_name,  // {TRIGGER.PRIORITY.NAME}

    // Host Information
    host_id: params.host_id,                    // {HOST.ID}
    host_name: params.host_name,                // {HOST.NAME}
    host_ip: params.host_ip,                    // {HOST.IP}
    host_dns: params.host_dns,                  // {HOST.DNS}

    // Item Information
    item_name: params.item_name,                // {ITEM.NAME}
    item_value: params.item_value,              // {ITEM.VALUE}
    item_units: params.item_units,              // {ITEM.UNITS}

    // System
    user: 'zabbix-automation'
};

var response = request.post(
    'https://<webhook-host>/api/v1/zabbix/alerts',
    JSON.stringify(payload)
);

return response;
```

**Zabbix-Makro zu Parameter Mapping:**
| Zabbix-Makro | Param-Name | JSON-Feld |
|--------------|-----------|-----------|
| `{EVENT.ID}` | param[0] | `event_id` |
| `{EVENT.DATE}` | param[1] | `event_date` |
| `{EVENT.TIME}` | param[2] | `event_time` |
| `{EVENT.TIMESTAMP}` | param[3] | `event_timestamp` |
| `{EVENT.STATUS}` | param[4] | `event_status` |
| `{EVENT.SEVERITY}` | param[5] | `event_severity` |
| `{EVENT.NSEVERITY}` | param[6] | `event_nseverity` |
| `{EVENT.AGE}` | param[7] | `event_age` |
| `{EVENT.TAGS}` | param[8] | `event_tags` |
| `{TRIGGER.ID}` | param[9] | `trigger_id` |
| `{TRIGGER.NAME}` | param[10] | `trigger_name` |
| `{TRIGGER.STATUS}` | param[11] | `trigger_status` |
| `{TRIGGER.DESCRIPTION}` | param[12] | `trigger_description` |
| `{TRIGGER.URL}` | param[13] | `trigger_url` |
| `{TRIGGER.PRIORITY}` | param[14] | `trigger_priority` |
| `{TRIGGER.PRIORITY.NAME}` | param[15] | `trigger_priority_name` |
| `{HOST.ID}` | param[16] | `host_id` |
| `{HOST.NAME}` | param[17] | `host_name` |
| `{HOST.IP}` | param[18] | `host_ip` |
| `{HOST.DNS}` | param[19] | `host_dns` |
| `{ITEM.NAME}` | param[20] | `item_name` |
| `{ITEM.VALUE}` | param[21] | `item_value` |
| `{ITEM.UNITS}` | param[22] | `item_units` |

---

## 10. Testing

### 10.1 Unit Tests

**Test-Szenarien:**
1. Erfolgreiche Ticket-Erstellung mit allen Pflichtfeldern
2. Fehlerhafte Requests (fehlende Felder, ungültiges JSON)
3. Datum/Zeit-Konvertierung
4. Severity-Mapping
5. Body-Template-Generierung

### 10.2 Integration Tests

**Test-Szenarien:**
1. End-to-End: Zabbix Webhook → osTicket Ticket
2. osTicket API Connection Error → Retry-Logik
3. Rate Limiting → Backoff-Verhalten
4. Authentication Errors

### 10.3 Test-Payload (mit einheitlicher Syntax)

```json
{
  "event_id": "99999999",
  "event_date": "2025-10-26",
  "event_time": "14:32:15",
  "event_timestamp": "1729952535",
  "event_status": "1",
  "event_severity": "High",
  "event_nseverity": "4",
  "event_age": "3600",
  "event_tags": "service:test,priority:high,environment:staging",

  "trigger_id": "13926",
  "trigger_name": "High CPU usage on test-server-01",
  "trigger_status": "PROBLEM",
  "trigger_description": "CPU usage exceeded 90% threshold - TEST EVENT",
  "trigger_url": "https://zabbix.example.com/tr_events.php?triggerid=13926&eventid=99999999",
  "trigger_priority": "4",
  "trigger_priority_name": "High",

  "host_id": "10099",
  "host_name": "test-server-01",
  "host_ip": "192.168.1.99",
  "host_dns": "test01.example.com",
  "host_description": "Test Server",

  "item_id": "23499",
  "item_name": "CPU utilization",
  "item_key": "system.cpu.load.avg(1m)",
  "item_value": "0.95",
  "item_units": "%",

  "user": "test-automation"
}
```

**cURL Test-Befehl:**
```bash
curl -X POST https://<webhook-host>/api/v1/zabbix/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <webhook-api-key>" \
  -d @test-payload.json
```

---

## 11. Monitoring und Metriken

### 11.1 Zu überwachende Metriken

- **Request Rate:** Requests pro Minute
- **Success Rate:** Erfolgreiche vs. fehlgeschlagene Requests
- **Response Time:** P50, P95, P99 Latenz
- **osTicket API Latenz:** Separate Messung
- **Error Rate:** Nach Fehlertyp kategorisiert
- **Retry Rate:** Anzahl Retries pro Request

### 11.2 Alerts

- **Critical:** osTicket API > 5 Minuten nicht erreichbar
- **Warning:** Error Rate > 10% über 5 Minuten
- **Warning:** P95 Latenz > 2 Sekunden

---

## 12. Deployment-Checklist

### osTicket Setup
- [ ] osTicket API Key erstellt und konfiguriert
- [ ] Zabbix-Email-Adresse ("zabbix@example.com") in osTicket vorhanden oder als User angelegt
- [ ] Default Topic ID überprüft (Standard: 1)
- [ ] ⚠️ KEINE Custom Fields notwendig - nur Standard-Felder verwenden!

### Webhook Service Setup
- [ ] Webhook-Service implementiert (siehe IMPLEMENTATION_GUIDE)
- [ ] Webhook-Service deployt und erreichbar
- [ ] Umgebungsvariablen konfiguriert
- [ ] Logging-Verzeichnis erstellt und Permissions gesetzt
- [ ] SSL/HTTPS konfiguriert (falls erforderlich)
- [ ] Firewall-Regeln für osTicket API-Zugriff gesetzt

### Zabbix Setup
- [ ] Zabbix Media Type "osTicket Integration" angelegt
- [ ] 6 Script Parameters in korrekter Reihenfolge eingegeben:
  - [ ] 1. `{EVENT.ID}`
  - [ ] 2. `{EVENT.DATE}`
  - [ ] 3. `{EVENT.TIME}`
  - [ ] 4. `{EVENT.SEVERITY}`
  - [ ] 5. `{TRIGGER.NAME}`
  - [ ] 6. `{HOST.NAME}`
- [ ] Action für Trigger-Events konfiguriert

### Testing & Validierung
- [ ] Test-Webhook mit cURL ausgeführt
- [ ] Webhook-Response überprüft
- [ ] Test-Alarm in Zabbix ausgelöst
- [ ] Ticket in osTicket erstellt und verifiziert:
  - [ ] `name` (WER) = Hostname (max. 20 Zeichen)
  - [ ] `subject` (WAS) = "EVENT_ID: xxxx\nTrigger-Name"
  - [ ] `priority` (PRIORITÄT) = Severity-gemappt (1-4)
- [ ] Audit-Log überprüft

### Monitoring & Documentation
- [ ] Monitoring/Alerts konfiguriert
- [ ] Log-Rotation und Retention gesetzt
- [ ] Dokumentation aktualisiert
- [ ] Team-Training durchgeführt

---

## 13. Entscheidungen (RESOLVED)

✅ **RESOLVED - Alle Entscheidungen getroffen:**

1. **osTicket Felder - Phase 1 (AKTUELL):**
   - ✅ **4 Standard-Felder verwenden** - von Zabbix-Webhook gefüllt
   - ✅ `name` = Host-Name (max. 20 Zeichen)
   - ✅ `subject` = Event-ID + Trigger-Name mit Zeilenumbruch
   - ✅ `priority` = Severity-Mapping (1-4)
   - ✅ `date_created` = Deutsches Datumsformat (DD.MM.YYYY HH:MM:SS)

2. **osTicket Custom Fields - Phase 2 (ZUKÜNFTIG):**
   - ✅ **4 Custom Fields angelegt** - NICHT von aktueller Integration gefüllt
   - ✅ `root_ticket` (Link to Ticket) - für Parent-Zuordnung
   - ✅ `ursache` (Text, 256+) - Ursachenanalyse
   - ✅ `lösung` (Text, 256+) - Lösungsmaßnahme
   - ✅ `störungsende` (DateTime, deutsches Format) - Problem-Endzeitpunkt

3. **E-Mail für Requester:**
   - ✅ Fest "zabbix@example.com" (System-User)

4. **Webhook-Parameter (minimal):**
   - ✅ 6 Parameter: EVENT.ID, EVENT.DATE, EVENT.TIME, EVENT.SEVERITY, TRIGGER.NAME, HOST.NAME

5. **Ticket-Update bei Recovery:**
   - ✅ Phase 1: Nur CREATE
   - ⏳ Phase 2: UPDATE/CLOSE bei Recovery (zukünftig)

6. **Authentifizierung:**
   - ✅ API-Key primär
   - ⏳ IP-Whitelist optional in Phase 2

---

**Dokument Ende**
