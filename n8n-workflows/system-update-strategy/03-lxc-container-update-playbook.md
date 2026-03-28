# LXC Container Update Playbook

## Overview

LXC containers in Proxmox present unique challenges:
- Shared kernel with host (cannot update container kernel independently)
- Snapshot-based rollback is most effective
- Online updates possible with minimal disruption
- Layered dependencies (host changes affect all containers)

## Strategy Types

### A) Host Kernel Update Strategy (Affects All Containers)

**Impact**: All containers affected simultaneously, brief connectivity loss

**Process**:
```
1. Take snapshot of all affected containers
2. Update host kernel
3. Reboot host (affects all containers)
4. Verify all containers restart and come online
5. Health check all containers
6. If all healthy, delete snapshots
7. If any failed, restore from snapshots
```

**Timing**: Coordinate maintenance window to affect all containers at once

### B) Container Application Update Strategy (Individual)

**Impact**: Single container only, can do rolling updates

**Process**:
```
1. Select container
2. Create snapshot of container
3. Update packages inside container
4. Health check container
5. If fail, restore snapshot
6. If success, move to next container
```

**Timing**: Can update during maintenance window, stagger across containers

## Step-by-Step: Container Application Update (Individual)

### Pre-Update Phase (5-10 minutes)

**Step 1.1: Container Selection & Verification**
```bash
# Verify target container
CONTAINER="web-app-01"

# Check container is running
lxc list | grep $CONTAINER

# Verify from Proxmox perspective
pct status 100  # where 100 is VMID
```

**Step 1.2: Create Snapshot**
```bash
# Create snapshot with timestamp
SNAPSHOT_ID="before-update-$(date +%Y%m%d-%H%M%S)"

lxc snapshot $CONTAINER "$SNAPSHOT_ID"

# Verify snapshot created
lxc info $CONTAINER | grep -A 10 "Snapshots:"

# Note: Store snapshot ID for potential rollback
echo "Snapshot created: $SNAPSHOT_ID"
```

**Step 1.3: Pre-Update Health Baseline**
```bash
# Record baseline metrics before update
lxc exec $CONTAINER -- systemctl status --no-pager > /tmp/${CONTAINER}-baseline.txt
lxc exec $CONTAINER -- df -h > /tmp/${CONTAINER}-disk-baseline.txt
lxc exec $CONTAINER -- free -m > /tmp/${CONTAINER}-mem-baseline.txt
lxc exec $CONTAINER -- ps aux --sort -%cpu | head -10 > /tmp/${CONTAINER}-processes.txt

# Run application health check
lxc exec $CONTAINER -- curl -s http://localhost:8080/health || \
lxc exec $CONTAINER -- systemctl status app || echo "Health check attempt (may fail if app-specific)"
```

**Step 1.4: Backup Application State (If Applicable)**
```bash
# For stateful applications, backup configuration
lxc exec $CONTAINER -- tar -czf /tmp/app-config-backup.tar.gz /etc/app/ 2>/dev/null || true

# For databases, create dump
lxc exec $CONTAINER -- mysqldump -u root -p$MYSQL_PASS --all-databases > /tmp/backup.sql 2>/dev/null || true

# Retrieve backups to host
lxc file pull $CONTAINER/tmp/app-config-backup.tar.gz /backups/containers/ 2>/dev/null || true
```

### Update Phase (5-30 minutes depending on packages)

**Step 2.1: Update Package Lists**
```bash
# Inside container, update package lists
lxc exec $CONTAINER -- apt-get update

# Verify no errors
if [ $? -ne 0 ]; then
    echo "ERROR: apt-get update failed"
    # Troubleshoot: Check network, repository URLs
    lxc exec $CONTAINER -- apt-cache policy
    exit 1
fi
```

**Step 2.2: Dry-Run Simulation**
```bash
# Simulate upgrade to detect issues
OUTPUT=$(lxc exec $CONTAINER -- apt-get install -s dist-upgrade 2>&1)
echo "$OUTPUT" | tee /tmp/${CONTAINER}-apt-simulation.log

# Check for problematic removals
if echo "$OUTPUT" | grep -q "^Removing "; then
    echo "WARNING: Upgrade would remove packages:"
    echo "$OUTPUT" | grep "^Removing"

    # Review and decide to proceed
    read -p "Review removals above. Continue? (yes/no): " CONTINUE
    [[ "$CONTINUE" != "yes" ]] && exit 1
fi

# Check for broken dependencies
if echo "$OUTPUT" | grep -q "broken\|unmet"; then
    echo "ERROR: Broken dependencies detected, aborting"
    exit 1
fi
```

**Step 2.3: Execute Update**
```bash
# Log the update process
LOGFILE="/tmp/${CONTAINER}-update-$(date +%Y%m%d-%H%M%S).log"

echo "Starting update at $(date -Iseconds)" | tee $LOGFILE
lxc exec $CONTAINER -- apt-get -y dist-upgrade 2>&1 | tee -a $LOGFILE
UPDATE_RESULT=$?

if [ $UPDATE_RESULT -eq 0 ]; then
    echo "Update SUCCESSFUL at $(date -Iseconds)" | tee -a $LOGFILE
else
    echo "Update FAILED with exit code $UPDATE_RESULT" | tee -a $LOGFILE
    echo "ATTEMPTING ROLLBACK..."
    exit 1
fi

# Store update log in /backups for audit trail
cp $LOGFILE /backups/container-updates/
```

**Step 2.4: Handle Service Restarts**
```bash
# Check if any services need restart
RESTART_NEEDED=$(lxc exec $CONTAINER -- needrestart -b 2>&1 | grep -c "restarting")

if [ $RESTART_NEEDED -gt 0 ]; then
    echo "Services need restart. Proceeding with graceful restart..."

    # Use needrestart to auto-restart
    lxc exec $CONTAINER -- needrestart -a a

    # Alternative: manual restart of critical services
    # lxc exec $CONTAINER -- systemctl restart app
    # lxc exec $CONTAINER -- systemctl restart nginx
fi

# Wait for services to stabilize
echo "Waiting 30 seconds for services to stabilize..."
sleep 30
```

**Step 2.5: Check for Kernel Restart Requirement**
```bash
# Check if kernel update occurred
lxc exec $CONTAINER -- needs-restarting -k >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Kernel restart is pending"
    echo "Container must be restarted to apply kernel updates"
    echo "This requires HOST restart (coordinate with other containers)"
    KERNEL_RESTART_NEEDED=true
else
    echo "No kernel restart needed, container can stay running"
    KERNEL_RESTART_NEEDED=false
fi
```

### Post-Update Validation Phase (5-15 minutes)

**Step 3.1: Immediate Health Check (60 seconds)**
```bash
# System status
echo "=== System Status ==="
lxc exec $CONTAINER -- systemctl status --no-pager

# Check network connectivity
echo "=== Network Check ==="
lxc exec $CONTAINER -- ip addr show
lxc exec $CONTAINER -- ip route show
lxc exec $CONTAINER -- ping -c 1 8.8.8.8

# DNS resolution
echo "=== DNS Check ==="
lxc exec $CONTAINER -- nslookup google.com
```

**Step 3.2: Application Health Check**
```bash
# Check application is responding
echo "=== Application Health ==="

# For HTTP services
lxc exec $CONTAINER -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health || echo "App not responding"

# For database services
lxc exec $CONTAINER -- mysql -e "SELECT 1;" 2>/dev/null && echo "Database: OK" || echo "Database: Not responding"

# For generic services
lxc exec $CONTAINER -- systemctl status app --no-pager || echo "Service status check"
```

**Step 3.3: Log Analysis for Errors**
```bash
# Check system logs for errors/warnings
echo "=== Recent Log Errors ==="
lxc exec $CONTAINER -- journalctl -n 50 --no-pager -p 3..4

# Check application logs
echo "=== Application Log Errors ==="
lxc exec $CONTAINER -- tail -50 /var/log/app.log 2>/dev/null | grep -i "error\|failed\|exception" || echo "No errors found in app log"

# Check for kernel panics/OOM
echo "=== Kernel Issues ==="
lxc exec $CONTAINER -- dmesg | tail -20 | grep -i "panic\|oom" || echo "No kernel issues"
```

**Step 3.4: Performance Baseline Comparison**
```bash
# Compare with pre-update metrics
echo "=== Metric Comparison ==="

# CPU/Memory
echo "Pre-update memory:"
cat /tmp/${CONTAINER}-mem-baseline.txt
echo "Current memory:"
lxc exec $CONTAINER -- free -m

# Disk space
echo "Pre-update disk:"
cat /tmp/${CONTAINER}-disk-baseline.txt
echo "Current disk:"
lxc exec $CONTAINER -- df -h /

# Top processes
echo "Top CPU consumers:"
lxc exec $CONTAINER -- ps aux --sort -%cpu | head -5
```

**Step 3.5: Extended Health Monitoring (5 minutes)**
```bash
# Monitor container for 5 minutes for stability
echo "Monitoring container for 5 minutes..."
for i in {1..5}; do
    echo "Minute $i - $(date)"

    # Check service status
    lxc exec $CONTAINER -- systemctl is-active app

    # Check for memory leaks (increasing memory)
    lxc exec $CONTAINER -- free -h | grep ^Mem

    # Check for CPU spikes
    lxc exec $CONTAINER -- uptime

    # Check for new errors in logs
    lxc exec $CONTAINER -- journalctl -n 5 --no-pager -p 3..4

    [[ $i -lt 5 ]] && sleep 60
done
```

### Rollback Phase (If Needed)

**Step 4.1: Immediate Rollback Decision**
```bash
# If health checks failed, initiate rollback
HEALTH_CHECK_FAILED=false

# Run critical health checks
lxc exec $CONTAINER -- systemctl is-active app >/dev/null 2>&1 || HEALTH_CHECK_FAILED=true
lxc exec $CONTAINER -- curl -s http://localhost:8080/health >/dev/null 2>&1 || HEALTH_CHECK_FAILED=true

if [ "$HEALTH_CHECK_FAILED" = true ]; then
    echo "HEALTH CHECK FAILED - Initiating rollback"
    echo "$(date): Rollback initiated" >> /tmp/${CONTAINER}-rollback.log
fi
```

**Step 4.2: Rollback to Snapshot**
```bash
# Stop container
echo "Stopping container..."
lxc stop $CONTAINER

# Restore snapshot
echo "Restoring snapshot: $SNAPSHOT_ID"
lxc restore $CONTAINER "$SNAPSHOT_ID"

# Start container
echo "Starting container..."
lxc start $CONTAINER

# Wait for container to fully boot
echo "Waiting 30 seconds for container to boot..."
sleep 30

# Verify container is running
lxc list | grep $CONTAINER
```

**Step 4.3: Post-Rollback Validation**
```bash
# Verify rollback was successful
echo "=== Post-Rollback Validation ==="

# Check container running
lxc exec $CONTAINER -- systemctl status --no-pager

# Check application
lxc exec $CONTAINER -- curl -s http://localhost:8080/health || echo "App health check"

# Check data integrity
lxc exec $CONTAINER -- mysql -e "SHOW DATABASES;" 2>/dev/null || echo "DB check"

# Verify we're back to pre-update state
echo "Verify services are running as before update"
```

**Step 4.4: Post-Rollback Investigation**
```bash
# Retrieve logs to investigate
lxc file pull $CONTAINER/var/log/app.log /backups/container-incidents/ 2>/dev/null
lxc exec $CONTAINER -- journalctl -p 3..4 -n 100 > /tmp/rollback-analysis.log

# Document incident
cat > /tmp/incident-${CONTAINER}-$(date +%Y%m%d-%H%M%S).txt <<EOF
Container: $CONTAINER
Snapshot: $SNAPSHOT_ID
Update time: $UPDATE_TIMESTAMP
Rollback time: $(date -Iseconds)
Reason: Application health check failed
Next action: Investigate logs and plan retry

Logs saved to:
- /backups/container-incidents/app.log
- /tmp/rollback-analysis.log

For retry:
1. Wait 24 hours
2. Investigate error cause
3. Apply fixes (package versions, config changes)
4. Attempt update again
EOF

# Alert operations team
echo "INCIDENT: $CONTAINER rollback needed - investigation required"
```

## Step-by-Step: Host Kernel Update (All Containers)

### Pre-Update Phase

**Step 1.1: Coordinate with All Container Owners**
```bash
# List all containers to be affected
lxc list -c n,s

# Create maintenance notification
cat > /tmp/maintenance-notice.txt <<EOF
MAINTENANCE WINDOW: $(date -d '+2 days' +%Y-%m-%d" "02:00-04:00)
IMPACT: All LXC containers will be temporarily unreachable
REASON: Host kernel update
EXPECTED DURATION: 10-15 minutes total
  - Update: 5 minutes
  - Reboot: 2 minutes
  - Container restart: 5 minutes
  - Validation: 5 minutes

ACTION REQUIRED: No action needed, automatic process
COMMUNICATION: Updates will be posted to status page

Questions: Contact ops-team@example.com
EOF

# Notify stakeholders (integration with ticketing system)
```

**Step 1.2: Take Snapshots of All Containers**
```bash
# Create snapshots of all running containers
SNAPSHOT_ID="host-kernel-update-$(date +%Y%m%d-%H%M%S)"

for CONTAINER in $(lxc list -c n -f csv); do
    echo "Creating snapshot of $CONTAINER..."
    lxc snapshot $CONTAINER "$SNAPSHOT_ID"

    # Verify snapshot
    lxc info $CONTAINER | grep -q "$SNAPSHOT_ID" && \
        echo "  Snapshot created: $SNAPSHOT_ID" || \
        echo "  ERROR: Snapshot failed for $CONTAINER"
done

# Log snapshot IDs for potential mass-restore
lxc list -c n -f csv | while read CONTAINER; do
    echo "$CONTAINER:$SNAPSHOT_ID"
done > /tmp/container-snapshots.txt
```

**Step 1.3: Backup Host Kernel Config**
```bash
# Backup current kernel configuration
cp /boot/config-$(uname -r) /backups/kernel-backup/config-$(date +%Y%m%d).txt
cp /boot/grub/grub.cfg /backups/kernel-backup/grub.cfg-$(date +%Y%m%d)

# Document current kernel
uname -a > /tmp/kernel-before-update.txt
```

### Update Phase

**Step 2.1: Update Kernel on Host**
```bash
# Update package lists
apt-get update

# Get available kernel versions
apt-cache search linux-image | grep linux-image-generic

# Simulate kernel upgrade
apt-get install -s linux-image-generic 2>&1 | tee /tmp/kernel-upgrade-sim.log

# Check for issues
grep -i "error\|broken\|conflict" /tmp/kernel-upgrade-sim.log && \
    echo "Issues found, aborting" && exit 1

# Install new kernel
echo "Installing new kernel..."
apt-get -y install linux-image-generic linux-headers-generic 2>&1 | tee /tmp/kernel-install.log

if [ $? -eq 0 ]; then
    echo "Kernel installation successful"
else
    echo "ERROR: Kernel installation failed"
    exit 1
fi

# Update GRUB configuration
update-grub
```

**Step 2.2: Verify Boot Configuration**
```bash
# Check GRUB menu entries
grub-mkconfig -o /boot/grub/grub.cfg

# Verify multiple boot options exist
grep "^menuentry" /boot/grub/grub.cfg | wc -l

# Check if new kernel is default
grep "GRUB_DEFAULT" /etc/default/grub

# Verify boot partition has space
df /boot
```

**Step 2.3: Schedule and Execute Reboot**
```bash
# Set maintenance window start
echo "Host will reboot in 2 minutes. Stopping new container creation..."

# Stop accepting new connections (drain load balancer)
# This would integrate with your infrastructure - example:
# curl -X POST http://localhost:5000/maintenance/drain

# Announce reboot to all users
wall "System reboot in 2 minutes for kernel update"

# Actually reboot
echo "Rebooting system..."
shutdown -r +2 "Kernel update - automatic reboot"

# Or immediate reboot if in maintenance window
reboot
```

### Post-Update Validation Phase

**Step 3.1: Verify Host is Back Online (Automated, runs after reboot)**
```bash
# This script should run at boot to auto-verify
# Add to /etc/rc.local or systemd service

#!/bin/bash

echo "Post-reboot validation started at $(date)" | logger

# Wait for system to fully boot
sleep 30

# Verify we're running new kernel
NEW_KERNEL=$(uname -r)
echo "Current kernel: $NEW_KERNEL" | logger

# Check if it's the expected new kernel
grep -i "$NEW_KERNEL" /tmp/kernel-before-update.txt && \
    echo "ERROR: Still running old kernel!" | logger && exit 1

# Verify all containers are online
EXPECTED_CONTAINERS=$(lxc list -c n -f csv | wc -l)
ONLINE_CONTAINERS=$(lxc list -c n,s -f csv | grep RUNNING | wc -l)

echo "Containers: $ONLINE_CONTAINERS/$EXPECTED_CONTAINERS online" | logger

if [ $ONLINE_CONTAINERS -eq $EXPECTED_CONTAINERS ]; then
    echo "All containers online - kernel update successful" | logger
else
    echo "WARNING: Some containers not online, checking..." | logger
    lxc list -c n,s
fi
```

**Step 3.2: Validate Each Container**
```bash
# Health check all containers
for CONTAINER in $(lxc list -c n -f csv); do
    echo "Validating $CONTAINER..."

    # Container is running
    lxc list | grep -q "$CONTAINER.*RUNNING" || {
        echo "ERROR: $CONTAINER not running"
        continue
    }

    # Container is responsive
    lxc exec $CONTAINER -- systemctl is-system-running >/dev/null 2>&1 || {
        echo "WARNING: $CONTAINER system not fully ready"
    }

    # Application is running (example for web app)
    lxc exec $CONTAINER -- curl -s http://localhost:8080/health >/dev/null 2>&1 && \
        echo "  Health check: PASS" || echo "  Health check: needs investigation"
done
```

**Step 3.3: Container-Specific Recovery**
```bash
# If a container is not coming up automatically, investigate
FAILED_CONTAINER="web-app-02"

# Check container logs
lxc exec $FAILED_CONTAINER -- journalctl -n 50 -p 3..4 2>&1 || \
    echo "Cannot access container logs"

# Check from Proxmox perspective
pct status 102  # Check VMID

# Try restart
lxc restart $FAILED_CONTAINER

# Monitor for 2 minutes
for i in {1..12}; do
    sleep 10
    lxc exec $FAILED_CONTAINER -- systemctl is-system-running && {
        echo "Container recovered"
        break
    }
done
```

## LXC Container Update Summary

| Phase | Duration | Key Actions |
|-------|----------|------------|
| **Pre-Update** | 5-10 min | Snapshot, baseline, notification |
| **Update** | 5-30 min | apt update/upgrade, service restart |
| **Validation** | 5-15 min | Health checks, log review, monitoring |
| **Rollback (if needed)** | 2-5 min | Stop, restore, start, verify |

## Automation Considerations

- Individual container updates can be parallelized (update 3-5 simultaneously)
- Host kernel updates affect all containers, must be coordinated
- Snapshots should be retained for at least 24 hours post-update
- All updates must be logged with timestamps for audit trail
- Integration with n8n for automated sequencing and reporting
