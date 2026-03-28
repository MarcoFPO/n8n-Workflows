# Failure Scenarios & Recovery Procedures

## Scenario 1: Package Dependency Conflicts

### Symptoms
- apt-get dist-upgrade reports "broken dependencies"
- Unable to resolve package versions
- Error: "E: Unable to correct problems, you have held broken packages"

### Root Cause Analysis
```bash
# Identify held packages
apt-mark showhold

# Check for conflicting pinned versions
grep -r "Pin" /etc/apt/preferences* 2>/dev/null

# Review which packages are incompatible
apt-cache policy conflicting-package

# Check dependency tree
apt-cache depends package-name
```

### Recovery Procedure

**Step 1: Analyze the Conflict**
```bash
# Get detailed error output
apt-get install -s dist-upgrade > /tmp/apt-error.log 2>&1

# Identify the problematic package
grep -i "error\|conflict\|broken" /tmp/apt-error.log

# Show which packages are causing issues
apt-get install -s package-name 2>&1 | grep -A 10 "Broken"
```

**Step 2: Resolve Conflicts**
```bash
# Option A: Hold problematic package and update rest
PROBLEM_PACKAGE="conflicting-package"
apt-mark hold $PROBLEM_PACKAGE
apt-get install -s dist-upgrade  # Re-simulate to see if resolved

# Option B: Downgrade holding packages to compatible versions
apt-get install package-name/focal  # Specify version from repo

# Option C: Update package sources if old/incompatible
# Edit /etc/apt/sources.list to point to correct repositories
apt-get update
apt-cache policy package-name
```

**Step 3: Attempt Update Again**
```bash
# Clear any existing partial installations
apt-get clean
apt-get autoclean

# Run update with enhanced logging
apt-get -y dist-upgrade 2>&1 | tee /tmp/apt-update-retry.log

# Check result
if [ $? -eq 0 ]; then
    echo "Update successful after conflict resolution"
else
    echo "Still failing - escalate to rollback"
    exit 1
fi
```

**Step 4: If Unresolved - Rollback**
```bash
# Restore from snapshot if dependency issue cannot be resolved
SNAPSHOT_ID=$(qm listsnapshot VMID | grep "before-update" | awk '{print $1}')

echo "Dependency conflict unresolved, restoring snapshot: $SNAPSHOT_ID"
qm stop VMID --timeout=30
qm restore VMID "$SNAPSHOT_ID"
qm start VMID

# After restore, document the issue
cat > /tmp/dependency-conflict-$(date +%Y%m%d).txt <<EOF
System: $(hostname)
Conflict packages: [list]
Repositories configured: [list repositories]
Recommended action: Review package sources and held versions before retry
EOF
```

### Prevention for Next Update
```bash
# Pre-update checks to catch conflicts early
apt-get install -s dist-upgrade > /tmp/apt-pre-check.log 2>&1

# Review for conflicts before update begins
if grep -q "broken\|Broken" /tmp/apt-pre-check.log; then
    echo "ERROR: Pre-check detected conflicts, aborting update"
    grep "Broken" /tmp/apt-pre-check.log
    exit 1
fi
```

## Scenario 2: Kernel Panic After Reboot

### Symptoms
- System does not come back online after reboot
- QEMU console shows kernel panic message
- Reboot hangs at boot loader
- Continuous reboot loop

### Root Cause Analysis
```bash
# Via Proxmox console/serial
# During boot, you should see kernel panic output
# Common causes:
# - Hardware driver incompatibility
# - Device tree changes (for ARM-based systems)
# - Incompatible initramfs
# - Corrupted boot parameters
```

### Recovery Procedure

**Step 1: Access Boot Menu**
```bash
# During system boot, access GRUB menu
# Press ESC or SHIFT during boot countdown

# In GRUB menu:
# 1. Select previous kernel version
# 2. Boot with that kernel
# 3. If successful, previous kernel is stable
```

**Step 2: If Kernel Boot Fails**
```bash
# Edit GRUB boot parameters to disable problematic features
# In GRUB menu, press 'e' to edit
# Add boot parameters like:
# - noapic (disable APIC)
# - nomodeset (disable GPU drivers)
# - mem=512M (limit memory if issue is memory-related)

# Press Ctrl+X to boot with modified parameters

# If system comes up, kernel was compatible but parameters were issue
```

**Step 3: From Snapshots**
```bash
# If cannot boot even with fallback kernel, restore snapshot

# Via Proxmox:
qm stop VMID --force
qm restore VMID "before-update-timestamp"
qm start VMID

# Verify system boots
qm guest cmd-status VMID  # Check if guest tools respond
```

**Step 4: Investigate Root Cause**
```bash
# Once system is back up, investigate
ssh user@system "apt-cache policy linux-image"

# Check initramfs was built correctly
ssh user@system "ls -la /boot/initrd*"

# Rebuild initramfs if corrupted
ssh user@system "sudo update-initramfs -u -k all"

# Test reboot with verbose output
ssh user@system "sudo shutdown -r +1"

# Monitor reboot via console
qm terminal VMID

# If boots successfully, issue was initramfs corruption
# If still panics, kernel is incompatible - don't update that package yet
```

### Prevention
```bash
# Before rebooting, verify boot configuration
ssh user@system "sudo grub-mkconfig -o /boot/grub/grub.cfg"

# Verify GRUB has multiple boot options
ssh user@system "sudo grep '^menuentry' /boot/grub/grub.cfg | wc -l"

# If < 2 options, rebuild:
ssh user@system "sudo grub-mkconfig -o /boot/grub/grub.cfg"

# Only then proceed with reboot
```

## Scenario 3: Service Fails to Start Post-Update

### Symptoms
- systemctl status shows "inactive (failed)"
- Application not responding on expected port
- Error logs show startup errors
- Service restarts in loop

### Root Cause Analysis
```bash
# Check service status
systemctl status service-name

# View recent logs
journalctl -u service-name -n 50 --no-pager

# Check service startup command
systemctl cat service-name | grep ExecStart

# Test manual startup
/usr/bin/service-executable start  # Run actual command

# Check for missing dependencies
ldd /usr/bin/service-executable | grep "not found"

# Check configuration file syntax
service-binary --test-config  # Most apps support this
```

### Recovery Procedure

**Step 1: Identify the Actual Error**
```bash
# Get full startup output
systemctl start service-name
sleep 2
journalctl -u service-name -n 100 -p 3..4

# Common causes:
# - Missing library after update: "error while loading shared libraries"
# - Config file incompatibility: "invalid config file"
# - Missing prerequisite service: "failed to get required service"
```

**Step 2: Common Fixes**

**For Missing Library Issue:**
```bash
# Identify missing library
MISSING=$(journalctl -u service-name | grep -o "libc.*.so[^ ]*" | head -1)

# Find which package provides it
apt-file search $MISSING | grep "\.so"

# Install missing library
apt-get install library-package

# Restart service
systemctl restart service-name
```

**For Config Incompatibility:**
```bash
# View old vs new config
diff /etc/service/config.conf.dpkg-old /etc/service/config.conf

# Merge configs manually or use old version
cp /etc/service/config.conf.dpkg-old /etc/service/config.conf
systemctl restart service-name

# Verify service starts
systemctl is-active service-name
```

**For Missing Service Dependency:**
```bash
# Check what the service requires
systemctl cat service-name | grep "^Requires\|^After"

# Enable and start required service
systemctl enable required-service
systemctl start required-service

# Start original service
systemctl restart service-name
```

**Step 3: If Manual Fix Fails**
```bash
# Downgrade service package to previous version
OLD_VERSION=$(apt-cache policy service-package | grep "Candidate" | awk '{print $2}')
apt-get install service-package=$(apt-cache show service-package | grep "Version:" | awk '{print $2}' | head -2 | tail -1)

# Or rollback via snapshot
systemctl stop service-name
# [restore from snapshot]
systemctl start service-name
```

## Scenario 4: Network Connectivity Loss

### Symptoms
- Cannot ping gateway
- SSH disconnects mid-update
- DNS not resolving
- Network interface down

### Root Cause Analysis
```bash
# Check network interfaces
ip link show

# Check IP configuration
ip addr show

# Check routing table
ip route show

# Check DNS configuration
cat /etc/resolv.conf
systemctl status systemd-resolved

# Check for network-related error messages
journalctl -n 100 | grep -i "network\|eth0\|wlan0"
```

### Recovery Procedure

**Step 1: Verify Physical Connection**
```bash
# Check interface is up
ip link show eth0

# If DOWN, bring up:
ip link set eth0 up

# Check for IP configuration
ip addr show eth0 | grep "inet "

# If no IP, try DHCP
dhclient eth0

# Or configure static IP if known
ip addr add 192.168.1.50/24 dev eth0
ip route add default via 192.168.1.1
```

**Step 2: Network Restart**
```bash
# Restart networking
systemctl restart networking

# Or for newer systems
systemctl restart systemd-networkd

# Wait for interfaces to come up
sleep 5

# Verify connectivity
ping -c 1 8.8.8.8
```

**Step 3: DNS Restoration**
```bash
# Check DNS is configured
cat /etc/resolv.conf

# Set nameserver if missing
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Restart DNS resolver
systemctl restart systemd-resolved

# Test DNS
nslookup google.com
```

**Step 4: If Network Still Down**
```bash
# Check if network driver was removed in update
lsmod | grep -i "e1000\|virtio\|driver"

# If missing, check if package update removed driver
dpkg -l | grep -i "network\|driver"

# Reinstall network drivers if needed
apt-get install linux-headers-$(uname -r) build-essential
# Rebuild driver if necessary

# Or rollback to previous kernel
```

### Prevention
```bash
# Pre-update: Ensure network services can survive
systemctl is-enabled networking
systemctl is-enabled systemd-resolved

# Configure static routes as backup
ip route show

# Document gateway MAC address in case needed
ip neigh show | grep gateway
```

## Scenario 5: Disk Space Exhaustion During Update

### Symptoms
- "E: Insufficient free space" during update
- /var disk full
- Update process hangs
- Package partially installed

### Root Cause Analysis
```bash
# Check available space
df -h /
df -h /var
df -h /tmp

# Find what's consuming space
du -sh /var/cache/*
du -sh /var/log/*
du -sh /home/*

# Check for orphaned files
find /tmp -type f -mtime +7  # Files older than 7 days
```

### Recovery Procedure

**Step 1: Clean Package Cache**
```bash
# Remove old package cache
apt-get clean

# This usually frees 500MB-2GB
df -h / | awk 'NR==2 {printf "Freed %.0fGB\n", ($4-$3)/1024}'

# More aggressive cleanup
apt-get autoclean
apt-get autoremove
```

**Step 2: Clean Logs**
```bash
# Find large log files
find /var/log -type f -size +100M

# Clear old logs (keep recent)
journalctl --vacuum=100M

# Or delete old logs manually
rm /var/log/syslog.* /var/log/auth.log.*
```

**Step 3: Clean Temporary Files**
```bash
# Remove old temp files
find /tmp -type f -atime +7 -delete

# Clear package manager temp directory
rm -rf /var/lib/apt/lists/partial/*
```

**Step 4: Check if Sufficient Space Now**
```bash
# Verify we have 20% free
ROOT_FREE=$(df / | awk 'NR==2 {printf "%.0f", $4/($2)*100}')
[[ $ROOT_FREE -ge 20 ]] && echo "OK to proceed" || echo "Still insufficient"

# If still insufficient, consider removing old kernels
dpkg -l | grep "linux-image" | grep -v "$(uname -r)"
apt-get remove linux-image-old-version

# Or clean up non-essential applications
apt-get remove package-name
```

**Step 5: Resume Update**
```bash
# Clean any partial installations
apt-get clean
apt-get autoclean

# Retry update
apt-get update
apt-get -y dist-upgrade

# Monitor for same error
if [ $? -ne 0 ]; then
    echo "Update failed, likely still space issue"
    exit 1
fi
```

## Scenario 6: Memory Pressure / OOMKill Events

### Symptoms
- "out of memory" in kernel logs
- Services being killed unexpectedly
- System becomes unresponsive
- Swap usage very high

### Root Cause Analysis
```bash
# Check memory usage
free -h
cat /proc/meminfo | head -20

# Check swap
swapon --show
free -h | grep Swap

# Identify memory-consuming processes
ps aux --sort -%mem | head -10

# Check for memory leaks (process memory growing)
watch -n 1 'ps aux --sort -%mem | head -5'

# Check kernel OOM events
journalctl | grep -i "oom\|killed"
```

### Recovery Procedure

**Step 1: Immediate Relief**
```bash
# Identify and stop unnecessary services
systemctl list-units --state=running | grep -i "app\|worker"

# Stop non-critical services
systemctl stop non-critical-service

# Flush page cache (safe on Linux, will be repopulated)
sync
echo 3 > /proc/sys/vm/drop_caches

# Monitor result
free -h
```

**Step 2: Address Root Cause**
```bash
# If update created large temporary files
du -sh /var/cache/* /tmp/*

# Clean caches
rm -rf /var/cache/apt/archives/*.deb
apt-get clean

# If process has memory leak, restart it
systemctl restart leaky-service

# Monitor its memory usage
watch -n 5 'ps aux | grep leaky-service'
```

**Step 3: Increase Swap (Temporary)**
```bash
# Create swap file
dd if=/dev/zero of=/swapfile bs=1M count=1024  # 1GB swap
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Verify
swapon --show
free -h

# Make permanent if needed
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

**Step 4: If Still OOMing**
```bash
# Reduce background jobs
systemctl stop backup-service
systemctl stop worker-service

# Limit memory for specific service
# Edit service unit file:
# [Service]
# MemoryLimit=1G

systemctl daemon-reload
systemctl restart service-name

# If system still unstable, rollback
```

## Scenario 7: Replication Lag / Data Sync Issues

### Symptoms (For Replicated Systems)
- Replication lag increasing
- Slave SQL thread stopped
- Error: "Could not parse replication event"
- Master-slave binary log mismatch

### Root Cause Analysis
```bash
# Check replication status
mysql -e "SHOW SLAVE STATUS\G;"

# Key fields:
# - Seconds_Behind_Master (lag in seconds)
# - Slave_IO_Running (should be Yes)
# - Slave_SQL_Running (should be Yes)
# - Last_Error (shows replication errors)

# Check master-slave sync
mysql -e "SHOW MASTER STATUS\G;" # on master
mysql -e "SHOW SLAVE STATUS\G;"  # on replica

# Compare binlog positions
```

### Recovery Procedure

**Step 1: If Replication Just Started Lagging**
```bash
# Check network latency
ping -c 5 master-ip

# Check master binary log space
mysql -e "SHOW BINARY LOGS;" | head -20

# If master has too many binary logs, cleanup old ones
mysql -e "PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 3 DAY);"
```

**Step 2: If Replication Thread Stopped**
```bash
# Get the error
mysql -e "SHOW SLAVE STATUS\G;" | grep "Last_Error"

# Common errors and fixes:

# Error: Duplicate key error
# Fix: Skip the failing statement
mysql -e "SET GLOBAL SQL_SLAVE_SKIP_COUNTER = 1; START SLAVE;"

# Error: Cannot find master binlog
# Fix: Reset from new backup or point to correct binlog
mysql -e "CHANGE MASTER TO MASTER_LOG_FILE='mysql-bin.000050', MASTER_LOG_POS=4;"

# Error: Network error
# Fix: Restart replication
mysql -e "STOP SLAVE; START SLAVE;"
```

**Step 3: Resync If Severely Out of Sync**
```bash
# Option A: Use mysqldump (if lag acceptable)
mysqldump -h master --all-databases | mysql

# Then resync position
# Get position from master
POSITION=$(mysql -h master -e "SHOW MASTER STATUS\G;" | grep "Position:" | awk '{print $2}')
FILE=$(mysql -h master -e "SHOW MASTER STATUS\G;" | grep "File:" | awk '{print $2}')

# Set on replica
mysql -e "CHANGE MASTER TO MASTER_LOG_FILE='$FILE', MASTER_LOG_POS=$POSITION; START SLAVE;"

# Option B: Restore from backup
# Restore latest backup to replica
# Then continue from that point
```

**Step 4: Monitor Recovery**
```bash
# Watch replication status
while true; do
    mysql -e "SHOW SLAVE STATUS\G;" | grep "Seconds_Behind_Master"
    sleep 10
done

# Once Seconds_Behind_Master is < 5, replication is caught up
```

## Common Recovery Commands Reference

```bash
# Database recovery
mysql -e "RESET SLAVE;"
mysql -e "CHANGE MASTER TO ..."
mysql -e "START SLAVE;"
mysql -e "SHOW SLAVE STATUS\G;"

# Filesystem recovery
fsck -n /dev/vda1  # Check without fixing
fsck -y /dev/vda1  # Fix issues

# Package manager recovery
apt-get clean
apt-get autoclean
apt-get install -f  # Fix broken packages
apt-get -o DPkg::Pre-Install-Pkgs::=/dev/null install package  # Force install

# Network recovery
systemctl restart networking
systemctl restart systemd-networkd
systemctl restart systemd-resolved
dhclient eth0

# Service recovery
systemctl restart service-name
systemctl reset-failed service-name
journalctl -u service-name -p 0..3  # View errors

# Snapshot recovery (LXC)
lxc stop container-name
lxc restore container-name "snapshot-name"
lxc start container-name

# Snapshot recovery (VM)
qm stop VMID
qm restore VMID "snapshot-name"
qm start VMID
```

## Summary

- Early detection through comprehensive health checks prevents escalation
- Most failures have well-known recovery procedures
- Immediate remediation within 2 minutes avoids cascade failures
- Rollback is always an option if recovery takes too long
- Root cause analysis after each incident prevents recurrence
- Documentation of failures improves incident response
