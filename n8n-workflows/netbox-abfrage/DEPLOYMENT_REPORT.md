# N8N Workflow Deployment Report

## Deployment Status: SUCCESS ✓

**Datum:** 2026-01-24 16:12:50 UTC

---

## Workflow Details

| Field | Value |
|-------|-------|
| **Workflow ID** | `qQXIZPWmuFR6ylWC` |
| **Workflow Name** | Test: NetBox-Abfrage Sub-Workflow |
| **Deployment Server** | http://10.1.1.180 |
| **API Endpoint** | /api/v1/workflows |
| **HTTP Method** | POST |

---

## Workflow-Struktur

### Nodes (4 Nodes)

1. **🚀 Manual Trigger** (manualTrigger)
   - Type: `n8n-nodes-base.manualTrigger`
   - Version: 1
   - Funktion: Manueller Trigger für Workflow-Start

2. **🔧 Define Test Parameters** (code)
   - Type: `n8n-nodes-base.code`
   - Version: 2
   - Funktion: Definiert Test-Parameter für NetBox-Abfrage
   - Parameters:
     - load_vms: true
     - load_lxcs: true
     - load_devices: true
     - filter_by_type: null
     - filter_by_ids: null
     - device_primary_ip_filter: true

3. **📞 Call: Primitive NetBox-Abfrage** (executeWorkflow)
   - Type: `n8n-nodes-base.executeWorkflow`
   - Version: 1
   - SubWorkflow ID: `k8qsLh2kePMYWurk`
   - Funktion: Ruft primitive NetBox-Abfrage auf

4. **📊 Process Response** (code)
   - Type: `n8n-nodes-base.code`
   - Version: 2
   - Funktion: Verarbeitet und loggt Sub-Workflow-Antwort

### Connections (3 Flows)

- Manual Trigger → Define Test Parameters
- Define Test Parameters → Call: Primitive NetBox-Abfrage
- Call: Primitive NetBox-Abfrage → Process Response

---

## Settings

| Setting | Value |
|---------|-------|
| **Execution Order** | v1 |
| **Caller Policy** | workflowsFromSameOwner |
| **Available in MCP** | False |

---

## Deployment-Prozess

### Problem: "additional properties" Error

**Original Fehler:**
```
{"message":"request/body must NOT have additional properties"}
```

**Ursache:**
Die n8n API akzeptiert nur spezifische Felder in der JSON-Payload. Die Original-Datei enthielt extra Felder wie `description`, die nicht im Request-Body erlaubt sind.

**Lösung:**
1. Entfernt `description` Feld aus der Payload
2. Hinzugefügt erforderliches `settings` Objekt
3. Payload enthält nur: `name`, `nodes`, `connections`, `settings`

### API Anfrage

```bash
POST /api/v1/workflows HTTP/1.1
Host: 10.1.1.180
X-N8N-API-KEY: [API Key]
Content-Type: application/json

{
  "name": "Test: NetBox-Abfrage Sub-Workflow",
  "nodes": [...],
  "connections": {...},
  "settings": {
    "executionOrder": "v1"
  }
}
```

**Response Status:** 200 OK

---

## Workflow Status

| Property | Value |
|----------|-------|
| **Active** | FALSE |
| **Status** | READY (Manual Trigger) |
| **Version ID** | cc461ecc-0062-45af-8a9f-fcdb41d1916a |
| **Version Counter** | 1 |
| **Created At** | 2026-01-24T16:12:50.415Z |
| **Updated At** | 2026-01-24T16:12:50.415Z |
| **Trigger Count** | 0 |

### Note zu "Active = FALSE"
Das ist NORMAL für Workflows mit Manual Trigger. Manual Trigger können jederzeit manuell ausgelöst werden und müssen nicht aktiviert sein. Der Workflow ist bereit zur Ausführung.

---

## Verwendung

### Via n8n UI
1. Öffne http://10.1.1.180
2. Gehe zu "Workflows" oder suche nach "Test: NetBox-Abfrage Sub-Workflow"
3. Öffne den Workflow
4. Klicke auf den "Test Workflow" Button
5. Oder aktiviere den Workflow in den Settings für kontinuierliche Ausführung

### Via API
```bash
# Workflow Info abrufen
curl -H "X-N8N-API-KEY: [API_KEY]" \
  http://10.1.1.180/api/v1/workflows/qQXIZPWmuFR6ylWC

# Workflow Liste
curl -H "X-N8N-API-KEY: [API_KEY]" \
  http://10.1.1.180/api/v1/workflows
```

---

## Wichtige Hinweise

1. Der Sub-Workflow `k8qsLh2kePMYWurk` muss auf dem Server existieren
2. Der API-Key ist nur für Public API Endpoints gültig
3. Manual Trigger ermöglichen flexible Test-Ausführung ohne Zeitplan
4. Logs sind verfügbar in der n8n UI unter "Executions"

---

## Debugging & Troubleshooting

### Falls der Workflow nicht startet:
1. Überprüfe, dass der Sub-Workflow `k8qsLh2kePMYWurk` existiert
2. Überprüfe die Execution Logs in der UI
3. Aktiviere Debug-Logging in den Code Nodes

### Falls Parameter nicht übergeben werden:
1. Überprüfe die Expression `={{ $json }}` im executeWorkflow Node
2. Stelle sicher, dass das Mapping korrekt ist
3. Nutze Debug-Ausgaben in den Code Nodes

---

**Deployment abgeschlossen:** 2026-01-24 16:12:50 UTC
**Status:** READY FOR EXECUTION ✓
