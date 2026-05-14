# Update Decision Tree & System Classification

## Decision Framework Overview

This decision tree determines whether a system should be updated, what strategy to use, and what approval level is required.

## Part 1: Initial System Assessment

```
START: Update Required?
    ├─ Security patch (CVE-related)?
    │   ├─ YES: Critical/High severity
    │   │   └─> Priority: IMMEDIATE (within 24 hours)
    │   ├─ YES: Medium severity
    │   │   └─> Priority: URGENT (within 1 week)
    │   └─ NO: Continue below
    │
    ├─ Bug fix for active issue?
    │   ├─ YES: Production-impacting
    │   │   └─> Priority: HIGH (within 48 hours)
    │   ├─ YES: Non-critical workaround exists
    │   │   └─> Priority: MEDIUM (within 2 weeks)
    │   └─ NO: Continue below
    │
    ├─ Feature upgrade or enhancement?
    │   ├─ YES: Dependencies require it
    │   │   └─> Priority: MEDIUM (within 2 weeks)
    │   ├─ YES: Nice-to-have
    │   │   └─> Priority: LOW (within 30 days)
    │   └─ NO: Continue below
    │
    └─ Routine maintenance (quarterly/monthly)?
        ├─ YES: Scheduled window available
        │   └─> Priority: STANDARD (schedule normally)
        └─ NO: Defer to next planned window
```

## Part 2: System Classification & Update Strategy

### Tier 1: Critical Production Systems (RTO < 5 min, RPO = 0)

**Examples**: Database clusters, main API servers, load balancers, payment processing

**Classification Check**:
```yaml
Is_Critical:
  - Data loss tolerance: ZERO
  - Acceptable downtime: < 1 minute
  - Revenue impact per minute: > $1000
  - Customer-facing: YES
  - SLA requirement: 99.99%+ uptime
```

**Decision Path**:
```
Critical Production System Update?
    ├─ Security patch (Critical/High)
    │   ├─ Kernel update required?
    │   │   ├─ YES: Use Blue-Green Strategy
    │   │   │   └─> Prepare standby, test, switch, verify, keep N-1
    │   │   └─ NO: Use Rolling Update Strategy
    │   │       └─> 1 system at a time, health check between each
    │   │
    │   └─ Approval: VP Ops + Ops Lead required
    │       └─> Maintenance window: Tuesday/Thursday 2-4 AM only
    │
    ├─ Non-security update
    │   └─> Decision: DEFER unless blocking critical issue
    │       └─> Reschedule to next scheduled maintenance (30 days max)
    │
    └─ Rollback Plan:
        ├─> L1: Package downgrade (< 30 sec)
        ├─> L2: Snapshot restore (< 2 min)
        └─> L3: Failover to replica (< 5 min)
```

### Tier 2: Important Infrastructure (RTO < 30 min, RPO <= 1 hour)

**Examples**: Secondary databases, backup servers, monitoring infrastructure, internal APIs

**Classification Check**:
```yaml
Is_Important:
  - Data loss tolerance: <= 1 hour
  - Acceptable downtime: < 5 minutes
  - Revenue impact per minute: $100-1000
  - Customer-facing: NO
  - SLA requirement: 99.9%+ uptime
```

**Decision Path**:
```
Important Infrastructure Update?
    ├─ Security patch (Critical/High)
    │   ├─ Kernel update required?
    │   │   ├─ YES: Use Rolling Strategy (can do 2-3 at time)
    │   │   │   └─> Health check between batches
    │   │   └─ NO: Use Canary Strategy
    │   │       └─> Update 1, monitor 30 min, then batch remaining
    │   │
    │   └─ Approval: Ops Lead only
    │       └─> Maintenance window: Any scheduled window
    │
    ├─ Non-security update
    │   ├─ Resolves active bug? YES
    │   │   └─> Use Rolling Strategy
    │   │       └─> Approval: Ops Lead
    │   └─ Routine maintenance
    │       └─> Decision: Schedule next window (2 weeks max)
    │
    └─ Rollback Plan:
        ├─> L1: Package downgrade (< 1 min)
        ├─> L2: Snapshot restore (< 5 min)
        └─> L3: Service failover (< 10 min)
```

### Tier 3: Standard Infrastructure (RTO <= 4 hours, RPO <= 24 hours)

**Examples**: File servers, print servers, dev/test systems, build agents, log aggregation

**Classification Check**:
```yaml
Is_Standard:
  - Data loss tolerance: <= 24 hours
  - Acceptable downtime: <= 30 minutes
  - Revenue impact: INDIRECT/MINIMAL
  - Customer-facing: NO
  - SLA requirement: 99%+ uptime
```

**Decision Path**:
```
Standard Infrastructure Update?
    ├─ Security patch
    │   ├─ Kernel update required?
    │   │   ├─ YES: Use Rolling Strategy (5 systems at time)
    │   │   │   └─> Minimal monitoring required
    │   │   └─ NO: Use Batch Strategy
    │   │       └─> Update 5-10 at once, monitor 15 min
    │   │
    │   └─ Approval: On-call engineer
    │       └─> Any maintenance window acceptable
    │
    ├─ Non-security update
    │   └─> Routine batch scheduling acceptable
    │       └─> Approval: Ops team decision
    │
    └─ Rollback Plan:
        ├─> L1: Package downgrade (auto if health fails)
        ├─> L2: Snapshot restore (5-10 min)
        └─> L3: Re-image from baseline (< 1 hour)
```

### Tier 4: Non-Critical Systems (RTO >= 24 hours, RPO = not critical)

**Examples**: Test environments, staging systems, old lab equipment, decommissioned systems

**Classification Check**:
```yaml
Is_NonCritical:
  - Data loss tolerance: ACCEPTABLE
  - Acceptable downtime: UNLIMITED
  - Revenue impact: ZERO
  - Customer-facing: NO
  - SLA requirement: NONE
```

**Decision Path**:
```
Non-Critical System Update?
    ├─ Any update type
    │   ├─> Approval: Not required
    │   ├─> Can update immediately or batch with others
    │   ├─> Maintenance window: NOT required
    │   │
    │   └─ Rollback Plan:
    │       ├─> Not required (reimaging acceptable)
    │       └─> Snapshot for efficiency only
```

## Part 3: Update Method Selection

### Decision: Kernel Update Required?

```
Does update include kernel?
    ├─ YES (linux-image package)
    │   ├─ System Type: LXC Container
    │   │   └─> Strategy: Host Kernel (update host only, restart containers)
    │   │
    │   ├─ System Type: Proxmox VM
    │   │   ├─ Critical system?
    │   │   │   ├─ YES: Blue-Green Strategy
    │   │   │   │   └─> Create backup VM, update, test, switch
    │   │   │   └─ NO: Rolling Strategy
    │   │   │       └─> Update, snapshot, reboot, verify
    │   │   │
    │   │   ├─ Replication enabled?
    │   │   │   ├─ YES: Pause replication, update, resume
    │   │   │   └─ NO: Proceed normally
    │   │   │
    │   │   └─ Storage type?
    │   │       ├─ Local: Snapshot only
    │   │       ├─ Ceph: Can do live migration
    │   │       └─ Network: Follow network storage policy
    │   │
    │   ├─ System Type: Physical Server
    │   │   ├─ Redundancy available?
    │   │   │   ├─ YES: Blue-Green on standby hardware
    │   │   │   └─ NO: Scheduled downtime required
    │   │   │
    │   │   ├─ Critical service?
    │   │   │   ├─ YES: Drain connections, coordinate failover
    │   │   │   └─ NO: Standard reboot acceptable
    │   │   │
    │   │   └─ Update GRUB/bootloader
    │   │       └─> grub-mkconfig must succeed
    │   │
    │   └─ Post-Update Actions: MANDATORY
    │       ├─ Wait 60 seconds after kernel selection
    │       ├─ Verify system boots with new kernel
    │       ├─ Check kernel loaded: uname -r matches
    │       ├─ Verify all services started
    │       └─ Monitor for next 5 minutes for kernel panic
    │
    └─ NO (only application/library updates)
        ├─ System Type: Any
        │   └─> Strategy: Direct Update (no reboot required usually)
        │       ├─ Update packages: apt-get dist-upgrade
                ├─ Check for service restarts: needrestart -k
        │       ├─ Restart services if needed: systemctl restart
        │       └─ Verify services running
        │
        └─ Post-Update Actions:
            ├─ Monitor for 2-5 minutes
            ├─ Check application health
            └─ Verify log files for errors
```

### Decision: Service Restart Strategy

```
Update requires service restart?
    ├─ Downtime < 30 seconds acceptable?
    │   ├─ YES: Direct Restart Strategy
    │   │   └─> systemctl restart SERVICE_NAME
    │   │
    │   └─ NO: Continue below
    │
    ├─ Service has connection pooling?
    │   ├─ YES: Graceful Shutdown Strategy
    │   │   ├─ Send SIGTERM to processes
    │   │   ├─ Wait 30 seconds for connections to drain
    │   │   ├─ Send SIGKILL if not stopped
    │   │   └─ Restart service
    │   │
    │   └─ NO: Continue below
    │
    └─ Service is critical (no replica)?
        ├─ YES: Blue-Green Restart Strategy
        │   ├─ Start second instance on different port
        │   ├─ Warm up (allow client connections)
        │   ├─ Switch load balancer to new instance
        │   ├─ Wait for draining
        │   ├─ Restart original instance
        │   └─ Keep both running (N+1 for 5 min)
        │
        └─ NO: Standard Restart
            └─> Direct restart acceptable
```

## Part 4: Update Safety Gates

### Pre-Update Gate
```
All checks PASSED?
    ├─ YES: All green lights
    │   ├─ Disk space ✓
    │   ├─ Memory available ✓
    │   ├─ Network connected ✓
    │   ├─ Critical services healthy ✓
    │   ├─ Backup verified ✓
    │   └─ Snapshot created ✓
    │
    │   └─> PROCEED: Execute update
    │
    └─ NO: One or more failures
        ├─ Critical failure (backup, snapshot, services)?
        │   ├─ YES: ABORT
        │   │   └─> Investigate and resolve
        │   │
        │   └─ NO: Non-critical failure
        │       ├─ Attempt remediation
        │       ├─ If resolved: PROCEED
        │       └─ If unresolved: RESCHEDULE
```

### Post-Update Gate
```
Update completed, checking results...
    ├─ Reboot required?
    │   ├─ YES: Execute reboot
    │   │   ├─ Wait for system to come back (max 5 min)
    │   │   ├─ If not back: TRIGGER ROLLBACK (L2)
    │   │   └─ Continue below
    │   │
    │   └─ NO: Continue below
    │
    ├─ Health check phase (5 minutes)
    │   ├─ System online and responsive? YES/NO
    │   ├─ Critical services running? YES/NO
    │   ├─ Network connectivity? YES/NO
    │   ├─ Application serving requests? YES/NO
    │   ├─ Error logs clean? YES/NO
    │   └─ Metrics normal? YES/NO
    │
    ├─ All health checks passed?
    │   ├─ YES: UPDATE SUCCESS
    │   │   ├─ Clean up old snapshots (keep N-1)
    │   │   ├─ Document successful update
    │   │   └─ Resume normal operations
    │   │
    │   └─ NO: TRIGGER AUTOMATIC ROLLBACK
    │       └─> Execute L1 or L2 rollback based on failure type
```

## Part 5: Approval Requirements by Tier & Type

### Approval Matrix

| Tier | Security Patch | Bug Fix | Routine Update |
|------|---|---|---|
| **Tier 1 (Critical)** | VP Ops + Ops Lead | VP Ops approval | Defer or Ops Lead + change mgmt |
| **Tier 2 (Important)** | Ops Lead + on-call | Ops Lead | Ops team decision |
| **Tier 3 (Standard)** | On-call + peer review | On-call | Team lead sign-off |
| **Tier 4 (Non-critical)** | No approval needed | No approval | Free to update |

### Approval Sign-Off Requirements

```yaml
For Tier 1 & 2 updates:
  - Approval ticket must reference:
    * CVE number (if security)
    * Change management ticket
    * Maintenance window
    * Rollback plan
    * Health check criteria
    * Expected impact
    * Estimated duration

  - Approval must be documented with:
    * Approver name and title
    * Approval timestamp
    * Any conditions or special requirements

For Tier 3 updates:
  - Can batch multiple systems
  - Brief documented approval sufficient
  - Escalate to Tier 2 if issues found

For Tier 4 updates:
  - Self-service, log entry sufficient
  - No approval blocking updates
```

## Part 6: Rollback Decision Tree

```
Update failed or health check failed?
    ├─ Yes, Continue below
    │
    ├─ Time since update: MEASURE
    │   ├─ < 30 seconds: Try L1 (package downgrade)
    │   │   ├─ Revertable packages? YES
    │   │   │   └─> apt-get install package=old-version
    │   │   │       ├─ Success: Restart service, verify
    │   │   │       └─ Fail: Escalate to L2
    │   │   │
    │   │   └─ Revertable packages? NO
    │   │       └─> Escalate to L2
    │   │
    │   ├─ 30 seconds - 2 min: Use L2 (snapshot restore)
    │   │   ├─ Snapshot exists? YES
    │   │   │   └─> Restore from snapshot
    │   │   │       ├─ System restores successfully
    │   │   │       ├─ Services start
    │   │   │       ├─ Data integrity verified
    │   │   │       └─ Success: Return to production
    │   │   │
    │   │   └─ Snapshot exists? NO
    │   │       └─> Escalate to L3
    │   │
    │   ├─ 2 - 5 min: Use L2 or L3 depending on availability
    │   │   ├─ Is this critical system with failover?
    │   │   │   ├─ YES: Use L3 (failover to replica)
    │   │   │   └─ NO: Use L2 (snapshot restore)
    │   │   │
    │   │   └─ Continue with chosen strategy
    │   │
    │   └─ > 5 min: Use L3 (Full system restore or failover)
    │       ├─ Can failover to replica? YES
    │       │   └─> Failover immediately
    │       │       ├─ Update replica instead
    │       │       ├─ Test replica thoroughly
    │       │       ├─ Failback when replica ready
    │       │       └─ Update original when safe
    │       │
    │       └─ Can failover to replica? NO
    │           └─> Restore from backup
    │               ├─ Restore to original system
    │               ├─ Verify data integrity
    │               ├─ Restore may take 30+ min
    │               └─> Communicate ETA to stakeholders
    │
    └─ Post-Rollback Actions (ALL levels):
        ├─ Verify system operational
        ├─ Check data integrity
        ├─ Investigate root cause
        ├─ Document incident
        ├─ Plan retry with remediation
        └─> Escalate to engineering for review
```

## Summary: Quick Reference

**Key Decision Points**:
1. What tier is this system? (Determines approval, urgency)
2. Does update include kernel? (Determines strategy type)
3. Are replicas/snapshots available? (Determines rollback depth)
4. Is downtime acceptable? (Determines update strategy)

**Default Strategies**:
- **Tier 1 Critical**: Blue-Green (with approval gate)
- **Tier 2 Important**: Rolling (batch by service dependency)
- **Tier 3 Standard**: Batch update (5-10 systems at time)
- **Tier 4 Non-critical**: Batch anytime

**Rollback Thresholds**:
- < 2 min: L1 (package) or L2 (snapshot)
- 2-5 min: L2 (snapshot) or L3 (failover)
- > 5 min: L3 (failover/restore)
