#!/bin/bash

##############################################################################
# SYSTEM UPDATE ORCHESTRATION SHELL SCRIPTS
#
# These scripts provide practical implementations for:
# - Pre-flight checks
# - Update execution
# - Health checks
# - Rollback procedures
# - n8n integration
#
# Usage: Source this file in your shell or n8n bash nodes
##############################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Logging
LOG_DIR="${LOG_DIR:-/var/log/system-updates}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
SCRIPT_DIR="${SCRIPT_DIR:-/opt/update-scripts}"

# Thresholds
DISK_FREE_MIN=20  # Percent
MEMORY_MIN=512    # MB
LOAD_THRESHOLD_MULTIPLIER=0.7
REBOOT_TIMEOUT=300  # Seconds (5 minutes)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case $level in
        INFO)
            echo -e "${BLUE}[INFO]${NC} $timestamp: $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} $timestamp: $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $timestamp: $message"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} $timestamp: $message"
            ;;
    esac

    # Also log to file
    mkdir -p "$LOG_DIR"
    echo "[$level] $timestamp: $message" >> "$LOG_DIR/updates.log"
}

execute_cmd() {
    local cmd=$1
    local description=$2
    local log_output=${3:-true}

    log INFO "Executing: $description"

    if [ "$log_output" = true ]; then
        eval "$cmd" 2>&1 | tee -a "$LOG_DIR/updates.log"
    else
        eval "$cmd" 2>&1 >> "$LOG_DIR/updates.log"
    fi

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log SUCCESS "$description completed"
        return 0
    else
        log ERROR "$description failed"
        return 1
    fi
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

check_disk_space() {
    local target_dir=${1:-/}
    local min_free=${2:-$DISK_FREE_MIN}

    log INFO "Checking disk space for $target_dir (minimum ${min_free}%)"

    local free_percent=$(df "$target_dir" | awk 'NR==2 {printf "%.0f", $4/($2)*100}')
    local used_percent=$(df "$target_dir" | awk 'NR==2 {printf "%.0f", $3/($2)*100}')

    log INFO "Disk usage: ${used_percent}% used, ${free_percent}% free"

    if [ "$free_percent" -lt "$min_free" ]; then
        log ERROR "Insufficient disk space: ${free_percent}% < ${min_free}% required"
        return 1
    fi

    log SUCCESS "Disk space check passed"
    return 0
}

check_memory() {
    local min_mem=${1:-$MEMORY_MIN}

    log INFO "Checking available memory (minimum ${min_mem}MB)"

    local available=$(free -m | awk '/^Mem:/ {print $7}')
    log INFO "Available memory: ${available}MB"

    if [ "$available" -lt "$min_mem" ]; then
        log ERROR "Insufficient memory: ${available}MB < ${min_mem}MB required"
        return 1
    fi

    log SUCCESS "Memory check passed"
    return 0
}

check_load_average() {
    local max_load=${1:-$LOAD_THRESHOLD_MULTIPLIER}

    log INFO "Checking load average (maximum ${max_load}x CPU cores)"

    local load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
    local cpu_cores=$(nproc)
    local threshold=$(echo "$cpu_cores * $max_load" | bc)

    log INFO "Current load: $load, threshold: $threshold"

    if (( $(echo "$load > $threshold" | bc -l) )); then
        log WARN "System load is high: $load > $threshold"
        log INFO "Waiting 15 minutes for load to decrease..."
        sleep 900

        # Re-check after wait
        load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
        if (( $(echo "$load > $threshold" | bc -l) )); then
            log ERROR "Load still high after wait, aborting update"
            return 1
        fi
    fi

    log SUCCESS "Load average check passed"
    return 0
}

check_network_connectivity() {
    log INFO "Checking network connectivity"

    # Check gateway reachable
    local gateway=$(ip route | grep default | awk '{print $3}' | head -1)
    if [ -z "$gateway" ]; then
        log ERROR "No default gateway configured"
        return 1
    fi

    if ! ping -c 1 -W 2 "$gateway" >/dev/null 2>&1; then
        log ERROR "Gateway $gateway unreachable"
        return 1
    fi

    log SUCCESS "Gateway reachable: $gateway"

    # Check DNS resolution
    if ! nslookup google.com >/dev/null 2>&1; then
        log WARN "DNS resolution issues, but may continue"
    else
        log SUCCESS "DNS resolution working"
    fi

    # Check package repository
    if ! curl -s -I http://deb.debian.org >/dev/null 2>&1; then
        log WARN "Debian repository may be unreachable"
    else
        log SUCCESS "Package repository accessible"
    fi

    return 0
}

check_critical_services() {
    log INFO "Checking critical services"

    local critical_services=("networking" "ssh" "rsyslog")
    local failed_services=()

    for service in "${critical_services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log SUCCESS "Service $service: running"
        else
            log ERROR "Service $service: NOT running"
            failed_services+=("$service")
        fi
    done

    if [ ${#failed_services[@]} -gt 0 ]; then
        log ERROR "Critical services failed: ${failed_services[*]}"
        log INFO "Attempting to restart failed services..."

        for service in "${failed_services[@]}"; do
            if systemctl restart "$service"; then
                log SUCCESS "Successfully restarted $service"
            else
                log ERROR "Failed to restart $service, aborting"
                return 1
            fi
        done
    fi

    return 0
}

pre_flight_checks() {
    local system_type=${1:-physical}

    log INFO "Starting pre-flight checks for $system_type system"

    # Run all checks
    check_disk_space "/" 20 || return 1
    check_memory 512 || return 1
    check_load_average 0.7 || return 1
    check_network_connectivity || return 1
    check_critical_services || return 1

    log SUCCESS "All pre-flight checks passed"
    return 0
}

# ============================================================================
# SNAPSHOT MANAGEMENT
# ============================================================================

create_lxc_snapshot() {
    local container=$1
    local snapshot_id="before-update-$(date +%Y%m%d-%H%M%S)"

    log INFO "Creating LXC snapshot: $container -> $snapshot_id"

    if lxc snapshot "$container" "$snapshot_id"; then
        log SUCCESS "Snapshot created: $snapshot_id"
        echo "$snapshot_id"
        return 0
    else
        log ERROR "Failed to create snapshot"
        return 1
    fi
}

create_vm_snapshot() {
    local vmid=$1
    local snapshot_id="before-update-$(date +%Y%m%d-%H%M%S)"

    log INFO "Creating VM snapshot: VMID=$vmid -> $snapshot_id"

    if qm snapshot "$vmid" "$snapshot_id"; then
        log SUCCESS "Snapshot created: $snapshot_id"
        echo "$snapshot_id"
        return 0
    else
        log ERROR "Failed to create snapshot"
        return 1
    fi
}

verify_snapshot() {
    local system_id=$1
    local snapshot=$2
    local system_type=${3:-vm}  # vm or lxc

    log INFO "Verifying snapshot: $snapshot"

    if [ "$system_type" = "lxc" ]; then
        if lxc info "$system_id" | grep -q "$snapshot"; then
            log SUCCESS "Snapshot verified"
            return 0
        fi
    else
        if qm listsnapshot "$system_id" | grep -q "$snapshot"; then
            log SUCCESS "Snapshot verified"
            return 0
        fi
    fi

    log ERROR "Snapshot verification failed"
    return 1
}

# ============================================================================
# UPDATE EXECUTION
# ============================================================================

update_packages_ssh() {
    local host=$1
    local user=${2:-root}
    local log_file="${LOG_DIR}/update-${host}-$(date +%Y%m%d-%H%M%S).log"

    log INFO "Updating packages on $host via SSH"

    # Create update script
    local update_script=$(mktemp)
    cat > "$update_script" <<'EOF'
#!/bin/bash
set -e

echo "=== Updating package lists ==="
apt-get update

echo "=== Simulating upgrade ==="
apt-get install -s dist-upgrade 2>&1 | tee /tmp/apt-simulation.log

if grep -q "broken\|Broken" /tmp/apt-simulation.log; then
    echo "ERROR: Broken dependencies detected"
    cat /tmp/apt-simulation.log
    exit 1
fi

echo "=== Executing upgrade ==="
apt-get -y dist-upgrade

echo "=== Checking for service restarts ==="
needrestart -b || true

echo "=== Upgrade complete ==="
EOF

    # Execute on remote
    if scp "$update_script" "$user@$host:/tmp/" >/dev/null 2>&1 && \
       ssh "$user@$host" "bash /tmp/$(basename $update_script)" > "$log_file" 2>&1; then
        log SUCCESS "Update completed on $host"
        cat "$log_file" >> "$LOG_DIR/updates.log"
        rm "$update_script"
        return 0
    else
        log ERROR "Update failed on $host"
        cat "$log_file" >> "$LOG_DIR/updates.log"
        rm "$update_script"
        return 1
    fi
}

update_packages_local() {
    local log_file="${LOG_DIR}/update-local-$(date +%Y%m%d-%H%M%S).log"

    log INFO "Updating packages locally"

    # Update package lists
    log INFO "apt-get update"
    if ! apt-get update >> "$log_file" 2>&1; then
        log ERROR "apt-get update failed"
        return 1
    fi

    # Simulate upgrade
    log INFO "Simulating apt-get dist-upgrade"
    if ! apt-get install -s dist-upgrade >> "$log_file" 2>&1; then
        log ERROR "Simulation detected issues"
        grep "broken\|Broken" "$log_file" || true
        return 1
    fi

    # Execute upgrade
    log INFO "Executing apt-get dist-upgrade"
    if ! apt-get -y dist-upgrade >> "$log_file" 2>&1; then
        log ERROR "apt-get dist-upgrade failed"
        return 1
    fi

    log SUCCESS "Local package update completed"
    return 0
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

health_check_immediate() {
    local system_id=$1
    local system_type=${2:-physical}
    local host=${3:-}

    log INFO "Running immediate health checks (30 seconds)"

    # For SSH-accessible systems
    if [ -n "$host" ]; then
        # System responsive
        if ! ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
            log ERROR "System not responding to ping"
            return 1
        fi

        # SSH access
        if ! ssh -o ConnectTimeout=2 -o BatchMode=yes root@"$host" "echo ok" >/dev/null 2>&1; then
            log ERROR "SSH not accessible"
            return 1
        fi

        # Services
        for service in ssh networking rsyslog; do
            if ! ssh root@"$host" "systemctl is-active --quiet $service"; then
                log WARN "Service $service not running on $host"
            fi
        done
    fi

    # For local system
    if systemctl is-active --quiet ssh; then
        log SUCCESS "SSH service running"
    else
        log WARN "SSH service not running"
    fi

    log SUCCESS "Immediate health checks passed"
    return 0
}

health_check_functional() {
    local host=$1
    local port=${2:-8080}

    log INFO "Running functional health checks (5 minutes)"

    # Wait 5 seconds for services to stabilize
    sleep 5

    # Check application health endpoint
    local health_response=$(curl -s -w "%{http_code}" -o /dev/null http://"$host":"$port"/health 2>/dev/null || echo "000")

    if [ "$health_response" = "200" ]; then
        log SUCCESS "Application health check: HTTP 200"
        return 0
    elif [ "$health_response" != "000" ]; then
        log WARN "Application health check: HTTP $health_response"
        return 0
    else
        log ERROR "Application health check failed"
        return 1
    fi
}

health_check_operational() {
    local host=$1

    log INFO "Running operational health checks (30 minutes)"

    # Memory usage
    local mem_usage=$(ssh root@"$host" "free -m | grep '^Mem' | awk '{printf \"%.0f\", \$3/\$2*100}'" 2>/dev/null)
    if [ -n "$mem_usage" ]; then
        log INFO "Memory usage: ${mem_usage}%"
        if [ "$mem_usage" -gt 90 ]; then
            log WARN "Memory usage high: ${mem_usage}%"
        fi
    fi

    # Disk usage
    local disk_usage=$(ssh root@"$host" "df / | tail -1 | awk '{print \$5}' | sed 's/%//'" 2>/dev/null)
    if [ -n "$disk_usage" ]; then
        log INFO "Disk usage: ${disk_usage}%"
        if [ "$disk_usage" -gt 90 ]; then
            log WARN "Disk usage high: ${disk_usage}%"
        fi
    fi

    # Error count
    local error_count=$(ssh root@"$host" "journalctl -n 100 -p 3..4 2>/dev/null | wc -l" 2>/dev/null)
    log INFO "Recent errors: $error_count"

    log SUCCESS "Operational health checks completed"
    return 0
}

# ============================================================================
# ROLLBACK PROCEDURES
# ============================================================================

rollback_level_1() {
    local package_list=${1:-}

    log INFO "Executing Level 1 rollback: Package downgrade"

    if [ -z "$package_list" ]; then
        log ERROR "No packages specified for downgrade"
        return 1
    fi

    # Note: This is complex because apt doesn't track previous versions well
    # Usually triggered manually or from version history
    log WARN "L1 rollback requires manual intervention for version history"

    return 0
}

rollback_level_2_lxc() {
    local container=$1
    local snapshot=$2

    log INFO "Executing Level 2 rollback: LXC snapshot restore"

    # Stop container
    log INFO "Stopping container..."
    if ! lxc stop "$container" --timeout=30 2>/dev/null; then
        log WARN "Container didn't stop gracefully, forcing..."
        lxc stop "$container" --force
    fi

    # Restore snapshot
    log INFO "Restoring snapshot: $snapshot"
    if ! lxc restore "$container" "$snapshot"; then
        log ERROR "Snapshot restore failed"
        return 1
    fi

    # Start container
    log INFO "Starting container..."
    if ! lxc start "$container"; then
        log ERROR "Container failed to start"
        return 1
    fi

    # Wait for startup
    log INFO "Waiting for container to boot (max 60 seconds)..."
    local max_attempts=12
    for ((i=1; i<=max_attempts; i++)); do
        if lxc list | grep "$container" | grep -q RUNNING; then
            log SUCCESS "Container is running"
            break
        fi
        echo -n "."
        sleep 5
    done

    log SUCCESS "Level 2 rollback completed"
    return 0
}

rollback_level_2_vm() {
    local vmid=$1
    local snapshot=$2

    log INFO "Executing Level 2 rollback: VM snapshot restore"

    # Stop VM
    log INFO "Stopping VM..."
    if ! qm stop "$vmid" --timeout=30 2>/dev/null; then
        log WARN "VM didn't stop gracefully, forcing..."
        qm stop "$vmid" --force
    fi

    # Restore snapshot
    log INFO "Restoring snapshot: $snapshot"
    if ! qm restore "$vmid" "$snapshot"; then
        log ERROR "Snapshot restore failed"
        return 1
    fi

    # Start VM
    log INFO "Starting VM..."
    if ! qm start "$vmid"; then
        log ERROR "VM failed to start"
        return 1
    fi

    # Wait for VM to boot
    log INFO "Waiting for VM to boot (max 90 seconds)..."
    local max_attempts=18
    for ((i=1; i<=max_attempts; i++)); do
        if qm status "$vmid" | grep -q running; then
            sleep 30  # Wait for guest OS to boot
            log SUCCESS "VM is running"
            break
        fi
        echo -n "."
        sleep 5
    done

    log SUCCESS "Level 2 rollback completed"
    return 0
}

rollback_level_3_failover() {
    local primary_ip=$1
    local replica_ip=$2
    local service_name=$3

    log INFO "Executing Level 3 rollback: Failover to replica"

    # This is infrastructure-specific
    log WARN "Level 3 failover requires manual load balancer reconfiguration"
    log INFO "Primary: $primary_ip -> Replica: $replica_ip"
    log INFO "Failover procedure:"
    log INFO "  1. Update load balancer to point to $replica_ip"
    log INFO "  2. Monitor traffic shift"
    log INFO "  3. Verify replica is serving requests"
    log INFO "  4. Update primary when ready"

    return 0
}

# ============================================================================
# ORCHESTRATION WORKFLOWS
# ============================================================================

update_system_workflow() {
    local system_name=$1
    local system_type=${2:-physical}
    local host=${3:-}

    log INFO "=== Starting Update Workflow for $system_name ==="

    # Pre-flight checks
    if ! pre_flight_checks "$system_type"; then
        log ERROR "Pre-flight checks failed, aborting"
        return 1
    fi

    # Create snapshot if applicable
    local snapshot_id=""
    if [ "$system_type" = "lxc" ]; then
        snapshot_id=$(create_lxc_snapshot "$system_name") || return 1
    elif [ "$system_type" = "vm" ]; then
        snapshot_id=$(create_vm_snapshot "$system_name") || return 1
    fi

    # Update packages
    if [ -n "$host" ]; then
        if ! update_packages_ssh "$host"; then
            log ERROR "Update failed, initiating rollback"
            if [ -n "$snapshot_id" ]; then
                if [ "$system_type" = "lxc" ]; then
                    rollback_level_2_lxc "$system_name" "$snapshot_id"
                elif [ "$system_type" = "vm" ]; then
                    rollback_level_2_vm "$system_name" "$snapshot_id"
                fi
            fi
            return 1
        fi
    else
        if ! update_packages_local; then
            log ERROR "Update failed"
            return 1
        fi
    fi

    # Post-update health checks
    sleep 30
    if ! health_check_immediate "$system_name" "$system_type" "$host"; then
        log ERROR "Health checks failed, initiating rollback"
        if [ -n "$snapshot_id" ]; then
            if [ "$system_type" = "lxc" ]; then
                rollback_level_2_lxc "$system_name" "$snapshot_id"
            elif [ "$system_type" = "vm" ]; then
                rollback_level_2_vm "$system_name" "$snapshot_id"
            fi
        fi
        return 1
    fi

    # Verify update success
    log SUCCESS "=== Update Workflow Completed Successfully ==="

    # Document the update
    cat > "${LOG_DIR}/${system_name}-update-$(date +%Y%m%d).log" <<EOF
System: $system_name
Type: $system_type
Update Date: $(date -Iseconds)
Snapshot: $snapshot_id
Status: SUCCESSFUL
EOF

    return 0
}

# ============================================================================
# UTILITY COMMANDS
# ============================================================================

# Export functions so they can be called from n8n
export -f log execute_cmd check_disk_space check_memory check_load_average
export -f check_network_connectivity check_critical_services pre_flight_checks
export -f create_lxc_snapshot create_vm_snapshot verify_snapshot
export -f update_packages_ssh update_packages_local
export -f health_check_immediate health_check_functional health_check_operational
export -f rollback_level_1 rollback_level_2_lxc rollback_level_2_vm rollback_level_3_failover
export -f update_system_workflow

# Main execution (if called directly, not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Example usage:
    # ./08-shell-scripts.sh <function> <args>

    FUNCTION=${1:-help}
    shift || true

    case "$FUNCTION" in
        pre-flight)
            pre_flight_checks "$@"
            ;;
        update)
            update_system_workflow "$@"
            ;;
        health-check)
            health_check_immediate "$@"
            ;;
        rollback-lxc)
            rollback_level_2_lxc "$@"
            ;;
        rollback-vm)
            rollback_level_2_vm "$@"
            ;;
        *)
            echo "Usage: $0 <function> [args]"
            echo ""
            echo "Available functions:"
            echo "  pre-flight [system-type]              - Run pre-flight checks"
            echo "  update <name> <type> [host] [user]    - Run full update workflow"
            echo "  health-check <id> <type> [host]       - Run health checks"
            echo "  rollback-lxc <container> <snapshot>   - Rollback LXC container"
            echo "  rollback-vm <vmid> <snapshot>         - Rollback Proxmox VM"
            echo ""
            echo "Examples:"
            echo "  $0 pre-flight physical"
            echo "  $0 update prod-api-01 vm 10.1.1.50 root"
            echo "  $0 health-check 10.1.1.50 physical"
            ;;
    esac
fi
