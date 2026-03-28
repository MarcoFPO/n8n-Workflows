# 🤖 Agent Configuration & Documentation

**Zweck:** Vollständige n8n API Dokumentation und Konfiguration für spezialisierte Agenten
**Status:** ✅ Production Ready
**Version:** 1.0

---

## 📦 Was ist enthalten?

### 3 Agent-spezifische Dateien

```
.n8n-agent-config.json
├─ API Key & Credentials ✅
├─ Server URLs & Endpoints ✅
├─ Deployed Workflows ✅
├─ HTTP Headers ✅
└─ Error-Code Mapping ✅

AGENT-INSTRUCTIONS.md
├─ Config laden ✅
├─ API Requests ✅
├─ Fehlerbehandlung ✅
├─ Code-Beispiele ✅
└─ Häufige Operationen ✅

AGENT-SYSTEM-PROMPT.md
├─ Agent-Rolle & Verhalten ✅
├─ Authentifizierung ✅
├─ Deployed Workflows ✅
├─ Endpoints Referenz ✅
├─ Error Handling ✅
├─ Best Practices ✅
└─ Debugging Guide ✅
```

---

## 🚀 Für den Agent: So wird's verwendet

### Schritt 1: Config laden

```python
import json

# Config-Datei laden
with open('/opt/Projekte/n8n-workflows/netbox-abfrage/.n8n-agent-config.json') as f:
    config = json.load(f)

# Zugriff auf alle Infos
api_key = config['authentication']['api_key']
api_url = config['n8n_server']['api_base_url']
headers = config['http_headers']['default']
```

---

### Schritt 2: API Request ausführen

```python
import requests

# Headers aus Config
headers = {
    "X-N8N-API-KEY": config['authentication']['api_key'],
    "Content-Type": "application/json"
}

# Request
response = requests.get(
    f"{config['n8n_server']['api_base_url']}/workflows",
    headers=headers
)
```

---

### Schritt 3: Error-Handling

```python
# Error-Code aus Config
if response.status_code != 200:
    error_desc = config['error_codes'].get(str(response.status_code))
    print(f"❌ Error {response.status_code}: {error_desc}")
```

---

## 📋 Config-Struktur

```json
{
  "n8n_server": {
    "base_url": "http://10.1.1.180",
    "api_base_url": "http://10.1.1.180/api/v1"
  },
  "authentication": {
    "method": "API_KEY",
    "api_key": "eyJhbGc...",
    "header_name": "X-N8N-API-KEY"
  },
  "endpoints": {
    "workflows": {
      "list": "GET /api/v1/workflows",
      "create": "POST /api/v1/workflows",
      "update": "PUT /api/v1/workflows/{workflowId}",
      "delete": "DELETE /api/v1/workflows/{workflowId}"
    },
    "executions": {
      "list": "GET /api/v1/executions",
      "run": "POST /api/v1/rest/workflows/{workflowId}/run"
    }
  },
  "deployed_workflows": {
    "primitive_netbox_abfrage": {
      "id": "k8qsLh2kePMYWurk",
      "status": "active"
    }
  },
  "documentation": {
    "local_path": "/opt/Projekte/n8n-workflows/netbox-abfrage/",
    "files": {
      "n8n_api_reference": "N8N-API-REFERENCE.md",
      "n8n_deployment_guide": "N8N-DEPLOYMENT-GUIDE.md",
      "examples": "EXAMPLES.md"
    }
  }
}
```

---

## 🔌 Hauptfunktionen

### Workflows verwalten
```python
# Auflisten
/api/v1/workflows?limit=100

# Abrufen
/api/v1/workflows/{workflowId}

# Erstellen
POST /api/v1/workflows

# Aktualisieren
PUT /api/v1/workflows/{workflowId}

# Löschen
DELETE /api/v1/workflows/{workflowId}
```

### Executions verwalten
```python
# Auflisten
/api/v1/executions?limit=50&sort=-startedAt

# Abrufen
/api/v1/executions/{executionId}

# Workflow ausführen
POST /api/v1/rest/workflows/{workflowId}/run
```

### Credentials verwalten
```python
# Auflisten
/api/v1/credentials

# Erstellen
POST /api/v1/credentials

# Aktualisieren
PUT /api/v1/credentials/{credentialId}

# Löschen
DELETE /api/v1/credentials/{credentialId}
```

---

## 🎯 Deployed Workflows (aktuell)

| ID | Name | Status | Type |
|---|---|---|---|
| `k8qsLh2kePMYWurk` | Primitive: NetBox-Abfrage | ✅ Active | Sub-Workflow |
| `qQXIZPWmuFR6ylWC` | Test: NetBox-Abfrage Sub-Workflow | ⏹️ Inactive | Test |
| `yt2okRvNmGItRjCI` | Primitive: KI-Executer | ✅ Active | Sub-Workflow |

---

## 📚 Dokumentations-Links in Config

```python
# Alle Doku-Pfade aus Config abrufen
doc_base = config['documentation']['local_path']
docs = config['documentation']['files']

# Beispiel
api_ref = f"{doc_base}{docs['n8n_api_reference']}"
# → /opt/Projekte/n8n-workflows/netbox-abfrage/N8N-API-REFERENCE.md
```

---

## ⚠️ Error-Codes (aus Config)

```python
errors = config['error_codes']

# Beispiele:
400: "Bad Request - Invalid parameters"
401: "Unauthorized - API Key invalid"
404: "Not Found - Resource doesn't exist"
429: "Too Many Requests - Rate limited"
500: "Server Error - Server problem"
```

---

## ✅ Agent-Workflow

```
1. Benutzer-Anfrage → Agent
2. Agent: Config laden
3. Agent: Dokumentation lesen (falls Fragen)
4. Agent: API-Request mit Config-Daten
5. Agent: Error-Handling mit Config error_codes
6. Agent: Response formatieren
7. Agent: Ergebnis an Benutzer
```

---

## 🛠️ Praktische Code-Beispiele

### Python

```python
import json
import requests

# Config laden
with open('.n8n-agent-config.json') as f:
    config = json.load(f)

# API Request
def list_workflows():
    response = requests.get(
        f"{config['n8n_server']['api_base_url']}/workflows?limit=100",
        headers=config['http_headers']['default']
    )

    if response.status_code == 200:
        return response.json()['data']
    else:
        error = config['error_codes'][str(response.status_code)]
        raise Exception(f"Error: {error}")
```

### Bash

```bash
#!/bin/bash

CONFIG_FILE=".n8n-agent-config.json"
API_KEY=$(jq -r '.authentication.api_key' "$CONFIG_FILE")
BASE_URL=$(jq -r '.n8n_server.api_base_url' "$CONFIG_FILE")

curl -X GET "$BASE_URL/workflows" \
  -H "X-N8N-API-KEY: $API_KEY" \
  -H "Content-Type: application/json"
```

---

## 📞 Wenn der Agent ein Problem hat

### Problem: "401 Unauthorized"
```
Ursache: API Key ungültig
Lösung: Config überprüfen, API Key aus Config laden
```

### Problem: "404 Not Found"
```
Ursache: Workflow existiert nicht
Lösung: Mit GET /workflows alle IDs abrufen
```

### Problem: "400 Bad Request"
```
Ursache: Ungültige Parameter oder JSON
Lösung: N8N-API-REFERENCE.md konsultieren, JSON validieren
```

---

## 🎯 Agent-Verantwortung

### MUST (absolut notwendig)
- ✅ Config-Datei laden
- ✅ API Key aus Config verwenden
- ✅ HTTP Headers komplett setzen
- ✅ Error-Status überprüfen
- ✅ Error-Code Mapping nutzen

### SHOULD (empfohlen)
- ✅ Benutzer über Status informieren
- ✅ Dokumentation referenzieren
- ✅ Request-Parameter validieren
- ✅ Pagination beachten
- ✅ Rate Limits beachten

### SHOULD NOT (vermeiden)
- ❌ API Key hardcoden
- ❌ Requests ohne Error-Handling
- ❌ Falsche Base URL verwenden
- ❌ Workflows ohne Validierung deployen

---

## 📊 Gesamtstruktur

```
Project Root: /opt/Projekte/n8n-workflows/netbox-abfrage/

├─ .n8n-agent-config.json          ← Config & Credentials
├─ AGENT-INSTRUCTIONS.md            ← How-to Guide
├─ AGENT-SYSTEM-PROMPT.md           ← System Prompt
├─ AGENT-README.md                  ← This file
│
├─ N8N-API-REFERENCE.md             ← REST API Docs
├─ N8N-DEPLOYMENT-GUIDE.md          ← Deployment Guide
│
├─ README.md                         ← Sub-Workflow Overview
├─ INPUT-SPEC.md                    ← Parameters
├─ OUTPUT-SPEC.md                   ← Output Format
├─ USAGE-GUIDE.md                   ← Integration Guide
├─ EXAMPLES.md                       ← Code Examples
│
├─ netbox-abfrage.json              ← Workflow Definition
└─ test-workflow.json               ← Test Workflow
```

---

## 🔗 Quick Links (für Agent)

| Was | Wo |
|-----|-----|
| **Config & Credentials** | `.n8n-agent-config.json` |
| **How to deploy** | `AGENT-INSTRUCTIONS.md` |
| **API Reference** | `N8N-API-REFERENCE.md` |
| **Code Examples** | `EXAMPLES.md` |
| **Deployment** | `N8N-DEPLOYMENT-GUIDE.md` |

---

## ✅ Agent Ready Checklist

- [ ] Config-Datei gefunden
- [ ] API Key aus Config extrahiert
- [ ] Base URL korrekt
- [ ] Headers zusammengestellt
- [ ] Error-Codes gemappt
- [ ] Dokumentation erreichbar
- [ ] Code-Beispiele verfügbar

---

## 🎓 Learning Path für Agent

### Anfänger
1. AGENT-README.md (dieses Dokument)
2. AGENT-SYSTEM-PROMPT.md (Verhalten)
3. AGENT-INSTRUCTIONS.md (Praktische Anleitung)

### Fortgeschrittene
1. N8N-API-REFERENCE.md (vollständige API)
2. EXAMPLES.md (10 Szenarien)
3. N8N-DEPLOYMENT-GUIDE.md (Deployment)

### Experte
1. Sub-Workflow Dokumentation (INPUT/OUTPUT-SPEC)
2. Lokale Config optimieren
3. Eigene Agents konfigurieren

---

## 🚀 Agent Ready!

Die Konfiguration ist **vollständig** und **produktionsreif**.

Der Agent kann sofort:
- ✅ n8n API ansprechmen
- ✅ Workflows deployen
- ✅ Executions verwalten
- ✅ Errors handhaben
- ✅ Dokumentation nutzen

**Viel Erfolg!** 🎯

---

**Version:** 1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24
