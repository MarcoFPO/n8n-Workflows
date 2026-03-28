# 📚 n8n REST API Reference

**Offizielle Dokumentation:** https://docs.n8n.io/api/
**API Version:** v1
**Status:** ✅ Production Ready
**Last Updated:** 2026-01-24

---

## 🎯 Überblick

Die n8n REST API ermöglicht programmatische Automation von Workflows, Credentials, Variablen und mehr. Die API basiert auf **OpenAPI 3.0 Spezifikation** und folgt dem Basis-Pfad `/api/v1`.

---

## 🔐 Authentication

### API Key Generation

1. Öffne n8n UI: `https://your-n8n-instance.com`
2. Gehe zu **Settings** → **API**
3. Klick **Create API Key**
4. Kopiere den generierten Key

### Authentication Header

```bash
X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Beispiel cURL Request

```bash
curl -X GET https://your-n8n-instance.com/api/v1/workflows \
  -H "X-N8N-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json"
```

### Authentifizierungsfehler

| Status | Error | Lösung |
|--------|-------|--------|
| **401** | Unauthorized | API Key überprüfen oder neu generieren |
| **403** | Forbidden | Berechtigungen prüfen |

---

## 📋 Core Endpoints

### 1. **Workflows** `/api/v1/workflows`

#### GET - Workflows auflisten

```bash
GET /api/v1/workflows?limit=100&skip=0
```

**Query Parameters:**
| Parameter | Typ | Beschreibung |
|-----------|-----|-------------|
| `limit` | integer | Max. Ergebnisse (default: 100, max: 250) |
| `skip` | integer | Einträge überspringen (Pagination) |

**Response:**
```json
{
  "data": [
    {
      "id": "abc123",
      "name": "My Workflow",
      "active": true,
      "createdAt": "2025-01-24T10:00:00.000Z",
      "updatedAt": "2025-01-24T10:30:00.000Z"
    }
  ],
  "paginationData": {
    "pageSize": 100,
    "page": 1,
    "itemsCount": 1,
    "pagesCount": 1
  }
}
```

---

#### GET - Einzelnen Workflow abrufen

```bash
GET /api/v1/workflows/{workflowId}
```

**Parameter:**
- `workflowId` - Workflow ID (z.B. `k8qsLh2kePMYWurk`)

**Response:**
```json
{
  "data": {
    "id": "k8qsLh2kePMYWurk",
    "name": "Primitive: NetBox-Abfrage",
    "description": "Sub-Workflow für NetBox Queries",
    "nodes": [...],
    "connections": {...},
    "settings": {
      "executionOrder": "v1"
    },
    "active": true,
    "createdAt": "2025-01-24T10:00:00.000Z",
    "updatedAt": "2025-01-24T10:30:00.000Z"
  }
}
```

---

#### POST - Workflow erstellen

```bash
POST /api/v1/workflows
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "My New Workflow",
  "description": "Optional description",
  "nodes": [
    {
      "id": "node-1",
      "name": "Start",
      "type": "n8n-nodes-base.start",
      "position": [250, 300]
    }
  ],
  "connections": {},
  "settings": {
    "executionOrder": "v1"
  },
  "active": false
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "new-workflow-id",
    "name": "My New Workflow",
    ...
  }
}
```

---

#### PUT - Workflow aktualisieren

```bash
PUT /api/v1/workflows/{workflowId}
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Updated Workflow Name",
  "nodes": [...],
  "connections": {...}
}
```

---

#### DELETE - Workflow löschen

```bash
DELETE /api/v1/workflows/{workflowId}
```

**Response (204 No Content):** Erfolg ohne Body

---

### 2. **Executions** `/api/v1/executions`

#### GET - Ausführungen auflisten

```bash
GET /api/v1/executions?limit=50&skip=0&sort=-startedAt
```

**Query Parameters:**
| Parameter | Beschreibung |
|-----------|-------------|
| `limit` | Max. Ergebnisse |
| `skip` | Pagination |
| `sort` | Sortierung (z.B. `-startedAt` für neueste zuerst) |

**Response:**
```json
{
  "data": [
    {
      "id": "exec-123",
      "workflowId": "workflow-456",
      "startedAt": "2025-01-24T10:00:00.000Z",
      "stoppedAt": "2025-01-24T10:00:05.000Z",
      "status": "success"
    }
  ],
  "paginationData": {...}
}
```

---

#### GET - Einzelne Ausführung abrufen

```bash
GET /api/v1/executions/{executionId}
```

**Response:**
```json
{
  "data": {
    "id": "exec-123",
    "workflowId": "workflow-456",
    "status": "success",
    "data": [...]
  }
}
```

---

#### DELETE - Ausführung löschen

```bash
DELETE /api/v1/executions/{executionId}
```

---

#### POST - Workflow ausführen

```bash
POST /api/v1/rest/workflows/{workflowId}/run
Content-Type: application/json
```

**Request Body (optional):**
```json
{
  "data": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

---

### 3. **Credentials** `/api/v1/credentials`

#### GET - Credentials auflisten

```bash
GET /api/v1/credentials?limit=100
```

---

#### GET - Einzelnes Credential abrufen

```bash
GET /api/v1/credentials/{credentialId}
```

---

#### POST - Credential erstellen

```bash
POST /api/v1/credentials
```

**Request Body:**
```json
{
  "name": "My API Credentials",
  "type": "httpBasicAuth",
  "data": {
    "username": "user",
    "password": "pass"
  }
}
```

---

#### PUT - Credential aktualisieren

```bash
PUT /api/v1/credentials/{credentialId}
```

---

#### DELETE - Credential löschen

```bash
DELETE /api/v1/credentials/{credentialId}
```

---

### 4. **Variables** `/api/v1/variables`

#### GET - Variablen auflisten

```bash
GET /api/v1/variables
```

---

#### POST - Variable erstellen

```bash
POST /api/v1/variables
```

**Request Body:**
```json
{
  "key": "MY_VARIABLE",
  "value": "my-value"
}
```

---

#### PUT - Variable aktualisieren

```bash
PUT /api/v1/variables/{variableId}
```

---

#### DELETE - Variable löschen

```bash
DELETE /api/v1/variables/{variableId}
```

---

### 5. **Audit** `/api/v1/audit`

#### GET - Audit Logs abrufen

```bash
GET /api/v1/audit?limit=100&skip=0
```

---

## 📊 Request/Response Format

### Standard Response Structure

**Success Response (2xx):**
```json
{
  "data": {
    "id": "resource-id",
    "name": "resource-name",
    ...
  }
}
```

**List Response mit Pagination:**
```json
{
  "data": [
    { "id": "1", "name": "Item 1" },
    { "id": "2", "name": "Item 2" }
  ],
  "paginationData": {
    "pageSize": 100,
    "page": 1,
    "itemsCount": 2,
    "pagesCount": 1,
    "nextCursor": "eyJpZCI6MjAwfQ=="
  }
}
```

### Error Response Structure

**Error Response (4xx, 5xx):**
```json
{
  "code": 400,
  "message": "Bad Request",
  "detail": "Detailed error message"
}
```

---

## ⚠️ HTTP Status Codes

| Code | Bedeutung | Lösung |
|------|-----------|--------|
| **200 OK** | Request erfolgreich | - |
| **201 Created** | Ressource erstellt | - |
| **204 No Content** | Erfolgreich, kein Content | - |
| **400 Bad Request** | Ungültige Parameter | Gültige Parameter prüfen, JSON validieren |
| **401 Unauthorized** | API Key ungültig/fehlt | API Key überprüfen |
| **403 Forbidden** | Zugriff verweigert | Berechtigungen überprüfen |
| **404 Not Found** | Endpoint/Ressource nicht vorhanden | URL auf Tippfehler prüfen |
| **429 Too Many Requests** | Rate Limit erreicht | Anfragen verlangsamen, Batching nutzen |
| **500 Server Error** | Server-Fehler | Server-Logs prüfen, später versuchen |

---

## 🔄 Pagination

### Limit/Skip Methode

```bash
GET /api/v1/workflows?limit=100&skip=0    # Seite 1
GET /api/v1/workflows?limit=100&skip=100  # Seite 2
GET /api/v1/workflows?limit=100&skip=200  # Seite 3
```

### Cursor-basierte Pagination (empfohlen)

```bash
GET /api/v1/workflows?limit=100&cursor=<nextCursor>
```

### Limits

| Parameter | Min | Default | Max |
|-----------|-----|---------|-----|
| **limit** | 1 | 100 | 250 |
| **skip** | 0 | 0 | unbegrenzt |

---

## 🚀 Rate Limiting

### Rate Limit Verhalten

- **429 Status Code:** Zu viele Anfragen
- **Error Message:** "The service is receiving too many requests from you"

### Strategien zur Vermeidung

**Strategie 1: Retry with Backoff**
```bash
# Wartet 1 Sekunde, dann erneut versuchen
sleep 1 && curl -X GET https://your-instance.com/api/v1/workflows ...
```

**Strategie 2: Batching**
- Anfragen in kleinere Chunks aufteilen
- Delay zwischen Batches einfügen

**Strategie 3: Pagination**
- Mit `limit` und `skip` Seite für Seite durchgehen
- Verzögerung zwischen Seiten einfügen

---

## 💻 Praktische Beispiele

### Python - Workflows auflisten

```python
import requests

API_URL = "http://10.1.1.180"
API_KEY = "your_api_key_here"

headers = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

response = requests.get(
    f"{API_URL}/api/v1/workflows?limit=50",
    headers=headers
)

if response.status_code == 200:
    workflows = response.json()["data"]
    for workflow in workflows:
        print(f"✓ {workflow['name']} (ID: {workflow['id']})")
else:
    print(f"❌ Error: {response.status_code} - {response.text}")
```

---

### Bash - Workflow ausführen

```bash
#!/bin/bash

N8N_URL="http://10.1.1.180"
N8N_API_KEY="your_api_key_here"
WORKFLOW_ID="k8qsLh2kePMYWurk"

curl -X POST "$N8N_URL/api/v1/rest/workflows/$WORKFLOW_ID/run" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "load_vms": true,
      "load_lxcs": true,
      "load_devices": true,
      "filter_by_type": null,
      "filter_by_ids": null,
      "device_primary_ip_filter": true
    }
  }'
```

---

### JavaScript/Node.js - Workflow abrufen

```javascript
const axios = require('axios');

const API_URL = 'http://10.1.1.180';
const API_KEY = 'your_api_key_here';
const WORKFLOW_ID = 'k8qsLh2kePMYWurk';

const headers = {
  'X-N8N-API-KEY': API_KEY,
  'Content-Type': 'application/json'
};

axios.get(`${API_URL}/api/v1/workflows/${WORKFLOW_ID}`, { headers })
  .then(response => {
    console.log('✓ Workflow:', response.data.data.name);
    console.log('✓ Nodes:', response.data.data.nodes.length);
  })
  .catch(error => {
    console.error('❌ Error:', error.response?.status, error.response?.data?.message);
  });
```

---

## 🛠️ API Playground

### Self-Hosted n8n

Interaktive API-Dokumentation unter:
```
https://your-n8n-instance.com/api/docs/
```

**Funktionen:**
- ✅ Swagger/OpenAPI UI
- ✅ Live Testing mit echten Daten
- ✅ Request/Response Anzeige
- ✅ Parameter-Vorschläge

---

## 🔗 Wichtige Links

- **Offizielle API Docs:** https://docs.n8n.io/api/
- **API Reference:** https://docs.n8n.io/api/api-reference/
- **Authentication Guide:** https://docs.n8n.io/api/authentication/
- **Pagination Docs:** https://docs.n8n.io/api/pagination/
- **Error Handling:** https://docs.n8n.io/integrations/creating-nodes/build/reference/error-handling/
- **n8n Community:** https://community.n8n.io/
- **n8n Blog:** https://blog.n8n.io/

---

## 📝 Häufig gestellte Fragen

### F: Wie erhalte ich einen API Key?
**A:** Gehe zu n8n UI → Settings → API → Create API Key

### F: Kann ich die API von außerhalb zugreifen?
**A:** Ja, solange der n8n Server erreichbar ist und der API Key gültig ist.

### F: Was ist das Rate Limit?
**A:** n8n hat keine strikte globale Rate Limit, aber zu viele schnelle Anfragen können zu 429 führen. Implementiere Backoff-Strategie.

### F: Kann ich Workflows mit der API deployen?
**A:** Ja, mit POST `/api/v1/workflows` und PUT `/api/v1/workflows/{id}` kannst du Workflows erstellen und aktualisieren.

### F: Wie authentifiziere ich mich?
**A:** Mit dem `X-N8N-API-KEY` Header in allen Requests.

---

## ✅ Best Practices

1. **API Keys sicher speichern** - Niemals in Code hardcoden
2. **Fehlerbehandlung** - Alle Response-Status überprüfen
3. **Pagination nutzen** - Mit `limit` und `skip` große Datenmengen handhaben
4. **Rate Limits beachten** - Implementiere Backoff-Strategien
5. **Timeouts setzen** - Verhindere hängende Requests
6. **Logging** - Alle API-Calls für Debugging loggken
7. **Testing** - Teste mit API Playground vor Production

---

**Version:** 1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24

---

## 📚 Quellen

Diese Dokumentation basiert auf den folgenden offiziellen n8n Ressourcen:

- [n8n Public REST API Documentation](https://docs.n8n.io/api/)
- [API Reference](https://docs.n8n.io/api/api-reference/)
- [Authentication Guide](https://docs.n8n.io/api/authentication/)
- [Pagination Documentation](https://docs.n8n.io/api/pagination/)
- [Rate Limiting Guide](https://docs.n8n.io/integrations/builtin/rate-limits/)
- [Error Handling Documentation](https://docs.n8n.io/integrations/creating-nodes/build/reference/error-handling/)
- [Using an API Playground](https://docs.n8n.io/api/using-api-playground/)
