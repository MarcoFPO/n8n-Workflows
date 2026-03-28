# Quick Reference Guide for System Updates

## Fastest Path to Production Update

### 1. Classify Your System (2 minutes)

**Quick test**: Answer these 3 questions:

```
1. If this system goes down, how long can the business tolerate downtime?
   ├─ < 1 minute       → TIER 1 (Critical)
   ├─ < 5 minutes      → TIER 2 (Important)
   ├─ < 30 minutes     → TIER 3 (Standard)
   └─ > 30 minutes/OK  → TIER 4 (Non-critical)

2. What type of system?
   ├─ LXC Container
   ├─ Proxmox VM
   └─ Physical Server

3. Can this system failover/replicate?
   ├─ Yes → Blue-Green update possible
   └─ No → Snapshot update required
```

### 2. Run Pre-Flight Checks (5 minutes)

```bash
# Option A: Run full automated checks
bash /opt/update-scripts/08-shell-scripts.sh pre-flight physical

# Option B: Manual quick check
df -h /                    # Check disk space (need 20% free)
free -m                    # Check memory (need 512MB)
uptime                     # Check load
ping -c 1 8.8.8.8         # Check network
systemctl status ssh       # Check critical services
```

**MUST PASS all checks before proceeding**

### 3. Create Snapshot (2 minutes)

**For LXC Container:**
```bash
lxc snapshot my-container "before-update-$(date +%s)"
lxc info my-container | grep Snapshots
```

**For Proxmox VM:**
```bash
qm snapshot 100 "before-update-$(date +%s)"
qm listsnapshot 100
```

**For Physical (if supported):**
```bash
# LVM snapshot (if using LVM)
lvcreate -L 5G -s -n backup_snapshot /dev/vg0/root
```

### 4. Execute Update (10-30 minutes)

```bash
# Update packages
apt-get update
apt-get dist-upgrade -y

# Check for service restarts needed
needrestart -a a

# If kernel updated, you need to reboot
needs-restarting -r && echo "Reboot needed" || echo "No reboot needed"
```

### 5. Health Checks (5 minutes)

```bash
# Immediate (now)
systemctl status --no-pager        # System running
curl -s http://localhost:8080/health  # App health
free -m                            # Memory OK
df -h /                            # Disk OK

# Wait 5 minutes, then check again
sleep 300
systemctl is-active ssh            # SSH still up
systemctl is-active app            # App still running
uptime                             # Load reasonable
```

### 6. Document & Done

```bash
# Log the successful update
echo "Update successful at $(date)" >> /var/log/system-updates/updates.log

# If everything OK for 30 minutes, you can delete snapshot
# lxc delete my-container/before-update-123456
# qm delsnapshot 100 before-update-123456
```

---

## What to Do If Update Fails

### System Won't Boot (Kernel Issue)

```
1. Access GRUB menu (press ESC during boot)
2. Select previous kernel
3. If boots: use that kernel, skip new one
4. If doesn't boot: restore snapshot
```

**Restore LXC Snapshot:**
```bash
lxc stop container-name
lxc restore container-name "snapshot-name"
lxc start container-name
```

**Restore VM Snapshot:**
```bash
qm stop VMID
qm restore VMID "snapshot-name"
qm start VMID
```

### Service Failed to Start

```
1. Check what's wrong:
   systemctl status app --no-pager
   journalctl -u app -n 50

2. Common fixes:
   - Missing library: apt-get install <package>
   - Config issue: revert config file
   - Permission issue: fix file ownership

3. If can't fix quickly: ROLLBACK
   - Stop the service
   - Restore snapshot
   - Start everything
```

### High Memory Usage / Disk Full

```
1. Clean caches:
   apt-get clean
   apt-get autoclean

2. Remove old logs:
   journalctl --vacuum=100M

3. Delete old temp files:
   find /tmp -atime +7 -delete

4. If still full: restore snapshot
```

### Network Issues

```
1. Check connectivity:
   ping 8.8.8.8
   ip route show
   systemctl restart networking

2. Check DNS:
   nslookup google.com
   systemctl restart systemd-resolved

3. If still broken: restore snapshot
```

---

## Pre-Maintenance Checklist (Use Before Any Update)

```
SYSTEM: _________________   DATE: ________   TIME: ________

PRE-UPDATE:
[ ] Disk space >= 20% free
[ ] Memory >= 512MB available
[ ] Load < 0.7x CPU cores
[ ] Network online
[ ] SSH access working
[ ] Critical services running
[ ] Backup recent (< 24 hours)
[ ] Snapshot created

UPDATE:
[ ] apt-get update completed
[ ] apt-get install -s OK (no conflicts)
[ ] apt-get dist-upgrade completed
[ ] needrestart executed (if services need restart)
[ ] Reboot completed (if needed)

POST-UPDATE (wait 5 min, then check):
[ ] System online
[ ] SSH working
[ ] App responding
[ ] Memory OK
[ ] Disk OK
[ ] Services running
[ ] No obvious errors in logs

SUCCESS: [ ] YES [ ] NO (if NO, proceed to ROLLBACK section below)

ROLLBACK (if needed):
[ ] Stop services
[ ] lxc restore / qm restore / lvconvert
[ ] Start services
[ ] Verify restored
[ ] Delete snapshot

NOTES:
_________________________________________________________________
_________________________________________________________________

Signed: ________________  Time: ________
```

---

## Common Commands Reference

### Snapshot Management

```bash
# LXC
lxc snapshot <container> "<name>"      # Create snapshot
lxc info <container> | grep Snapshots   # List snapshots
lxc restore <container> "<name>"        # Restore snapshot
lxc delete <container>/<name>           # Delete snapshot

# Proxmox VM
qm snapshot <vmid> "<name>"             # Create
qm listsnapshot <vmid>                  # List
qm restore <vmid> "<name>"              # Restore
qm delsnapshot <vmid> "<name>"          # Delete
```

### Package Management

```bash
apt-get update                          # Update package lists
apt-get install -s dist-upgrade         # Simulate upgrade (DRY RUN!)
apt-get dist-upgrade                    # Actual upgrade
apt-get autoremove                      # Remove unused packages
apt-get clean                           # Clean package cache
apt-mark hold <package>                 # Prevent upgrade
apt-mark unhold <package>               # Allow upgrade again
```

### Service Management

```bash
systemctl status <service>              # Check status
systemctl restart <service>             # Restart service
systemctl stop <service>                # Stop service
systemctl start <service>               # Start service
systemctl enable <service>              # Enable at boot
systemctl disable <service>             # Disable at boot
needrestart -b                          # Check what needs restart
needs-restarting -r                     # Check if reboot needed
```

### Health Checks

```bash
df -h /                                 # Disk usage
free -m                                 # Memory usage
uptime                                  # Load average
systemctl status --no-pager             # System status
journalctl -n 50 -p 3..4               # Recent errors
curl -s http://localhost:8080/health    # App health
mysql -e "SHOW SLAVE STATUS\G;"         # Replication (if DB)
```

### Log Access

```bash
# Last 50 lines of system log
journalctl -n 50 --no-pager

# Errors/warnings only
journalctl -p 3..4 --no-pager

# Last 30 minutes
journalctl --since "30 minutes ago"

# For specific service
journalctl -u service-name -n 100

# Follow in real-time
journalctl -f
```

---

## When to Use Each Rollback Level

```
Rollback needed?

├─ Less than 30 seconds since start?
│  └─ Try L1 (Package downgrade)
│     apt-get install package=old-version
│
├─ Less than 2 minutes?
│  └─ Use L2 (Snapshot restore)
│     lxc restore / qm restore
│
├─ 2-5 minutes + replica available?
│  └─ Use L3 (Failover to replica)
│     Update DNS/load balancer to replica
│
└─ More than 5 minutes OR no snapshot?
   └─ Use L4 (Restore from backup)
      Full system restore (30+ minutes)
```

---

## Emergency Contacts

For immediate help during failed update:

1. **First**: Try rolling back using snapshot (fastest)
2. **Second**: Contact ops team on-call
3. **Third**: Check failure scenarios doc (07-failure-scenarios-recovery.md)
4. **Last**: Manual emergency restore from backup

---

## Statistics You Should Track

**After each update, record:**

```
System: _______________
Update Date: __________
Start Time: ___________
End Time: ______________
Duration: _____________ minutes

Success: [ ] YES [ ] NO

If NO:
Failure Type: ___________________
Rollback Level: [ ] L1 [ ] L2 [ ] L3 [ ] L4
Recovery Time: _________________ minutes

Errors Encountered:
_______________________________________
_______________________________________

Root Cause:
_______________________________________

Prevention for Next Time:
_______________________________________
```

**Monthly Metrics:**
- % of updates successful (target: >= 95%)
- Number of rollbacks (target: < 5 per 100)
- Average recovery time (target: < 5 min)
- Downtime per system (target: < 1 min critical, < 5 min non-critical)

---

## Maintenance Window Hours

**Standard Windows:**
- Tuesday: 2:00 AM - 4:00 AM
- Thursday: 2:00 AM - 4:00 AM

**Emergency Updates (Security/Critical):**
- Can be done anytime with VP Operations approval
- Follow same procedures
- Notify stakeholders immediately

---

## Decision Tree: Should I Update This System?

```
Is there a security patch?
├─ YES (Critical/High CVE)
│  └─> UPDATE IMMEDIATELY (or within 24 hours)
│
├─ YES (Medium CVE)
│  └─> UPDATE within 1 week
│
└─ NO: Is there a bug fix for active issue?
   ├─ YES (production-impacting)
   │  └─> UPDATE within 2 days
   │
   ├─ YES (non-critical)
   │  └─> UPDATE within 2 weeks
   │
   └─ NO: Is this routine maintenance?
      ├─ YES (scheduled window available)
      │  └─> UPDATE in next window
      │
      └─ NO: Can you defer?
         ├─ YES
         │  └─> DEFER to next window
         │
         └─ NO (critical requirement)
            └─> SCHEDULE SPECIAL WINDOW
```

---

## File Locations

All scripts and procedures are in:
```
/home/mdoehler/system-update-strategy/

00-EXECUTIVE-SUMMARY.md              Start here
01-pre-flight-checklist.md           Before any update
02-update-decision-tree.md           Choose update method
03-lxc-container-update-playbook.md  LXC containers
04-proxmox-vm-update-playbook.md     Proxmox VMs
05-rollback-procedures.md            If update fails
06-update-sequencing-health-checks.md Batching & validation
07-failure-scenarios-recovery.md     Troubleshooting
08-shell-scripts.sh                  Automated scripts
09-zabbix-monitoring-integration.md  Monitoring setup
10-quick-reference-guide.md          This file
```

Deploy scripts to:
```
/opt/update-scripts/08-shell-scripts.sh
```

Logs are written to:
```
/var/log/system-updates/updates.log
```

---

## One-Page Update Flowchart

```
START
  ↓
Classify System (Tier 1-4)
  ↓
Run Pre-Flight Checks → FAIL → Fix issues → Re-check
  ↓ PASS
Create Snapshot
  ↓
Notify stakeholders
  ↓
Execute Update (apt dist-upgrade)
  ↓
Reboot if needed
  ↓
Wait 5 minutes for stability
  ↓
Health Checks → FAIL → ROLLBACK → Go to RESTORE
  ↓ PASS
Continue monitoring (30 min)
  ↓
Continue monitoring (4 hours) → Any issues? → ESCALATE
  ↓ All good
Document successful update
  ↓
Delete old snapshots
  ↓
END - SUCCESS

RESTORE (from rollback):
  ↓
Stop services
  ↓
Restore snapshot (L2)
  OR
Failover to replica (L3)
  OR
Restore from backup (L4)
  ↓
Start services
  ↓
Verify system operational
  ↓
END - RECOVERED
```

---

## Remember

1. **Snapshots are your safety net** - Always create before update
2. **Health checks save lives** - Run all 4 levels
3. **Rollback is OK** - Better to rollback than spend hours debugging
4. **Dry-run first** - apt-get install -s catches most issues
5. **Pre-flight matters** - 80% of issues caught in pre-flight
6. **Batch intelligently** - Update non-critical before critical
7. **Monitor everything** - During and after update
8. **Document everything** - For post-mortems and learning

---

## Still Have Questions?

1. **How do I...?** → Check 06-update-sequencing-health-checks.md
2. **What if...?** → Check 07-failure-scenarios-recovery.md
3. **Show me code** → Check 08-shell-scripts.sh
4. **Big picture** → Check 00-EXECUTIVE-SUMMARY.md
5. **How to decide?** → Check 02-update-decision-tree.md

---

**Last Updated**: 2025-11-17
**For Questions**: Contact Ops Team
**For Emergencies**: Page on-call engineer immediately
