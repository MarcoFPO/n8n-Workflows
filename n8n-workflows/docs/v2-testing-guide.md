# Zabbix Workflow V2 - Testing Guide

## Übersicht

Dieser Guide beschreibt das vollständige Testing der Event-basierten Workflow-Architektur V2.

## Voraussetzungen

- ✅ V2 Workflows in n8n hochgeladen
- ✅ Redis läuft und ist erreichbar
- ✅ n8n läuft auf 10.1.1.180
- ✅ Zabbix Action ist konfiguriert (optional für manuelle Tests)

## Test-Levels

### 1. Unit Tests (Einzelne Komponenten)

#### Test 1.1: Sub-1 V2 Webhook Empfang

**Ziel:** Prüfen ob Sub-1 V2 Events empfängt und in Redis Queue speichert

**Vorher:**
```bash
# Queue leeren
redis-cli DEL zabbix:event:queue
redis-cli DEL zabbix:event:counter
```

**Test:**
```bash
curl -X POST http://10.1.1.180/webhook/zabbix-event \
  -H "Content-Type: application/json" \
  -d '{
    "eventid": "12345",
    "name": "Test Problem: High CPU Usage",
    "severity": "3",
    "host": "test-server-01",
    "hostid": "10001",
    "triggerid": "20001",
    "clock": "1697123456",
    "timestamp": "2025-10-13 15:30:45"
  }'
```

**Erwartetes Ergebnis:**
```json
{
  "success": true,
  "event_id": "12345",
  "queued": true,
  "queue_position": 1,
  "message": "Event queued for processing"
}
```

**Nachher:**
```bash
# Queue prüfen
redis-cli LLEN zabbix:event:queue
# Erwartung: 1

redis-cli GET zabbix:event:counter
# Erwartung: 1

# Event-Daten prüfen
redis-cli LRANGE zabbix:event:queue 0 -1
# Erwartung: JSON mit Event-Daten
```

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 1.2: Master V2 Lock-Mechanismus

**Ziel:** Prüfen ob Lock verhindert dass mehrere Instanzen parallel laufen

**Test:**
```bash
# Lock manuell setzen
redis-cli SETEX zabbix:processing:lock 60 "test-lock"

# Master triggern
curl -X POST http://10.1.1.180/webhook/master-zabbix-processor \
  -H "Content-Type: application/json" \
  -d '{"trigger": "test"}'
```

**Erwartetes Ergebnis:**
```json
{
  "success": true,
  "message": "Already processing, skipping",
  "timestamp": "2025-10-13T15:30:45.123Z"
}
```

**Nachher:**
```bash
# Lock sollte noch existieren
redis-cli EXISTS zabbix:processing:lock
# Erwartung: 1
```

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 1.3: Master V2 Event-Verarbeitung

**Ziel:** Prüfen ob Master Event aus Queue holt und verarbeitet

**Vorher:**
```bash
# Lock entfernen falls vorhanden
redis-cli DEL zabbix:processing:lock

# Test-Event in Queue pushen
redis-cli LPUSH zabbix:event:queue '{
  "event_id": "67890",
  "zabbix_event": {
    "eventid": "67890",
    "name": "Test Problem: Disk Full",
    "severity": "4",
    "host": "test-server-02"
  },
  "received_at": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
  "status": "queued"
}'
```

**Test:**
```bash
curl -X POST http://10.1.1.180/webhook/master-zabbix-processor \
  -H "Content-Type: application/json" \
  -d '{"trigger": "test"}'
```

**Erwartetes Ergebnis:**
```json
{
  "success": true,
  "event_id": "67890",
  "message": "Event processed successfully",
  "timestamp": "2025-10-13T15:30:45.123Z"
}
```

**Nachher:**
```bash
# Queue sollte leer sein
redis-cli LLEN zabbix:event:queue
# Erwartung: 0

# Event-Status prüfen
redis-cli GET zabbix:event:67890:status
# Erwartung: completed

# Lock sollte released sein
redis-cli EXISTS zabbix:processing:lock
# Erwartung: 0
```

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 1.4: Master V2 Leere Queue

**Ziel:** Prüfen ob Master korrekt reagiert wenn Queue leer ist

**Vorher:**
```bash
# Sicherstellen dass Queue leer ist
redis-cli DEL zabbix:event:queue
redis-cli DEL zabbix:processing:lock
```

**Test:**
```bash
curl -X POST http://10.1.1.180/webhook/master-zabbix-processor \
  -H "Content-Type: application/json" \
  -d '{"trigger": "test"}'
```

**Erwartetes Ergebnis:**
```json
{
  "success": true,
  "message": "Queue empty, no events to process",
  "timestamp": "2025-10-13T15:30:45.123Z"
}
```

**Status:** ✅ PASS / ❌ FAIL

---

### 2. Integration Tests

#### Test 2.1: End-to-End Single Event

**Ziel:** Kompletter Durchlauf von Webhook-Empfang bis Email

**Vorher:**
```bash
# Alles zurücksetzen
redis-cli DEL zabbix:event:queue
redis-cli DEL zabbix:event:counter
redis-cli DEL zabbix:processing:lock
redis-cli KEYS "zabbix:event:*:status" | xargs redis-cli DEL
```

**Test:**
```bash
# 1. Event senden
curl -X POST http://10.1.1.180/webhook/zabbix-event \
  -H "Content-Type: application/json" \
  -d '{
    "eventid": "TEST001",
    "name": "Test: Service not responding",
    "severity": "4",
    "host": "web-server-prod",
    "hostid": "10050",
    "ip": "10.1.1.50",
    "triggerid": "30001",
    "trigger_description": "HTTP service is down",
    "clock": "'$(date +%s)'",
    "timestamp": "'$(date '+%Y.%m.%d %H:%M:%S')'"
  }'

# 2. Kurz warten (Event wird in Queue geschrieben und Master getriggert)
sleep 2

# 3. Prüfen ob Master bereits läuft (Lock sollte existieren)
redis-cli EXISTS zabbix:processing:lock
```

**Erwartungen:**
1. Sub-1 V2 Response: `{"success": true, "event_id": "TEST001", "queued": true}`
2. Queue-Länge: 0 (Event wurde bereits verarbeitet oder gerade in Arbeit)
3. Event-Status: "processing" oder "completed"
4. Email sollte angekommen sein (prüfe Inbox)

**Prüfung in n8n UI:**
```
1. Öffne http://10.1.1.180
2. Workflow: "Zabbix Sub-1: Problem-Erfassung V2"
   → Executions → Sollte SUCCESS zeigen
3. Workflow: "Zabbix MASTER: Event-Based Processor V2"
   → Executions → Sollte SUCCESS zeigen
4. Workflow: "Zabbix Sub-2: Root Cause Analyse"
   → Executions → Sollte SUCCESS zeigen
5. Workflow: "Zabbix Sub-3: Entscheidung Remote-Lösbarkeit"
   → Executions → Sollte SUCCESS zeigen
6. Workflow: "Zabbix Sub-4: Remote-Lösung" (nur wenn remote_loesbar=true)
   → Executions → Optional
7. Workflow: "Zabbix Sub-5: User-Benachrichtigung"
   → Executions → Sollte SUCCESS zeigen
```

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 2.2: Concurrent Events (Queue Buffering)

**Ziel:** Mehrere Events gleichzeitig, Queue-Pufferung testen

**Test:**
```bash
# Sende 5 Events schnell hintereinander
for i in {1..5}; do
  curl -X POST http://10.1.1.180/webhook/zabbix-event \
    -H "Content-Type: application/json" \
    -d "{
      \"eventid\": \"BURST00$i\",
      \"name\": \"Test Problem $i\",
      \"severity\": \"3\",
      \"host\": \"test-server-$i\"
    }" &
done
wait

# Queue-Länge prüfen
redis-cli LLEN zabbix:event:queue
# Erwartung: 0-5 (abhängig von Verarbeitungsgeschwindigkeit)
```

**Erwartungen:**
1. Alle 5 Events werden in Queue geschrieben
2. Master verarbeitet sie sequenziell
3. Lock verhindert Concurrent Processing
4. Alle Events bekommen Status "completed"

**Prüfung:**
```bash
# Alle Event-Status prüfen
for i in {1..5}; do
  echo "Event BURST00$i: $(redis-cli GET zabbix:event:BURST00$i:status)"
done
```

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 2.3: Event Burst (Stress Test)

**Ziel:** System-Verhalten bei hoher Last

**Test:**
```bash
# Sende 50 Events
for i in {1..50}; do
  curl -X POST http://10.1.1.180/webhook/zabbix-event \
    -H "Content-Type: application/json" \
    -d "{
      \"eventid\": \"STRESS$(printf %03d $i)\",
      \"name\": \"Stress Test Event $i\",
      \"severity\": \"2\",
      \"host\": \"test-server\"
    }" > /dev/null 2>&1 &

  # Kleine Pause um Webhook nicht zu überlasten
  [ $((i % 10)) -eq 0 ] && sleep 1
done
wait

echo "Alle Events gesendet."
echo "Queue-Länge: $(redis-cli LLEN zabbix:event:queue)"
```

**Monitoring während Test:**
```bash
# In separatem Terminal: Queue-Länge live beobachten
watch -n 1 'redis-cli LLEN zabbix:event:queue'

# Event-Counter beobachten
watch -n 1 'redis-cli GET zabbix:event:counter'

# Lock-Status beobachten
watch -n 1 'redis-cli EXISTS zabbix:processing:lock'
```

**Erwartungen:**
1. Queue steigt auf max ~40-50 Events
2. Master verarbeitet kontinuierlich (Lock alterniert)
3. Nach Verarbeitung: Queue = 0
4. Alle Events haben Status "completed"

**Nachher:**
```bash
# Warten bis Queue leer ist
while [ $(redis-cli LLEN zabbix:event:queue) -gt 0 ]; do
  echo "Queue: $(redis-cli LLEN zabbix:event:queue) | Warte..."
  sleep 5
done

# Prüfe wie viele Events completed sind
completed_count=$(redis-cli KEYS "zabbix:event:STRESS*:status" | xargs redis-cli MGET | grep -c "completed")
echo "Completed Events: $completed_count / 50"
```

**Status:** ✅ PASS / ❌ FAIL

---

### 3. System Tests

#### Test 3.1: Zabbix Real Event

**Ziel:** Echtes Event von Zabbix empfangen und verarbeiten

**Voraussetzung:** Zabbix Action ist konfiguriert

**Test:**
1. Trigger manuell ein Problem in Zabbix:
   ```bash
   # Beispiel: Service stoppen um Alert zu triggern
   ssh root@test-server "systemctl stop nginx"
   ```

2. In Zabbix UI prüfen:
   - Dashboard → Problems → Neues Problem sollte erscheinen

3. Prüfen ob Webhook gesendet wurde:
   - Administration → Audit → Actions
   - Suche nach der konfigurierten Action
   - Status sollte "Sent" sein

4. In n8n prüfen:
   ```
   Sub-1 V2 → Executions → Neueste Execution
   Master V2 → Executions → Neueste Execution
   ```

5. Email-Inbox prüfen:
   - Email mit Report sollte angekommen sein
   - Enthält Zabbix-Problem-Details
   - Enthält Root Cause Analysis
   - Enthält Entscheidung (remote_loesbar)

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 3.2: Recovery Event

**Ziel:** Problem-Recovery wird erkannt und verarbeitet

**Test:**
1. Recovery triggern:
   ```bash
   ssh root@test-server "systemctl start nginx"
   ```

2. In Zabbix UI prüfen:
   - Dashboard → Problems → Problem sollte zu "Resolved" wechseln

3. Falls Recovery-Webhook konfiguriert:
   - Email mit "RECOVERED: ..." sollte ankommen

**Status:** ✅ PASS / ❌ FAIL

---

### 4. Error Tests

#### Test 4.1: Sub-2 Failure

**Ziel:** System-Verhalten wenn Claude CLI fehlschlägt

**Test:**
```bash
# Claude CLI vorübergehend umbenennen (auf LXC 105)
ssh root@10.1.1.105 "mv /home/mdoehler/.local/bin/claude /home/mdoehler/.local/bin/claude.bak"

# Test-Event senden
curl -X POST http://10.1.1.180/webhook/zabbix-event \
  -H "Content-Type: application/json" \
  -d '{
    "eventid": "ERROR001",
    "name": "Test Error Handling",
    "severity": "3",
    "host": "test-server"
  }'

# Warten und prüfen
sleep 10

# Claude CLI wiederherstellen
ssh root@10.1.1.105 "mv /home/mdoehler/.local/bin/claude.bak /home/mdoehler/.local/bin/claude"
```

**Erwartungen:**
1. Master V2 Execution zeigt ERROR
2. Event-Status bleibt "processing" oder wird "error"
3. Email-Benachrichtigung über Fehler
4. Lock wird trotzdem released (TTL 5min)

**Status:** ✅ PASS / ❌ FAIL

---

#### Test 4.2: Redis Failure

**Ziel:** System-Verhalten wenn Redis nicht erreichbar

**Test:**
```bash
# Redis stoppen
ssh root@10.1.1.180 "systemctl stop redis"

# Test-Event senden
curl -X POST http://10.1.1.180/webhook/zabbix-event \
  -H "Content-Type: application/json" \
  -d '{
    "eventid": "REDIS_FAIL",
    "name": "Test Redis Failure",
    "severity": "3",
    "host": "test-server"
  }'

# Redis wieder starten
ssh root@10.1.1.180 "systemctl start redis"
```

**Erwartungen:**
1. Sub-1 V2 Execution zeigt ERROR
2. Webhook antwortet mit Fehler
3. Event geht verloren (kein Retry-Mechanismus)

**Verbesserung:** Zabbix Action sollte Retry-Logik haben

**Status:** ✅ PASS / ❌ FAIL

---

## Performance-Metriken

### Durchschnittliche Latenz pro Workflow-Step

| Step | Target | Acceptable | Critical |
|------|--------|------------|----------|
| Zabbix → Sub-1 V2 | < 100ms | < 500ms | > 1s |
| Sub-1 V2 → Redis Queue | < 50ms | < 200ms | > 500ms |
| Sub-1 V2 → Master Trigger | < 100ms | < 500ms | > 1s |
| Master → Queue Pop | < 50ms | < 200ms | > 500ms |
| Master → Sub-2 (Claude) | < 5s | < 15s | > 30s |
| Sub-2 → Sub-3 (Claude) | < 3s | < 10s | > 20s |
| Sub-3 → Sub-4 (Claude Code) | < 30s | < 60s | > 120s |
| Sub-5 Email Send | < 2s | < 5s | > 10s |
| **Total (ohne Sub-4)** | < 15s | < 35s | > 60s |
| **Total (mit Sub-4)** | < 45s | < 95s | > 180s |

### Durchsatz-Metriken

| Metrik | Target | Acceptable |
|--------|--------|------------|
| Events/Minute | 10 | 5 |
| Queue Max Size | 50 | 100 |
| Concurrent Processing | 1 (by design) | 1 |

## Continuous Monitoring

### Shell-Script für Live-Monitoring

```bash
#!/bin/bash
# monitor-v2.sh

while true; do
  clear
  echo "==== Zabbix Workflow V2 - Live Monitor ===="
  echo "Zeit: $(date '+%Y-%m-%d %H:%M:%S')"
  echo ""

  echo "Redis Queue:"
  queue_len=$(redis-cli LLEN zabbix:event:queue)
  echo "  Queue Length: $queue_len"

  event_count=$(redis-cli GET zabbix:event:counter)
  echo "  Total Events: ${event_count:-0}"

  lock_status=$(redis-cli EXISTS zabbix:processing:lock)
  if [ "$lock_status" -eq 1 ]; then
    lock_time=$(redis-cli GET zabbix:processing:lock)
    echo "  Processing: LOCKED (since $lock_time)"
  else
    echo "  Processing: IDLE"
  fi

  echo ""
  echo "Event Status (last 10):"
  redis-cli KEYS "zabbix:event:*:status" | tail -10 | while read key; do
    status=$(redis-cli GET "$key")
    event_id=$(echo "$key" | sed 's/zabbix:event://;s/:status//')
    echo "  $event_id: $status"
  done

  sleep 2
done
```

**Usage:**
```bash
chmod +x monitor-v2.sh
./monitor-v2.sh
```

## Test-Report Template

```markdown
# Zabbix Workflow V2 - Test Report

**Datum:** YYYY-MM-DD
**Tester:** Name
**Version:** V2.0

## Test Results

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| 1.1 | Sub-1 Webhook Empfang | ✅ PASS | |
| 1.2 | Master Lock-Mechanismus | ✅ PASS | |
| 1.3 | Master Event-Verarbeitung | ✅ PASS | |
| 1.4 | Master Leere Queue | ✅ PASS | |
| 2.1 | End-to-End Single Event | ✅ PASS | |
| 2.2 | Concurrent Events | ✅ PASS | |
| 2.3 | Event Burst (Stress) | ⚠️ PARTIAL | Queue bis 87, OK |
| 3.1 | Zabbix Real Event | ✅ PASS | |
| 3.2 | Recovery Event | ✅ PASS | |
| 4.1 | Sub-2 Failure | ⚠️ PARTIAL | Kein Retry |
| 4.2 | Redis Failure | ❌ FAIL | Event lost |

## Performance Metrics

- Average Latency (without Sub-4): 18s
- Average Latency (with Sub-4): 52s
- Max Queue Length: 87
- Events Processed: 150
- Success Rate: 98.7%

## Issues Found

1. **Redis Failure Recovery:** Events gehen verloren wenn Redis down ist
   - **Severity:** High
   - **Mitigation:** Zabbix Action Retry + Dead Letter Queue

2. **Email Flood:** Bei vielen Events viele einzelne Emails
   - **Severity:** Medium
   - **Mitigation:** Email-Batching in Sub-5 implementieren

## Recommendations

1. Implement Email Batching (max 1 email / 5 min)
2. Add Dead Letter Queue for failed events
3. Add Master self-loop for continuous queue processing
4. Add Grafana Dashboard for Redis metrics

## Sign-off

- ✅ Ready for Production
- ⏳ Needs Improvements
- ❌ Not Ready
```

## Nächste Schritte nach Testing

1. ✅ Alle Tests PASS
2. Dokumentiere gefundene Issues
3. Implementiere Verbesserungen
4. Re-Test nach Fixes
5. Sign-off für Production
6. Migration V1 → V2
7. V1 deaktivieren
