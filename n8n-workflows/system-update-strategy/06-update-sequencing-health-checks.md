# Update Sequencing & Health Checks Strategy

## Part 1: Update Sequencing Strategy

### Dependency-Based Ordering

Systems should be updated in an order that respects dependencies:

```
TIER 1: Foundation Services (updated first)
├─ Network infrastructure
│   ├─ Switches/routers
│   ├─ DNS servers (recursive resolvers)
│   └─ DHCP servers
│
├─ Storage infrastructure
│   ├─ NFS/SMB file servers
│   ├─ Backup systems
│   └─ Database servers (primaries)
│
└─ Core services
    ├─ Time servers (NTP)
    ├─ Monitoring infrastructure
    └─ Logging aggregation

TIER 2: Support Services (updated after Tier 1 passes)
├─ Load balancers
├─ Reverse proxies
├─ Message queues
├─ Cache servers (Redis)
└─ Database replicas

TIER 3: Application Servers (updated after Tier 2 passes)
├─ API servers
├─ Web servers
├─ Worker processes
├─ Background job processors
└─ Scheduled task runners

TIER 4: Support Tools (updated last)
├─ Development tools
├─ Test systems
├─ Staging environments
└─ Non-production infrastructure
```

### Batching Strategy by System Tier

```yaml
TIER 1 - Critical Foundation:
  Batch Size: 1 system at a time
  Monitoring: Continuous (no gaps)
  Downtime Tolerance: < 1 minute
  Validation: Full suite before next
  Rollback: Automatic if any failure
  Example: Primary database - update alone

TIER 2 - Important Infrastructure:
  Batch Size: 2-3 systems simultaneously
  Monitoring: Every 10 minutes
  Downtime Tolerance: < 5 minutes
  Validation: Quick smoke test
  Rollback: Automatic if threshold exceeded
  Example: Redis clusters - update 2 at a time

TIER 3 - Application Servers:
  Batch Size: 5 systems per batch
  Monitoring: Every 30 minutes
  Downtime Tolerance: Acceptable with load balancing
  Validation: Application-level tests
  Rollback: Possible but depends on state
  Example: Web servers - update 5-10 at a time

TIER 4 - Support Tools:
  Batch Size: 10+ systems simultaneously
  Monitoring: Daily summary
  Downtime Tolerance: Complete outage acceptable
  Validation: Not required
  Rollback: Not required, reimaging acceptable
  Example: Test systems - batch update all
```

### Update Sequencing Timeline

```
Day 1: Tier 1 Foundation Services (Monday 2-4 AM)
├─ DNS servers (recursive): 1 at a time
├─ Wait 15 min between each
├─ Validate DNS is working globally
├─ NTP servers: 1 at a time
├─ Validate time synchronization
└─ Status: Review and approve before proceeding

Day 2: Tier 2 Infrastructure (Tuesday 2-4 AM)
├─ Database replicas: 2 at a time
├─ Monitor replication lag
├─ Load balancers: 1 at a time
├─ Test failover during update
├─ Cache servers: 3 at a time
└─ Status: Review before moving to Tier 3

Day 3-4: Tier 3 Application Servers (Wednesday-Thursday 2-4 AM)
├─ API servers: 5 at a time
├─ Monitor error rates
├─ Background workers: 5 at a time
├─ Monitor queue depth
└─ Web servers: Remaining systems

Day 5: Tier 4 Support Tools (Friday night)
├─ Batch update all non-critical systems
├─ No monitoring required
└─ Document completion
```

### Decision: Halt vs Proceed Gates

Between each tier, evaluate:

```yaml
Gate 1: After Tier 1 (Foundation)
  Questions:
    - Are all Tier 1 systems up and responsive?
    - Is DNS resolving correctly?
    - Is time synchronized across all systems?
    - Were there any rollbacks? (if yes, investigate)
  Decision:
    - PROCEED if all Tier 1 healthy for 30 minutes
    - HALT if any Tier 1 issues remain (investigate root cause)
    - ROLLBACK if critical dependency broken

Gate 2: After Tier 2 (Infrastructure)
  Questions:
    - Are all load balancers passing traffic?
    - Is database replication synchronized?
    - Are cache servers populated and responding?
    - What is the error rate trend?
  Decision:
    - PROCEED if error rate unchanged from baseline
    - HALT if error rate increased > 10%
    - ROLLBACK if any Tier 2 critical failures

Gate 3: After Tier 3 (Applications)
  Questions:
    - Are application health checks passing?
    - Are request latencies normal?
    - Are error logs clean?
    - Is any user impact detected?
  Decision:
    - PROCEED if all metrics green for 1 hour
    - HALT if user complaints received
    - CONSIDER ROLLBACK if widespread failures

Gate 4: Completion (Tier 4 + Final)
  Actions:
    - Generate update completion report
    - Archive all logs and snapshots (keep N-1)
    - Conduct postmortem if any issues occurred
    - Plan improvements for next update cycle
```

### Rollback Triggers During Sequencing

```
IF: System in batch fails health check
  THEN: Rollback that system IMMEDIATELY

IF: >20% systems in batch fail
  THEN: Rollback entire batch + pause updates (24 hours)

IF: Dependency broken (e.g., DNS fails)
  THEN: Rollback ALL dependent systems + investigate root cause

IF: Error rate increases > 25%
  THEN: Pause updates + investigate + consider full rollback

IF: Manual override requested by on-call
  THEN: Stop immediately + preserve state for investigation
```

## Part 2: Health Check Specification

### Health Check Categories

```
1. IMMEDIATE CHECKS (run at end of update)
   ├─ System online (ping/SSH responsive)
   ├─ Critical services running (systemctl status)
   ├─ Network connectivity (default route, DNS)
   └─ Time: 1-2 minutes

2. FUNCTIONAL CHECKS (run 5 minutes after update)
   ├─ Application responding (HTTP/port check)
   ├─ Database connectivity (query execution)
   ├─ Service-specific features
   └─ Time: 2-5 minutes

3. OPERATIONAL CHECKS (run 30 minutes after update)
   ├─ Performance metrics (CPU, memory, disk)
   ├─ Error rate (log analysis)
   ├─ Replication status (for distributed systems)
   └─ Time: 5-10 minutes

4. COMPREHENSIVE CHECKS (run post-batch)
   ├─ Full integration tests
   ├─ Synthetic transaction tests
   ├─ Data consistency checks
   └─ Time: 10-30 minutes

5. STABILITY CHECKS (continuous for 2-4 hours)
   ├─ Anomaly detection
   ├─ Trend analysis
   ├─ Resource leak detection
   └─ Time: Continuous monitoring
```

### Health Check Specifications by System Type

#### LXC Containers

```bash
# Immediate Check (30 seconds)
lxc list | grep RUNNING
lxc exec CONTAINER -- systemctl is-system-running
lxc exec CONTAINER -- ping -c 1 8.8.8.8

# Functional Check (5 minutes)
lxc exec CONTAINER -- curl -s http://localhost:8080/health | jq .status
lxc exec CONTAINER -- systemctl status --no-pager | head -10

# Operational Check (30 minutes)
MEMORY=$(lxc exec CONTAINER -- free -m | grep Mem | awk '{printf "%.0f", $3/$2*100}')
DISK=$(lxc exec CONTAINER -- df / | tail -1 | awk '{printf "%.0f", $5}')
ERRORS=$(lxc exec CONTAINER -- journalctl -n 100 -p 3..4 | wc -l)

# Pass Criteria
[[ $(lxc list | grep -c RUNNING) -eq $EXPECTED_COUNT ]] && echo "PASS" || echo "FAIL"
[[ $MEMORY -lt 80 ]] && echo "Memory: PASS" || echo "Memory: HIGH"
[[ $DISK -lt 85 ]] && echo "Disk: PASS" || echo "Disk: HIGH"
[[ $ERRORS -lt 5 ]] && echo "Errors: PASS" || echo "Errors: ELEVATED"
```

#### Proxmox VMs

```bash
# Immediate Check (1 minute)
qm status VMID | grep running
qm agent VMID ping
ssh USER@VM_IP "systemctl is-system-running"

# Functional Check (5 minutes)
ssh USER@VM_IP "curl -s http://localhost/health"
qm guest cmd-status VMID | jq '.status'

# Operational Check (30 minutes)
ssh USER@VM_IP "free -m | grep Mem | awk '{printf \"%.0f\", \$3/\$2*100}'"
ssh USER@VM_IP "uptime"
ssh USER@VM_IP "journalctl --since '30 minutes ago' -p 3..4 | wc -l"

# Pass Criteria
[[ $(qm list | grep -c running) -eq $EXPECTED_COUNT ]] && echo "PASS" || echo "FAIL"
[[ $MEMORY -lt 90 ]] && echo "Memory: PASS" || echo "Memory: WARNING"
```

#### Physical Servers

```bash
# Immediate Check (1 minute)
ping -c 1 HOST_IP
ssh USER@HOST_IP "systemctl status --no-pager | head -5"
ssh USER@HOST_IP "lsb_release -d"

# Functional Check (5 minutes)
ssh USER@HOST_IP "systemctl status app"
curl -s http://HOST_IP:8080/health

# Operational Check (30 minutes)
ssh USER@HOST_IP "uptime"
ssh USER@HOST_IP "free -m"
ssh USER@HOST_IP "df -h /"
ssh USER@HOST_IP "systemctl status --failed"

# Hardware Health (if applicable)
ssh USER@HOST_IP "sudo megacli -LDInfo -Lall -aALL | grep State"
ssh USER@HOST_IP "sensors | grep -i alarm"

# Pass Criteria
LOAD=$(ssh USER@HOST_IP "uptime | awk -F'load average:' '{print \$2}' | awk '{print \$1}'")
[[ $(echo "$LOAD < 0.7" | bc) -eq 1 ]] && echo "Load: PASS" || echo "Load: HIGH"
```

### Health Check Dashboard Template

```yaml
System: prod-api-01 (10.1.1.50)
Type: Proxmox VM
Update Time: 2025-11-17 02:30
Snapshot: before-update-20251117-023000

IMMEDIATE CHECKS (@ 02:31)
✓ System online: YES (ping ok)
✓ SSH responsive: YES (latency 25ms)
✓ Services running: systemd OK, app OK
✓ Network: default route OK, DNS working

FUNCTIONAL CHECKS (@ 02:35)
✓ Health endpoint: 200 OK
✓ Application responding: YES
✓ Database connected: YES
✗ Cache warming: slow (will retry)

OPERATIONAL CHECKS (@ 03:00)
✓ CPU: 15% (normal)
✓ Memory: 65% (normal)
✓ Disk: 42% (normal)
✓ Error count: 2 (normal baseline: 1-3)
✓ Response time: 125ms (baseline: 120ms)
✓ Replication lag: 0.5s (normal: <1s)

CONTINUOUS MONITORING (@ 02:31 - 05:30)
✓ No anomalies detected
✓ Memory stable (no leak pattern)
✓ CPU even distribution
✓ Network throughput normal
✓ No crash loops

VERDICT: PASS - Update successful, all checks pass
```

## Health Check Automation Scripts

### Bash Health Check Suite

```bash
#!/bin/bash
# Universal health check script for all system types

SYSTEM_NAME=$1
SYSTEM_TYPE=$2  # lxc, vm, physical
SYSTEM_IP=$3
SSH_USER=$4

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Health check result storage
HEALTH_LOG="/tmp/health-check-${SYSTEM_NAME}-$(date +%Y%m%d-%H%M%S).log"
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Log function
log_result() {
    local test_name=$1
    local status=$2
    local value=$3

    case $status in
        PASS)
            echo -e "${GREEN}✓${NC} $test_name: $value"
            ((PASS_COUNT++))
            ;;
        FAIL)
            echo -e "${RED}✗${NC} $test_name: $value"
            ((FAIL_COUNT++))
            ;;
        WARN)
            echo -e "${YELLOW}⚠${NC} $test_name: $value"
            ((WARN_COUNT++))
            ;;
    esac
    echo "$test_name: $status ($value)" >> $HEALTH_LOG
}

echo "=== Health Check for $SYSTEM_NAME ($SYSTEM_TYPE) ===" | tee $HEALTH_LOG
echo "Timestamp: $(date -Iseconds)" | tee -a $HEALTH_LOG

# === IMMEDIATE CHECKS ===
echo -e "\n--- Immediate Checks ---"

# 1. System Responsive
if ping -c 1 -W 2 $SYSTEM_IP >/dev/null 2>&1; then
    log_result "System online" "PASS" "ping ok"
else
    log_result "System online" "FAIL" "not responding to ping"
fi

# 2. SSH Access
if ssh -o ConnectTimeout=2 -o BatchMode=yes $SSH_USER@$SYSTEM_IP "echo ok" >/dev/null 2>&1; then
    log_result "SSH access" "PASS" "connected"
else
    log_result "SSH access" "FAIL" "cannot connect"
    exit 1
fi

# 3. Critical Services
for SERVICE in networking ssh rsyslog; do
    if ssh $SSH_USER@$SYSTEM_IP "systemctl is-active $SERVICE" >/dev/null 2>&1; then
        log_result "Service: $SERVICE" "PASS" "running"
    else
        log_result "Service: $SERVICE" "FAIL" "not running"
    fi
done

# 4. Network Connectivity
if ssh $SSH_USER@$SYSTEM_IP "curl -s -m 5 https://8.8.8.8" >/dev/null 2>&1; then
    log_result "Internet connectivity" "PASS" "ok"
else
    log_result "Internet connectivity" "WARN" "may be offline"
fi

# === FUNCTIONAL CHECKS (5 minutes) ===
echo -e "\n--- Functional Checks ---"
sleep 5

# 5. Application Health
HEALTH_RESPONSE=$(ssh $SSH_USER@$SYSTEM_IP "curl -s -w '%{http_code}' -o /dev/null http://localhost:8080/health" 2>/dev/null)
if [ "$HEALTH_RESPONSE" == "200" ]; then
    log_result "Application health" "PASS" "HTTP 200"
elif [ -n "$HEALTH_RESPONSE" ]; then
    log_result "Application health" "WARN" "HTTP $HEALTH_RESPONSE"
else
    log_result "Application health" "FAIL" "no response"
fi

# 6. Database Connectivity
if ssh $SSH_USER@$SYSTEM_IP "mysql -e 'SELECT 1;'" >/dev/null 2>&1; then
    log_result "Database connectivity" "PASS" "responsive"
else
    log_result "Database connectivity" "WARN" "may not be installed"
fi

# === OPERATIONAL CHECKS (30 minutes) ===
echo -e "\n--- Operational Checks ---"

# 7. Memory Usage
MEMORY_USAGE=$(ssh $SSH_USER@$SYSTEM_IP "free -m | grep '^Mem' | awk '{printf \"%.0f\", \$3/\$2*100}'")
if [ "$MEMORY_USAGE" -lt 80 ]; then
    log_result "Memory usage" "PASS" "${MEMORY_USAGE}%"
elif [ "$MEMORY_USAGE" -lt 90 ]; then
    log_result "Memory usage" "WARN" "${MEMORY_USAGE}%"
else
    log_result "Memory usage" "FAIL" "${MEMORY_USAGE}% (critical)"
fi

# 8. Disk Usage
DISK_USAGE=$(ssh $SSH_USER@$SYSTEM_IP "df / | tail -1 | awk '{print \$5}' | sed 's/%//'")
if [ "$DISK_USAGE" -lt 80 ]; then
    log_result "Disk usage" "PASS" "${DISK_USAGE}%"
elif [ "$DISK_USAGE" -lt 90 ]; then
    log_result "Disk usage" "WARN" "${DISK_USAGE}%"
else
    log_result "Disk usage" "FAIL" "${DISK_USAGE}% (critical)"
fi

# 9. Load Average
LOAD=$(ssh $SSH_USER@$SYSTEM_IP "uptime | awk -F'load average:' '{print \$2}' | awk '{print \$1}'")
CPU_COUNT=$(ssh $SSH_USER@$SYSTEM_IP "nproc")
LOAD_THRESHOLD=$(echo "$CPU_COUNT * 0.7" | bc)
if (( $(echo "$LOAD < $LOAD_THRESHOLD" | bc -l) )); then
    log_result "Load average" "PASS" "$LOAD (threshold: $LOAD_THRESHOLD)"
else
    log_result "Load average" "WARN" "$LOAD (high, threshold: $LOAD_THRESHOLD)"
fi

# 10. Recent Errors
ERROR_COUNT=$(ssh $SSH_USER@$SYSTEM_IP "journalctl -n 100 -p 3..4 2>/dev/null | wc -l")
if [ "$ERROR_COUNT" -lt 5 ]; then
    log_result "Recent errors" "PASS" "$ERROR_COUNT errors"
elif [ "$ERROR_COUNT" -lt 20 ]; then
    log_result "Recent errors" "WARN" "$ERROR_COUNT errors"
else
    log_result "Recent errors" "FAIL" "$ERROR_COUNT errors (elevated)"
fi

# === SUMMARY ===
echo -e "\n--- Summary ---"
echo "PASS: $PASS_COUNT | WARN: $WARN_COUNT | FAIL: $FAIL_COUNT"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}Overall Status: PASS${NC}"
    exit 0
elif [ $FAIL_COUNT -le 2 ] && [ $WARN_COUNT -gt 0 ]; then
    echo -e "${YELLOW}Overall Status: WARN (check required)${NC}"
    exit 0
else
    echo -e "${RED}Overall Status: FAIL (rollback may be needed)${NC}"
    exit 1
fi
```

## Health Check Integration with n8n

```javascript
// n8n workflow node for health checks

// Execute health check script
const healthCheckResult = await bash.execute(
    `/opt/scripts/health-check.sh ${systemName} ${systemType} ${systemIP} ${sshUser}`
);

// Parse results
const passed = healthCheckResult.exitCode === 0;
const checkLog = healthCheckResult.stdout;

// Store results in database
await database.updateHealthCheck({
    systemName: systemName,
    timestamp: new Date(),
    passed: passed,
    log: checkLog,
    duration: healthCheckResult.duration
});

// Decide next action
if (passed) {
    // Health check successful - proceed
    workflow.setOutput('healthCheckPass', true);
} else {
    // Health check failed - trigger rollback
    workflow.setOutput('healthCheckPass', false);
    workflow.setVariable('rollbackLevel', 2);  // L2 snapshot restore
}
```

## Summary

- Updates follow strict dependency order (Tier 1 → 4)
- Each tier must pass health checks before proceeding
- 4 levels of health checks capture different aspects
- Automation reduces manual verification time
- Failures at any stage trigger immediate rollback
- Gates between tiers provide safety checkpoint
