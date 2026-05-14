# Zabbix to osTicket Integration - Setup Guide

**Version:** 1.0.0
**Date:** 2025-10-26
**Status:** Ready for Deployment

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Zabbix Setup](#zabbix-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This integration automatically creates osTicket tickets when Zabbix triggers fire PROBLEM events and closes/resolves them when events are RESOLVED.

### Features

- **Automatic Ticket Creation**: Creates osTicket tickets for Zabbix PROBLEM events
- **Ticket Closure**: Closes tickets when Zabbix events are RESOLVED
- **Field Mapping**: Maps Zabbix severity to osTicket priority
- **Custom Fields**: Stores complete Zabbix event information in osTicket custom fields
- **Error Handling**: Includes retry logic and comprehensive logging
- **Webhook Security**: Optional HMAC signature verification

### Benefits

- ✅ No manual ticket creation for alerts
- ✅ Automatic ticket correlation with events
- ✅ Complete audit trail of all changes
- ✅ Scalable for large volume environments
- ✅ Easy to extend and customize

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Zabbix Monitoring System                                   │
│  - Trigger Event (PROBLEM/RESOLVED)                         │
│  - Calls Media Type: Webhook                                │
│  - Sends event data to webhook endpoint                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP POST
                       │ JSON Payload
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Webhook Service (Port 8000)                        │
│  - Receives Zabbix events                                   │
│  - Validates payload                                        │
│  - Maps severity to priority                                │
│  - Transforms data format                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP POST
                       │ Ticket Data
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  osTicket API Endpoint                                      │
│  - /api/tickets.json (create)                               │
│  - Stores custom Zabbix fields                              │
│  - Assigns to Zabbix topic                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  osTicket Database                                          │
│  - Ticket Storage                                           │
│  - Custom Field Values                                      │
│  - Audit Trail                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Components

### 1. osTicket Configuration

**Created Components:**

| Component | ID | Description |
|-----------|-----|-------------|
| Help Topic | 12 | "Zabbix Monitoring" |
| Custom Form | 7 | Zabbix tab form |
| Custom Fields | 40-48 | 9 Zabbix-specific fields |
| API Key | 54BF4029D1C92F730A6A8FC211C3A514 | API access key |

**Custom Fields (Form 2 & 7):**

| Field | Type | Description | Form |
|-------|------|-------------|------|
| zabbix_event_id | text | Unique event ID from Zabbix | 2, 7 |
| affected_object | text | The affected host/item (WER) | 2, 7 |
| event_status | text | PROBLEM or RESOLVED | 2, 7 |
| severity | text | Severity level name | 2, 7 |
| host_name | text | Hostname from Zabbix | 2, 7 |
| event_url | text | Link to Zabbix event | 2, 7 |
| event_time | datetime | When event was triggered | 2, 7 |
| source | text | Always "Zabbix" | 2, 7 |
| trigger_name | text | Name of the trigger | 2, 7 |

### 2. FastAPI Webhook Service

**File:** `zabbix_osticket_webhook.py`

**Features:**
- Receives webhook events from Zabbix
- Validates JSON payload
- Maps Zabbix severity to osTicket priority
- Creates/updates osTicket tickets
- Error handling and logging
- Health check endpoint

**Dependencies:**
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.4.2
- Requests 2.31.0
- Python 3.9+

**Endpoints:**
- `GET /health` - Health check
- `POST /webhook/zabbix` - Zabbix webhook receiver
- `POST /webhook/test` - Test endpoint

### 3. Zabbix Webhook Script

**File:** `zabbix_webhook_script.sh`

**Purpose:**
- Bash script that Zabbix calls when events occur
- Formats event data as JSON
- Sends to FastAPI webhook service
- Handles optional HMAC signing

---

## 📦 Installation

### Step 1: osTicket Configuration (✅ COMPLETED)

The following have already been configured:

- ✅ Help Topic "Zabbix Monitoring" created (ID: 12)
- ✅ Custom Form created (ID: 7)
- ✅ 9 Custom Fields added to forms
- ✅ API Key generated: `54BF4029D1C92F730A6A8FC211C3A514`

### Step 2: Install FastAPI Webhook Service

```bash
# On the webhook server (or osTicket host)

# 1. Clone/download the service files
cd /opt/Projekte/n8n-workflows

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create environment configuration
cp .env.example .env

# 4. Edit .env with your settings
nano .env
# Required:
#   OSTICKET_URL=http://10.1.1.182/api
#   OSTICKET_API_KEY=54BF4029D1C92F730A6A8FC211C3A514

# 5. Test the service
python3 zabbix_osticket_webhook.py

# 6. (Optional) Run as systemd service
sudo cp zabbix_osticket_webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zabbix_osticket_webhook
sudo systemctl start zabbix_osticket_webhook
```

### Step 3: Copy Zabbix Script

```bash
# On Zabbix server

# 1. Copy webhook script
sudo cp zabbix_webhook_script.sh /usr/lib/zabbix/alertscripts/zabbix_webhook_script.sh

# 2. Make executable
sudo chmod +x /usr/lib/zabbix/alertscripts/zabbix_webhook_script.sh

# 3. Ensure Zabbix user can execute
sudo chown zabbix:zabbix /usr/lib/zabbix/alertscripts/zabbix_webhook_script.sh

# 4. Create log file
sudo touch /var/log/zabbix_webhook.log
sudo chmod 666 /var/log/zabbix_webhook.log
```

---

## ⚙️ Configuration

### FastAPI Service Configuration

Create `.env` file:

```bash
# osTicket API Configuration
OSTICKET_URL=http://10.1.1.182/api
OSTICKET_API_KEY=54BF4029D1C92F730A6A8FC211C3A514

# Webhook Security (optional)
ZABBIX_WEBHOOK_SECRET=your_secret_key_here

# Logging
LOG_FILE=/var/log/zabbix_osticket_webhook.log

# Server
HOST=0.0.0.0
PORT=8000
```

### Systemd Service File

Create `/etc/systemd/system/zabbix_osticket_webhook.service`:

```ini
[Unit]
Description=Zabbix osTicket Webhook Service
After=network.target

[Service]
Type=simple
User=zabbix
WorkingDirectory=/opt/Projekte/n8n-workflows
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/Projekte/n8n-workflows/.env
ExecStart=/usr/bin/python3 /opt/Projekte/n8n-workflows/zabbix_osticket_webhook.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy (Optional)

```nginx
upstream zabbix_webhook {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name webhook.zabbix.local;

    location / {
        proxy_pass http://zabbix_webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🔌 Zabbix Setup

### Step 1: Create Media Type

In Zabbix Web Interface:

1. Go to **Administration → Media Types → Create Media Type**

2. Fill in the form:
   - **Name:** `osTicket Webhook`
   - **Type:** `Script`
   - **Script name:** `zabbix_webhook_script.sh`

3. Add Script Parameters (in order):
   - `{ALERT.SENDTO}` - Webhook URL
   - `{ALERT.MESSAGE}` - Secret (optional)
   - `{EVENT.ID}` - Event ID
   - `{TRIGGER.ID}` - Trigger ID
   - `{TRIGGER.NAME}` - Trigger Name
   - `{HOST.NAME}` - Host Name
   - `{ITEM.NAME}` - Item Name
   - `{EVENT.CLOCK}` - Event Time
   - `{EVENT.VALUE}` - Event Value (0/1)
   - `{EVENT.SEVERITY}` - Severity Level
   - `{EVENT.URL}` - Event URL

4. Click **Add**

### Step 2: Create User for Notifications

In Zabbix Web Interface:

1. Go to **Administration → Users → Create User**

2. Fill in:
   - **Username:** `osTicket Webhook`
   - **Name:** `osTicket`
   - **Surname:** `Integration`
   - **User type:** `Zabbix User`
   - **Groups:** Select appropriate monitoring groups

3. Go to **Media** tab:
   - **Add** new media
   - **Type:** `osTicket Webhook`
   - **Send to:** `http://webhook-server:8000/webhook/zabbix`
   - **When active:** `1-7,00:00-24:00` (Always)
   - **Status:** `Enabled`

### Step 3: Create Action

In Zabbix Web Interface:

1. Go to **Configuration → Actions → Create Action**

2. **Action** tab:
   - **Name:** `Send to osTicket`
   - **Eventsource:** `Trigger`
   - **Enabled:** ✅

3. **Conditions** tab (examples):
   - Add condition if you want to filter triggers
   - Or leave empty to process all triggers

4. **Operations** tab:
   - Click **New**
   - **Operation type:** `Send message`
   - **Send to users:** Select `osTicket Webhook` user
   - **Send only to:** Select the Media Type
   - **Default message:** Leave empty or customize

5. **Recovery Operations** tab (for RESOLVED events):
   - Click **New**
   - **Operation type:** `Send message`
   - **Send to users:** Select `osTicket Webhook` user
   - **Custom message:** Leave empty

6. Click **Add**

### Step 4: Test Action

To test:

1. Create a test trigger
2. Wait for condition to be met
3. Check:
   - Zabbix logs: `/var/log/zabbix/zabbix_server.log`
   - Webhook logs: `/var/log/zabbix_webhook.log`
   - FastAPI logs: `/var/log/zabbix_osticket_webhook.log`
   - osTicket: Check for new ticket in "Zabbix Monitoring" topic

---

## 🧪 Testing

### Test 1: API Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "Zabbix osTicket Webhook Service",
  "version": "1.0.0"
}
```

### Test 2: Webhook Test Endpoint

```bash
curl -X POST http://localhost:8000/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Test 3: Create Test Event Manually

```bash
curl -X POST http://localhost:8000/webhook/zabbix \
  -H "Content-Type: application/json" \
  -d '{
    "event": {
      "eventid": "test_001",
      "triggerid": "10001",
      "triggername": "Test Trigger - High CPU",
      "host": "test-server",
      "item": "cpu_load",
      "eventtime": "'$(date +%s)'",
      "eventvalue": "1",
      "severity": "4",
      "eventurl": "http://zabbix.local/events"
    }
  }'
```

Expected response (201 Created):
```json
{
  "status": "success",
  "message": "Ticket created for Zabbix event",
  "ticket_id": "123",
  "action": "created"
}
```

### Test 4: osTicket API Test

```bash
python3 test_osticket_api.py
```

---

## 🔧 Troubleshooting

### Issue: API Key 401 Unauthorized

**Problem:** osTicket API returns "Valid API key required"

**Solutions:**
1. Verify API key in database:
   ```bash
   mysql osticket -e "SELECT id, apikey, ipaddr FROM ost_api_key;"
   ```

2. Check API key is active:
   ```bash
   mysql osticket -e "SELECT isactive FROM ost_api_key WHERE apikey='YOUR_KEY';"
   ```

3. Verify IP restrictions:
   ```bash
   # If ipaddr='0.0.0.0' or '%', should accept all IPs
   mysql osticket -e "UPDATE ost_api_key SET ipaddr='%' WHERE apikey='YOUR_KEY';"
   ```

### Issue: FastAPI Service Won't Start

**Problem:** Port 8000 already in use

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn zabbix_osticket_webhook:app --host 0.0.0.0 --port 8001
```

### Issue: Webhook Logs Show 500 Errors

**Problem:** Internal server error in FastAPI

**Check:**
1. osTicket API is accessible:
   ```bash
   curl http://10.1.1.182/api/tickets.json \
     -H "X-API-Key: YOUR_KEY"
   ```

2. Custom fields exist:
   ```bash
   mysql osticket -e "SELECT * FROM ost_form_field WHERE form_id=2 AND sort>=40;"
   ```

3. Help topic exists:
   ```bash
   mysql osticket -e "SELECT * FROM ost_help_topic WHERE topic='Zabbix Monitoring';"
   ```

### Issue: Webhook Logs Show Network Errors

**Problem:** Can't reach osTicket API

**Check:**
1. Network connectivity:
   ```bash
   ping 10.1.1.182
   curl http://10.1.1.182/api
   ```

2. Check firewall rules:
   ```bash
   sudo iptables -L -n | grep 1.1.1.182
   ```

3. Check osTicket API endpoint:
   ```bash
   ssh root@10.1.1.182 'curl http://localhost/api/tickets.json'
   ```

---

## 📊 Severity Mapping

**Zabbix → osTicket Priority:**

| Zabbix Severity | osTicket Priority | Level |
|-----------------|------------------|-------|
| Not classified (0) | 1 | Low |
| Information (1) | 1 | Low |
| Warning (2) | 2 | Medium |
| Average (3) | 2 | Medium |
| High (4) | 3 | High |
| Disaster (5) | 3 | High |

---

## 📝 Event Workflow

### PROBLEM Event (eventvalue = 1)

```
1. Zabbix trigger fires (PROBLEM state)
   ↓
2. Media Type calls zabbix_webhook_script.sh
   ↓
3. Script sends JSON to FastAPI webhook
   ↓
4. FastAPI validates payload
   ↓
5. Maps severity to priority
   ↓
6. Creates osTicket ticket via API
   ↓
7. Ticket assigned to "Zabbix Monitoring" topic
   ↓
8. Custom fields populated with Zabbix data
   ↓
9. Agent reviews in osTicket UI
```

### RESOLVED Event (eventvalue = 0)

```
1. Zabbix trigger recovers (OK state)
   ↓
2. Media Type calls webhook script
   ↓
3. Script sends JSON with eventvalue=0
   ↓
4. FastAPI identifies as RESOLVED
   ↓
5. Searches for matching ticket by event ID
   ↓
6. Closes/resolves the ticket
   ↓
7. Updates custom fields with resolution info
   ↓
8. Audit trail recorded
```

---

## 📚 Additional Resources

- [Zabbix Documentation](https://www.zabbix.com/documentation/)
- [osTicket API Guide](https://docs.osticket.com/en/latest/api/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## ✅ Verification Checklist

Before going live:

- [ ] osTicket Help Topic "Zabbix Monitoring" created
- [ ] Custom fields added to osTicket
- [ ] API key generated and tested
- [ ] FastAPI service installed and running
- [ ] Webhook script deployed to Zabbix server
- [ ] Media Type created in Zabbix
- [ ] User created for notifications
- [ ] Action created for triggers
- [ ] Test event creates ticket successfully
- [ ] Logging configured and working
- [ ] Error handling tested
- [ ] Network connectivity verified
- [ ] Firewall rules updated

---

**Status:** ✅ Ready for Deployment
**Last Updated:** 2025-10-26
**Maintainer:** Claude Code Integration System
