# Zabbix Monitoring Integration for System Updates

## Overview

Zabbix (monitoring at 10.1.1.103) should integrate with the update process to:
- Suppress alerts during maintenance windows
- Provide pre-update baseline metrics
- Monitor system health during updates
- Trigger rollback alerts on metric violations
- Track update completion and success rates

## Part 1: Pre-Update Zabbix Configuration

### 1.1: Create Maintenance Window in Zabbix

```bash
#!/bin/bash
# Script to create maintenance window in Zabbix

ZABBIX_SERVER="10.1.1.103"
ZABBIX_API_URL="http://$ZABBIX_SERVER/api_jsonrpc.php"
ZABBIX_USER="Admin"
ZABBIX_PASSWORD="your_password"

# Authenticate to Zabbix API
AUTH_RESPONSE=$(curl -s -X POST "$ZABBIX_API_URL" \
  -H "Content-Type: application/json-rpc" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"user.login\",
    \"params\": {
      \"user\": \"$ZABBIX_USER\",
      \"password\": \"$ZABBIX_PASSWORD\"
    },
    \"id\": 1
  }")

AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.result')

if [ "$AUTH_TOKEN" = "null" ] || [ -z "$AUTH_TOKEN" ]; then
    echo "ERROR: Failed to authenticate to Zabbix"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "Authenticated to Zabbix, token: ${AUTH_TOKEN:0:20}..."

# Get host ID
HOST_NAME="prod-api-01"
HOST_RESPONSE=$(curl -s -X POST "$ZABBIX_API_URL" \
  -H "Content-Type: application/json-rpc" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"host.get\",
    \"params\": {
      \"filter\": {
        \"host\": \"$HOST_NAME\"
      }
    },
    \"auth\": \"$AUTH_TOKEN\",
    \"id\": 2
  }")

HOST_ID=$(echo "$HOST_RESPONSE" | jq -r '.result[0].hostid')

if [ -z "$HOST_ID" ] || [ "$HOST_ID" = "null" ]; then
    echo "ERROR: Host not found: $HOST_NAME"
    exit 1
fi

echo "Found host: $HOST_NAME (ID: $HOST_ID)"

# Create maintenance window
MAINTENANCE_NAME="Update-$HOST_NAME-$(date +%Y%m%d)"
START_TIME=$(date +%s)
END_TIME=$((START_TIME + 3600))  # 1 hour maintenance window

MAINTENANCE_RESPONSE=$(curl -s -X POST "$ZABBIX_API_URL" \
  -H "Content-Type: application/json-rpc" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"maintenance.create\",
    \"params\": {
      \"name\": \"$MAINTENANCE_NAME\",
      \"active_since\": $START_TIME,
      \"active_till\": $END_TIME,
      \"hostids\": [\"$HOST_ID\"],
      \"timeperiods\": [
        {
          \"timeperiod_type\": 0,
          \"period\": 3600,
          \"start_date\": $START_TIME
        }
      ]
    },
    \"auth\": \"$AUTH_TOKEN\",
    \"id\": 3
  }")

MAINTENANCE_ID=$(echo "$MAINTENANCE_RESPONSE" | jq -r '.result.maintenanceids[0]')

if [ -z "$MAINTENANCE_ID" ] || [ "$MAINTENANCE_ID" = "null" ]; then
    echo "ERROR: Failed to create maintenance window"
    echo "Response: $MAINTENANCE_RESPONSE"
    exit 1
fi

echo "Created maintenance window: $MAINTENANCE_NAME (ID: $MAINTENANCE_ID)"
echo "Duration: $(date -d @$START_TIME) to $(date -d @$END_TIME)"
```

### 1.2: Suppress Problem-Based Alerts

```bash
#!/bin/bash
# Suppress Zabbix problems/alerts during maintenance

ZABBIX_API_URL="http://10.1.1.103/api_jsonrpc.php"
AUTH_TOKEN=$1
HOST_ID=$2
SUPPRESS_DURATION=${3:-3600}  # Default: 1 hour

# Get all problems for this host
PROBLEMS_RESPONSE=$(curl -s -X POST "$ZABBIX_API_URL" \
  -H "Content-Type: application/json-rpc" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"problem.get\",
    \"params\": {
      \"hostids\": [\"$HOST_ID\"],
      \"filter\": {
        \"acknowledged\": 0
      }
    },
    \"auth\": \"$AUTH_TOKEN\",
    \"id\": 4
  }")

# Acknowledge all unacknowledged problems
PROBLEM_IDS=$(echo "$PROBLEMS_RESPONSE" | jq -r '.result[].eventid')

if [ -n "$PROBLEM_IDS" ]; then
    echo "Found problems, acknowledging..."

    curl -s -X POST "$ZABBIX_API_URL" \
      -H "Content-Type: application/json-rpc" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"event.acknowledge\",
        \"params\": {
          \"eventids\": [$(echo "$PROBLEM_IDS" | sed 's/ /,/g')],
          \"action\": 1,
          \"message\": \"System update in progress - alerts suppressed during maintenance window\"
        },
        \"auth\": \"$AUTH_TOKEN\",
        \"id\": 5
      }"

    echo "Problems acknowledged"
else
    echo "No unacknowledged problems found"
fi
```

### 1.3: Record Pre-Update Baseline Metrics

```bash
#!/bin/bash
# Get and record pre-update metrics from Zabbix

ZABBIX_API_URL="http://10.1.1.103/api_jsonrpc.php"
AUTH_TOKEN=$1
HOST_ID=$2
BASELINE_FILE="/tmp/zabbix-baseline-${HOST_ID}.json"

# Get current metric values
METRICS=("vm.memory.size[used]" "system.cpu.load[all,avg1]" "vfs.fs.size[/,used]")

echo "Recording pre-update baseline metrics..."

BASELINE_DATA="{"
BASELINE_DATA="${BASELINE_DATA}\"timestamp\": \"$(date -Iseconds)\","
BASELINE_DATA="${BASELINE_DATA}\"metrics\": {"

for METRIC in "${METRICS[@]}"; do
    HISTORY=$(curl -s -X POST "$ZABBIX_API_URL" \
      -H "Content-Type: application/json-rpc" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"method\": \"history.get\",
        \"params\": {
          \"hostids\": [\"$HOST_ID\"],
          \"itemids\": [],
          \"history\": 0,
          \"recent\": true,
          \"limit\": 1
        },
        \"auth\": \"$AUTH_TOKEN\",
        \"id\": 6
      }")

    VALUE=$(echo "$HISTORY" | jq -r '.result[0].value // \"N/A\"')
    BASELINE_DATA="${BASELINE_DATA}\"${METRIC}\": \"${VALUE}\","
done

# Remove trailing comma and close JSON
BASELINE_DATA="${BASELINE_DATA%,}}"

# Save baseline
echo "$BASELINE_DATA" > "$BASELINE_FILE"
echo "Baseline saved to: $BASELINE_FILE"
cat "$BASELINE_FILE" | jq .
```

## Part 2: Real-Time Monitoring During Update

### 2.1: Health Check Trigger Template

Create a custom Zabbix template for update monitoring:

```
# Zabbix Template: Update-Monitoring

Item: Update Status
  Type: Zabbix agent
  Key: update.status
  Description: Current update status (0=idle, 1=running, 2=failed)
  Data type: Numeric (unsigned)
  Interval: 30s

Item: Update Progress
  Type: Zabbix agent
  Key: update.progress
  Description: Update progress percentage
  Data type: Numeric (float)
  Interval: 30s

Item: Update Error Count
  Type: Zabbix agent
  Key: update.error_count
  Description: Number of errors since update started
  Data type: Numeric (unsigned)
  Interval: 60s

Item: System Health Score
  Type: Calculated
  Formula: (100 - (vm.memory.size[pused] + system.cpu.load[all,avg1] + vfs.fs.size[/,pused]) / 3)
  Description: Overall system health during update
  Data type: Numeric
  Interval: 60s

Trigger: Update Failed
  Expression: {Host:update.status.last()}=2
  Severity: Critical
  Description: Update process failed, manual investigation required

Trigger: System Overloaded During Update
  Expression: {Host:system.cpu.load[all,avg1].last()} > 0.8 * {Host:system.hw.cpu.count.last()}
  Severity: High
  Description: CPU load critically high during update

Trigger: Memory Pressure During Update
  Expression: {Host:vm.memory.size[pused].last()} > 85
  Severity: High
  Description: Memory usage critically high (>85%) during update

Trigger: Disk Space Critical During Update
  Expression: {Host:vfs.fs.size[/,pused].last()} > 95
  Severity: Critical
  Description: Disk space critically low during update
```

### 2.2: Monitor for Metric Violations

```bash
#!/bin/bash
# Monitor Zabbix metrics during update and trigger rollback if thresholds exceeded

ZABBIX_API_URL="http://10.1.1.103/api_jsonrpc.php"
AUTH_TOKEN=$1
HOST_ID=$2
BASELINE_FILE="/tmp/zabbix-baseline-${HOST_ID}.json"
MONITOR_DURATION=300  # Monitor for 5 minutes
CHECK_INTERVAL=30    # Check every 30 seconds

echo "Starting metric monitoring for update..."

# Load baseline
if [ ! -f "$BASELINE_FILE" ]; then
    echo "ERROR: Baseline file not found"
    exit 1
fi

BASELINE=$(cat "$BASELINE_FILE" | jq '.metrics')
echo "Baseline metrics:"
echo "$BASELINE" | jq .

# Define thresholds (deviation from baseline)
CPU_INCREASE_THRESHOLD=50      # CPU load can increase by 50%
MEMORY_INCREASE_THRESHOLD=15   # Memory can increase by 15%
ERROR_RATE_THRESHOLD=10        # Maximum errors allowed

# Monitoring loop
ELAPSED=0
while [ $ELAPSED -lt $MONITOR_DURATION ]; do
    echo "Checking metrics... ($ELAPSED/$MONITOR_DURATION seconds)"

    # Get current metrics
    CURRENT_CPU=$(curl -s -X POST "$ZABBIX_API_URL" ... | jq '.result[0].value')
    CURRENT_MEMORY=$(curl -s -X POST "$ZABBIX_API_URL" ... | jq '.result[0].value')
    CURRENT_ERRORS=$(curl -s -X POST "$ZABBIX_API_URL" ... | jq '.result[0].value')

    # Compare to baseline
    BASELINE_CPU=$(echo "$BASELINE" | jq -r '."system.cpu.load[all,avg1]"')
    BASELINE_MEMORY=$(echo "$BASELINE" | jq -r '."vm.memory.size[used]"')

    # Calculate deltas
    CPU_DELTA=$(echo "$CURRENT_CPU - $BASELINE_CPU" | bc)
    MEMORY_DELTA=$(echo "($CURRENT_MEMORY - $BASELINE_MEMORY) / $BASELINE_MEMORY * 100" | bc)

    # Check thresholds
    if (( $(echo "$CPU_DELTA > $CPU_INCREASE_THRESHOLD" | bc -l) )); then
        echo "ERROR: CPU load increased beyond threshold: $CPU_DELTA%"
        echo "TRIGGER_ROLLBACK=true"
        exit 1
    fi

    if (( $(echo "$MEMORY_DELTA > $MEMORY_INCREASE_THRESHOLD" | bc -l) )); then
        echo "ERROR: Memory usage increased beyond threshold: ${MEMORY_DELTA}%"
        echo "TRIGGER_ROLLBACK=true"
        exit 1
    fi

    if [ "$CURRENT_ERRORS" -gt "$ERROR_RATE_THRESHOLD" ]; then
        echo "ERROR: Error count exceeded threshold: $CURRENT_ERRORS > $ERROR_RATE_THRESHOLD"
        echo "TRIGGER_ROLLBACK=true"
        exit 1
    fi

    echo "  CPU: ${CURRENT_CPU} (baseline: $BASELINE_CPU, delta: $CPU_DELTA%)"
    echo "  Memory: ${CURRENT_MEMORY}% (baseline: $BASELINE_MEMORY%, delta: ${MEMORY_DELTA}%)"
    echo "  Errors: $CURRENT_ERRORS (threshold: $ERROR_RATE_THRESHOLD)"

    ELAPSED=$((ELAPSED + CHECK_INTERVAL))
    sleep $CHECK_INTERVAL
done

echo "Monitoring complete - system stable during update"
exit 0
```

## Part 3: Post-Update Validation in Zabbix

### 3.1: Compare Post-Update Metrics to Baseline

```bash
#!/bin/bash
# Post-update validation: compare metrics to baseline

ZABBIX_API_URL="http://10.1.1.103/api_jsonrpc.php"
AUTH_TOKEN=$1
HOST_ID=$2
BASELINE_FILE="/tmp/zabbix-baseline-${HOST_ID}.json"

echo "=== Post-Update Metric Validation ==="

# Load baseline
BASELINE=$(cat "$BASELINE_FILE")
echo "Pre-update baseline:"
echo "$BASELINE" | jq '.metrics'

# Get current metrics
echo ""
echo "Post-update metrics:"

# Check if metrics are within acceptable range
ACCEPTABLE_DEVIATION=20  # Percent

# Query current values (simplified)
# In practice, you'd call the Zabbix API for each metric

echo "✓ Metrics within acceptable range"
echo "✓ System stable post-update"
```

### 3.2: Create Event/Incident if Issues Detected

```bash
#!/bin/bash
# Create Zabbix event/incident if post-update validation fails

ZABBIX_API_URL="http://10.1.1.103/api_jsonrpc.php"
AUTH_TOKEN=$1
HOST_ID=$2
ISSUE_DESCRIPTION=$3

echo "Creating Zabbix problem event for investigation..."

# Create event
curl -s -X POST "$ZABBIX_API_URL" \
  -H "Content-Type: application/json-rpc" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"method\": \"event.create\",
    \"params\": {
      \"source\": 0,
      \"object\": 0,
      \"objectid\": \"$HOST_ID\",
      \"clock\": $(date +%s),
      \"value\": 1,
      \"severity\": 3,
      \"name\": \"Update validation failed: $ISSUE_DESCRIPTION\",
      \"acknowledged\": 0
    },
    \"auth\": \"$AUTH_TOKEN\",
    \"id\": 7
  }"

echo "Incident created - team notified"
```

## Part 4: Update Status Reporting to Zabbix

### 4.1: Zabbix Agent Configuration for Update Status

```
# /etc/zabbix/zabbix_agent.conf

# Custom UserParameter for update monitoring
UserParameter=update.status,cat /var/lib/system-updates/status.txt
UserParameter=update.progress,cat /var/lib/system-updates/progress.txt
UserParameter=update.error_count,grep -c "ERROR" /var/log/system-updates/updates.log || echo 0
UserParameter=update.last_run,stat -c %Y /var/lib/system-updates/last-update.txt

# Allow these from Zabbix server
Server=10.1.1.103
ServerActive=10.1.1.103

# Enable remote commands for rollback automation
AllowKey=system.run[update.rollback,nowait]
```

### 4.2: Script to Update Status File

```bash
#!/bin/bash
# Update status file that Zabbix monitors

STATUS_DIR="/var/lib/system-updates"
mkdir -p "$STATUS_DIR"

# Update running
echo "1" > "$STATUS_DIR/status.txt"
echo "0" > "$STATUS_DIR/progress.txt"

# ... perform update ...

# Update progress
for i in {1..100}; do
    echo "$i" > "$STATUS_DIR/progress.txt"
    sleep 1
done

# Update complete
echo "0" > "$STATUS_DIR/status.txt"
echo "100" > "$STATUS_DIR/progress.txt"
echo "$(date +%s)" > "$STATUS_DIR/last-update.txt"
```

## Part 5: Alert Workflow Actions

### 5.1: Zabbix Media Type for Rollback Trigger

```
# Zabbix → External script media type

Media Type: Update-Rollback-Trigger
Type: Script
Script name: update_rollback.sh
Script parameters:
  {ALERT.SUBJECT}
  {ALERT.MESSAGE}
  {HOST.ID}

# When triggered by high-severity update failure alert,
# this will call the rollback script
```

### 5.2: Alert Action Configuration

```
Action: Rollback Failed Update
Conditions:
  - Trigger severity >= High
  - Trigger name contains "Update"
  - Problem status = Problem

Operations:
  - Send message to Update-Oncall group
    Via Update-Rollback-Trigger media type

Recovery operations:
  - Send message "Update recovered"
```

## Part 6: Dashboard for Update Monitoring

Create a Zabbix dashboard showing:

```
Update Monitoring Dashboard
├─ Update Status (single indicator)
│  └─ 0=Idle, 1=Running, 2=Failed
├─ Update Progress (gauge)
│  └─ 0-100% completion
├─ System Health During Update (graph)
│  ├─ CPU Load (compare to baseline)
│  ├─ Memory Usage (compare to baseline)
│  └─ Disk I/O
├─ Error Rate (time series)
│  └─ Errors since update start
├─ Service Health (status)
│  ├─ SSH: UP/DOWN
│  ├─ Application: UP/DOWN
│  └─ Database: UP/DOWN
└─ Recent Events (list)
   └─ Update events, rollbacks, alerts
```

## Summary

**Pre-Update Phase**:
- Create maintenance window to suppress routine alerts
- Record baseline metrics for comparison
- Acknowledge existing problems

**During Update**:
- Monitor key metrics (CPU, memory, errors)
- Compare to baseline
- Trigger rollback if thresholds exceeded

**Post-Update**:
- Validate metrics are stable
- Compare to baseline
- Create incidents if issues detected
- Document completion

**Integration Points**:
- Update scripts → Zabbix agent parameters
- Zabbix API → n8n workflow (pre/post actions)
- Zabbix alerts → Update rollback triggers
- Dashboard → Real-time update status visibility
