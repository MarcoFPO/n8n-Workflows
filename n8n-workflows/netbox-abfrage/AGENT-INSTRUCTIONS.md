# 🤖 Agent Instructions – n8n Experte

**Zielgruppe:** n8n Deployment & API Agent
**Konfigurationsdatei:** `.n8n-agent-config.json`
**Dokumentation:** Siehe `documentation.files` in der Config
**Status:** ✅ Production Ready

---

## 📋 Agent-Übersicht

Dieser Guide richtet sich an spezialisierte n8n Agenten, die API-basierte Operationen durchführen. Der Agent hat Zugriff auf:

- ✅ Vollständige n8n Server-Konfiguration
- ✅ API Key für Authentifizierung
- ✅ Alle Endpoint-Definitionen
- ✅ Umfassende Dokumentation
- ✅ Fehlerbehandlungs-Matrix

---

## 🔐 Konfiguration laden

### Schritt 1: Config-Datei laden

```bash
CONFIG_FILE="/opt/Projekte/n8n-workflows/netbox-abfrage/.n8n-agent-config.json"

# Config in Variable laden (Python)
import json
with open(CONFIG_FILE) as f:
    config = json.load(f)

# API Key extrahieren
api_key = config['authentication']['api_key']
api_url = config['n8n_server']['api_base_url']
```

### Schritt 2: Standard-Header setzen

```bash
# Aus Config laden
headers = {
    "X-N8N-API-KEY": config['http_headers']['default']['X-N8N-API-KEY'],
    "Content-Type": config['http_headers']['default']['Content-Type']
}
```

### Schritt 3: Dokumentation referenzieren

```bash
doc_path = config['documentation']['local_path']
api_ref = f"{doc_path}{config['documentation']['files']['n8n_api_reference']}"
deployment_guide = f"{doc_path}{config['documentation']['files']['n8n_deployment_guide']}"
```

---

## 🔌 API Requests durchführen

### Template: HTTP Request mit Config

```python
import requests
import json

# Config laden
with open('/opt/Projekte/n8n-workflows/netbox-abfrage/.n8n-agent-config.json') as f:
    config = json.load(f)

# Extrahieren
api_url = config['n8n_server']['api_base_url']
headers = config['http_headers']['default']

# Request durchführen
response = requests.get(
    f"{api_url}/workflows?limit=100",
    headers=headers
)

# Error-Codes aus Config überprüfen
if response.status_code != 200:
    error_mapping = config['error_codes']
    error_desc = error_mapping.get(str(response.status_code), "Unknown error")
    print(f"❌ Error {response.status_code}: {error_desc}")
else:
    print(f"✅ Success: {response.status_code}")
```

---

## 📋 Häufige Operationen

### 1. Workflows auflisten

```python
def list_workflows(limit=100):
    endpoint = config['endpoints']['workflows']['list']
    url = f"{config['n8n_server']['api_base_url']}/workflows?limit={limit}"
    return requests.get(url, headers=config['http_headers']['default'])
```

**Dokumentation:** `N8N-API-REFERENCE.md` → Workflows → GET /api/v1/workflows

---

### 2. Workflow abrufen

```python
def get_workflow(workflow_id):
    endpoint = config['endpoints']['workflows']['get']
    url = f"{config['n8n_server']['api_base_url']}/workflows/{workflow_id}"
    return requests.get(url, headers=config['http_headers']['default'])
```

**Beispiel:**
```python
workflow = get_workflow('k8qsLh2kePMYWurk')
```

---

### 3. Workflow deployen

```python
def deploy_workflow(workflow_json):
    endpoint = config['endpoints']['workflows']['create']
    url = f"{config['n8n_server']['api_base_url']}/workflows"

    response = requests.post(
        url,
        headers=config['http_headers']['default'],
        json=workflow_json
    )

    if response.status_code == 201:
        return response.json()['data']['id']
    else:
        # Fehlerbehandlung
        error = config['error_codes'].get(str(response.status_code))
        raise Exception(f"Deployment failed: {error}")
```

**Dokumentation:** `N8N-API-REFERENCE.md` → Workflows → POST /api/v1/workflows

---

### 4. Workflow ausführen

```python
def run_workflow(workflow_id, parameters=None):
    endpoint = config['endpoints']['executions']['run']
    url = f"{config['n8n_server']['api_base_url']}/rest/workflows/{workflow_id}/run"

    data = {"data": parameters} if parameters else {}

    return requests.post(
        url,
        headers=config['http_headers']['default'],
        json=data
    )
```

**Beispiel:**
```python
# Primitive: NetBox-Abfrage ausführen
params = {
    "load_vms": True,
    "load_lxcs": True,
    "load_devices": True,
    "filter_by_type": None,
    "filter_by_ids": None,
    "device_primary_ip_filter": True
}

result = run_workflow('k8qsLh2kePMYWurk', params)
```

**Dokumentation:** `USAGE-GUIDE.md` → Basis-Integration

---

### 5. Executions abrufen

```python
def get_executions(limit=50, sort="-startedAt"):
    endpoint = config['endpoints']['executions']['list']
    url = f"{config['n8n_server']['api_base_url']}/executions?limit={limit}&sort={sort}"
    return requests.get(url, headers=config['http_headers']['default'])
```

---

## 🐛 Fehlerbehandlung

### Error-Code Referenz aus Config

```python
def handle_error(status_code):
    error_desc = config['error_codes'].get(str(status_code), "Unknown error")

    if status_code == 400:
        return "Bad Request - Check parameters and JSON format"
    elif status_code == 401:
        return "Unauthorized - API Key invalid or missing"
    elif status_code == 404:
        return "Not Found - Workflow or endpoint doesn't exist"
    elif status_code == 429:
        return "Rate Limited - Slow down requests"
    else:
        return error_desc
```

---

## 📚 Dokumentation referenzieren

### Bei Fragen: Immer in Config schauen

**Für Endpoint-Details:**
```
config['documentation']['local_path'] + config['documentation']['files']['n8n_api_reference']
→ N8N-API-REFERENCE.md
```

**Für Deployment-Probleme:**
```
config['documentation']['local_path'] + config['documentation']['files']['n8n_deployment_guide']
→ N8N-DEPLOYMENT-GUIDE.md
```

**Für Sub-Workflow Integration:**
```
config['documentation']['local_path'] + config['documentation']['files']['usage_guide']
→ USAGE-GUIDE.md
```

**Für Code-Beispiele:**
```
config['documentation']['local_path'] + config['documentation']['files']['examples']
→ EXAMPLES.md
```

---

## ✅ Deployed Workflows

Die Config enthält alle aktuell deployed Workflows:

```python
workflows = config['deployed_workflows']

# Zugriff
netbox_workflow = workflows['primitive_netbox_abfrage']
print(f"ID: {netbox_workflow['id']}")
print(f"Name: {netbox_workflow['name']}")
print(f"Status: {netbox_workflow['status']}")
```

**Verfügbare Workflows:**
- `primitive_netbox_abfrage` (ID: `k8qsLh2kePMYWurk`) – Active ✅
- `test_netbox_abfrage` (ID: `qQXIZPWmuFR6ylWC`) – Inactive ⏹️
- `primitive_ki_executer` (ID: `yt2okRvNmGItRjCI`) – Active ✅

---

## 🔗 Häufige Endpoints (aus Config)

```python
# Directly from config
endpoints = config['endpoints']

# Workflows
workflows_list = endpoints['workflows']['list']      # GET /api/v1/workflows
workflows_create = endpoints['workflows']['create']  # POST /api/v1/workflows

# Executions
executions_list = endpoints['executions']['list']    # GET /api/v1/executions
executions_run = endpoints['executions']['run']      # POST /api/v1/rest/workflows/{id}/run

# Credentials
credentials_list = endpoints['credentials']['list']  # GET /api/v1/credentials
credentials_create = endpoints['credentials']['create'] # POST /api/v1/credentials
```

---

## 🎯 Agent-Workflow Template

```python
#!/usr/bin/env python3

import json
import requests
import sys

# 1. Config laden
def load_config():
    config_path = '/opt/Projekte/n8n-workflows/netbox-abfrage/.n8n-agent-config.json'
    with open(config_path) as f:
        return json.load(f)

# 2. API Request ausführen
def make_request(config, method, endpoint, data=None):
    url = f"{config['n8n_server']['api_base_url']}{endpoint}"
    headers = config['http_headers']['default']

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)

        return response
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

# 3. Error-Handling
def handle_response(response, config):
    if response.status_code >= 200 and response.status_code < 300:
        return response.json()
    else:
        error_desc = config['error_codes'].get(str(response.status_code))
        print(f"❌ Error {response.status_code}: {error_desc}")
        return None

# 4. Main
def main():
    config = load_config()

    # Beispiel: Workflows auflisten
    response = make_request(config, 'GET', '/workflows?limit=100')
    if response:
        result = handle_response(response, config)
        if result:
            print(f"✅ Success: {len(result['data'])} workflows found")
            return result

    return None

if __name__ == '__main__':
    main()
```

---

## 📞 Wenn der Agent ein Problem hat

### Fehlerbehebungs-Schritte:

1. **Config überprüfen**
   ```python
   if not config['authentication']['api_key']:
       raise Exception("API Key not configured")
   ```

2. **Dokumentation konsultieren**
   ```python
   doc = f"{config['documentation']['local_path']}{doc_file}"
   print(f"See: {doc}")
   ```

3. **Error-Code nachschlagen**
   ```python
   error_desc = config['error_codes'][str(status_code)]
   ```

4. **Request debuggen**
   ```python
   print(f"URL: {url}")
   print(f"Headers: {headers}")
   print(f"Response: {response.text}")
   ```

---

## 🚀 Best Practices für Agenten

### 1. Config immer laden
```python
config = json.load(open('.n8n-agent-config.json'))
```

### 2. Headers immer nutzen
```python
headers = config['http_headers']['default']
```

### 3. Error-Codes immer überprüfen
```python
error_info = config['error_codes'].get(str(status_code))
```

### 4. Dokumentation referenzieren
```python
doc_path = config['documentation']['local_path'] + file_name
```

### 5. Pagination nutzen
```python
limit = config['pagination']['default_limit']  # 100
max_limit = config['pagination']['max_limit']  # 250
```

---

## ✅ Agenten-Checkliste

- [ ] Config geladen
- [ ] API Key vorhanden
- [ ] Headers gesetzt
- [ ] Endpoint korrekt
- [ ] Request validiert
- [ ] Error-Handling implementiert
- [ ] Dokumentation verfügbar
- [ ] Response überprüft

---

## 📚 Referenzen in Config

```json
{
  "documentation": {
    "local_path": "/opt/Projekte/n8n-workflows/netbox-abfrage/",
    "files": {
      "n8n_api_reference": "N8N-API-REFERENCE.md",
      "n8n_deployment_guide": "N8N-DEPLOYMENT-GUIDE.md",
      "usage_guide": "USAGE-GUIDE.md",
      "examples": "EXAMPLES.md"
    }
  }
}
```

---

**Version:** 1.0 | **Status:** ✅ Production Ready | **Last Updated:** 2026-01-24

**Für den n8n Agenten: Nutze IMMER `.n8n-agent-config.json` als Single Source of Truth! 🎯**
