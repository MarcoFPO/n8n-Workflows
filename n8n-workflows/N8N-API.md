# n8n – API & Kommunikations-Referenz

## Northbound – Eingehende Aufrufe

n8n wird **ausschließlich** über die n8n REST API angesteuert. Direkter Zugriff von außen ist nicht vorgesehen.

### Authentifizierung

```http
X-N8N-API-KEY: <key-aus-vaultwarden>
```

Token-Quelle: Vaultwarden Org „Bots" → `n8n API Key`

---

## Workflow triggern (bestehender Workflow)

```http
POST /api/v1/workflows/{workflow_id}/activate
Host: 10.1.1.180:5678
X-N8N-API-KEY: <key>
```

**Manuelle Execution starten:**

```http
POST /api/v1/executions
Host: 10.1.1.180:5678
X-N8N-API-KEY: <key>
Content-Type: application/json

{
  "workflowId": "<workflow_id>",
  "data": {
    "key": "value"
  }
}
```

**Antwort:**

```json
{
  "id": "12345",
  "workflowId": "abc123",
  "status": "running",
  "startedAt": "2025-11-17T10:00:00.000Z"
}
```

---

## Workflow-Status abfragen

```http
GET /api/v1/executions/{execution_id}
Host: 10.1.1.180:5678
X-N8N-API-KEY: <key>
```

**Antwort:**

```json
{
  "id": "12345",
  "status": "success | running | error | waiting",
  "startedAt": "2025-11-17T10:00:00.000Z",
  "stoppedAt": "2025-11-17T10:01:23.000Z",
  "data": {}
}
```

---

## Alle Workflows auflisten

```http
GET /api/v1/workflows
Host: 10.1.1.180:5678
X-N8N-API-KEY: <key>
```

**Antwort:**

```json
{
  "data": [
    {
      "id": "abc123",
      "name": "Incident-Bearbeitung",
      "active": true,
      "createdAt": "2025-11-17T09:00:00.000Z"
    }
  ],
  "nextCursor": null
}
```

---

## Outbound – Southbound-Aufrufe von n8n

n8n ruft folgende externe Dienste auf. Die Credentials werden in der **n8n Credential-Verwaltung** gespeichert (befüllt aus Vaultwarden beim Setup).

### Orchestrator (LXC 131 :8420)

```http
POST http://10.1.1.207:8420/api/v1/workflows
X-Internal-Token: <shared-secret>
Content-Type: application/json

{
  "task_id": "uuid",
  "type": "infrastructure | software | documentation",
  "title": "Kurzbeschreibung",
  "description": "Vollständige Aufgabenbeschreibung",
  "priority": "normal | high",
  "context": {},
  "callback_url": "http://10.1.1.180:5678/webhook/<webhook_id>"
}
```

### Claude API (LXC 105 :3001)

```http
POST http://10.1.1.105:3001/v1/chat/completions
Authorization: Bearer <claude-api-key>
Content-Type: application/json

{
  "model": "claude-sonnet-4-6",
  "messages": [
    {"role": "user", "content": "Analysiere..."}
  ]
}
```

### Zabbix (VM 103)

```http
POST http://10.1.1.103/zabbix/api_jsonrpc.php
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "problem.get",
  "params": {},
  "auth": "<zabbix-api-token>",
  "id": 1
}
```

### NetBox (VM 102)

```http
GET http://10.1.1.102/api/dcim/devices/
Authorization: Token <netbox-api-token>
```

### Proxmox (10.1.1.100)

```http
POST https://10.1.1.100:8006/api2/json/nodes/{node}/lxc/{vmid}/snapshot
Authorization: PVEAPIToken=<proxmox-api-token>
Content-Type: application/json

{
  "snapname": "pre-update-20251117",
  "description": "Vor System-Update"
}
```

### SSH-Targets

n8n nutzt den eingebauten SSH-Node für direkte Befehlsausführung auf LXCs/VMs.

---

## Webhook-Eingang (Trigger)

### Znuny → n8n (Incident-Bearbeitung)

Znuny triggert den Incident-Workflow sobald Zabbix ein Ticket erstellt hat:

```http
POST http://10.1.1.180:5678/webhook/incident
Content-Type: application/json

{
  "ticket_id": "12345",
  "ticket_number": "2025111700001",
  "subject": "Server down: LXC-107",
  "priority": "high",
  "state": "new",
  "queue": "Monitoring",
  "body": "Zabbix Alert: CPU > 95% auf LXC-107 seit 5 Minuten",
  "created_by": "zabbix@intern",
  "created_at": "2025-11-17T10:00:00Z"
}
```

| Quelle | Webhook-Pfad | Workflow |
|--------|-------------|----------|
| Znuny (LXC 118) | `/webhook/incident` | Incident-Bearbeitung |
| Externe Systeme | `/webhook/custom` | Konfigurierbar |

---

## Znuny-Integration (Outbound)

n8n liest und aktualisiert Znuny-Tickets über die Znuny REST API:

### Ticket lesen

```http
GET http://10.1.1.182/znuny/api/v1/tickets/{ticket_id}
Authorization: Bearer <znuny-api-token>
```

### Ticket aktualisieren (Artikel hinzufügen)

```http
POST http://10.1.1.182/znuny/api/v1/tickets/{ticket_id}/articles
Authorization: Bearer <znuny-api-token>
Content-Type: application/json

{
  "Subject": "Automatische Remediation abgeschlossen",
  "Body": "n8n hat die Störung behoben: <Ergebnis>",
  "ContentType": "text/plain; charset=utf-8",
  "SenderType": "agent",
  "IsVisibleForCustomer": false
}
```

### Ticket schließen

```http
PATCH http://10.1.1.182/znuny/api/v1/tickets/{ticket_id}
Authorization: Bearer <znuny-api-token>
Content-Type: application/json

{
  "State": "closed successful",
  "PendingTime": null
}
```

---

## Callback von Orchestrator an n8n

Nach Abschluss eines delegierten Tasks ruft der Orchestrator die n8n-Callback-URL auf:

```http
POST http://10.1.1.180:5678/webhook/<callback_id>
Content-Type: application/json

{
  "workflow_id": "uuid",
  "task_id": "uuid",
  "status": "completed | failed",
  "result": "Zusammenfassung",
  "artifacts": [],
  "duration_seconds": 142
}
```

---

## Credentials in n8n (Credential-Verwaltung)

| Credential-Name (n8n intern) | Typ | Quelle (Vaultwarden) |
|-----------------------------|-----|---------------------|
| `Claude API` | HTTP Header Auth | `Claude API Key` |
| `Zabbix API` | HTTP Header Auth | `Zabbix API Token` |
| `Znuny API` | HTTP Header Auth | `Znuny API Token` |
| `NetBox API` | HTTP Header Auth | `NetBox API Token` |
| `Proxmox API` | HTTP Header Auth | `Proxmox API Token` |
| `Orchestrator Internal` | HTTP Header Auth | `Internal Service Token` |
| `SSH Key` | SSH | lokal auf LXC 117 (ed25519) |

---

## n8n Healthcheck

```http
GET http://10.1.1.180:5678/healthz
```

**Antwort:**

```json
{"status": "ok"}
```

---

## Deployment-Referenz

| Parameter | Wert |
|-----------|------|
| LXC | 117 |
| IP | 10.1.1.180 |
| Port | 5678 |
| Dienst | `n8n.service` (systemd) |
| Logs | `journalctl -u n8n --tail 100` |
| API-Basis-URL | `http://10.1.1.180:5678/api/v1` |
