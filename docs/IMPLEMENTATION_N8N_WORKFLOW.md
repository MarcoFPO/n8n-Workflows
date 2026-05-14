# Implementierungsanleitung: n8n Workflow für Zabbix-osTicket Integration

**Datum:** 2025-10-26
**Version:** 1.0
**Zweck:** Anleitung zum Erstellen/Aktualisieren des n8n Workflows für die Zabbix-osTicket Integration
**Zielgruppe:** n8n Administratoren und Workflow-Developer

---

## Übersicht

Der n8n Workflow fungiert als **Webhook-Service**, der:
1. Zabbix-Alarme empfängt (HTTP POST)
2. Daten validiert und transformiert
3. osTicket Tickets erstellt
4. Logging und Error-Handling durchführt

**Datenfluss:**
```
Zabbix Trigger
    ↓
n8n Webhook Node (Empfang)
    ↓
Validierung & Daten-Transformation
    ↓
osTicket API Call (Ticket erstellen)
    ↓
Response an Zabbix
```

---

## Voraussetzungen

- n8n Installation (selbst-gehostet oder cloud)
- Zugriff auf n8n Admin Panel
- osTicket API Key (siehe IMPLEMENTATION_OSTICKET_CUSTOM_FIELDS.md)
- Webhook-Host erreichbar von Zabbix-Server

---

## Schritt 1: n8n Workflow erstellen/öffnen

### 1.1 Öffnen Sie n8n

```
URL: https://n8n.example.com/
```

### 1.2 Erstellen Sie einen neuen Workflow

1. Klicken Sie auf **+ New Workflow** (oder öffnen Sie den bestehenden Workflow)
2. Benennen Sie den Workflow: `Zabbix-osTicket Integration`
3. Speichern Sie ihn

---

## Schritt 2: Webhook Node hinzufügen (Empfang)

### 2.1 Fügen Sie einen "Webhook" Node hinzu

1. Klicken Sie auf **+** (Add Node)
2. Suchen Sie nach **"Webhook"**
3. Wählen Sie **Webhook** aus

### 2.2 Konfigurieren Sie den Webhook

| Einstellung | Wert |
|-------------|------|
| **HTTP Method** | `POST` |
| **Response Code** | `200` |
| **Response Body** | `{"status": "success"}` |
| **Authentication** | `Header Auth` |
| **Header Name** | `X-API-Key` |
| **Expected Header Value** | `YOUR_WEBHOOK_API_KEY` |

**URL kopieren:** Die URL wird angezeigt - Sie brauchen Sie für Zabbix:
```
https://n8n.example.com/webhook/UNIQUE_ID
```

---

## Schritt 3: Data Validation Node

### 3.1 Fügen Sie einen "Function" Node hinzu

1. Klicken Sie auf **+** neben dem Webhook Node
2. Suchen Sie nach **"Function"**
3. Wählen Sie **Function** (Funktion) aus

### 3.2 Validierungslogik eingeben

```javascript
// Validiere erforderliche Felder
const required = ['event_id', 'event_date', 'event_time', 'event_severity', 'trigger_name', 'host_name'];
const data = $input.first().json;

for (const field of required) {
  if (!data[field]) {
    throw new Error(`Missing required field: ${field}`);
  }
}

// Validiere host_name Länge (max. 20 Zeichen)
if (data.host_name.length > 20) {
  throw new Error(`host_name exceeds 20 characters: ${data.host_name.length}`);
}

// Validiere trigger_name Länge (max. 220 Zeichen nach EVENT_ID)
if (data.trigger_name.length > 220) {
  throw new Error(`trigger_name exceeds 220 characters`);
}

return data;
```

---

## Schritt 4: Data Transformation Node

### 4.1 Fügen Sie einen "Set" (oder "Function") Node hinzu

Dieser Node transformiert die Zabbix-Daten in osTicket-Format.

### 4.2 Geben Sie die Transformation ein

**Option A: Mit "Set" Node (UI-basiert)**

```
Assignments:

1. Name: `name`
   Value: `{{ $input.first().json.host_name }}`

2. Name: `email`
   Value: `zabbix@example.com`

3. Name: `subject`
   Value: `EVENT_ID: {{ $input.first().json.event_id }}
{{ $input.first().json.trigger_name }}`

4. Name: `message`
   Value: `Zabbix Alert`

5. Name: `priority`
   Value: (siehe Priority-Mapping unten)

6. Name: `date_created`
   Value: (siehe DateTime-Transformation unten)

7. Name: `source`
   Value: `API`

8. Name: `alert`
   Value: `true`

9. Name: `autorespond`
   Value: `true`
```

**Option B: Mit "Function" Node (Code-basiert)**

```javascript
const data = $input.first().json;

// Severity zu Priority Mapping
const severityMap = {
  'Disaster': 4,
  'High': 3,
  'Average': 2,
  'Warning': 1,
  'Information': 1,
  'Not classified': 2
};

// Konvertiere Zeit zu deutschem Format
function convertToGermanDateTime(dateStr, timeStr) {
  // dateStr: "2025-10-26" (YYYY-MM-DD)
  // timeStr: "14:32:15" (HH:MM:SS)
  const [year, month, day] = dateStr.split('-');
  return `${day}.${month}.${year} ${timeStr}`;
}

const osTicketData = {
  name: data.host_name,
  email: 'zabbix@example.com',
  subject: `EVENT_ID: ${data.event_id}\n${data.trigger_name}`,
  message: 'Zabbix Alert',
  priority: severityMap[data.event_severity] || 2,
  date_created: convertToGermanDateTime(data.event_date, data.event_time),
  source: 'API',
  alert: true,
  autorespond: true
};

return osTicketData;
```

---

## Schritt 5: osTicket API Node

### 5.1 Fügen Sie einen "HTTP Request" Node hinzu

1. Klicken Sie auf **+** neben dem Transformation Node
2. Suchen Sie nach **"HTTP Request"**
3. Wählen Sie **HTTP Request** aus

### 5.2 Konfigurieren Sie den osTicket API Call

| Einstellung | Wert |
|-------------|------|
| **Method** | `POST` |
| **URL** | `https://osticket.example.com/api/tickets.json` |
| **Authentication** | `Generic Credential Type` |
| **Headers** | Siehe unten |
| **Body** | `{{ JSON.stringify($input.first().json) }}` |
| **Response Format** | `JSON` |

### 5.3 Authentifizierung

Klicken Sie auf **+** neben **Authentication**, um einen neuen Credential zu erstellen:

```
Type: Generic Credential Type
Name: osTicket API Key
apikey: YOUR_OSTICKET_API_KEY
```

Dann setzen Sie im HTTP Request Header:

```
Header Name: X-API-Key
Header Value: {{ $credentials.osTicketAPIKey.apikey }}
```

### 5.4 Response Handling

Konfigurieren Sie die **Response**:
- **Response Code Check**: `Enabled`
- **Success Response Code**: `201` (Created)
- **Error Handler**: `Enabled`

---

## Schritt 6: Error Handling

### 6.1 Fehlerbehandlung für osTicket API Fehler

Nach dem osTicket HTTP Request Node fügen Sie einen **"If"** Node ein:

```
Condition: Response Code = 201
  True Branch: Success (next step)
  False Branch: Error logging (unten)
```

### 6.2 Error Logging Node

Fügen Sie einen **"Function"** Node für Fehler-Logging hinzu:

```javascript
const error = $input.first().json;

const errorLog = {
  timestamp: new Date().toISOString(),
  status: 'error',
  http_code: error.statusCode || 'unknown',
  zabbix_event_id: $node["Previous Node"].json.event_id,
  error_message: error.body || error.message,
  error_details: error
};

// Hier könnte ein Logging-Service aufgerufen werden
// (z.B. Datenbank, Log-Service, etc.)

return errorLog;
```

---

## Schritt 7: Success Response Node

### 7.1 Erstellen Sie einen Success Response

Fügen Sie einen **"Respondent"** Node hinzu:

```javascript
const response = {
  status: 'success',
  ticket_id: $input.first().json.ticket_id,
  ticket_number: $input.first().json.number,
  message: 'Ticket created successfully',
  zabbix_event_id: $input.first().json.event_id
};

return response;
```

---

## Schritt 8: Logging & Audit Trail

### 8.1 Optionaler Logging Node

Wenn Sie Logging-Database unterstützen, fügen Sie einen **"Database"** Node hinzu:

```sql
INSERT INTO webhook_audit_log (
  transaction_id,
  created_at,
  zabbix_event_id,
  osticket_ticket_id,
  status,
  request_json,
  response_json
) VALUES (
  :transaction_id,
  NOW(),
  :event_id,
  :ticket_id,
  :status,
  :request,
  :response
)
```

---

## Schritt 9: Workflow testen

### 9.1 Test-Payload vorbereiten

```json
{
  "event_id": "12345678",
  "event_date": "2025-10-26",
  "event_time": "14:32:15",
  "event_severity": "High",
  "trigger_name": "High CPU usage on test-server-01",
  "host_name": "test-server"
}
```

### 9.2 Workflow manuell ausführen

1. Klicken Sie auf **Execute** im n8n Workflow
2. Überprüfen Sie jeden Node:
   - ✅ Webhook empfängt Daten
   - ✅ Validierung erfolgreich
   - ✅ Transformation läuft
   - ✅ osTicket API antwortet mit 201

### 9.3 Überprüfen Sie das Ticket in osTicket

1. Melden Sie sich in osTicket an
2. Gehen Sie zu **Support → Tickets → Open**
3. Suchen Sie nach dem neuen Ticket mit `EVENT_ID: 12345678`
4. Überprüfen Sie die Felder:
   - [ ] `name` = "test-server" (max. 20 Zeichen)
   - [ ] `subject` = "EVENT_ID: 12345678\nHigh CPU usage on test-server-01"
   - [ ] `priority` = 3 (High)
   - [ ] `created_at` = "26.10.2025 14:32:15"

### 9.4 Test mit cURL

Sie können den Workflow auch direkt testen:

```bash
curl -X POST https://n8n.example.com/webhook/UNIQUE_ID \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_WEBHOOK_API_KEY" \
  -d '{
    "event_id": "12345678",
    "event_date": "2025-10-26",
    "event_time": "14:32:15",
    "event_severity": "High",
    "trigger_name": "High CPU usage on webserver-01",
    "host_name": "webserver-01"
  }'
```

**Erwartete Response (HTTP 200):**
```json
{
  "status": "success",
  "ticket_id": "123456",
  "ticket_number": "OST-123456",
  "message": "Ticket created successfully"
}
```

---

## Schritt 10: Produktion-Deployment

### 10.1 Workflow aktivieren

1. Klicken Sie auf den **Power-Button** rechts oben
2. Der Workflow ist jetzt **Active**
3. Der Webhook ist jetzt erreichbar von Zabbix

### 10.2 Webhook-URL zu Zabbix hinzufügen

Kopieren Sie die Webhook-URL aus n8n:

```
https://n8n.example.com/webhook/UNIQUE_ID
```

Verwenden Sie diese URL in der Zabbix Media Type Konfiguration:
- Siehe `IMPLEMENTATION_ZABBIX_WEBHOOK.md`

### 10.3 Monitoring aktivieren

n8n bietet **Executions Monitoring**:

1. Klicken Sie auf **Executions** im Workflow
2. Überprüfen Sie:
   - Erfolgreiche Ausführungen (grün)
   - Fehler (rot)
   - Execution Times
   - Logs

---

## Schritt 11: Erweiterte Konfiguration (Optional)

### 11.1 Retry-Logik

Falls osTicket API antwortet mit 5xx Fehler, implementieren Sie Retries:

**Zwischen HTTP Request und Error Handling:**

```javascript
// Retry-Logik
let maxRetries = 3;
let backoffFactor = 2;
let attempt = 0;

while (attempt < maxRetries) {
  try {
    // osTicket API Call
    break; // Erfolg
  } catch (error) {
    attempt++;
    if (attempt >= maxRetries) throw error;

    const waitTime = Math.pow(backoffFactor, attempt) * 1000;
    await new Promise(resolve => setTimeout(resolve, waitTime));
  }
}
```

### 11.2 Rate Limiting

Falls Sie viele Alarms erwarten, implementieren Sie Rate Limiting:

```javascript
// Zähle Requests in letzten 60 Sekunden
const rateLimit = 100; // Requests pro Minute
const currentRate = await getRequestCountLastMinute();

if (currentRate >= rateLimit) {
  throw new Error('Rate limit exceeded');
}
```

### 11.3 Custom Fields Handling (Phase 2)

Wenn Sie später Custom Fields von Zabbix füllen wollen:

```javascript
const osTicketData = {
  // Phase 1 Fields (immer gefüllt)
  name: data.host_name,
  subject: `EVENT_ID: ${data.event_id}\n${data.trigger_name}`,
  priority: severityMap[data.event_severity] || 2,

  // Phase 2 Fields (optional, wenn vorhanden in Zabbix-Daten)
  ...(data.ursache && { ursache: data.ursache }),
  ...(data.lösung && { lösung: data.lösung }),
  ...(data.störungsende && { störungsende: data.störungsende }),
  ...(data.root_ticket_id && { root_ticket: data.root_ticket_id })
};
```

---

## Schritt 12: Troubleshooting

### Problem: Webhook antwortet mit 401 (Unauthorized)

**Grund:** API-Key ist falsch oder nicht gesetzt.

**Lösung:**
1. Überprüfen Sie den API-Key in den n8n Credentials
2. Vergleichen Sie mit dem osTicket API Key
3. Stellen Sie sicher, dass der Credential korrekt ist

### Problem: osTicket antwortet mit 400 (Bad Request)

**Grund:** JSON-Format ist falsch oder Felder sind ungültig.

**Lösung:**
1. Überprüfen Sie das JSON-Format mit cURL
2. Validieren Sie Field-Namen (lowercase)
3. Überprüfen Sie Field-Längen (name max. 20 Zeichen)

### Problem: Webhook wird nicht aufgerufen

**Grund:** n8n Workflow ist nicht aktiv oder Zabbix erreicht die URL nicht.

**Lösung:**
1. Überprüfen Sie den Power-Button (muss **aktiv** sein)
2. Testen Sie die Webhook-URL mit cURL
3. Überprüfen Sie Firewall-Regeln
4. Überprüfen Sie DNS-Auflösung

### Problem: Tickets werden mit falscher Priorität erstellt

**Grund:** Severity-Mapping ist falsch.

**Lösung:**
1. Überprüfen Sie die SEVERITY_MAP Variable
2. Prüfen Sie, welche Severity-Werte Zabbix sendet
3. Testen Sie mit cURL und verschiedenen Severity-Werten

---

## Schritt 13: Production Checklist

- [ ] n8n Workflow erstellt mit allen Nodes
- [ ] Webhook Node konfiguriert (X-API-Key)
- [ ] Validierung Node implementiert
- [ ] Transformation Node mit Severity-Mapping
- [ ] osTicket HTTP Request Node mit API Key
- [ ] Error Handling implementiert
- [ ] Success Response konfiguriert
- [ ] Test-Payload erfolgreich verarbeitet
- [ ] Ticket in osTicket erstellt und überprüft
- [ ] Workflow ist **Active**
- [ ] Webhook-URL zu Zabbix hinzugefügt
- [ ] cURL Test erfolgreich
- [ ] Monitoring aktiviert
- [ ] Logs überprüft

---

## Nächste Schritte

Nach der n8n Workflow Einrichtung:

1. **Zabbix Webhook** → Siehe `IMPLEMENTATION_ZABBIX_WEBHOOK.md`
2. **osTicket Custom Fields** → Siehe `IMPLEMENTATION_OSTICKET_CUSTOM_FIELDS.md`
3. **End-to-End Test** → Alle 3 Systeme zusammen testen

---

## Links & Ressourcen

- **n8n Dokumentation:** https://docs.n8n.io/
- **osTicket API Docs:** https://docs.osticket.com/en/latest/API/
- **Zabbix Webhook Docs:** https://www.zabbix.com/documentation/current/en/manual/config/notifications/media/webhook

---

**Dokument Ende**
