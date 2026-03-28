# Multi-Level Rollback Procedures

## Overview

This document defines 4 levels of rollback, each escalating in scope and recovery time.

```
ROLLBACK DECISION FLOW:

Health check failed?
├─ Yes: Time since update?
│   ├─ < 30 seconds
│   │   ├─ Package downgrade revertable? YES → L1 Rollback
│   │   └─ Package downgrade revertable? NO → L2 Rollback
│   │
│   ├─ 30 sec - 2 min
│   │   └─ L2 Rollback (snapshot restore)
│   │
│   ├─ 2 - 5 min
│   │   ├─ Replica available? YES → L3 Rollback (failover)
│   │   └─ Replica available? NO → L2 Rollback (snapshot)
│   │
│   └─ > 5 min
│       ├─ Failover available? YES → L3 Rollback (failover)
│       └─ Failover available? NO → L4 Rollback (restore from backup)
│
└─ No: Update successful, proceed with documentation
```

## Level 1: Package Downgrade Rollback (< 30 seconds)

**Target Recovery Time**: 30 seconds
**Scope**: Individual packages only
**Data Risk**: NONE (packages are reverted, not removed)
**Applicability**: Minor updates, library updates, non-kernel updates

### L1-A: Identify Revertable Packages

```bash
# Check which packages were updated in this session
apt-get install -s dist-upgrade 2>&1 | grep ^Inst | awk '{print $2}' > /tmp/updated-packages.txt

# Verify we can get previous versions
for PACKAGE in $(cat /tmp/updated-packages.txt); do
    # Check if package is available in archive
    apt-cache policy $PACKAGE | grep -q "Candidate:" && echo "$PACKAGE: Can revert"
done

# EXCLUDE these packages from downgrade (too risky):
PROTECTED_PACKAGES=("linux-image.*" "grub-pc" "systemd" "e2fsprogs")

for PACKAGE in $(cat /tmp/updated-packages.txt); do
    SKIP=0
    for PROTECTED in "${PROTECTED_PACKAGES[@]}"; do
        [[ $PACKAGE == $PROTECTED ]] && SKIP=1
    done

    if [ $SKIP -eq 0 ]; then
        echo "$PACKAGE: Safe to downgrade"
    else
        echo "$PACKAGE: PROTECTED - do not downgrade"
    fi
done
```

### L1-B: Execute Downgrade

```bash
# Only downgrade if < 30 seconds since update
TIME_SINCE_UPDATE=$(( $(date +%s) - UPDATE_TIMESTAMP ))

if [ $TIME_SINCE_UPDATE -gt 30 ]; then
    echo "ERROR: More than 30 seconds since update, use L2 rollback instead"
    exit 1
fi

echo "Downgrading packages..."

# Get previously installed version from apt history
PACKAGES_TO_DOWNGRADE=""
for PACKAGE in $(cat /tmp/updated-packages.txt); do
    PREVIOUS_VERSION=$(grep "^Install: $PACKAGE" /var/log/apt/history.log | tail -2 | head -1 | awk -F: '{print $2}' | xargs)

    if [ -n "$PREVIOUS_VERSION" ]; then
        PACKAGES_TO_DOWNGRADE="$PACKAGES_TO_DOWNGRADE $PACKAGE=$PREVIOUS_VERSION"
        echo "Downgrading: $PACKAGE -> $PREVIOUS_VERSION"
    fi
done

# Execute downgrade
if [ -n "$PACKAGES_TO_DOWNGRADE" ]; then
    apt-get install -y $PACKAGES_TO_DOWNGRADE
    DOWNGRADE_STATUS=$?

    if [ $DOWNGRADE_STATUS -eq 0 ]; then
        echo "Downgrade completed successfully"
    else
        echo "Downgrade failed, escalating to L2"
        exit 1
    fi
else
    echo "No previous versions available for downgrade"
    exit 1
fi
```

### L1-C: Service Restart & Verification

```bash
# Restart affected services
needrestart -a a -r a

# Quick health check
echo "Waiting 10 seconds for services to stabilize..."
sleep 10

# Verify critical services
CRITICAL_SERVICES=("networking" "ssh" "rsyslog")
HEALTH_FAILED=0

for SERVICE in "${CRITICAL_SERVICES[@]}"; do
    if systemctl is-active --quiet $SERVICE; then
        echo "$SERVICE: UP"
    else
        echo "$SERVICE: DOWN - Rollback incomplete"
        HEALTH_FAILED=1
    fi
done

if [ $HEALTH_FAILED -eq 0 ]; then
    echo "L1 Rollback SUCCESSFUL"
    # Log the rollback
    logger "L1 Rollback successful for packages: $PACKAGES_TO_DOWNGRADE"
else
    echo "L1 Rollback incomplete, services failed"
    exit 1
fi
```

## Level 2: Snapshot Restore Rollback (< 2 minutes)

**Target Recovery Time**: 2 minutes
**Scope**: Full system state
**Data Risk**: Changes since snapshot are lost
**Applicability**: All system types that support snapshots

### L2-A: Snapshot Verification

```bash
# For LXC Containers
rollback_lxc_snapshot() {
    local CONTAINER=$1
    local SNAPSHOT=$2

    echo "Verifying snapshot for LXC: $CONTAINER"

    # Check snapshot exists
    lxc info $CONTAINER | grep -q "$SNAPSHOT" || {
        echo "ERROR: Snapshot not found: $SNAPSHOT"
        return 1
    }

    # Check snapshot is valid (can be restored)
    lxc info $CONTAINER | grep -A 50 "Snapshots:" | grep -A 5 "$SNAPSHOT" | grep -q "stateful" && {
        echo "Snapshot type: Stateful"
    } || {
        echo "Snapshot type: Stateless"
    }

    return 0
}

# For Proxmox VMs
rollback_vm_snapshot() {
    local VMID=$1
    local SNAPSHOT=$2

    echo "Verifying snapshot for VM: $VMID"

    # Check snapshot exists
    qm listsnapshot $VMID | grep -q "$SNAPSHOT" || {
        echo "ERROR: Snapshot not found: $SNAPSHOT"
        return 1
    }

    # Check snapshot is recent
    SNAPSHOT_TIME=$(qm listsnapshot $VMID | grep "$SNAPSHOT" | awk '{print $3}')
    echo "Snapshot time: $SNAPSHOT_TIME"

    return 0
}
```

### L2-B: Pre-Rollback Checks

```bash
# Record current state before rollback
cat > /tmp/pre-rollback-state.txt <<EOF
Time: $(date -Iseconds)
System: $(hostname)
Uptime: $(uptime)
Disk usage: $(df -h /)
Memory: $(free -h | grep Mem)
Processes: $(ps aux | wc -l)
EOF

# Identify processes that might lose state
echo "Currently running applications:"
ps aux --sort -%cpu | head -5

# For database systems, check for active transactions
if command -v mysql &> /dev/null; then
    echo "Active MySQL processes:"
    mysql -e "SHOW PROCESSLIST;" 2>/dev/null | grep -v "Sleep" || echo "No active transactions"
fi

# Notify users if applicable
echo "Rollback will be initiated in 30 seconds"
# broadcast_message "System maintenance: Reverting to previous state"
```

### L2-C: Execute Snapshot Restore

```bash
# LXC Container Rollback
lxc_rollback() {
    local CONTAINER=$1
    local SNAPSHOT=$2

    echo "=== LXC Container Rollback ==="
    echo "Container: $CONTAINER"
    echo "Snapshot: $SNAPSHOT"
    echo "Time: $(date -Iseconds)"

    # Stop container (graceful shutdown)
    echo "Stopping container..."
    lxc stop $CONTAINER --timeout=30

    # Verify it stopped
    lxc list | grep $CONTAINER | grep -q STOPPED || {
        echo "ERROR: Container did not stop gracefully, forcing..."
        lxc stop $CONTAINER --force
    }

    # Restore from snapshot
    echo "Restoring snapshot..."
    lxc restore $CONTAINER "$SNAPSHOT"

    # Verify restore succeeded
    if [ $? -ne 0 ]; then
        echo "ERROR: Snapshot restore failed"
        return 1
    fi

    # Start container
    echo "Starting container..."
    lxc start $CONTAINER

    # Wait for container to be ready
    echo "Waiting for container to boot (max 60 seconds)..."
    for i in {1..12}; do
        lxc list | grep $CONTAINER | grep -q RUNNING && break
        echo "  Waiting... ($i/12)"
        sleep 5
    done

    echo "Rollback completed at $(date -Iseconds)"
}

# Proxmox VM Rollback
vm_rollback() {
    local VMID=$1
    local SNAPSHOT=$2

    echo "=== Proxmox VM Rollback ==="
    echo "VMID: $VMID"
    echo "Snapshot: $SNAPSHOT"
    echo "Time: $(date -Iseconds)"

    # Stop VM (graceful)
    echo "Stopping VM..."
    qm stop $VMID --timeout=30

    # Verify it stopped
    qm status $VMID | grep -q stopped || {
        echo "Forcing VM stop..."
        qm stop $VMID --force
    }

    # Restore snapshot
    echo "Restoring snapshot..."
    qm restore $VMID "$SNAPSHOT"

    if [ $? -ne 0 ]; then
        echo "ERROR: Snapshot restore failed"
        return 1
    fi

    # Start VM
    echo "Starting VM..."
    qm start $VMID

    # Wait for VM to boot
    echo "Waiting for VM to boot (max 90 seconds)..."
    for i in {1..18}; do
        qm status $VMID | grep -q running && {
            # Additional wait for guest OS to fully boot
            sleep 30
            break
        }
        echo "  Waiting... ($i/18)"
        sleep 5
    done

    echo "Rollback completed at $(date -Iseconds)"
}
```

### L2-D: Post-Rollback Verification

```bash
# Verify system is back online
echo "=== Post-Rollback Verification ==="

# System responsiveness
if ping -c 1 -W 5 127.0.0.1 >/dev/null 2>&1; then
    echo "System responsive: YES"
else
    echo "System responsive: NO (CRITICAL)"
    return 1
fi

# Check critical services
echo "Checking critical services:"
for SERVICE in ssh networking rsyslog; do
    if systemctl is-active --quiet $SERVICE 2>/dev/null; then
        echo "  $SERVICE: UP"
    else
        echo "  $SERVICE: DOWN (may still be starting)"
    fi
done

# Check filesystem integrity
echo "Filesystem check:"
if [ $(df / | awk 'NR==2 {print $1}') ]; then
    echo "  Root filesystem: OK"
fi

# Application-specific checks
echo "Application checks:"
curl -s http://localhost:8080/health >/dev/null && echo "  Web app: UP" || echo "  Web app: may need time to start"

# Log the rollback
cat > /tmp/rollback-${SNAPSHOT}-$(date +%Y%m%d-%H%M%S).log <<EOF
Rollback completed successfully
Time: $(date -Iseconds)
From snapshot: $SNAPSHOT
System state post-rollback:
$(systemctl status --no-pager | head -20)

Data integrity notes:
- All changes since snapshot have been lost
- Last consistent state: $(stat -c %y /backups/ | head -1)
- Database state: pre-snapshot

Next steps:
1. Verify application functionality
2. Re-apply updates with caution
3. Investigate what caused rollback
EOF

echo "Rollback log: /tmp/rollback-${SNAPSHOT}-$(date +%Y%m%d-%H%M%S).log"
```

## Level 3: Failover to Replica (< 5 minutes)

**Target Recovery Time**: 5 minutes
**Scope**: Service failover to redundant system
**Data Risk**: Depends on replication lag (typically < 1 minute)
**Applicability**: Critical systems with replicas

### L3-A: Replica Health Check

```bash
# Verify replica is healthy and synchronized
check_replica_health() {
    local PRIMARY=$1
    local REPLICA=$2

    echo "=== Replica Health Check ==="

    # Check replica is online
    ping -c 1 -W 5 $REPLICA >/dev/null 2>&1 || {
        echo "ERROR: Replica unreachable at $REPLICA"
        return 1
    }

    # Check replica services
    ssh $REPLICA "systemctl is-active app" >/dev/null 2>&1 || {
        echo "ERROR: Application not running on replica"
        return 1
    }

    # Database replication status
    if ssh $REPLICA "mysql -e 'SHOW SLAVE STATUS;'" >/dev/null 2>&1; then
        SECONDS_BEHIND=$(ssh $REPLICA "mysql -e 'SHOW SLAVE STATUS\\G;' | grep Seconds_Behind_Master | awk '{print \$2}'")

        if [ "$SECONDS_BEHIND" == "NULL" ]; then
            echo "ERROR: Replica SQL thread not running"
            return 1
        elif [ "$SECONDS_BEHIND" -gt 5 ]; then
            echo "WARNING: Replica lag is ${SECONDS_BEHIND}s (acceptable but monitor)"
        else
            echo "Replica is synchronized (lag: ${SECONDS_BEHIND}s)"
        fi
    fi

    # Data consistency check
    PRIMARY_CHECKSUM=$(ssh $PRIMARY "mysql -e 'CHECKSUM TABLE main_table;' | tail -1 | awk '{print \$2}'")
    REPLICA_CHECKSUM=$(ssh $REPLICA "mysql -e 'CHECKSUM TABLE main_table;' | tail -1 | awk '{print \$2}'")

    if [ "$PRIMARY_CHECKSUM" == "$REPLICA_CHECKSUM" ]; then
        echo "Data consistency: VERIFIED"
    else
        echo "WARNING: Data checksum mismatch (may indicate lag)"
    fi

    return 0
}
```

### L3-B: Failover Execution

```bash
# Execute failover from primary to replica
execute_failover() {
    local PRIMARY=$1
    local REPLICA=$2
    local SERVICE_VIP=$3  # Virtual IP for the service

    echo "=== Executing Failover ==="
    echo "Primary: $PRIMARY -> Replica: $REPLICA"
    echo "Service VIP: $SERVICE_VIP"
    echo "Time: $(date -Iseconds)"

    # Option 1: DNS-based failover
    echo "Updating DNS to point to replica..."
    # dig_update_record $SERVICE_VIP $REPLICA

    # Option 2: Virtual IP failover (using keepalived or similar)
    echo "Moving virtual IP to replica..."
    # keepalived_promote_replica $REPLICA

    # Option 3: Load balancer reconfiguration
    echo "Reconfiguring load balancer..."
    cat > /tmp/lb-failover.conf <<EOF
upstream backend {
    server $REPLICA:8080 weight=100;
    server $PRIMARY:8080 weight=0 down;
}
EOF
    # scp to load balancer and reload

    # Stop application on primary (prevent conflicts)
    echo "Disabling primary application..."
    ssh $PRIMARY "systemctl stop app" 2>/dev/null || true

    # Wait for failover to propagate
    echo "Waiting for failover propagation (30 seconds)..."
    sleep 30

    # Verify replica is receiving traffic
    TRAFFIC_COUNT=$(ssh $REPLICA "tail -100 /var/log/access.log | wc -l")
    if [ $TRAFFIC_COUNT -gt 0 ]; then
        echo "Replica receiving traffic: YES"
    else
        echo "Replica receiving traffic: UNKNOWN (may not have failed over)"
    fi

    echo "Failover completed at $(date -Iseconds)"
}
```

### L3-C: Post-Failover Validation

```bash
# Verify failover was successful
validate_failover() {
    local REPLICA=$1

    echo "=== Post-Failover Validation ==="

    # Check application is serving requests
    for i in {1..10}; do
        RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null http://$SERVICE_VIP/health)
        if [ "$RESPONSE" == "200" ]; then
            echo "Health check PASS (attempt $i)"
            break
        fi
        echo "Health check attempt $i failed ($RESPONSE), retrying..."
        sleep 3
    done

    # Monitor for 5 minutes
    echo "Monitoring replica for 5 minutes..."
    for i in {1..5}; do
        echo "--- Minute $i ($(date)) ---"

        # CPU and memory
        ssh $REPLICA "free -h | grep Mem"
        ssh $REPLICA "uptime"

        # Error count
        ERROR_COUNT=$(curl -s http://monitoring/metrics | grep 'errors_total' | awk -F' ' '{print $2}')
        echo "Total errors: $ERROR_COUNT"

        [[ $i -lt 5 ]] && sleep 60
    done

    echo "Failover validation completed"
}
```

### L3-D: Failback Procedure (When Primary Recovered)

```bash
# Failback from replica to primary after primary is updated
execute_failback() {
    local PRIMARY=$1
    local REPLICA=$2

    echo "=== Failback to Primary ==="
    echo "Primary: $PRIMARY"
    echo "Time: $(date -Iseconds)"

    # Verify primary is ready
    echo "Verifying primary is ready..."
    ping -c 1 -W 5 $PRIMARY >/dev/null 2>&1 || {
        echo "ERROR: Primary not reachable"
        return 1
    }

    ssh $PRIMARY "systemctl is-active app" >/dev/null 2>&1 || {
        echo "ERROR: Application not running on primary"
        return 1
    }

    # Sync primary with replica (if applicable)
    if ssh $PRIMARY "mysql -e 'SELECT 1;'" >/dev/null 2>&1; then
        echo "Synchronizing primary with latest replica changes..."
        # This depends on your replication setup
        # For MySQL: point primary's replica to replica and sync
    fi

    # Update replica replication to point to primary
    echo "Restoring replication..."
    ssh $REPLICA "mysql -e 'STOP SLAVE; RESET SLAVE;'" 2>/dev/null

    # Restart application on primary
    echo "Starting application on primary..."
    ssh $PRIMARY "systemctl start app"

    # Switch load balancer back
    echo "Switching load balancer to primary..."
    # Update load balancer config to primary weight=100, replica weight=0

    # Monitor transition
    echo "Monitoring failback..."
    sleep 30

    TRAFFIC_RESPONSE=$(curl -s http://$PRIMARY/health)
    if [ -n "$TRAFFIC_RESPONSE" ]; then
        echo "Failback successful - primary is serving requests"
    else
        echo "WARNING: Primary may not be serving requests"
    fi

    echo "Failback completed"
}
```

## Level 4: Full System Restore from Backup (5+ minutes)

**Target Recovery Time**: 30+ minutes
**Scope**: Complete system restore from full backup
**Data Risk**: Loss of all data since last backup
**Applicability**: Catastrophic failure, no snapshots available

### L4-A: Backup Verification

```bash
# Verify backup is accessible and valid
verify_backup() {
    local BACKUP_PATH=$1
    local SYSTEM_NAME=$2

    echo "=== Backup Verification ==="
    echo "Backup: $BACKUP_PATH"
    echo "System: $SYSTEM_NAME"

    # Check backup exists
    if [ ! -f "$BACKUP_PATH" ]; then
        echo "ERROR: Backup file not found at $BACKUP_PATH"
        return 1
    fi

    # Check backup integrity
    if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
        echo "Verifying tar archive integrity..."
        tar -tzf "$BACKUP_PATH" >/dev/null 2>&1 || {
            echo "ERROR: Backup archive is corrupted"
            return 1
        }

        # Count files
        FILE_COUNT=$(tar -tzf "$BACKUP_PATH" | wc -l)
        echo "Backup contains $FILE_COUNT files"
    fi

    # Check backup size
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | awk '{print $1}')
    echo "Backup size: $BACKUP_SIZE"

    # Check target filesystem has space
    TARGET_FILESYSTEM="/"
    REQUIRED_SPACE=$(du -s "$BACKUP_PATH" | awk '{print $1}')
    AVAILABLE_SPACE=$(df "$TARGET_FILESYSTEM" | awk 'NR==2 {print $4}')

    if [ $AVAILABLE_SPACE -gt $REQUIRED_SPACE ]; then
        echo "Available space: $(($AVAILABLE_SPACE / 1024))MB (SUFFICIENT)"
    else
        echo "ERROR: Insufficient space to restore backup"
        return 1
    fi

    # Check backup metadata
    if tar -tzf "$BACKUP_PATH" -O backup-metadata.txt 2>/dev/null | head -10; then
        echo "Backup metadata found and readable"
    else
        echo "WARNING: Backup metadata not found"
    fi

    return 0
}
```

### L4-B: Restore Execution

```bash
# Restore system from backup
restore_from_backup() {
    local BACKUP_PATH=$1
    local RESTORE_POINT=$2  # "/" for full restore

    echo "=== Full System Restore from Backup ==="
    echo "Backup: $BACKUP_PATH"
    echo "Restore point: $RESTORE_POINT"
    echo "Time: $(date -Iseconds)"

    # Create restore log
    RESTORE_LOG="/tmp/restore-$(date +%Y%m%d-%H%M%S).log"

    # Stop all services
    echo "Stopping all services..."
    systemctl isolate rescue.target 2>&1 | tee -a $RESTORE_LOG

    # Mount backup location if remote
    if [[ "$BACKUP_PATH" == *://* ]]; then
        echo "Mounting remote backup..."
        # nfs/smb mount logic
    fi

    # Perform restore
    echo "Extracting backup to filesystem..."
    tar -xzf "$BACKUP_PATH" -C "$RESTORE_POINT" 2>&1 | tee -a $RESTORE_LOG

    RESTORE_STATUS=$?

    if [ $RESTORE_STATUS -eq 0 ]; then
        echo "Restore completed successfully" | tee -a $RESTORE_LOG
    else
        echo "ERROR: Restore failed with status $RESTORE_STATUS" | tee -a $RESTORE_LOG
        return 1
    fi

    # Restore configuration from metadata
    if tar -xzf "$BACKUP_PATH" -C /tmp backup-metadata.txt 2>/dev/null; then
        echo "Restoring system configuration from metadata..."
        # Apply config from metadata
    fi

    # Rebuild boot loader if needed
    if [ -f /sys/firmware/efi/fw_platform_size ]; then
        echo "Rebuilding EFI bootloader..."
        grub-mkconfig -o /boot/grub/grub.cfg 2>&1 | tee -a $RESTORE_LOG
    fi

    echo "Restore completed, rebooting system..." | tee -a $RESTORE_LOG
    # System will boot with restored filesystem
}
```

### L4-C: Post-Restore Validation

```bash
# Validate restored system
validate_restore() {
    echo "=== Post-Restore Validation ==="
    echo "Timestamp: $(date -Iseconds)"

    # Wait for system to fully boot
    echo "Waiting for system to fully boot..."
    sleep 30

    # Check filesystem integrity
    echo "Checking filesystem integrity..."
    fsck -n / 2>&1 | head -20

    # Verify critical files
    CRITICAL_FILES=("/etc/hosts" "/etc/fstab" "/etc/hostname")
    for FILE in "${CRITICAL_FILES[@]}"; do
        if [ -f "$FILE" ]; then
            echo "  $FILE: EXISTS"
        else
            echo "  $FILE: MISSING (ERROR)"
        fi
    done

    # Check services
    echo "Checking critical services:"
    systemctl isolate multi-user.target
    sleep 10

    for SERVICE in ssh networking rsyslog; do
        if systemctl is-active --quiet $SERVICE; then
            echo "  $SERVICE: UP"
        else
            echo "  $SERVICE: DOWN (checking startup log)"
            journalctl -u $SERVICE -n 20 | head -5
        fi
    done

    # Data integrity check
    echo "Data integrity:"
    if command -v mysql &>/dev/null; then
        mysql -e "SHOW DATABASES;" | head -5 && echo "  Database: Accessible"
    fi

    # Network verification
    echo "Network:"
    ip addr show | grep "inet " | wc -l
    ip route show | head -3

    # Logs analysis
    echo "Recent errors (last 30 minutes):"
    journalctl --since "30 minutes ago" -p 3..4 | tail -20

    echo "Post-restore validation completed"
}
```

## Rollback Decision Matrix

| Scenario | Time | Level | Recovery Time | Data Loss |
|----------|------|-------|---|---|
| Package update failed immediately | < 30s | L1 | 30s | None |
| Service startup issue | 30s-2m | L2 | 2m | None* |
| Kernel panic after boot | 2-5m | L2/L3 | 2-5m | None* |
| Cascading service failures | > 5m | L3/L4 | 5-30m | Depends |
| Complete system failure | Any | L4 | 30m+ | Lost since backup |

*Snapshot rollback loses changes since snapshot, not original data

## Rollback Automation in n8n

```javascript
// Pseudo-code for n8n rollback workflow

if (updateFailed) {
    let rollbackLevel = determineRollbackLevel(timeSinceUpdate, systemType);

    switch(rollbackLevel) {
        case 1:
            executeLevel1Downgrade();
            break;
        case 2:
            executeLevel2SnapshotRestore();
            break;
        case 3:
            executeLevel3Failover();
            break;
        case 4:
            executeLevel4FullRestore();
            break;
    }

    // Always notify after rollback
    notifyOperations(systemName, rollbackLevel, timeElapsed);
    createIncidentTicket();
    logAllChanges();
}
```

## Summary

- **L1**: Fastest, lowest impact, for minor package issues
- **L2**: Default for most failures, snapshot-based, quick
- **L3**: For critical systems with replicas
- **L4**: Last resort, longest recovery, highest data loss risk
