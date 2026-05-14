# Implementierungs-Guide: Zabbix-osTicket Integration

**Zielgruppe:** Entwickler und DevOps-Ingenieure
**Status:** Produktionsreif
**Version:** 1.0

---

## Überblick

Dieser Guide beschreibt die praktische Implementierung der Zabbix-osTicket Webhook-Integration mit konkreten Code-Beispielen.

---

## 1. Webhook-Endpunkt (Python/FastAPI)

### Grundstruktur

```python
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import httpx
import logging
import uuid

app = FastAPI(title="Zabbix-osTicket Webhook")
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================

class ZabbixAlertRequest(BaseModel):
    """Zabbix Webhook Request Body"""
    event_id: str
    event_time: str
    event_date: str
    trigger_id: str
    trigger_name: str
    trigger_status: str
    trigger_severity: str
    trigger_description: str
    trigger_url: str
    host_name: str
    host_ip: str
    item_name: str
    item_value: str
    event_tags: Optional[str] = ""
    user: str = "zabbix-automation"

    class Config:
        schema_extra = {
            "example": {
                "event_id": "12345678",
                "event_time": "2025-10-26 14:32:15",
                "event_date": "2025-10-26",
                "trigger_id": "13926",
                "trigger_name": "High CPU usage on {HOST.NAME}",
                "trigger_status": "PROBLEM",
                "trigger_severity": "High",
                "trigger_description": "CPU usage exceeded 90% threshold",
                "trigger_url": "https://zabbix.example.com/...",
                "host_name": "webserver-01",
                "host_ip": "192.168.1.100",
                "item_name": "CPU utilization",
                "item_value": "95%",
                "event_tags": "service:web,priority:high",
                "user": "zabbix-automation"
            }
        }

class OSTicketRequest(BaseModel):
    """osTicket API Request Body"""
    alert: bool = True
    autorespond: bool = True
    source: str = "API"
    name: str
    email: str
    subject: str
    message: str
    ip: str
    priority: int
    topicId: int = 1
    zabbix_event_id: str
    zabbix_trigger_id: str
    zabbix_event_time: str

class WebhookResponse(BaseModel):
    """Success Response"""
    status: str
    ticket_id: int
    ticket_number: str
    message: str
    zabbix_event_id: str
    transaction_id: str

class ErrorResponse(BaseModel):
    """Error Response"""
    status: str
    error_code: str
    message: str
    details: Optional[dict] = None
    transaction_id: str

# ============================================================================
# Configuration
# ============================================================================

import os

WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "default-secret-key")
OSTICKET_URL = os.getenv("OSTICKET_URL", "http://10.1.1.182")
OSTICKET_API_KEY = os.getenv("OSTICKET_API_KEY", "")
OSTICKET_DEFAULT_EMAIL = os.getenv("OSTICKET_DEFAULT_EMAIL", "zabbix@example.com")
OSTICKET_DEFAULT_TOPIC_ID = int(os.getenv("OSTICKET_DEFAULT_TOPIC_ID", "1"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

# ============================================================================
# Transformations
# ============================================================================

SEVERITY_MAP = {
    "Disaster": 4,
    "High": 3,
    "Average": 2,
    "Warning": 1,
    "Information": 1,
    "Not classified": 2
}

def convert_zabbix_time(zabbix_time: str) -> str:
    """Zabbix Zeit (YYYY-MM-DD HH:MM:SS) → ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)"""
    try:
        dt = datetime.strptime(zabbix_time, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        logger.error(f"Fehler bei Zeit-Konvertierung: {zabbix_time} - {e}")
        return zabbix_time

def map_severity(severity: str) -> int:
    """Severity String → osTicket Priority (1-4)"""
    return SEVERITY_MAP.get(severity, 2)

def generate_ticket_body(zabbix_data: ZabbixAlertRequest) -> str:
    """Generiert HTML-formatierte Ticket-Body"""
    html_body = f"""
    <h2>Zabbix Alert Details</h2>

    <p><strong>Problem:</strong> {zabbix_data.trigger_name}</p>
    <p><strong>Status:</strong> {zabbix_data.trigger_status}</p>
    <p><strong>Severity:</strong> {zabbix_data.trigger_severity}</p>

    <h3>Host Information</h3>
    <ul>
        <li><strong>Hostname:</strong> {zabbix_data.host_name}</li>
        <li><strong>IP Address:</strong> {zabbix_data.host_ip}</li>
    </ul>

    <h3>Event Details</h3>
    <ul>
        <li><strong>Event ID:</strong> {zabbix_data.event_id}</li>
        <li><strong>Event Time:</strong> {zabbix_data.event_time}</li>
        <li><strong>Item:</strong> {zabbix_data.item_name}</li>
        <li><strong>Current Value:</strong> {zabbix_data.item_value}</li>
    </ul>

    <h3>Description</h3>
    <p>{zabbix_data.trigger_description}</p>

    <p><a href="{zabbix_data.trigger_url}" target="_blank">View in Zabbix</a></p>

    <hr />
    <p><small>Tags: {zabbix_data.event_tags}</small></p>
    """

    return f"data:text/html,{html_body}"

# ============================================================================
# osTicket API
# ============================================================================

async def create_osticket(ticket_request: OSTicketRequest) -> dict:
    """Erstellt Ticket in osTicket mit Retry-Logik"""

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{OSTICKET_URL}/api/http.php/tickets.json",
                    json=ticket_request.dict(),
                    headers={"X-API-Key": OSTICKET_API_KEY},
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    logger.info(f"osTicket Ticket erstellt: {data}")
                    return {
                        "success": True,
                        "ticket_id": data.get("ticket_id"),
                        "ticket_number": data.get("number"),
                        "status_code": response.status_code
                    }

                elif response.status_code == 401:
                    logger.error("osTicket Authentication Error - API Key invalid")
                    raise Exception("osTicket Authentication Error")

                elif response.status_code == 429:
                    # Rate Limit - Retry mit Backoff
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_BACKOFF_FACTOR ** attempt
                        logger.warning(f"Rate Limit - Retry {attempt + 1}/{MAX_RETRIES} nach {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    raise Exception("Rate Limit exceeded")

                else:
                    raise Exception(f"osTicket API Error: {response.status_code} - {response.text}")

        except httpx.ConnectError as e:
            logger.error(f"Connection Error (Versuch {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                await asyncio.sleep(wait_time)
                continue
            raise

        except Exception as e:
            logger.error(f"Error creating osTicket (Versuch {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt == MAX_RETRIES - 1:
                raise
            wait_time = RETRY_BACKOFF_FACTOR ** attempt
            await asyncio.sleep(wait_time)

    raise Exception("Max retries exceeded")

# ============================================================================
# Webhook Endpoint
# ============================================================================

@app.post(
    "/api/v1/zabbix/alerts",
    response_model=WebhookResponse,
    status_code=201,
    tags=["Webhook"]
)
async def webhook_zabbix_alert(
    request: ZabbixAlertRequest,
    x_api_key: str = Header(None)
) -> WebhookResponse:
    """
    Zabbix Webhook Endpunkt für Alert-Integration mit osTicket

    **Authentifizierung:** X-API-Key Header erforderlich
    **Content-Type:** application/json

    **Rückgabe:** WebhookResponse mit Ticket-Details
    """

    # Transaction ID für Logging
    transaction_id = str(uuid.uuid4())

    logger.info(f"[{transaction_id}] Webhook aufgerufen - Event: {request.event_id}")

    # ====== 1. Authentifizierung ======
    if x_api_key != WEBHOOK_API_KEY:
        logger.warning(f"[{transaction_id}] Authentifizierung fehlgeschlagen")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

    try:
        # ====== 2. Daten-Transformation ======
        logger.debug(f"[{transaction_id}] Transformiere Daten...")

        iso_time = convert_zabbix_time(request.event_time)
        priority = map_severity(request.trigger_severity)
        ticket_body = generate_ticket_body(request)
        requester_name = f"{request.user} ({request.host_name})"

        # ====== 3. osTicket Request zusammenstellen ======
        ticket_request = OSTicketRequest(
            name=requester_name,
            email=OSTICKET_DEFAULT_EMAIL,
            subject=f"[Zabbix] {request.trigger_name}",
            message=ticket_body,
            ip=request.host_ip,
            priority=priority,
            topicId=OSTICKET_DEFAULT_TOPIC_ID,
            zabbix_event_id=request.event_id,
            zabbix_trigger_id=request.trigger_id,
            zabbix_event_time=iso_time,
        )

        logger.debug(f"[{transaction_id}] osTicket Request: {ticket_request}")

        # ====== 4. Ticket erstellen ======
        logger.info(f"[{transaction_id}] Erstelle osTicket Ticket...")
        result = await create_osticket(ticket_request)

        # ====== 5. Response zurückgeben ======
        response_data = WebhookResponse(
            status="success",
            ticket_id=result["ticket_id"],
            ticket_number=result["ticket_number"],
            message="Ticket created successfully",
            zabbix_event_id=request.event_id,
            transaction_id=transaction_id
        )

        logger.info(
            f"[{transaction_id}] ✓ Erfolg - Ticket {result['ticket_number']} erstellt"
        )

        return response_data

    except ValueError as e:
        logger.error(f"[{transaction_id}] Validierungsfehler: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"[{transaction_id}] Fehler: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create ticket: {str(e)}"
        )

@app.get("/health", tags=["Health"])
async def health_check():
    """Health Check Endpoint"""
    return {
        "status": "healthy",
        "service": "Zabbix-osTicket Webhook",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
        port=int(os.getenv("WEBHOOK_PORT", "8080")),
        log_level="info"
    )
```

---

## 2. Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY . .

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Port
EXPOSE 8080

# Start
CMD ["python", "-m", "uvicorn", "webhook:app", "--host", "0.0.0.0", "--port", "8080"]
```

### requirements.txt

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
httpx==0.25.2
python-multipart==0.0.6
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  zabbix-osticket-webhook:
    build: .
    container_name: zabbix-osticket-webhook
    ports:
      - "8080:8080"
    environment:
      WEBHOOK_HOST: 0.0.0.0
      WEBHOOK_PORT: 8080
      WEBHOOK_API_KEY: ${WEBHOOK_API_KEY:-your-secret-key-here}
      OSTICKET_URL: ${OSTICKET_URL:-http://osticket:8080}
      OSTICKET_API_KEY: ${OSTICKET_API_KEY:-your-osticket-api-key}
      OSTICKET_DEFAULT_EMAIL: zabbix@example.com
      OSTICKET_DEFAULT_TOPIC_ID: 1
      MAX_RETRIES: 3
      RETRY_BACKOFF_FACTOR: 2.0
    restart: unless-stopped
    networks:
      - monitoring
    volumes:
      - ./logs:/app/logs

networks:
  monitoring:
    driver: bridge
```

---

## 3. Zabbix Konfiguration

### Media Type erstellen

```
Administration → Media Types → Create Media Type

Name: osTicket Webhook
Type: Webhook
Endpoint: https://your-webhook-host/api/v1/zabbix/alerts
HTTP Method: POST
Verify SSL Certificate: Yes/No (je nach Umgebung)

Script Parameters:
{EVENT.ID}
{EVENT.TIME}
{EVENT.DATE}
{TRIGGER.ID}
{TRIGGER.NAME}
{TRIGGER.STATUS}
{TRIGGER.SEVERITY}
{HOST.NAME}
{HOST.IP}
{ITEM.NAME}
{ITEM.VALUE}
{TRIGGER.DESCRIPTION}
{TRIGGER.URL}
{EVENT.TAGS}
```

### Action erstellen

```
Configuration → Actions → Create Action

Name: Send to osTicket

Conditions:
- Trigger Value = PROBLEM

Operations:
- Send to users: (Select User)
- Send only to: osTicket Webhook (Media Type)
- Message: (Default oder Custom)

Recovery Operations:
- (Optional) Bei Recovery-Event
```

---

## 4. Testing

### Test mit cURL

```bash
# 1. Webhook testen
curl -X POST http://localhost:8080/api/v1/zabbix/alerts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "event_id": "99999999",
    "event_time": "2025-10-26 14:32:15",
    "event_date": "2025-10-26",
    "trigger_id": "13926",
    "trigger_name": "Test Alert - High CPU",
    "trigger_status": "PROBLEM",
    "trigger_severity": "High",
    "trigger_description": "CPU usage exceeded 90% - TEST EVENT",
    "trigger_url": "https://zabbix.example.com/tr_events.php?triggerid=13926",
    "host_name": "test-server-01",
    "host_ip": "192.168.1.99",
    "item_name": "CPU utilization",
    "item_value": "95%",
    "event_tags": "service:test,priority:high",
    "user": "test-automation"
  }'

# Erwartet: 201 Created mit WebhookResponse
```

### Health Check

```bash
curl http://localhost:8080/health
```

---

## 5. Logging & Monitoring

### Log-Ausgabe

```
2025-10-26 14:32:16 INFO [a1b2c3d4-e5f6-...] Webhook aufgerufen - Event: 12345678
2025-10-26 14:32:16 DEBUG [a1b2c3d4-e5f6-...] Transformiere Daten...
2025-10-26 14:32:16 INFO [a1b2c3d4-e5f6-...] Erstelle osTicket Ticket...
2025-10-26 14:32:17 INFO [a1b2c3d4-e5f6-...] osTicket Ticket erstellt: {'ticket_id': 123456, 'number': 'OST-123456'}
2025-10-26 14:32:17 INFO [a1b2c3d4-e5f6-...] ✓ Erfolg - Ticket OST-123456 erstellt
```

### Prometheus Metriken (Optional)

```python
from prometheus_client import Counter, Histogram, start_http_server

webhook_requests = Counter('webhook_requests_total', 'Total webhook requests')
webhook_successes = Counter('webhook_successes_total', 'Successful tickets created')
webhook_errors = Counter('webhook_errors_total', 'Failed webhook requests', ['error_type'])
webhook_latency = Histogram('webhook_latency_seconds', 'Webhook request latency')

start_http_server(8081)  # Metrics auf Port 8081
```

---

## 6. Deployment-Checklist

- [ ] Code & Dependencies korrekt installiert
- [ ] Umgebungsvariablen gesetzt (.env Datei)
- [ ] osTicket API Key generiert und gültig
- [ ] Webhook URL von Zabbix erreichbar (Firewall, Routing)
- [ ] SSL/TLS konfiguriert (falls produktiv)
- [ ] Logging-Verzeichnis vorhanden und Permissions korrekt
- [ ] Docker Image gebaut und getestet
- [ ] Health Check bestätigt
- [ ] Test-Alarm in Zabbix ausgelöst
- [ ] Ticket in osTicket verifiziert
- [ ] Monitoring/Alerting konfiguriert

---

**Guide Version:** 1.0
**Datum:** 2025-10-26
**Status:** Produktionsreif
