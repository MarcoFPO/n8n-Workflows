# Zabbix Action Configuration für Event-Based Workflow

## Überblick

Diese Anleitung beschreibt die Konfiguration einer Zabbix Action, die bei jedem neuen Problem-Event einen Webhook an den n8n Sub-1 Workflow sendet.

## Architektur

```
Zabbix Problem Event
    ↓
Zabbix Action (Webhook)
    ↓
n8n Sub-1 V2 (Webhook-Empfänger)
    ↓
Redis Queue (Event-Puffer)
    ↓
n8n Master V2 (Event-Verarbeitung)
    ↓
Sub-2 → Sub-3 → Sub-4 (conditional) → Sub-5
```

## Zabbix Action anlegen

### 1. Action erstellen

**Navigation:** Configuration → Actions → Trigger actions → Create action

**Name:** `n8n Workflow Integration`

### 2. Action Conditions

Definiere, welche Events den Workflow triggern sollen:

**Conditions:**
```
A: Maintenance status not in maintenance
B: Trigger value = PROBLEM
```

**Kombination:** `(A and B)`

Dies stellt sicher, dass nur neue Probleme außerhalb von Maintenance-Fenstern gemeldet werden.

### 3. Operations - Webhook konfigurieren

**Operation Type:** Send to webhook

**URL:** `http://10.1.1.180/webhook/zabbix-event`

**HTTP Method:** POST

**HTTP Headers:**
```
Content-Type: application/json
```

**Message Body:**
```json
{
  "eventid": "{EVENT.ID}",
  "event_id": "{EVENT.ID}",
  "name": "{EVENT.NAME}",
  "problem": "{EVENT.NAME}",
  "severity": "{EVENT.SEVERITY}",
  "host": "{HOST.NAME}",
  "hostid": "{HOST.ID}",
  "ip": "{HOST.IP}",
  "triggerid": "{TRIGGER.ID}",
  "trigger_description": "{TRIGGER.DESCRIPTION}",
  "trigger_expression": "{TRIGGER.EXPRESSION}",
  "clock": "{EVENT.TIME}",
  "timestamp": "{EVENT.DATE} {EVENT.TIME}",
  "status": "{EVENT.STATUS}",
  "value": "{EVENT.VALUE}",
  "recovery_value": "{EVENT.RECOVERY.VALUE}",
  "tags": "{EVENT.TAGS}",
  "opdata": "{EVENT.OPDATA}",
  "update_status": "{EVENT.UPDATE.STATUS}",
  "update_action": "{EVENT.UPDATE.ACTION}"
}
```

### 4. Recovery Operations (Optional)

Falls auch Recovery-Events erfasst werden sollen:

**Operation Type:** Send to webhook

**URL:** `http://10.1.1.180/webhook/zabbix-event`

**HTTP Method:** POST

**Message Body:**
```json
{
  "eventid": "{EVENT.RECOVERY.ID}",
  "event_id": "{EVENT.RECOVERY.ID}",
  "name": "{EVENT.RECOVERY.NAME}",
  "problem": "RECOVERED: {EVENT.NAME}",
  "severity": "0",
  "host": "{HOST.NAME}",
  "hostid": "{HOST.ID}",
  "ip": "{HOST.IP}",
  "triggerid": "{TRIGGER.ID}",
  "trigger_description": "{TRIGGER.DESCRIPTION}",
  "clock": "{EVENT.RECOVERY.TIME}",
  "timestamp": "{EVENT.RECOVERY.DATE} {EVENT.RECOVERY.TIME}",
  "status": "RECOVERY",
  "value": "{EVENT.RECOVERY.VALUE}",
  "original_eventid": "{EVENT.ID}"
}
```

## Zabbix Macros Erklärung

| Macro | Beschreibung |
|-------|--------------|
| `{EVENT.ID}` | Eindeutige Event-ID |
| `{EVENT.NAME}` | Name des Problems |
| `{EVENT.SEVERITY}` | Severity (0-5: Not classified, Information, Warning, Average, High, Disaster) |
| `{HOST.NAME}` | Hostname des betroffenen Systems |
| `{HOST.ID}` | Zabbix Host ID |
| `{HOST.IP}` | IP-Adresse des Hosts |
| `{TRIGGER.ID}` | Trigger ID |
| `{TRIGGER.DESCRIPTION}` | Trigger Beschreibung |
| `{TRIGGER.EXPRESSION}` | Trigger Expression |
| `{EVENT.TIME}` | Zeitstempel (HH:MM:SS) |
| `{EVENT.DATE}` | Datum (YYYY.MM.DD) |
| `{EVENT.STATUS}` | Event Status |
| `{EVENT.TAGS}` | Event Tags |

## Test der Konfiguration

### 1. Manueller Test

Erstelle ein Test-Problem oder triggere ein bestehendes Problem manuell.

### 2. Überprüfung in n8n

**Prüfe die Webhook-Ausführungen:**
- Öffne n8n UI: `http://10.1.1.180`
- Navigiere zu Workflow: `Zabbix Sub-1: Problem-Erfassung V2 (Event-Based)`
- Prüfe Execution History

### 3. Redis Queue überprüfen

```bash
# Verbinde zu Redis
redis-cli

# Zeige Queue-Länge
LLEN zabbix:event:queue

# Zeige Event-Counter
GET zabbix:event:counter

# Zeige letztes Event in Queue (ohne zu entfernen)
LRANGE zabbix:event:queue -1 -1

# Zeige alle Events in Queue
LRANGE zabbix:event:queue 0 -1
```

### 4. Event-Status prüfen

```bash
# Prüfe Status eines spezifischen Events
GET zabbix:event:12345:status

# Zeige alle Event-Status-Keys
KEYS zabbix:event:*:status
```

### 5. Lock-Status prüfen

```bash
# Prüfe ob Master gerade verarbeitet
EXISTS zabbix:processing:lock

# Zeige Lock-Wert (Timestamp)
GET zabbix:processing:lock
```

## Troubleshooting

### Problem: Events kommen nicht an

**Prüfung:**
1. Teste Webhook manuell mit curl:
```bash
curl -X POST http://10.1.1.180/webhook/zabbix-event \
  -H "Content-Type: application/json" \
  -d '{"eventid":"12345","name":"Test Problem","severity":"3","host":"test-server"}'
```

2. Prüfe Zabbix Action Log:
   - Administration → Audit → Actions
   - Suche nach der Action und prüfe Status

3. Prüfe n8n Logs:
```bash
# Auf dem n8n Server
docker logs n8n
# oder
journalctl -u n8n -f
```

### Problem: Queue läuft voll

**Symptome:**
- Queue-Länge steigt kontinuierlich
- Events werden nicht verarbeitet

**Lösung:**
```bash
# Prüfe Queue-Länge
redis-cli LLEN zabbix:event:queue

# Prüfe Lock
redis-cli EXISTS zabbix:processing:lock

# Falls Lock hängt, manuell entfernen
redis-cli DEL zabbix:processing:lock

# Trigger Master-Workflow manuell
curl -X POST http://10.1.1.180/webhook/master-zabbix-processor \
  -H "Content-Type: application/json" \
  -d '{"event_id":"trigger","trigger":"manual"}'
```

### Problem: Duplicate Processing

**Symptome:**
- Events werden mehrfach verarbeitet
- Lock funktioniert nicht

**Lösung:**
- Prüfe ob TTL korrekt gesetzt ist (5 Minuten = 300 Sekunden)
- Stelle sicher, dass Lock immer released wird
- Prüfe n8n Error-Handler

## Performance-Tuning

### Queue-Größe limitieren

Falls zu viele Events gleichzeitig eintreffen:

```bash
# Limitiere Queue auf max 1000 Events
redis-cli LTRIM zabbix:event:queue 0 999
```

### Event-TTL anpassen

Events älter als 24h automatisch löschen:

```bash
# Setze TTL für Event-Status-Keys auf 24h
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Master-Workflow Loop

Um die Queue kontinuierlich zu verarbeiten, kann der Master-Workflow am Ende sich selbst triggern:

**Zusätzlicher Node in Master V2:** "Trigger Next Iteration"
- Type: HTTP Request
- URL: `http://10.1.1.180/webhook/master-zabbix-processor`
- Condition: Queue length > 0
- Fire & Forget: Yes

## Monitoring

### Wichtige Metriken

1. **Queue-Länge:** `LLEN zabbix:event:queue`
2. **Event-Counter:** `GET zabbix:event:counter`
3. **Processing Lock:** `EXISTS zabbix:processing:lock`
4. **Event Status:** `KEYS zabbix:event:*:status`

### Alert bei Queue-Overflow

Erstelle Zabbix Item für Queue-Monitoring:

```bash
# Script für Zabbix External Check
#!/bin/bash
redis-cli -h 10.1.1.180 LLEN zabbix:event:queue
```

**Trigger:**
- Expression: `{redis_queue_check.last()} > 100`
- Severity: Warning

## Sicherheit

### Webhook-Authentifizierung

Erweitere Sub-1 V2 um Header-Check:

```javascript
// In "Extract Event Data" Node
const authToken = $('Zabbix Event Webhook').item.json.headers['x-auth-token'];
if (authToken !== 'YOUR_SECRET_TOKEN') {
  throw new Error('Unauthorized');
}
```

### IP-Whitelist

Konfiguriere n8n Webhook nur für Zabbix-Server IP:

```nginx
# nginx config
location /webhook/zabbix-event {
  allow 10.1.1.103;
  deny all;
  proxy_pass http://n8n:5678;
}
```

## Nächste Schritte

1. ✅ Zabbix Action konfigurieren
2. ✅ Test-Events senden
3. ✅ Monitoring aufsetzen
4. ✅ Workflows in n8n aktivieren
5. ✅ Dokumentation vervollständigen
