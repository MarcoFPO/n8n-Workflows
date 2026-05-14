# Zabbix Alert-Variablen und Makros

**Quelle:** Zabbix Official Documentation
**Version:** Zabbix 6.0 - 7.0 kompatibel
**Datum:** 2025-10-26

---

## Übersicht

Diese Dokumentation zeigt alle Makro-Variablen, die Zabbix bei Alerts und Webhook-Actions bereitstellt. Diese Variablen können in Webhook-Requests, Benachrichtigungen und anderen Alert-Aktionen verwendet werden.

---

## Webhook-Spezifische Makros

Diese Makros sind speziell für Webhook-Konfigurationen verfügbar:

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{ALERT.SENDTO}` | Empfängeradresse der Benachrichtigung | zabbix@example.com |
| `{ALERT.SUBJECT}` | Betreffzeile der Benachrichtigung | Problem: High CPU on server-01 |
| `{ALERT.MESSAGE}` | Nachrichtentext der Benachrichtigung | Detailed alert message |

---

## Event-Makros

Makros für Event-Informationen:

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{EVENT.ID}` | Eindeutige Event-ID | 12345678 |
| `{EVENT.DATE}` | Datum des Events | 2025-10-26 |
| `{EVENT.TIME}` | Zeit des Events | 14:32:15 |
| `{EVENT.TIMESTAMP}` | Unix Timestamp des Events | 1729952535 |
| `{EVENT.STATUS}` | Status des Events (0=OK, 1=PROBLEM) | 1 |
| `{EVENT.VALUE}` | Trigger Wert | 1 |
| `{EVENT.SEVERITY}` | Severity Level (Text) | High |
| `{EVENT.AGE}` | Alter des Events in Sekunden | 3600 |
| `{EVENT.SOURCE}` | Event-Quelle | trigger |
| `{EVENT.UPDATE.STATUS}` | Update-Status | 0 |
| `{EVENT.UPDATE.ACTION}` | Update-Aktion | 0 |
| `{EVENT.RECOVERY.DATE}` | Recovery-Datum | 2025-10-26 |
| `{EVENT.RECOVERY.TIME}` | Recovery-Zeit | 14:45:30 |
| `{EVENT.RECOVERY.TIMESTAMP}` | Recovery Timestamp | 1729953330 |
| `{EVENT.TAGS.<tag_name>}` | Trigger-Tags nach Name | service=web |
| `{EVENT.TAGS}` | Alle Trigger-Tags | service=web,priority=high |
| `{EVENT.NSEVERITY}` | Severity Nummer (0-5) | 3 |
| `{EVENT.ACK.STATUS}` | Acknowledgement Status | 1 |

---

## Trigger-Makros

Makros für Trigger-Informationen:

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{TRIGGER.ID}` | Eindeutige Trigger-ID | 13926 |
| `{TRIGGER.NAME}` | Trigger-Name | High CPU usage on {HOST.NAME} |
| `{TRIGGER.STATUS}` | Trigger-Status (0=OK, 1=PROBLEM) | 1 |
| `{TRIGGER.STATUS.CHANGE}` | Status-Änderung | 1 |
| `{TRIGGER.DESCRIPTION}` | Trigger-Beschreibung | CPU usage exceeded 90% threshold |
| `{TRIGGER.EXPRESSION}` | Trigger-Expression | {server-01:system.cpu.load.avg(1m)}>0.9 |
| `{TRIGGER.URL}` | Link zum Trigger | https://zabbix.example.com/tr_events.php?triggerid=13926 |
| `{TRIGGER.COMMENT}` | Trigger-Kommentar | Monitoring CPU performance |
| `{TRIGGER.PRIORITY}` | Trigger-Priorität (0-5) | 4 |
| `{TRIGGER.PRIORITY.NAME}` | Prioritäts-Name | High |
| `{TRIGGER.TYPE}` | Trigger-Typ (0=Single, 1=Multiple) | 0 |
| `{TRIGGER.TYPE.NAME}` | Trigger-Typ-Name | Single |
| `{TRIGGER.RECOVERY.EXPRESSION}` | Recovery-Expression | {server-01:system.cpu.load.avg(1m)}<0.7 |
| `{TRIGGER.CORRELATION.TAG}` | Correlation-Tag | service:web |
| `{TRIGGER.CORRELATION.MODE}` | Correlation-Mode | tag value |

---

## Host-Makros

Makros für Host-Informationen:

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{HOST.ID}` | Host-ID | 10001 |
| `{HOST.NAME}` | Hostname | webserver-01 |
| `{HOST.IP}` | IP-Adresse (IPv4) | 192.168.1.100 |
| `{HOST.DNS}` | DNS-Name | web01.example.com |
| `{HOST.CONN}` | Host-Verbindung (IP oder DNS) | 192.168.1.100 |
| `{HOST.HOST}` | Host-Technischer Name | webserver-01 |
| `{HOST.DESCRIPTION}` | Host-Beschreibung | Main web server |
| `{HOST.PORT}` | Host-Port | 10050 |
| `{HOST.STATUS}` | Host-Status (0=Monitored, 1=Not monitored) | 0 |
| `{HOST.MAINTENANCE_TYPE}` | Wartungstyp | 0 |
| `{HOST.INVENTORY.<property>}` | Host-Inventory Eigenschaften | |
| `{HOST.INVENTORY.SERIALNUMBER}` | Seriennummer | SN123456 |
| `{HOST.INVENTORY.MODEL}` | Modell | Dell PowerEdge R750 |
| `{HOST.INVENTORY.VENDOR}` | Hersteller | Dell |
| `{HOST.INVENTORY.LOCATION}` | Standort | Datacenter 1, Rack 5 |
| `{HOST.INVENTORY.OS}` | Betriebssystem | CentOS 7.9 |
| `{HOST.INVENTORY.ASSET_TAG}` | Asset-Tag | AT-12345 |

---

## Item-Makros

Makros für Item (Metrik)-Informationen:

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{ITEM.ID}` | Item-ID | 23456 |
| `{ITEM.NAME}` | Item-Name | CPU utilization |
| `{ITEM.NAME.ORIG}` | Original Item-Name (unformattiert) | system.cpu.load |
| `{ITEM.KEY}` | Item-Key | system.cpu.load.avg(1m) |
| `{ITEM.VALUE}` | Aktueller Item-Wert | 0.95 |
| `{ITEM.LASTVALUE}` | Letzter Item-Wert | 0.92 |
| `{ITEM.DESCRIPTION}` | Item-Beschreibung | CPU load average for 1 minute |
| `{ITEM.VALUETYPE}` | Value-Typ (0=Float, 1=String, 2=Log, 3=Unsigned, 4=Text) | 0 |
| `{ITEM.UNITS}` | Einheiten | % |

---

## Problem-Makros (für Problem-basierte Benachrichtigungen)

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{PROBLEM.DURATION}` | Dauer des Problems | 1h 30m |
| `{PROBLEM.DURATION.SEC}` | Dauer in Sekunden | 5400 |
| `{PROBLEM.AGE}` | Alter des Problems | 1h 30m |
| `{PROBLEM.ID}` | Problem-ID | 543 |
| `{PROBLEM.NAME}` | Problem-Name | High CPU usage |
| `{PROBLEM.SEVERITY}` | Problem-Schweregrad | High |
| `{PROBLEM.STATUS}` | Problem-Status | PROBLEM |

---

## User und Acknowledgement Makros

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{USER.FULLNAME}` | Vollständiger Benutzername | John Smith |
| `{USER.NAME}` | Benutzer Vorname | John |
| `{USER.SURNAME}` | Benutzer Nachname | Smith |
| `{USER.USERNAME}` | Benutzername (Login) | jsmith |
| `{USER.EMAIL}` | Benutzer-Email | jsmith@example.com |
| `{USER.PHONE}` | Benutzer-Telefon | +1-234-567-8900 |
| `{ACK.DATE}` | Acknowledgement-Datum | 2025-10-26 |
| `{ACK.TIME}` | Acknowledgement-Zeit | 15:00:00 |
| `{ACK.COMMENT}` | Acknowledgement-Kommentar | Issue resolved |

---

## Systemzeit-Makros

| Makro | Beschreibung | Beispiel |
|-------|-------------|---------|
| `{DATE}` | Aktuelles Datum | 2025-10-26 |
| `{TIME}` | Aktuelle Zeit | 14:32:15 |
| `{TIMESTAMP}` | Aktueller Unix Timestamp | 1729952535 |

---

## Benutzerdefinierte Makros (User Macros)

Benutzerdefinierte Makros können auf globaler, Host-Gruppen- oder Host-Ebene definiert werden:

| Makro-Typ | Format | Beispiel |
|-----------|--------|---------|
| Global User Macro | `${MACRO_NAME}` | ${ESCALATION_LEVEL} |
| Host User Macro | `${MACRO_NAME}` | ${DEPARTMENT} |
| Host Group User Macro | `${MACRO_NAME}` | ${SEVERITY_LEVEL} |

---

## Wichtige Notizen

### Severity Level Mapping

Zabbix Severity wird als Zahl von 0-5 dargestellt:

```
0 = Not classified (Nicht klassifiziert)
1 = Information (Information)
2 = Warning (Warnung)
3 = Average (Durchschnitt)
4 = High (Hoch)
5 = Disaster (Katastrophe)
```

### Event Status

```
0 = OK (Problem gelöst)
1 = PROBLEM (Aktuelles Problem)
```

### Host Status

```
0 = Monitored (Überwacht)
1 = Not monitored (Nicht überwacht)
```

---

## Webhook-Beispiel mit Makros

```javascript
// Zabbix Webhook Script - Beispiel mit Makros

var params = JSON.parse(value);

var request = new HttpRequest();
request.addHeader('Content-Type: application/json');
request.addHeader('X-API-Key: your-api-key');

// JSON Payload mit Makro-Variablen
var payload = {
    // Event Information
    event_id: params.event_id,                          // {EVENT.ID}
    event_date: params.event_date,                      // {EVENT.DATE}
    event_time: params.event_time,                      // {EVENT.TIME}
    event_timestamp: params.event_timestamp,            // {EVENT.TIMESTAMP}
    event_status: params.event_status,                  // {EVENT.STATUS}
    event_severity: params.event_severity,              // {EVENT.SEVERITY}
    event_nseverity: params.event_nseverity,            // {EVENT.NSEVERITY}
    event_age: params.event_age,                        // {EVENT.AGE}
    event_tags: params.event_tags,                      // {EVENT.TAGS}

    // Trigger Information
    trigger_id: params.trigger_id,                      // {TRIGGER.ID}
    trigger_name: params.trigger_name,                  // {TRIGGER.NAME}
    trigger_status: params.trigger_status,              // {TRIGGER.STATUS}
    trigger_description: params.trigger_description,    // {TRIGGER.DESCRIPTION}
    trigger_url: params.trigger_url,                    // {TRIGGER.URL}
    trigger_priority: params.trigger_priority,          // {TRIGGER.PRIORITY}
    trigger_priority_name: params.trigger_priority_name,// {TRIGGER.PRIORITY.NAME}

    // Host Information
    host_id: params.host_id,                            // {HOST.ID}
    host_name: params.host_name,                        // {HOST.NAME}
    host_ip: params.host_ip,                            // {HOST.IP}
    host_dns: params.host_dns,                          // {HOST.DNS}
    host_description: params.host_description,          // {HOST.DESCRIPTION}

    // Item Information
    item_id: params.item_id,                            // {ITEM.ID}
    item_name: params.item_name,                        // {ITEM.NAME}
    item_key: params.item_key,                          // {ITEM.KEY}
    item_value: params.item_value,                      // {ITEM.VALUE}
    item_units: params.item_units,                      // {ITEM.UNITS}

    // User Information
    user_fullname: params.user_fullname,                // {USER.FULLNAME}
    user_email: params.user_email,                      // {USER.EMAIL}

    // Alert Information
    alert_subject: params.alert_subject,                // {ALERT.SUBJECT}
    alert_message: params.alert_message                 // {ALERT.MESSAGE}
};

var response = request.post(
    'https://your-webhook-host/api/v1/zabbix/alerts',
    JSON.stringify(payload)
);

return response;
```

---

## Häufig verwendete Makro-Kombinationen

### Für osTicket Integration

```
WER:         {USER.FULLNAME} oder {HOST.NAME}
WANN:        {EVENT.DATE} {EVENT.TIME} oder {EVENT.TIMESTAMP}
WAS:         {TRIGGER.NAME} - {TRIGGER.DESCRIPTION}
EVENTNUMMER: {EVENT.ID}
HOST:        {HOST.NAME} ({HOST.IP})
SEVERITY:    {EVENT.SEVERITY} ({EVENT.NSEVERITY})
ITEM:        {ITEM.NAME} = {ITEM.VALUE} {ITEM.UNITS}
URL:         {TRIGGER.URL}
TAGS:        {EVENT.TAGS}
```

### Für Ticket-Subject

```
[{EVENT.SEVERITY}] {HOST.NAME}: {TRIGGER.NAME}
Beispiel: [High] webserver-01: High CPU usage on webserver-01
```

### Für Ticket-Body

```
Problem: {TRIGGER.NAME}
Host: {HOST.NAME} ({HOST.IP})
Severity: {EVENT.SEVERITY}
Date/Time: {EVENT.DATE} {EVENT.TIME}
Event ID: {EVENT.ID}
Description: {TRIGGER.DESCRIPTION}
Item: {ITEM.NAME} = {ITEM.VALUE} {ITEM.UNITS}
View in Zabbix: {TRIGGER.URL}
Tags: {EVENT.TAGS}
```

---

## Welche Makros stellt Zabbix standardmäßig bereit?

Zabbix stellt folgende Makro-Kategorien bereit:

✅ **Event-Makros** - Event ID, Date, Time, Status, Severity
✅ **Trigger-Makros** - Trigger ID, Name, Description, URL, Priority
✅ **Host-Makros** - Host ID, Name, IP, DNS, Description, Inventory
✅ **Item-Makros** - Item ID, Name, Key, Value, Units
✅ **User-Makros** - User Name, Email, Phone
✅ **Alert-Makros** - Alert Subject, Message, SendTo
✅ **Problem-Makros** - Problem Duration, Age, Status
✅ **System-Makros** - Date, Time, Timestamp
✅ **Custom/User-Defined Macros** - Global, Host Group, Host Level

---

## Informationen abrufen

Diese Makros sind in folgenden Zabbix-Komponenten verfügbar:

- **Webhook Actions** - Alle meisten Makros werden unterstützt
- **Email Templates** - Standard-Makros
- **SMS Templates** - Standard-Makros
- **Slack Webhooks** - Standard-Makros
- **Custom Alert Scripts** - Alle verfügbaren Makros

---

**Quelle:** Zabbix Official Documentation
**Letzte Aktualisierung:** 2025-10-26
**Kompatibilität:** Zabbix 6.0, 6.4, 7.0

