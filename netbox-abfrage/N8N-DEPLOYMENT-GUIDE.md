# 🚀 n8n Deployment Guide – Lokale Instanz

**Server:** http://10.1.1.180
**API Base URL:** http://10.1.1.180/api/v1
**Status:** ✅ Production Ready
**Last Updated:** 2026-01-24

---

## 📝 Server-Informationen

| Eigenschaft | Wert |
|---|---|
| **Host** | 10.1.1.180 |
| **Port** | 80 (HTTP) |
| **URL** | http://10.1.1.180 |
| **API Endpoint** | http://10.1.1.180/api/v1 |
| **API Key** | Vorhanden ✅ |
| **Web UI** | Verfügbar ✅ |
| **API Playground** | http://10.1.1.180/api/docs/ |

---

## 🔐 API Authentifizierung

### Gespeicherte Credentials

**Datei:** `/home/mdoehler/.env`

```env
N8N_URL=http://10.1.1.180
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDk0ZDFhYy1jMmZmLTQ5YTItOTFlMC1hMTRmOGU0ZDc2MjYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMDM3MzAxfQ.tZ72KsjUc6EuuWm5ZeTz1loMPmcMtMjO2B7ABA5dsiA
```

### API Key verwenden

```bash
N8N_URL="http://10.1.1.180"
N8N_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZDk0ZDFhYy1jMmZmLTQ5YTItOTFlMC1hMTRmOGU0ZDc2MjYiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMDM3MzAxfQ.tZ72KsjUc6EuuWm5ZeTz1loMPmcMtMjO2B7ABA5dsiA"
```

---

## 🔌 Workflow Deployment

### 1. Workflow über Web UI hinzufügen (Einfach)

```
1. Öffne http://10.1.1.180
2. Klick "Create new Workflow"
3. Importiere JSON oder erstelle manuell
4. Speichern & Aktivieren
```

---

### 2. Workflow via API erstellen (Empfohlen)

#### cURL

```bash
curl -X POST "http://10.1.1.180/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

#### Python

```python
import requests
import json

N8N_URL = "http://10.1.1.180"
N8N_API_KEY = "your_api_key"

with open("workflow.json") as f:
    workflow_data = json.load(f)

response = requests.post(
    f"{N8N_URL}/api/v1/workflows",
    headers={
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    },
    json=workflow_data
)

if response.status_code == 201:
    workflow_id = response.json()["data"]["id"]
    print(f"✓ Workflow deployed: {workflow_id}")
else:
    print(f"✗ Error: {response.status_code} - {response.text}")
```

#### Node.js

```javascript
const axios = require('axios');
const fs = require('fs');

const N8N_URL = 'http://10.1.1.180';
const N8N_API_KEY = 'your_api_key';

const workflowData = JSON.parse(fs.readFileSync('workflow.json'));

axios.post(`${N8N_URL}/api/v1/workflows`, workflowData, {
  headers: {
    'X-N8N-API-KEY': N8N_API_KEY,
    'Content-Type': 'application/json'
  }
})
.then(response => {
  console.log(`✓ Workflow deployed: ${response.data.data.id}`);
})
.catch(error => {
  console.error(`✗ Error: ${error.response?.status} - ${error.response?.data?.message}`);
});
```

---

## 📤 Workflows abrufen

### List all Workflows

```bash
curl -X GET "http://10.1.1.180/api/v1/workflows?limit=100" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

**Response:**
```json
{
  "data": [
    {
      "id": "qQXIZPWmuFR6ylWC",
      "name": "Test: NetBox-Abfrage Sub-Workflow",
      "active": false,
      "createdAt": "2026-01-24T16:12:50.000Z"
    },
    {
      "id": "k8qsLh2kePMYWurk",
      "name": "Primitive: NetBox-Abfrage",
      "active": true,
      "createdAt": "2026-01-24T15:00:00.000Z"
    }
  ],
  "paginationData": {
    "pageSize": 100,
    "page": 1,
    "itemsCount": 2,
    "pagesCount": 1
  }
}
```

---

### Get Single Workflow

```bash
curl -X GET "http://10.1.1.180/api/v1/workflows/k8qsLh2kePMYWurk" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

---

## ⚙️ Workflow Aktualisierung

### Workflow Update via API

```bash
curl -X PUT "http://10.1.1.180/api/v1/workflows/k8qsLh2kePMYWurk" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Workflow Name",
    "nodes": [...],
    "connections": {...}
  }'
```

---

## 🏃 Workflow Ausführung

### Workflow triggern

```bash
curl -X POST "http://10.1.1.180/api/v1/rest/workflows/k8qsLh2kePMYWurk/run" \
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

### Executions abrufen

```bash
curl -X GET "http://10.1.1.180/api/v1/executions?limit=50&sort=-startedAt" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

---

## 🗑️ Workflow Löschen

```bash
curl -X DELETE "http://10.1.1.180/api/v1/workflows/workflow-id-to-delete" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

---

## 🔍 Deployed Workflows

### Aktueller Status (2026-01-24)

| Workflow ID | Name | Type | Status |
|---|---|---|---|
| **k8qsLh2kePMYWurk** | Primitive: NetBox-Abfrage | Sub-Workflow | ✅ Active |
| **qQXIZPWmuFR6ylWC** | Test: NetBox-Abfrage Sub-Workflow | Test | ⏹️ Inactive |
| **yt2okRvNmGItRjCI** | Primitive: KI-Executer | Sub-Workflow | ✅ Active |

---

## 📋 Deployment Checkliste

- [ ] n8n Server erreichbar (http://10.1.1.180)
- [ ] API Key vorhanden & gültig
- [ ] Workflow JSON valide
- [ ] Abhängige Sub-Workflows deployed (falls nötig)
- [ ] Credentials konfiguriert (NetBox, SSH, etc.)
- [ ] Workflow getestet
- [ ] Execution Logs überprüft
- [ ] Workflow aktiviert

---

## ⚠️ Häufige Fehler

### Error: "request/body must NOT have additional properties"

**Ursache:** Ungültige Felder in der JSON-Struktur

**Lösung:**
```bash
# JSON gegen API Schema validieren
jq '{name, description, nodes, connections, settings: {executionOrder: "v1"}}' workflow.json > workflow-clean.json
```

---

### Error: "401 Unauthorized"

**Ursache:** API Key ungültig oder nicht im Header

**Lösung:**
```bash
# API Key überprüfen
echo $N8N_API_KEY

# Header überprüfen
curl -v ... -H "X-N8N-API-KEY: $N8N_API_KEY"
```

---

### Error: "404 Not Found"

**Ursache:** Workflow oder Endpoint existiert nicht

**Lösung:**
1. Workflow ID überprüfen
2. URL auf Tippfehler prüfen
3. Mit GET `/api/v1/workflows` Workflow-IDs abrufen

---

## 🛠️ Praktische Scripts

### Alle Workflows exportieren

```bash
#!/bin/bash

N8N_URL="http://10.1.1.180"
N8N_API_KEY="your_api_key"
EXPORT_DIR="./workflows-export"

mkdir -p "$EXPORT_DIR"

# Alle Workflows abrufen
workflows=$(curl -s -X GET "$N8N_URL/api/v1/workflows?limit=250" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | jq -r '.data[].id')

# Jeden Workflow exportieren
for workflow_id in $workflows; do
  echo "Exporting workflow: $workflow_id"
  curl -s -X GET "$N8N_URL/api/v1/workflows/$workflow_id" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    | jq '.data' > "$EXPORT_DIR/$workflow_id.json"
done

echo "✓ Export complete: $EXPORT_DIR"
```

---

### Workflow Backup

```bash
#!/bin/bash

N8N_URL="http://10.1.1.180"
N8N_API_KEY="your_api_key"
BACKUP_DIR="./backups/$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

# Alle Workflows
curl -s -X GET "$N8N_URL/api/v1/workflows?limit=250" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | jq '.data' > "$BACKUP_DIR/all-workflows.json"

# Alle Credentials (ohne sensitive Daten)
curl -s -X GET "$N8N_URL/api/v1/credentials?limit=250" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | jq '.data' > "$BACKUP_DIR/all-credentials.json"

# Alle Executions (letzten 100)
curl -s -X GET "$N8N_URL/api/v1/executions?limit=100" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  | jq '.data' > "$BACKUP_DIR/executions.json"

echo "✓ Backup created: $BACKUP_DIR"
```

---

### Workflow Status Monitoring

```bash
#!/bin/bash

N8N_URL="http://10.1.1.180"
N8N_API_KEY="your_api_key"

echo "🔍 n8n Workflow Status"
echo "===================="

workflows=$(curl -s -X GET "$N8N_URL/api/v1/workflows?limit=250" \
  -H "X-N8N-API-KEY: $N8N_API_KEY")

echo "$workflows" | jq -r '.data[] | "\(.name): \(if .active then "✅ ACTIVE" else "⏹️ INACTIVE" end)"'

echo ""
echo "Total: $(echo "$workflows" | jq '.paginationData.itemsCount')"
```

---

## 📚 Referenzen

- **n8n API Reference:** https://docs.n8n.io/api/api-reference/
- **API Playground (lokal):** http://10.1.1.180/api/docs/
- **Sub-Workflow Guide:** /opt/Projekte/n8n-workflows/netbox-abfrage/README.md
- **Allgemeine API Docs:** ./N8N-API-REFERENCE.md

---

**Version:** 1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
