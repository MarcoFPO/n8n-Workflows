# osTicket Fields Mapping - Zabbix Integration

**Datum:** 2025-10-26
**Zweck:** Definiert die Felder in osTicket für Zabbix-Tickets (aktuell + zukünftig)
**Zielgruppe:** osTicket Administratoren, Webhook-Service Entwickler

---

## Übersicht: Felder für Zabbix-Tickets

Die Zabbix-osTicket Integration nutzt aktuell **4 Standard-osTicket-Felder**.

Zusätzlich werden **4 Custom Fields** angelegt für zukünftige Nutzung (Phase 2):

### Phase 1 (AKTUELL): 4 Standard-Felder beim CREATE gefüllt

| Attribut | osTicket-Feld | Datentyp | Länge | Quelle | Format |
|----------|---------------|----------|-------|--------|--------|
| **WER** | `name` (Requester Name) | Text | 20 | `{HOST.NAME}` | Hostname |
| **WANN** | `date_created` (Erstellungsdatum) | DateTime | - | `{EVENT.DATE}` + `{EVENT.TIME}` | Deutsches Format: `DD.MM.YYYY HH:MM:SS` |
| **WAS** | `subject` (Ticket-Betreff) | Text | 256 | `{TRIGGER.NAME}` | "[Zabbix] {trigger_name}" |
| **Priorität** | `priority` (Dropdown/Zahl) | Integer | 1-4 | `{EVENT.SEVERITY}` | Severity-Mapping (siehe unten) |
| **EVENTNUMMER** | In `subject` (Zeile 1) | String | 50 | `{EVENT.ID}` | `EVENT_ID: 12345678` |

---

## Phase 2 (ZUKÜNFTIG): 4 Custom Fields - NICHT aktuell gefüllt

Diese 4 Custom Fields werden **jetzt angelegt**, aber **NICHT** von der aktuellen Zabbix-Integration gefüllt. Sie sind für zukünftige Phasen vorgesehen:

| Custom Field | Datentyp | Länge | Zweck | Befüllung |
|------------------|----------|-------|-------|-----------|
| `root_ticket` | Link/Verknüpfung | - | Verknüpfung zu Parent-Ticket bei zusammenhängenden Problemen | Manuell oder Phase 2+ |
| `ursache` | Text | 256+ | Ursachenanalyse des Problems | Manuell durch Support |
| `lösung` | Text | 256+ | Durchgeführte Lösung / Behebungsmaßnahme | Manuell oder via Recovery |
| `störungsende` | DateTime | - | Zeitstempel wenn Problem behoben (DD.MM.YYYY HH:MM:SS) | Manuell oder Phase 2+ |

**Wichtig:**
- Diese 4 Felder werden **NICHT** von der aktuellen Webhook-Integration gefüllt
- Sie sind für zukünftige Erweiterungen reserviert (Phase 2+)
- Sie müssen in osTicket angelegt werden (siehe Setup-Anleitung weiter unten)
- Die aktuelle Integration sendet diese Felder nicht im API-Request

---

## Detaillierte Feld-Spezifikation

### 1. WER - Requester Name (`name`)

```
Feld: name
Typ: Text / String
Länge: 20 Zeichen (MAXIMUM)
Quelle: {HOST.NAME}
Beispiel: "webserver-01"
```

**Mapping:**
```python
"name": zabbix_data["host_name"]  # z.B. "webserver-01"
```

---

### 2. WANN - Erstellungsdatum (`date_created`)

```
Feld: date_created
Typ: DateTime
Format: Deutsches Format mit Sekunden: DD.MM.YYYY HH:MM:SS
Quelle: {EVENT.DATE} {EVENT.TIME}
Beispiel: "26.10.2025 14:32:15"
```

**Mapping & Transformation:**
```python
# Input von Zabbix: "2025-10-26 14:32:15" (ISO Format)
# Output für osTicket: "26.10.2025 14:32:15" (Deutsches Format)

from datetime import datetime

def convert_to_german_datetime(zabbix_time: str) -> str:
    """
    Konvertiert Zabbix-Zeitstempel zu deutschem Format
    Input:  "2025-10-26 14:32:15"
    Output: "26.10.2025 14:32:15"
    """
    dt = datetime.strptime(zabbix_time, "%Y-%m-%d %H:%M:%S")
    return dt.strftime("%d.%m.%Y %H:%M:%S")

# Nutzung
"date_created": convert_to_german_datetime(f"{event_date} {event_time}")
```

---

### 3. WAS - Problembeschreibung (`subject`)

```
Feld: subject
Typ: Text / String
Länge: 256 Zeichen (MAXIMUM)
Format: "{EVENT_ID}
{TRIGGER_NAME}"
Beispiel: "EVENT_ID: 12345678
High CPU usage on webserver-01"
```

**Mapping:**
```python
subject = f"EVENT_ID: {event_id}\n{trigger_name}"

# Beispiel:
# "EVENT_ID: 12345678
#  High CPU usage on webserver-01"
```

**Wichtig:**
- Eventnummer (`EVENT_ID: {EVENT.ID}`) am Anfang
- Zeilenumbruch (`\n`) nach der Event-ID
- Trigger-Name auf der zweiten Zeile
- Maximum 256 Zeichen total

---

### 4. Priorität (`priority`)

```
Feld: priority
Typ: Integer / Dropdown
Wertebereich: 1-4
Quelle: {EVENT.SEVERITY} oder {EVENT.NSEVERITY}
```

**Severity-Mapping (Zabbix → osTicket):**

| Zabbix Severity | Zabbix NSEVERITY | osTicket Priority | osTicket Meaning |
|----------------|------------------|-------------------|------------------|
| Disaster | 5 | 4 | Emergency (Höchste) |
| High | 4 | 3 | High |
| Average | 3 | 2 | Medium |
| Warning | 2 | 1 | Low |
| Information | 1 | 1 | Low |
| Not classified | 0 | 2 | Normal |

**Mapping:**
```python
SEVERITY_MAP = {
    "Disaster": 4,
    "High": 3,
    "Average": 2,
    "Warning": 1,
    "Information": 1,
    "Not classified": 2
}

def map_severity_to_priority(severity: str) -> int:
    return SEVERITY_MAP.get(severity, 2)  # Default: Normal (2)

# Nutzung
"priority": map_severity_to_priority(event_severity)
```

---

## osTicket API Request - Finale Struktur

```json
{
  "name": "webserver-01",
  "email": "zabbix@example.com",
  "subject": "EVENT_ID: 12345678\nHigh CPU usage on webserver-01",
  "message": "Zabbix Alert",
  "priority": 3,
  "source": "API",
  "alert": true,
  "autorespond": true
}
```

**Erklärung:**
- `name` → **WER** (Hostname, max. 20 Zeichen)
- `subject` → **WAS + EVENTNUMMER** (Problembeschreibung mit Event-ID am Anfang)
- `message` → Einfacher Hinweis "Zabbix Alert"
- `priority` → **PRIORITÄT** (Severity-gemappt)
- `email` → Fest auf "zabbix@example.com" (System-User)
- `source` → "API" (zeigt, dass es von Webhook kommt)

---

## Webhook-Request Body (von Zabbix)

Die Webhook-Service empfängt folgende minimalen Daten von Zabbix:

```json
{
  "event_id": "12345678",
  "event_date": "2025-10-26",
  "event_time": "14:32:15",
  "event_severity": "High",
  "trigger_name": "High CPU usage on webserver-01",
  "host_name": "webserver-01"
}
```

---

## Implementation (Python/FastAPI Pseudo-Code)

```python
def create_osticket_ticket(zabbix_data: dict) -> dict:
    """
    Erstellt osTicket Ticket aus Zabbix-Daten
    """
    # 1. Konvertiere Zeit zu deutschem Format
    german_datetime = convert_to_german_datetime(
        f"{zabbix_data['event_date']} {zabbix_data['event_time']}"
    )

    # 2. Erstelle Subject mit EVENT_ID am Anfang
    subject = f"EVENT_ID: {zabbix_data['event_id']}\n{zabbix_data['trigger_name']}"

    # 3. Mappe Severity zu Priority
    priority = map_severity_to_priority(zabbix_data['event_severity'])

    # 4. Erstelle osTicket Request
    ticket_data = {
        "name": zabbix_data['host_name'],  # WER (max 20 chars)
        "email": "zabbix@example.com",
        "subject": subject,  # WAS + EVENTNUMMER
        "message": "Zabbix Alert",
        "priority": priority,  # PRIORITÄT
        "source": "API",
        "alert": True,
        "autorespond": True
    }

    # 5. Sende an osTicket API
    response = requests.post(
        f"{OSTICKET_URL}/api/tickets.json",
        headers={"X-API-Key": OSTICKET_API_KEY},
        json=ticket_data
    )

    return response.json()
```

---

## Validation & Error Handling

**Pflicht-Felder prüfen:**
```python
REQUIRED_FIELDS = ["event_id", "event_date", "event_time", "event_severity", "trigger_name", "host_name"]

def validate_zabbix_data(zabbix_data: dict) -> bool:
    for field in REQUIRED_FIELDS:
        if field not in zabbix_data or not zabbix_data[field]:
            raise ValueError(f"Missing required field: {field}")

    # Längen-Validierung
    if len(zabbix_data['host_name']) > 20:
        raise ValueError(f"host_name exceeds 20 characters: {len(zabbix_data['host_name'])}")

    if len(zabbix_data['trigger_name']) > 220:  # 256 - "EVENT_ID: 12345678\n" (~36 chars)
        raise ValueError(f"trigger_name exceeds 220 characters (after EVENT_ID)")

    return True
```

---

## Zabbix Webhook Media Type Konfiguration

**Minimal erforderliche Script Parameters:**

```
1. {EVENT.ID}
2. {EVENT.DATE}
3. {EVENT.TIME}
4. {EVENT.SEVERITY}
5. {TRIGGER.NAME}
6. {HOST.NAME}
```

**JavaScript Webhook Script:**
```javascript
var params = JSON.parse(value);

var request = new HttpRequest();
request.addHeader('Content-Type: application/json');
request.addHeader('X-API-Key: <webhook-api-key>');

var payload = {
    event_id: params.event_id,              // {EVENT.ID}
    event_date: params.event_date,          // {EVENT.DATE}
    event_time: params.event_time,          // {EVENT.TIME}
    event_severity: params.event_severity,  // {EVENT.SEVERITY}
    trigger_name: params.trigger_name,      // {TRIGGER.NAME}
    host_name: params.host_name             // {HOST.NAME}
};

var response = request.post(
    'https://<webhook-host>/api/v1/zabbix/alerts',
    JSON.stringify(payload)
);

return response;
```

---

## Testing mit cURL

**Test-Payload:**
```bash
curl -X POST https://webhook-host/api/v1/zabbix/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{
    "event_id": "12345678",
    "event_date": "2025-10-26",
    "event_time": "14:32:15",
    "event_severity": "High",
    "trigger_name": "High CPU usage on webserver-01",
    "host_name": "webserver-01"
  }'
```

**Erwartete Response:**
```json
{
  "status": "success",
  "ticket_id": "123456",
  "ticket_number": "OST-123456",
  "message": "Ticket created successfully"
}
```

---

## Deployment Checklist

### osTicket Setup (Standard-Felder)
- [ ] osTicket API Key konfiguriert
- [ ] Zabbix-Email-Adresse ("zabbix@example.com") vorhanden

### osTicket Setup (Custom Fields für Phase 2)
- [ ] Custom Field `root_ticket` angelegt (Link to Ticket)
- [ ] Custom Field `ursache` angelegt (Text, 256+)
- [ ] Custom Field `lösung` angelegt (Text, 256+)
- [ ] Custom Field `störungsende` angelegt (DateTime, deutsches Format)

### Zabbix Webhook Setup
- [ ] Zabbix Webhook Media Type mit 6 Parametern angelegt
- [ ] Webhook-Service implementiert (siehe IMPLEMENTATION_GUIDE)
- [ ] Webhook-Service läuft und erreichbar
- [ ] Test-Webhook ausgelöst

### Testing & Validierung
- [ ] Ticket in osTicket erstellt und überprüft:
  - [ ] `name` (WER) = Hostname, max. 20 Zeichen
  - [ ] `subject` (WAS) = EVENT_ID + Trigger-Name, max. 256 Zeichen
  - [ ] `priority` (PRIORITÄT) = Severity-gemappt (1-4)
  - [ ] `date_created` = Deutsches Format (DD.MM.YYYY HH:MM:SS)
  - [ ] `root_ticket`, `ursache`, `lösung`, `störungsende` = Leer (noch nicht gefüllt)
- [ ] Logging & Monitoring aktiviert

---

## osTicket Custom Fields Anlegen (Phase 2 Fields)

Diese 4 Custom Fields müssen in osTicket angelegt werden. Sie werden **NICHT** von der aktuellen Zabbix-Integration gefüllt:

### Schritt 1: osTicket Admin Panel → Manage → Custom Fields

Für jedes Field die folgenden Schritte durchführen:

### Custom Field 1: `root_ticket` (Verknüpfung)

```
Label:       Root Ticket
Name:        root_ticket
Type:        Link to Ticket
Required:    Nein
Description: Verknüpfung zu Parent-Ticket bei zusammenhängenden Problemen
Visibility:  Admin
```

### Custom Field 2: `ursache` (Ursache)

```
Label:       Ursache
Name:        ursache
Type:        Text (Textarea)
Max Length:  256+ (z.B. 1000)
Required:    Nein
Description: Ursachenanalyse des Zabbix-Problems
Visibility:  Public
```

### Custom Field 3: `lösung` (Lösung)

```
Label:       Lösung
Name:        lösung
Type:        Text (Textarea)
Max Length:  256+ (z.B. 1000)
Required:    Nein
Description: Durchgeführte Lösungsmaßnahme zur Behebung des Problems
Visibility:  Public
```

### Custom Field 4: `störungsende` (Störungsende)

```
Label:       Störungsende
Name:        störungsende
Type:        Date & Time
Required:    Nein
Description: Zeitstempel wenn das Problem behoben wurde
Visibility:  Public
Format:      Deutsches Format (DD.MM.YYYY HH:MM:SS)
```

### Verifikation

Nach dem Anlegen sollten diese 4 Custom Fields sichtbar sein:

```
✅ root_ticket (Link to Ticket)
✅ ursache (Text, 256+)
✅ lösung (Text, 256+)
✅ störungsende (DateTime)
```

**Überprüfen:**
1. Gehen Sie zu "Admin Panel → Manage → Custom Fields"
2. Bestätigen Sie, dass alle 4 Felder mit korrekten Einstellungen sichtbar sind
3. Öffnen Sie ein Test-Ticket und überprüfen Sie, ob die Felder in der Form angezeigt werden

---

**Dokument Ende**
