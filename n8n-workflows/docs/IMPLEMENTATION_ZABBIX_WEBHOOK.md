# Implementierungsanleitung: Zabbix Webhook für osTicket Integration

**Datum:** 2025-10-26
**Version:** 1.0
**Zweck:** Schritt-für-Schritt Anleitung zum Konfigurieren des Zabbix Webhooks für die osTicket Integration
**Zielgruppe:** Zabbix Administratoren

---

## Übersicht

Dieser Webhook sendet Zabbix-Alarme als strukturierte JSON-Daten an den Webhook-Service, der diese in osTicket-Tickets umwandelt.

**Datenfluss:**
```
Zabbix Trigger Event
    ↓
Zabbix Action (webhook)
    ↓
HTTP POST an Webhook-Service
    ↓
osTicket Ticket erstellt
```

---

## Voraussetzungen

- Zabbix Server 6.0+ (mit Webhook-Unterstützung)
- HTTP(S) Zugriff auf den Webhook-Service
- API Key für den Webhook (wird generiert)

---

## Schritt 1: Webhook-Service Informationen sammeln

Bevor Sie den Webhook in Zabbix konfigurieren, sammeln Sie folgende Informationen:

| Information | Beschreibung | Beispiel |
|-------------|-------------|---------|
| **Webhook-Host** | FQDN oder IP des Webhook-Services | `https://webhook.example.com` |
| **Webhook-Port** | Port (Standard: 443 für HTTPS) | `443` |
| **Webhook-Pfad** | API-Endpunkt | `/api/v1/zabbix/alerts` |
| **Webhook-API-Key** | Security-Token | `xxxxxxxxxxxxxx` |
| **Protokoll** | HTTP oder HTTPS | `HTTPS` |

**Komplette Webhook-URL:**
```
https://webhook.example.com:443/api/v1/zabbix/alerts
```

---

## Schritt 2: Zabbix Media Type erstellen

### 2.1 Öffnen Sie Zabbix Administration

1. Melden Sie sich als Admin in Zabbix an
2. Gehen Sie zu: **Administration → Media Types**
3. Klicken Sie auf **Create media type**

### 2.2 Füllen Sie die Konfiguration aus

**Grundlegende Einstellungen:**

| Feld | Wert |
|------|------|
| Name | `osTicket Webhook` |
| Type | `Webhook` |
| Description | `Zabbix to osTicket Integration` |

### 2.3 Fügen Sie Script Parameter ein

Der Webhook empfängt folgende 6 Parameter (in dieser Reihenfolge):

```
1. {EVENT.ID}
2. {EVENT.DATE}
3. {EVENT.TIME}
4. {EVENT.SEVERITY}
5. {TRIGGER.NAME}
6. {HOST.NAME}
```

**In Zabbix eingeben:**
1. Klicken Sie auf **Add** (Parameter hinzufügen)
2. Geben Sie für jeden Parameter das Makro ein (z.B. `{EVENT.ID}`)
3. Wiederholen Sie dies für alle 6 Parameter

**Screenshot-Anleitung:**
```
Parameter 1: {EVENT.ID}
Parameter 2: {EVENT.DATE}
Parameter 3: {EVENT.TIME}
Parameter 4: {EVENT.SEVERITY}
Parameter 5: {TRIGGER.NAME}
Parameter 6: {HOST.NAME}
```

### 2.4 Webhook Script eingeben

Kopieren Sie diesen JavaScript-Code in das **Script**-Feld:

```javascript
// osTicket Webhook Script für Zabbix
// Konvertiert Zabbix Event-Daten zu osTicket API Format

var params = JSON.parse(value);

// Erstelle HTTP Request
var request = new HttpRequest();
request.addHeader('Content-Type: application/json');
request.addHeader('X-API-Key: your-webhook-api-key');

// Baue JSON Payload auf
var payload = {
    event_id: params.event_id,              // {EVENT.ID}
    event_date: params.event_date,          // {EVENT.DATE}
    event_time: params.event_time,          // {EVENT.TIME}
    event_severity: params.event_severity,  // {EVENT.SEVERITY}
    trigger_name: params.trigger_name,      // {TRIGGER.NAME}
    host_name: params.host_name             // {HOST.NAME}
};

// Sende Request an Webhook-Service
var response = request.post(
    'https://webhook.example.com/api/v1/zabbix/alerts',
    JSON.stringify(payload)
);

// Gebe Response zurück
return response;
```

**Wichtig:** Ersetzen Sie:
- `your-webhook-api-key` → Mit dem echten API-Key
- `webhook.example.com` → Mit der echten Webhook-Host-URL

### 2.5 Test-Parameter hinzufügen (Optional)

Im Abschnitt **Test parameters** können Sie einen Test durchführen:

```
{EVENT.ID}: 12345678
{EVENT.DATE}: 2025-10-26
{EVENT.TIME}: 14:32:15
{EVENT.SEVERITY}: High
{TRIGGER.NAME}: High CPU usage on webserver-01
{HOST.NAME}: webserver-01
```

Klicken Sie auf **Test** und überprüfen Sie die Response.

---

## Schritt 3: Zabbix Action erstellen

### 3.1 Öffnen Sie Zabbix Triggers

1. Gehen Sie zu: **Configuration → Actions → Trigger actions**
2. Klicken Sie auf **Create action**

### 3.2 Füllen Sie die Action-Details aus

**Name:**
```
osTicket Integration
```

**Condition (Trigger-Auswahl):**

Sie können hier Filter setzen, z.B.:
- Nur bestimmte Trigger
- Nur bestimmte Host Groups
- Nur bestimmte Severity Levels

Beispiel: **Nur Alarms mit Severity "High" oder "Disaster"**

```
Trigger severity ≥ High
```

### 3.3 Definieren Sie die Operations (Aktionen)

Wechseln Sie zum Tab **Operations**

**Send to users:**
1. Klicken Sie auf **Add**
2. Wählen Sie einen **User** (z.B. Admin oder Zabbix System User)
3. Wählen Sie **Send only to** → **osTicket Webhook** (die Media Type, die Sie gerade erstellt haben)

**Alternative (empfohlen):**
Verwenden Sie **Custom message** für mehr Kontrolle:

1. Aktivieren Sie **Custom message**
2. Subject: `Zabbix Alert: {TRIGGER.NAME}`
3. Message: `{TRIGGER.DESCRIPTION}`

**Default message should be sent:** Ja (aktiviert)

### 3.4 Recovery Operations (Optional)

Im Tab **Recovery operations** können Sie definieren, was passiert wenn das Problem behoben ist:

```
Send to users:
- Wählen Sie den gleichen User
- Media Type: osTicket Webhook
```

Nachricht: `Problem resolved`

---

## Schritt 4: Test durchführen

### 4.1 Manuelles Test-Event erstellen

```bash
# Via Zabbix Frontend:
# 1. Gehen Sie zu Configuration → Triggers
# 2. Wählen Sie einen Test-Trigger
# 3. Klicken Sie auf den Trigger-Namen
# 4. Klicken Sie auf "Generate action"
# 5. Dies löst ein Test-Event aus
```

Oder direkt im Zabbix API:

```bash
curl -X POST http://zabbix.example.com/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "event.create",
    "params": {
      "objectid": "TRIGGER_ID",
      "source": 0,
      "object": 0,
      "acknowledged": 0,
      "severity": 4,
      "value": 1
    },
    "auth": "AUTH_TOKEN",
    "id": 1
  }'
```

### 4.2 Webhook-Response überprüfen

**Überprüfen Sie in den Zabbix Logs:**

```
Administration → Reports → Audit
```

Suchen Sie nach dem Webhook-Aufruf und überprüfen Sie:
- HTTP Status Code (200 = OK)
- Response Body
- Timestamp

### 4.3 Überprüfen Sie in osTicket

1. Melden Sie sich in osTicket an
2. Gehen Sie zu **Tickets**
3. Suchen Sie nach dem neuen Ticket mit dem Pattern `EVENT_ID: xxxxx`
4. Überprüfen Sie:
   - `name` (WER) = Hostname
   - `subject` (WAS) = EVENT_ID + Trigger-Name
   - `priority` (PRIORITÄT) = Severity-gemappt
   - `created_at` = Aktuelles Datum/Zeit

---

## Schritt 5: Webhook-Monitoring

### 5.1 Webhook-Aufrufe überprüfen

**In Zabbix:**
```
Administration → Reports → Audit
Filter: Type = "Webhook"
```

Überprüfen Sie:
- Anzahl der Aufrufe
- HTTP Status Codes
- Fehlermeldungen

### 5.2 Fehlerbehandlung

**Häufige Fehler:**

| Fehler | Ursache | Lösung |
|--------|--------|--------|
| Connection refused | Webhook-Service nicht erreichbar | Prüfen Sie IP/Port/Firewall |
| 401 Unauthorized | Falscher API-Key | Überprüfen Sie den X-API-Key Header |
| 400 Bad Request | Ungültiges JSON Format | Überprüfen Sie das Script |
| 502 Bad Gateway | osTicket API nicht erreichbar | Überprüfen Sie osTicket-Status |

---

## Schritt 6: Trigger-Konfiguration für Zabbix-Alarms

Stellen Sie sicher, dass Ihre Trigger korrekt konfiguriert sind:

### Trigger-Beispiel 1: CPU-Auslastung

```
Name: High CPU usage on {HOST.NAME}
Expression: {HOST.NAME:system.cpu.load.avg(1m)}>0.9
Severity: High
Description: CPU load exceeded 90% threshold
```

### Trigger-Beispiel 2: Memory-Auslastung

```
Name: High memory usage on {HOST.NAME}
Expression: {HOST.NAME:vm.memory.pused}>90
Severity: High
Description: Memory usage exceeded 90%
```

---

## Schritt 7: Monitoring & Troubleshooting

### 7.1 Webhook-Logs überprüfen

```bash
# Zabbix Server Logs
tail -f /var/log/zabbix/zabbix_server.log | grep -i webhook

# Webhook-Service Logs (abhängig von Implementation)
tail -f /var/log/webhook/webhook.log
```

### 7.2 Test mit cURL

Testen Sie den Webhook direkt:

```bash
curl -X POST https://webhook.example.com/api/v1/zabbix/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-webhook-api-key" \
  -d '{
    "event_id": "12345678",
    "event_date": "2025-10-26",
    "event_time": "14:32:15",
    "event_severity": "High",
    "trigger_name": "High CPU usage on webserver-01",
    "host_name": "webserver-01"
  }'
```

**Erwartete Response (HTTP 201):**
```json
{
  "status": "success",
  "ticket_id": "123456",
  "ticket_number": "OST-123456",
  "message": "Ticket created successfully"
}
```

---

## Schritt 8: Produktion-Checklist

- [ ] Media Type "osTicket Webhook" erstellt
- [ ] Script Parameters (6 Stück) in korrekter Reihenfolge eingegeben
- [ ] Webhook-URL korrekt konfiguriert
- [ ] API-Key im Script aktualisiert
- [ ] Test-Event durchgeführt
- [ ] Ticket in osTicket erstellt
- [ ] Alle 4 Felder korrekt gefüllt:
  - [ ] name = Hostname (max. 20 Zeichen)
  - [ ] subject = EVENT_ID + Trigger-Name
  - [ ] priority = Severity-gemappt
  - [ ] date_created = Deutsches Format
- [ ] Zabbix-Logs überprüft (keine Fehler)
- [ ] Produktiv-Trigger konfiguriert

---

## Tipps & Best Practices

### 1. Severity-Level sinnvoll setzen
- **Disaster** = Produktiv-System komplett ausfallen
- **High** = Kritisches Problem, aber System funktioniert noch
- **Average** = Wichtiges Problem
- **Warning** = Warnung, noch kein Problem

### 2. Trigger-Beschreibungen aussagekräftig schreiben
- Nicht: "Alert"
- Sondern: "CPU load exceeded 90% - immediate action required"

### 3. Host-Namen kurz halten
- Maximum 20 Zeichen für osTicket-Feld `name`
- Verwenden Sie kurze, sprechende Host-Namen: `web01`, `db-prod`, etc.

### 4. Webhook-URL absichern
- Verwenden Sie HTTPS
- Implementieren Sie IP-Whitelisting
- Verwenden Sie starke API-Keys

### 5. Testing vor Production
- Test-Trigger für Vorphase nutzen
- Schrittweise auf Produktion gehen
- Mit kleinen Severity Levels starten

---

## Nächste Schritte

Nach der Zabbix-Konfiguration:

1. **osTicket Setup** → Siehe `IMPLEMENTATION_OSTICKET_CUSTOM_FIELDS.md`
2. **n8n Workflow** → Siehe `IMPLEMENTATION_N8N_WORKFLOW.md`
3. **End-to-End Test** → Vollständigen Flow testen

---

**Dokument Ende**
