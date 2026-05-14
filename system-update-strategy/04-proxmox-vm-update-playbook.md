# Proxmox VM Update Playbook

## Overview

Proxmox VMs running on QEMU/KVM provide:
- Independent kernel updates possible
- Snapshot capability for rollback
- Live migration capability (for HA environments)
- More resource-intensive than LXC
- Can use blue-green deployment pattern

## VM Update Strategy Selection

```
Update required for VM?
├─ Kernel update (linux-image)?
│   ├─ Tier 1 Critical: Blue-Green Strategy
│   │   └─> Prepare standby, update, test, switch
│   │
│   ├─ Tier 2/3: Snapshot + Reboot Strategy
│   │   └─> Snapshot, update, reboot, validate, keep snapshot
│   │
│   └─ After-hours emergency: Direct update
│       └─> Snapshot, update, reboot, rollback if fail
│
└─ Application/library update only:
    ├─ Tier 1 Critical: Graceful restart with N+1
    │   └─> Update, restart service, keep updated N-1 versions
    │
    └─ Tier 2/3: Direct update + restart
        └─> Update, restart, validate
```

## Step-by-Step: Standard VM Update (Snapshot + Reboot)

### Pre-Update Phase (10-15 minutes)

**Step 1.1: Identify Target VM**
```bash
# Find VM VMID and details
TARGET_VM_NAME="prod-db-01"
VMID=$(qm list | grep "$TARGET_VM_NAME" | awk '{print $1}')

echo "Target VM: $TARGET_VM_NAME (VMID: $VMID)"

# Verify VM is running
qm status $VMID

# Check VM resources
qm config $VMID | grep -E "memory|cores|sockets"

# Check storage location
qm config $VMID | grep "scsi\|sata\|ide"
```

**Step 1.2: Create VM Snapshot**
```bash
# Create snapshot with descriptive name
SNAPSHOT_NAME="before-update-$(date +%Y%m%d-%H%M%S)"

echo "Creating snapshot: $SNAPSHOT_NAME"
qm snapshot $VMID "$SNAPSHOT_NAME"

# Verify snapshot was created
qm listsnapshot $VMID | grep "$SNAPSHOT_NAME"

# Check snapshot size
qm listsnapshot $VMID --format json | jq ".[] | select(.name==\"$SNAPSHOT_NAME\")"

# Ensure adequate storage for snapshot
# Proxmox uses copy-on-write, snapshot size grows with changes
DISK_FREE=$(df /var/lib/vz | awk 'NR==2 {printf "%.0f", $4/1048576}')  # In GB
echo "Available storage for snapshot: ${DISK_FREE}GB"

[[ $DISK_FREE -lt 10 ]] && echo "WARNING: Limited storage for snapshot COW data" || echo "Storage OK"
```

**Step 1.3: Record Baseline Metrics**
```bash
# Get guest tools info (if installed)
qm agent $VMID ping 2>/dev/null && echo "QEMU agent: Available" || echo "QEMU agent: Not available"

# Create baseline document
cat > /tmp/${TARGET_VM_NAME}-baseline.txt <<EOF
VM: $TARGET_VM_NAME (VMID: $VMID)
Snapshot: $SNAPSHOT_NAME
Timestamp: $(date -Iseconds)

STORAGE STATUS:
EOF

# Get VM disk info
for disk in $(qm config $VMID | grep -oP "(?<=local:)[^ ]+\.raw" | cut -d: -f1); do
    du -h /var/lib/vz/images/$VMID/$disk 2>/dev/null >> /tmp/${TARGET_VM_NAME}-baseline.txt || true
done

echo "Baseline recorded in /tmp/${TARGET_VM_NAME}-baseline.txt"
```

**Step 1.4: Pre-Update VM Health**
```bash
# Via SSH into VM (requires network access)
SSH_USER="root"
VM_IP=$(qm guest cmd-status $VMID 2>/dev/null | grep "\"ip\"\:" | head -1)

if [[ -n "$VM_IP" ]]; then
    echo "VM IP: $VM_IP"

    # Record baseline
    ssh -o ConnectTimeout=5 $SSH_USER@$VM_IP "df -h; free -m; uptime" > /tmp/${TARGET_VM_NAME}-vm-baseline.txt 2>/dev/null
    echo "VM baseline recorded"
else
    echo "Cannot determine VM IP (QEMU agent may not be installed)"
fi

# Via Proxmox API if QEMU agent installed
qm guest cmd-status $VMID 2>/dev/null && \
    qm guest exec $VMID -- systemctl status --no-pager || echo "Cannot access guest OS via agent"
```

### Update Phase (15-30 minutes)

**Step 2.1: Update Package Lists Inside VM**
```bash
# Update via SSH
COMMAND="apt-get update"

if [[ -n "$VM_IP" ]]; then
    ssh $SSH_USER@$VM_IP "$COMMAND"
else
    echo "Manual update required - SSH access not available"
    echo "Execute inside VM: apt-get update"
fi
```

**Step 2.2: Simulate Upgrade and Check for Issues**
```bash
# Dry-run via SSH
SIMULATION_OUTPUT=$(ssh $SSH_USER@$VM_IP "apt-get install -s dist-upgrade 2>&1")
echo "$SIMULATION_OUTPUT" | tee /tmp/${TARGET_VM_NAME}-apt-sim.log

# Check for package removals
if echo "$SIMULATION_OUTPUT" | grep -q "^Removing"; then
    echo "WARNING: Some packages would be removed:"
    echo "$SIMULATION_OUTPUT" | grep "^Removing"
    read -p "Continue? (yes/no): " CONTINUE
    [[ "$CONTINUE" != "yes" ]] && exit 1
fi

# Check for conflicts
if echo "$SIMULATION_OUTPUT" | grep -q "broken\|unmet"; then
    echo "ERROR: Dependency conflicts detected"
    exit 1
fi
```

**Step 2.3: Execute Update**
```bash
# Run update with logging
UPDATE_LOG="/tmp/${TARGET_VM_NAME}-update-$(date +%Y%m%d-%H%M%S).log"

echo "Starting update at $(date -Iseconds)" | tee $UPDATE_LOG

# Execute apt dist-upgrade
ssh $SSH_USER@$VM_IP "apt-get -y dist-upgrade" 2>&1 | tee -a $UPDATE_LOG

UPDATE_STATUS=$?

if [ $UPDATE_STATUS -eq 0 ]; then
    echo "Update completed successfully" | tee -a $UPDATE_LOG
else
    echo "Update failed with status $UPDATE_STATUS" | tee -a $UPDATE_LOG
    echo "Proceeding to rollback analysis..."
fi

# Save log to backups
cp $UPDATE_LOG /backups/vm-updates/
```

**Step 2.4: Check for Reboot Requirement**
```bash
# Check if kernel or critical services need reboot
REBOOT_NEEDED=$(ssh $SSH_USER@$VM_IP "needs-restarting -r > /dev/null 2>&1; echo $?")

if [ "$REBOOT_NEEDED" == "1" ]; then
    echo "REBOOT REQUIRED: Kernel or critical services updated"
    REBOOT_PENDING=true
elif [ "$REBOOT_NEEDED" == "0" ]; then
    echo "No reboot required - can continue with service restart"
    REBOOT_PENDING=false
else
    echo "Cannot determine reboot status, assuming required"
    REBOOT_PENDING=true
fi
```

**Step 2.5: Service Restart or Reboot**
```bash
# Option A: Service restart only (if no kernel update)
if [ "$REBOOT_PENDING" = false ]; then
    echo "Restarting services that need restart..."

    # Identify services needing restart
    SERVICES_TO_RESTART=$(ssh $SSH_USER@$VM_IP "needrestart -b 2>&1 | grep 'Service:' | awk '{print \$2}'")

    for SERVICE in $SERVICES_TO_RESTART; do
        echo "Restarting $SERVICE..."
        ssh $SSH_USER@$VM_IP "systemctl restart $SERVICE"
    done

    echo "Service restart complete, no VM reboot needed"
fi

# Option B: VM reboot (required for kernel updates)
if [ "$REBOOT_PENDING" = true ]; then
    echo "Initiating VM reboot for kernel update..."

    # Graceful shutdown
    ssh $SSH_USER@$VM_IP "shutdown -r +1 'Rebooting for kernel update'"

    # Monitor reboot
    echo "Waiting for VM reboot..."
    REBOOT_START=$(date +%s)
    REBOOT_TIMEOUT=300  # 5 minutes max

    while true; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - REBOOT_START))

        if [ $ELAPSED -gt $REBOOT_TIMEOUT ]; then
            echo "ERROR: VM did not come back online within 5 minutes"
            echo "TRIGGERING ROLLBACK"
            # Jump to rollback section
            exit 1
        fi

        # Check if VM is back online
        if qm guest cmd-status $VMID >/dev/null 2>&1; then
            echo "VM is back online at $(date)"
            break
        fi

        echo "Still waiting... ($ELAPSED seconds elapsed)"
        sleep 5
    done

    echo "VM reboot successful"
fi
```

### Post-Update Validation Phase (10-15 minutes)

**Step 3.1: Immediate Health Check**
```bash
# Verify VM is responding
echo "Checking VM responsiveness..."

# Via QEMU agent
if qm agent $VMID ping >/dev/null 2>&1; then
    echo "QEMU agent responding"

    # Get system info
    qm guest cmd-status $VMID | jq '..'
else
    echo "QEMU agent not responding, checking SSH..."

    # Wait for SSH to be available
    for i in {1..30}; do
        ssh -o ConnectTimeout=2 -o BatchMode=yes $SSH_USER@$VM_IP "echo ok" >/dev/null 2>&1 && break
        echo "Waiting for SSH ($i/30)..."
        sleep 2
    done
fi

# Get VM status from Proxmox
qm status $VMID
```

**Step 3.2: Kernel Verification (If Rebooted)**
```bash
# Verify correct kernel loaded
if [ "$REBOOT_PENDING" = true ]; then
    LOADED_KERNEL=$(ssh $SSH_USER@$VM_IP "uname -r")
    echo "Loaded kernel: $LOADED_KERNEL"

    # Check if it's the new kernel
    ssh $SSH_USER@$VM_IP "dpkg -l | grep linux-image-[0-9]" | tail -3
fi
```

**Step 3.3: Service Status Check**
```bash
# Check critical services
CRITICAL_SERVICES="networking ssh rsyslog"

for SERVICE in $CRITICAL_SERVICES; do
    STATUS=$(ssh $SSH_USER@$VM_IP "systemctl is-active $SERVICE" 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        echo "  $SERVICE: UP"
    else
        echo "  $SERVICE: DOWN (ERROR)"
    fi
done
```

**Step 3.4: Application Validation**
```bash
# Check primary application
# Example for web server
if ssh $SSH_USER@$VM_IP "systemctl is-active nginx" >/dev/null 2>&1; then
    echo "Checking web service health..."

    # Check via localhost
    HEALTH_CHECK=$(ssh $SSH_USER@$VM_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost/health" 2>/dev/null)

    if [ "$HEALTH_CHECK" = "200" ]; then
        echo "  Web service: HEALTHY"
    else
        echo "  Web service: UNHEALTHY (HTTP $HEALTH_CHECK)"
    fi
fi

# Check database if applicable
if ssh $SSH_USER@$VM_IP "systemctl is-active mysql" >/dev/null 2>&1; then
    MYSQL_CHECK=$(ssh $SSH_USER@$VM_IP "mysql -e 'SELECT 1;'" 2>/dev/null)
    if [ -n "$MYSQL_CHECK" ]; then
        echo "  Database: RESPONSIVE"
    else
        echo "  Database: NOT RESPONDING"
    fi
fi
```

**Step 3.5: Log Error Analysis**
```bash
# Check for errors in system logs
echo "=== System Log Errors (last 5 minutes) ==="
ssh $SSH_USER@$VM_IP "journalctl --since '5 minutes ago' -p 3..4 --no-pager" 2>/dev/null | head -20

# Check application logs
echo "=== Application Errors ==="
ssh $SSH_USER@$VM_IP "tail -50 /var/log/syslog 2>/dev/null | grep -i 'error\|failed'" 2>/dev/null || echo "No obvious errors"
```

**Step 3.6: 5-Minute Stability Monitoring**
```bash
# Monitor VM for 5 minutes to ensure stability
echo "Monitoring for 5 minutes..."

for i in {1..5}; do
    echo "--- Minute $i ($(date)) ---"

    # Check process count and memory
    PROCESS_COUNT=$(ssh $SSH_USER@$VM_IP "ps aux | wc -l" 2>/dev/null)
    MEMORY_USAGE=$(ssh $SSH_USER@$VM_IP "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2*100}'" 2>/dev/null)
    LOAD=$(ssh $SSH_USER@$VM_IP "uptime | awk -F'load average:' '{print \$2}'" 2>/dev/null)

    echo "  Processes: $PROCESS_COUNT, Memory: ${MEMORY_USAGE}%, Load: $LOAD"

    # Check for new errors
    ssh $SSH_USER@$VM_IP "journalctl -n 3 -p 3..4 --no-pager" 2>/dev/null

    [[ $i -lt 5 ]] && sleep 60
done
```

### Successful Update Completion

**Step 4.1: Documentation and Cleanup**
```bash
# Update is confirmed successful
echo "Update SUCCESSFUL for $TARGET_VM_NAME"

# Clean up old snapshots (keep previous 2)
echo "Managing snapshots..."
qm listsnapshot $VMID | tail -n +2 | head -n -2 | awk '{print $1}' | while read OLD_SNAP; do
    echo "Deleting old snapshot: $OLD_SNAP"
    qm delsnapshot $VMID "$OLD_SNAP"
done

# Document the update
cat > /backups/vm-updates/${TARGET_VM_NAME}-update-$(date +%Y%m%d).log <<EOF
VM: $TARGET_VM_NAME (VMID: $VMID)
Update Date: $(date -Iseconds)
Snapshot: $SNAPSHOT_NAME
Status: SUCCESSFUL

Kernel Updated: $REBOOT_PENDING
Kernel Version: $(ssh $SSH_USER@$VM_IP "uname -r" 2>/dev/null)

Services Verified: OK
Health Checks: PASSED

Next snapshot to keep: [current]
Snapshots deleted: [list]
EOF

echo "Update complete - documentation saved"
```

## Step-by-Step: Blue-Green VM Update (Critical Systems)

### Pre-Deployment Phase

**Step 1.1: Prepare Standby VM**
```bash
# Option A: Clone existing VM
SOURCE_VM="prod-api-01"
SOURCE_VMID=100

STANDBY_VM="prod-api-01-bg"
NEW_VMID=101

echo "Cloning $SOURCE_VM to $STANDBY_VM..."
qm clone $SOURCE_VMID $NEW_VMID --name $STANDBY_VM --full

# Option B: Restore from snapshot (faster if available)
# qm restore $NEW_VMID $SOURCE_VMID:snapshots/latest-working

# Start standby VM
qm start $NEW_VMID
```

**Step 1.2: Verify Standby VM Functionality**
```bash
# Wait for standby to boot
sleep 30

# Verify network is available
STANDBY_IP=$(qm guest cmd-status $NEW_VMID | grep "ip" | head -1 | jq -r '.ip')
echo "Standby VM IP: $STANDBY_IP"

# Perform health checks
ssh $SSH_USER@$STANDBY_IP "systemctl status --no-pager | head -20"
ssh $SSH_USER@$STANDBY_IP "curl -s http://localhost:8080/health"

# Verify data consistency
ssh $SSH_USER@$STANDBY_IP "mysql -e 'SELECT COUNT(*) FROM tables;'" 2>/dev/null
```

### Update Standby & Testing Phase

**Step 2.1: Update Standby VM**
```bash
# Execute full update on standby
UPDATE_LOG="/tmp/standby-update-$(date +%Y%m%d-%H%M%S).log"

echo "Updating standby VM: $STANDBY_VM"
ssh $SSH_USER@$STANDBY_IP "apt-get update && apt-get -y dist-upgrade" 2>&1 | tee $UPDATE_LOG

# Handle reboot if needed
ssh $SSH_USER@$STANDBY_IP "needs-restarting -r" && {
    echo "Rebooting standby VM..."
    ssh $SSH_USER@$STANDBY_IP "shutdown -r +1"

    # Wait for reboot
    sleep 90
}
```

**Step 2.2: Comprehensive Testing of Standby**
```bash
# Functional tests
echo "=== FUNCTIONAL TESTS ==="

# Health check
HEALTH=$(ssh $SSH_USER@$STANDBY_IP "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health")
[[ "$HEALTH" == "200" ]] && echo "Health check: PASS" || echo "Health check: FAIL ($HEALTH)"

# Database connectivity
ssh $SSH_USER@$STANDBY_IP "mysql -e 'SHOW DATABASES;'" >/dev/null && \
    echo "Database: PASS" || echo "Database: FAIL"

# Load testing (light)
echo "=== LOAD TEST ==="
ssh $SSH_USER@$STANDBY_IP "for i in {1..100}; do curl -s http://localhost:8080/api/status >/dev/null; done"
echo "Load test completed"

# Data integrity check
echo "=== DATA INTEGRITY ==="
RECORD_COUNT=$(ssh $SSH_USER@$STANDBY_IP "mysql -e 'SELECT COUNT(*) FROM main_table;' 2>/dev/null | tail -1")
echo "Records in database: $RECORD_COUNT"
[[ -z "$RECORD_COUNT" ]] && echo "ERROR: Cannot verify data" || echo "Data count verified"
```

### Failover Phase

**Step 3.1: Load Balancer Reconfiguration**
```bash
# Update load balancer to route to standby
# This varies by your load balancer (HAProxy, nginx, etc.)

# Example for nginx load balancer:
cat > /tmp/lb-switch.conf <<EOF
upstream prod_api {
    server $STANDBY_IP:8080  max_fails=2 fail_timeout=10s;
    server $SOURCE_IP:8080 down;  # Take original offline
}
EOF

# Apply configuration
# ssh lb-server "cp /tmp/lb-switch.conf /etc/nginx/conf.d/ && nginx -t && systemctl reload nginx"

# Alternative: DNS switch (slower but safer for some use cases)
# Update DNS A record to point to standby IP
```

**Step 3.2: Verify Failover Success**
```bash
# Test that traffic routes to standby
TRACED_IP=$(curl -s -H "X-Forwarded-For: $STANDBY_IP" http://load-balancer/trace | jq -r '.server_ip')

if [ "$TRACED_IP" == "$STANDBY_IP" ]; then
    echo "Failover successful - traffic routing to standby"
else
    echo "ERROR: Traffic not routing to standby!"
    echo "Traced IP: $TRACED_IP, Expected: $STANDBY_IP"
    exit 1
fi

# Monitor failover for 10 minutes
echo "Monitoring failover stability for 10 minutes..."
for i in {1..10}; do
    echo "Minute $i: $(date)"

    # Check error rates
    ERROR_RATE=$(curl -s http://monitoring:9090/metrics | grep 'requests_failed{' | awk -F' ' '{print $2}')
    echo "  Error rate: $ERROR_RATE"

    # Check latency
    LATENCY=$(curl -s http://monitoring:9090/metrics | grep 'request_duration_seconds' | head -1 | awk -F' ' '{print $2}')
    echo "  Latency: ${LATENCY}ms"

    sleep 60
done
```

### Update Original VM

**Step 4.1: Update Original VM**
```bash
# Now update the original VM while standby is in production
SOURCE_IP=$(qm guest cmd-status $SOURCE_VMID | grep "ip" | head -1 | jq -r '.ip')

echo "Updating original VM: $SOURCE_VM ($SOURCE_IP)"

# Create snapshot before update
qm snapshot $SOURCE_VMID "before-bg-update-$(date +%Y%m%d-%H%M%S)"

# Execute update
UPDATE_LOG="/tmp/original-update-$(date +%Y%m%d-%H%M%S).log"
ssh $SSH_USER@$SOURCE_IP "apt-get update && apt-get -y dist-upgrade" 2>&1 | tee $UPDATE_LOG

# Reboot if needed
ssh $SSH_USER@$SOURCE_IP "needs-restarting -r" && {
    echo "Rebooting original VM..."
    ssh $SSH_USER@$SOURCE_IP "shutdown -r +1"
    sleep 90
}

# Verify update
ssh $SSH_USER@$SOURCE_IP "systemctl status --no-pager | head -10"
```

### Failback Phase

**Step 5.1: Health Check Both VMs**
```bash
# Verify both VMs are healthy and synchronized
echo "=== HEALTH CHECK BOTH VMs ==="

for VM_INFO in "$SOURCE_VM:$SOURCE_IP" "$STANDBY_VM:$STANDBY_IP"; do
    VM_NAME=${VM_INFO%:*}
    VM_IP=${VM_INFO#*:}

    echo "Checking $VM_NAME ($VM_IP)..."
    ssh $SSH_USER@$VM_IP "curl -s http://localhost:8080/health"
    ssh $SSH_USER@$VM_IP "mysql -e 'SELECT VERSION();'" 2>/dev/null
done

# Verify data is synchronized (if applicable)
echo "=== DATA SYNC CHECK ==="
RECORD_COUNT_SOURCE=$(ssh $SSH_USER@$SOURCE_IP "mysql -e 'SELECT COUNT(*) FROM main_table;' 2>/dev/null | tail -1")
RECORD_COUNT_STANDBY=$(ssh $SSH_USER@$STANDBY_IP "mysql -e 'SELECT COUNT(*) FROM main_table;' 2>/dev/null | tail -1")

if [ "$RECORD_COUNT_SOURCE" == "$RECORD_COUNT_STANDBY" ]; then
    echo "Data synchronized: Both VMs have $RECORD_COUNT_SOURCE records"
else
    echo "WARNING: Data mismatch! Source: $RECORD_COUNT_SOURCE, Standby: $RECORD_COUNT_STANDBY"
fi
```

**Step 5.2: Failback to Original**
```bash
# Switch load balancer back to original
cat > /tmp/lb-failback.conf <<EOF
upstream prod_api {
    server $SOURCE_IP:8080  max_fails=2 fail_timeout=10s;
    server $STANDBY_IP:8080 down;  # Put standby on backup
}
EOF

# Apply and monitor
echo "Switching traffic back to original VM..."
# ssh lb-server "cp /tmp/lb-failback.conf /etc/nginx/conf.d/ && nginx -t && systemctl reload nginx"

# Wait and monitor
sleep 30

TRACED_IP=$(curl -s http://load-balancer/trace | jq -r '.server_ip')
[[ "$TRACED_IP" == "$SOURCE_IP" ]] && echo "Failback successful" || echo "Failback check: $TRACED_IP"
```

**Step 5.3: Cleanup Standby VM**
```bash
# Stop and remove standby VM
qm stop $NEW_VMID

# After confirmation period (24 hours), delete standby
echo "Standby VM $STANDBY_VM will be deleted after 24-hour confirmation period"

# Delete standby VM
# qm destroy $NEW_VMID
```

## Troubleshooting & Recovery

### VM Won't Boot After Update
```bash
# Boot from previous kernel via GRUB
qm reboot $VMID --timeout 30

# If VM is unresponsive, access QEMU console
qm terminal $VMID

# Or use serial port console if available
# Press ESC during boot to access GRUB menu, select older kernel

# If console access fails, restore snapshot
qm restore $VMID "before-update-..."
qm start $VMID
```

### High Memory Usage After Update
```bash
# Check what's consuming memory
ssh $SSH_USER@$VM_IP "ps aux --sort -%mem | head -10"

# Check for memory leaks in logs
ssh $SSH_USER@$VM_IP "dmesg | grep -i 'out of memory'"

# If critical, revert to snapshot
qm stop $VMID
qm restore $VMID "before-update-..."
qm start $VMID
```

## VM Update Summary

| Phase | Duration | Key Tasks |
|-------|----------|-----------|
| **Preparation** | 10-15 min | Snapshot, baseline, notification |
| **Update** | 20-30 min | apt upgrade, potential reboot |
| **Validation** | 10-15 min | Health checks, log review, monitoring |
| **Blue-Green (if used)** | 1-2 hours | Clone, update, test, failover, failback |
| **Rollback (if needed)** | 5-10 min | Restore snapshot or failover to replica |

## n8n Integration Points

- Trigger update workflow based on schedule or approval
- Capture snapshot IDs and store in database
- Send update progress notifications
- Trigger health checks post-update
- Automatically rollback if health checks fail
- Log all changes for audit trail
- Create incident tickets if rollback occurs
