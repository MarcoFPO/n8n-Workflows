# Zabbix Alert-Variablen - Schnelle Referenz

**Für die osTicket Integration benötigte Variablen**

---

## Die 4 Kernattribute - Mit Zabbix Makros

### 1. **WER** (Initiator)
```
Empfohlenes Makro:  {USER.FULLNAME} oder {HOST.NAME}
Alternative:        {HOST.NAME} ({HOST.IP})
Beispiel:           "John Smith" oder "webserver-01 (192.168.1.100)"
```

### 2. **WANN** (Zeitpunkt)
```
Empfohlenes Makro:  {EVENT.DATE} {EVENT.TIME}
Alternative:        {EVENT.TIMESTAMP}
Beispiel:           "2025-10-26 14:32:15"
Format ISO 8601:    {EVENT.DATE}T{EVENT.TIME}Z → "2025-10-26T14:32:15Z"
```

### 3. **WAS** (Problem-Beschreibung)
```
Subject:            {TRIGGER.NAME}
Beispiel:           "High CPU usage on webserver-01"

Body:               {TRIGGER.DESCRIPTION}
Beispiel:           "CPU usage exceeded 90% threshold"

Details:            {ITEM.NAME} = {ITEM.VALUE} {ITEM.UNITS}
Beispiel:           "CPU utilization = 95 %"
```

### 4. **EVENTNUMMER** (Eindeutige ID)
```
Empfohlenes Makro:  {EVENT.ID}
Beispiel:           "12345678"
```

---

## Alle Event-Variablen

| Makro | Wert | Beispiel |
|-------|------|---------|
| `{EVENT.ID}` | Event ID | 12345678 |
| `{EVENT.DATE}` | Datum | 2025-10-26 |
| `{EVENT.TIME}` | Zeit | 14:32:15 |
| `{EVENT.TIMESTAMP}` | Unix Timestamp | 1729952535 |
| `{EVENT.STATUS}` | 0=OK, 1=PROBLEM | 1 |
| `{EVENT.SEVERITY}` | Text Severity | High |
| `{EVENT.NSEVERITY}` | Nummer 0-5 | 4 |
| `{EVENT.AGE}` | Alter in Sekunden | 3600 |
| `{EVENT.TAGS}` | Alle Tags | service=web,priority=high |
| `{EVENT.ACK.STATUS}` | Ack Status | 1 |

---

## Alle Trigger-Variablen

| Makro | Wert | Beispiel |
|-------|------|---------|
| `{TRIGGER.ID}` | Trigger ID | 13926 |
| `{TRIGGER.NAME}` | Trigger Name | High CPU usage on {HOST.NAME} |
| `{TRIGGER.STATUS}` | 0=OK, 1=PROBLEM | 1 |
| `{TRIGGER.DESCRIPTION}` | Beschreibung | CPU exceeded 90% |
| `{TRIGGER.URL}` | Zabbix URL | https://zabbix.../...?triggerid=13926 |
| `{TRIGGER.PRIORITY}` | 0-5 | 4 |
| `{TRIGGER.PRIORITY.NAME}` | Priority Name | High |

---

## Alle Host-Variablen

| Makro | Wert | Beispiel |
|-------|------|---------|
| `{HOST.ID}` | Host ID | 10001 |
| `{HOST.NAME}` | Hostname | webserver-01 |
| `{HOST.IP}` | IP-Adresse | 192.168.1.100 |
| `{HOST.DNS}` | DNS-Name | web01.example.com |
| `{HOST.CONN}` | Connection | 192.168.1.100 |
| `{HOST.DESCRIPTION}` | Beschreibung | Main web server |

---

## Alle Item-Variablen

| Makro | Wert | Beispiel |
|-------|------|---------|
| `{ITEM.ID}` | Item ID | 23456 |
| `{ITEM.NAME}` | Item Name | CPU utilization |
| `{ITEM.KEY}` | Item Key | system.cpu.load.avg(1m) |
| `{ITEM.VALUE}` | Aktueller Wert | 0.95 |
| `{ITEM.LASTVALUE}` | Letzter Wert | 0.92 |
| `{ITEM.UNITS}` | Einheiten | % |

---

## Severity Mapping (Zabbix → osTicket)

```
{EVENT.SEVERITY}     {EVENT.NSEVERITY}    osTicket Priority
─────────────────────────────────────────────────────────
Not classified          0                   2 (Normal)
Information             1                   1 (Low)
Warning                 2                   1 (Low)
Average                 3                   2 (Medium)
High                    4                   3 (High)
Disaster                5                   4 (Emergency)
```

---

## Beispiel JSON Payload mit Makros

```json
{
  "event_id": "{EVENT.ID}",
  "event_time": "{EVENT.DATE} {EVENT.TIME}",
  "event_timestamp": "{EVENT.TIMESTAMP}",
  "trigger_id": "{TRIGGER.ID}",
  "trigger_name": "{TRIGGER.NAME}",
  "trigger_status": "{TRIGGER.STATUS}",
  "trigger_severity": "{EVENT.SEVERITY}",
  "trigger_severity_num": "{EVENT.NSEVERITY}",
  "trigger_description": "{TRIGGER.DESCRIPTION}",
  "trigger_url": "{TRIGGER.URL}",
  "host_id": "{HOST.ID}",
  "host_name": "{HOST.NAME}",
  "host_ip": "{HOST.IP}",
  "host_dns": "{HOST.DNS}",
  "host_description": "{HOST.DESCRIPTION}",
  "item_name": "{ITEM.NAME}",
  "item_key": "{ITEM.KEY}",
  "item_value": "{ITEM.VALUE}",
  "item_units": "{ITEM.UNITS}",
  "event_age": "{EVENT.AGE}",
  "event_tags": "{EVENT.TAGS}",
  "user": "zabbix-automation"
}
```

---

## Zabbix Webhook Action Script Vorlage

```javascript
// Webhook Script mit Makro-Variablen

var params = JSON.parse(value);

var request = new HttpRequest();
request.addHeader('Content-Type: application/json');
request.addHeader('X-API-Key: your-api-key');

var payload = {
    // Event (WANN + EVENTNUMMER)
    event_id: params.event_id,           // {EVENT.ID}
    event_time: params.event_time,       // {EVENT.DATE} {EVENT.TIME}
    event_date: params.event_date,       // {EVENT.DATE}
    event_timestamp: params.event_timestamp,

    // Trigger (WAS)
    trigger_id: params.trigger_id,       // {TRIGGER.ID}
    trigger_name: params.trigger_name,   // {TRIGGER.NAME}
    trigger_status: params.trigger_status,
    trigger_severity: params.trigger_severity,  // {EVENT.SEVERITY}
    trigger_description: params.trigger_description,
    trigger_url: params.trigger_url,     // {TRIGGER.URL}

    // Host (WAS + Kontext)
    host_name: params.host_name,         // {HOST.NAME}
    host_ip: params.host_ip,             // {HOST.IP}
    host_dns: params.host_dns,           // {HOST.DNS}

    // Item (Wert)
    item_name: params.item_name,         // {ITEM.NAME}
    item_value: params.item_value,       // {ITEM.VALUE}
    item_units: params.item_units,       // {ITEM.UNITS}

    // User (WER)
    user_name: params.user_name,         // {USER.FULLNAME}
    
    // Tags
    event_tags: params.event_tags        // {EVENT.TAGS}
};

var response = request.post(
    'https://your-host/api/v1/zabbix/alerts',
    JSON.stringify(payload)
);

return response;
```

---

## Zabbix Webhook Media Type Konfiguration

```
Administration → Media Types → Create Media Type

Name: osTicket Webhook

Script Parameters (in dieser Reihenfolge):
1. {EVENT.ID}
2. {EVENT.DATE}
3. {EVENT.TIME}
4. {EVENT.TIMESTAMP}
5. {EVENT.STATUS}
6. {EVENT.SEVERITY}
7. {EVENT.NSEVERITY}
8. {EVENT.AGE}
9. {TRIGGER.ID}
10. {TRIGGER.NAME}
11. {TRIGGER.STATUS}
12. {TRIGGER.DESCRIPTION}
13. {TRIGGER.URL}
14. {HOST.ID}
15. {HOST.NAME}
16. {HOST.IP}
17. {HOST.DNS}
18. {ITEM.NAME}
19. {ITEM.VALUE}
20. {ITEM.UNITS}
21. {EVENT.TAGS}
22. {USER.FULLNAME}
```

---

## Welche Variablen sollten in den Webhook gehen?

### Minimal (Must-Have)
```
- {EVENT.ID}                    ← EVENTNUMMER
- {EVENT.DATE} {EVENT.TIME}     ← WANN
- {TRIGGER.NAME}                ← WAS (Title)
- {HOST.NAME}                   ← WER
```

### Empfohlen (Should-Have)
```
Zusätzlich zum Minimal:
- {TRIGGER.DESCRIPTION}         ← WAS (Details)
- {HOST.IP}                     ← Host Context
- {ITEM.VALUE} {ITEM.UNITS}    ← Aktueller Wert
- {EVENT.SEVERITY}              ← Severity Level
- {TRIGGER.URL}                 ← Link zu Zabbix
- {EVENT.TAGS}                  ← Tagging
- {EVENT.NSEVERITY}             ← Numerischer Severity (für Mapping)
```

### Optional (Nice-to-Have)
```
- {EVENT.AGE}                   ← Wie lange läuft das Problem
- {EVENT.TIMESTAMP}             ← Unix Timestamp
- {TRIGGER.ID}                  ← Trigger ID
- {HOST.DNS}                    ← DNS Name
- {ITEM.NAME}                   ← Item Bezeichnung
- {ITEM.KEY}                    ← Item Key
- {USER.FULLNAME}               ← Automation User
```

---

## Wichtige Hinweise

1. **Makros in Webhook Script verwenden:**
   - Im Zabbix Webhook Script müssen Makros wie `{EVENT.ID}` als Parameter definiert werden
   - Diese werden dann in `params` übergeben
   - Zugriff via `params.event_id` (lowercase, mit Underscore)

2. **Severity Level:**
   - Zabbix kennt Severity als Text (`High`, `Low`, etc.)
   - `{EVENT.NSEVERITY}` liefert die Zahl (0-5)
   - Für osTicket Mapping → NSEVERITY verwenden (0-5)

3. **Datum/Zeit Format:**
   - `{EVENT.DATE}` = YYYY-MM-DD Format
   - `{EVENT.TIME}` = HH:MM:SS Format
   - Kombination: `{EVENT.DATE} {EVENT.TIME}`
   - Für ISO 8601: Datum + T + Zeit + Z

4. **Tags nutzen:**
   - `{EVENT.TAGS}` enthält alle Tags im Format: `key1:value1,key2:value2`
   - Kann für automatisches Routing, Kategorisierung, etc. verwendet werden

---

**Quelle:** Zabbix Official Documentation + Praktische Erfahrung
**Aktualisiert:** 2025-10-26
**Kompatibilität:** Zabbix 6.0+

