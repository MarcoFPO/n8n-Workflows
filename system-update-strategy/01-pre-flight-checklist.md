# Pre-Flight Safety Checklist for System Updates

## Overview
This checklist must be completed and passed before ANY update is initiated. Failed checks require investigation and resolution before proceeding.

## Section 1: System Health Verification

### 1.1 Disk Space Check
**Requirement**: Minimum 20% free space on root partition, 30% on /var
**Rationale**: Updates require temporary space; insufficient space causes package corruption

```bash
# Check root partition
ROOT_FREE=$(df / | awk 'NR==2 {printf "%.0f", $4/($2)*100}')
VAR_FREE=$(df /var | awk 'NR==2 {printf "%.0f", $4/($2)*100}')

PASS_ROOT=$([[ $ROOT_FREE -ge 20 ]] && echo "PASS" || echo "FAIL")
PASS_VAR=$([[ $VAR_FREE -ge 30 ]] && echo "PASS" || echo "FAIL")
```

**Pass Criteria**:
- Root filesystem: >= 20% free (FAIL if < 15%)
- /var filesystem: >= 30% free (FAIL if < 20%)
- /tmp filesystem: >= 500MB free

**Failure Action**:
- Delete old logs, package caches, temporary files
- If still failing, ABORT and escalate to storage team
- Document free space before/after remediation

### 1.2 Memory & CPU Load Check
**Requirement**: Load average < 0.7x CPU cores, Available memory > 512MB

```bash
# Get system metrics
LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
CPU_CORES=$(nproc)
LOAD_THRESHOLD=$(echo "$CPU_CORES * 0.7" | bc)
MEM_AVAILABLE=$(free -m | awk '/^Mem:/ {print $7}')

PASS_LOAD=$([[ $(echo "$LOAD < $LOAD_THRESHOLD" | bc) -eq 1 ]] && echo "PASS" || echo "FAIL")
PASS_MEM=$([[ $MEM_AVAILABLE -gt 512 ]] && echo "PASS" || echo "FAIL")
```

**Pass Criteria**:
- Load average: < 0.7x CPU cores (systems at high load risk timeout)
- Available memory: >= 512MB (required for package unpacking)
- No memory pressure from swapping

**Failure Action**:
- Wait 15 minutes and retry (allow workload to settle)
- If persistent, investigate running processes: `ps aux --sort -%mem`
- Consider rescheduling update to low-traffic window

### 1.3 Network Connectivity Check
**Requirement**: All critical network interfaces UP, gateway reachable

```bash
# Network checks
for IFACE in eth0 eth1; do
    STATE=$(ip link show $IFACE | grep -o 'UP\|DOWN' | head -1)
    [[ "$STATE" == "UP" ]] || echo "FAIL: $IFACE is DOWN"
done

# Gateway reachability
GATEWAY=$(ip route | grep default | awk '{print $3}')
ping -c 1 -W 2 $GATEWAY >/dev/null 2>&1 || echo "FAIL: Gateway unreachable"
```

**Pass Criteria**:
- All configured network interfaces: UP
- Default gateway: Reachable (ping successful)
- DNS resolution: Working (nslookup google.com succeeds)
- Package repository: Accessible (curl -I http://deb.debian.org succeeds)

**Failure Action**:
- If interface down: Investigate with network team
- If gateway unreachable: Check routing table and ARP
- Abort update if network unreliable

## Section 2: Maintenance Window & Operational Checks

### 2.1 Active Maintenance Window Verification
**Requirement**: Update must fall within approved maintenance window

```bash
# Check against maintenance schedule (from Zabbix or local config)
CURRENT_HOUR=$(date +%H)
CURRENT_DAY=$(date +%A)

# Example: Tuesday 2-4 AM, Thursday 2-4 AM
ALLOWED_WINDOWS="Tuesday-02 Tuesday-03 Thursday-02 Thursday-03"

IS_VALID_WINDOW=0
for WINDOW in $ALLOWED_WINDOWS; do
    [[ "$CURRENT_DAY-$(printf '%02d' $CURRENT_HOUR)" == "$WINDOW" ]] && IS_VALID_WINDOW=1
done
```

**Pass Criteria**:
- Update time falls within approved maintenance window
- No business-critical operations scheduled
- On-call engineer available for rollback

**Failure Action**:
- Reschedule update to next valid maintenance window
- Escalate if update is critical (security fixes)

### 2.2 Backup Verification Status
**Requirement**: Recent backup exists within 24 hours, is accessible and verified

```bash
# Check backup age
BACKUP_DIR="/backups/system-backups"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
BACKUP_AGE=$(($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")))

PASS_BACKUP=$([[ $BACKUP_AGE -lt 86400 ]] && echo "PASS" || echo "FAIL")
```

**Pass Criteria**:
- Full system backup: Exists and < 24 hours old
- Backup integrity: Verified (tar -tzf succeeds)
- Backup location: Accessible and has sufficient space
- Backup restorable: Can restore at least 5 test files

**Failure Action**:
- Trigger immediate backup before proceeding
- Verify backup integrity with restore test
- Abort update if backup cannot be verified

### 2.3 Critical Service Status Check
**Requirement**: All critical services running normally, no pending restarts

```bash
# Check systemd critical services
CRITICAL_SERVICES=("networking" "ssh" "rsyslog" "crond")

for SERVICE in "${CRITICAL_SERVICES[@]}"; do
    systemctl is-active --quiet $SERVICE || echo "FAIL: $SERVICE not active"
    systemctl is-enabled --quiet $SERVICE || echo "WARN: $SERVICE not enabled"
done

# Check for pending kernel/library restarts
needs-restarting -k >/dev/null 2>&1 && echo "WARN: Kernel restart pending"
```

**Pass Criteria**:
- All critical services (SSH, syslog, networking): Running
- Services enabled: Auto-restart on reboot configured
- Pending restarts: None should exist (this is baseline)
- No zombie/defunct processes

**Failure Action**:
- Restart failed services immediately
- Investigate why service stopped
- If cannot restart, escalate and abort update

### 2.4 Active Connection Check (Production Systems)
**Requirement**: No active critical connections or batch jobs in progress

```bash
# SSH active sessions
ACTIVE_SSH=$(netstat -tn | grep :22 | grep ESTABLISHED | wc -l)

# Database connections
ACTIVE_DB=$(netstat -tn | grep -E :(3306|5432) | grep ESTABLISHED | wc -l)

# Batch job processes
BATCH_JOBS=$(pgrep -f "batch|scheduled|cron" | wc -l)
```

**Pass Criteria**:
- SSH sessions: <= 2 (maintenance personnel)
- Database connections: < 5 (no heavy workload)
- No active batch jobs or long-running queries
- Application request queue: Empty or draining

**Failure Action**:
- Notify active users of pending maintenance
- Wait for connections to close (max 5 minutes)
- If critical job in progress, reschedule update
- For containers: Drain connections before update

## Section 3: Update-Specific Checks

### 3.1 Kernel & GRUB Configuration
**Requirement**: GRUB configured correctly, multiple boot options available

```bash
# Check GRUB menu entries
GRUB_ENTRIES=$(grep -c "^menuentry" /boot/grub/grub.cfg)
echo "Available GRUB entries: $GRUB_ENTRIES"
[[ $GRUB_ENTRIES -ge 2 ]] && echo "PASS: Multiple boot options available" || echo "FAIL"

# Verify current kernel
CURRENT_KERNEL=$(uname -r)
echo "Current kernel: $CURRENT_KERNEL"

# Check for EFI vs BIOS
[[ -d /sys/firmware/efi ]] && echo "Boot mode: EFI" || echo "Boot mode: BIOS"
```

**Pass Criteria**:
- Multiple kernel versions in GRUB (for fallback)
- GRUB configuration: Valid and parseable
- Boot partition: Has sufficient space for new kernel
- Bootloader: Functional (can boot current system)

**Failure Action**:
- Update GRUB if missing fallback: `grub-mkconfig -o /boot/grub/grub.cfg`
- Verify GRUB update succeeded
- Test boot with new configuration (reboot validation)

### 3.2 Package Dependency Check
**Requirement**: No broken dependencies, package cache is clean

```bash
# Check for broken packages
apt-get check 2>&1 | grep -i "broken\|unmet" && echo "FAIL: Broken dependencies" || echo "PASS"

# Simulate update to detect conflicts
apt-get install -s dist-upgrade 2>&1 | tee /tmp/apt-simulation.log

# Check for held/pinned packages
apt-mark showhold
```

**Pass Criteria**:
- No broken dependencies detected
- apt-get check: Successful
- Simulated upgrade: No conflicts or removals of critical packages
- Pinned packages: Reviewed and approved for update

**Failure Action**:
- `apt-get clean && apt-get update` to refresh cache
- Investigate broken packages: `apt --fix-broken install`
- Hold critical packages if needed: `apt-mark hold package-name`

### 3.3 Rollback Snapshot Preparation
**Requirement**: Snapshots created and verified before update

**For LXC Containers**:
```bash
# Create LXC snapshot
SNAPSHOT_NAME="before-update-$(date +%s)"
lxc snapshot CONTAINER_NAME "$SNAPSHOT_NAME"

# Verify snapshot exists and is valid
lxc info CONTAINER_NAME | grep -A 5 "Snapshots:"
```

**For Proxmox VMs**:
```bash
# Create VM snapshot
VMID=$(qm list | grep "VM_NAME" | awk '{print $1}')
qm snapshot $VMID "before-update-$(date +%s)"

# Verify snapshot created
qm listsnapshot $VMID
```

**Pass Criteria**:
- Snapshot creation: Successful
- Snapshot verification: Can list and describe
- Snapshot location: Has sufficient space (>= 5% of system size)
- Parent system intact: Functional after snapshot

**Failure Action**:
- Extend storage if insufficient space
- Retry snapshot creation
- If snapshots unsupported (physical), use backup as fallback

## Section 4: System-Type Specific Checks

### 4.1 LXC Container Pre-Checks
```bash
# Container health
lxc exec CONTAINER_NAME -- systemctl status

# Container disk usage
lxc exec CONTAINER_NAME -- df -h /

# Container network
lxc exec CONTAINER_NAME -- ip route show default
lxc exec CONTAINER_NAME -- getent hosts example.com
```

### 4.2 Proxmox VM Pre-Checks
```bash
# VM status
qm status VMID

# VM disk usage
qm guest exec $VMID -- df -h /

# VM QEMU agent
qm agent $VMID ping

# Replication status (if applicable)
qm replication status $VMID
```

### 4.3 Physical Server Pre-Checks
```bash
# Hardware health
# LSI MegaRAID controller
megacli -LDInfo -Lall -aALL | grep "State"

# Check IPMI if available
ipmitool sel list | tail -5

# Check hardware sensors
sensors | grep -i "critical\|alarm"
```

## Complete Pre-Flight Checklist Template

```yaml
Checklist ID: PFC-$(date +%Y%m%d-%H%M%S)
System Hostname: [HOSTNAME]
System Type: [LXC/VM/Physical]
Executor: [NAME]
Timestamp: $(date -Iseconds)

SECTION 1: SYSTEM HEALTH
- [ ] Disk space check: PASS (Root: __%, /var: _%)
- [ ] Memory & load check: PASS (Load: __, Mem: __MB)
- [ ] Network connectivity: PASS
- [ ] Critical services: PASS
- [ ] Active connections: PASS

SECTION 2: OPERATIONAL
- [ ] Maintenance window: PASS (Window: __)
- [ ] Backup verified: PASS (Age: __ hours)
- [ ] On-call engineer: AVAILABLE
- [ ] Rollback plan: CONFIRMED

SECTION 3: UPDATE-SPECIFIC
- [ ] Package dependencies: PASS
- [ ] GRUB/bootloader: PASS
- [ ] Snapshot created: PASS (ID: __)
- [ ] Storage verified: PASS

SECTION 4: CRITICAL SERVICE VALIDATION
- [ ] SSH: RUNNING
- [ ] Networking: RUNNING
- [ ] Logging: RUNNING
- [ ] DNS: FUNCTIONAL

FINAL DECISION
- [ ] All checks PASSED
- [ ] Approved to proceed: [YES/NO]
- [ ] Next action: [PROCEED/RESCHEDULE/ABORT]
- [ ] Sign-off: _________________ (Name & Time)

NOTES:
[Add any issues discovered, workarounds, or special conditions]
```

## Summary

**Total checks**: 25+
**Critical failures**: Disk space, network, backup, critical services, dependencies
**Warning conditions**: Load, kernel restart pending, held packages
**Snapshot requirement**: MANDATORY before any update proceeds
**Manual verification**: Required for production systems, physical hardware

All checks must pass before update automation is triggered.
