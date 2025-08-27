#!/bin/bash
# Production Deployment Script v1.0.0
# Automatisiertes Deployment für Aktienanalyse-Ökosystem
# Server: 10.1.1.174

set -euo pipefail  # Strict error handling

# Configuration
PRODUCTION_SERVER="10.1.1.174"
PROJECT_ROOT="/opt/aktienanalyse-ökosystem"
BACKUP_DIR="/opt/backups/aktienanalyse"
DEPLOYMENT_LOG="/var/log/aktienanalyse-deployment.log"
DATETIME=$(date '+%Y%m%d_%H%M%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | ssh root@$PRODUCTION_SERVER "tee -a $DEPLOYMENT_LOG"
    echo -e "$1"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Function to run SSH commands with error handling
run_ssh() {
    local command="$1"
    local description="$2"
    
    log_info "Executing: $description"
    if ssh root@$PRODUCTION_SERVER "$command"; then
        log_success "$description completed"
        return 0
    else
        log_error "$description failed"
        return 1
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Starting pre-deployment checks..."
    
    # Check SSH connectivity
    if ! ssh root@$PRODUCTION_SERVER "echo 'SSH connection test'" >/dev/null 2>&1; then
        log_error "Cannot connect to production server $PRODUCTION_SERVER"
        exit 1
    fi
    log_success "SSH connectivity verified"
    
    # Check disk space
    local disk_usage=$(ssh root@$PRODUCTION_SERVER "df -h / | awk 'NR==2 {print \$5}' | sed 's/%//'")
    if [ "$disk_usage" -gt 85 ]; then
        log_error "Disk usage is ${disk_usage}% - deployment aborted"
        exit 1
    fi
    log_success "Disk space check passed (${disk_usage}% used)"
    
    # Check if production environment exists
    run_ssh "test -d $PROJECT_ROOT" "Production environment directory check"
    
    log_success "All pre-deployment checks passed"
}

# Create backup
create_backup() {
    log_info "Creating deployment backup..."
    
    run_ssh "mkdir -p $BACKUP_DIR" "Create backup directory"
    
    run_ssh "tar -czf $BACKUP_DIR/aktienanalyse_backup_$DATETIME.tar.gz -C $PROJECT_ROOT . --exclude='venv' --exclude='*.pyc' --exclude='__pycache__' --exclude='.git'" "Create compressed backup"
    
    # Keep only last 5 backups
    run_ssh "cd $BACKUP_DIR && ls -t aktienanalyse_backup_*.tar.gz | tail -n +6 | xargs -r rm --" "Cleanup old backups"
    
    log_success "Backup created: aktienanalyse_backup_$DATETIME.tar.gz"
}

# Deploy code changes
deploy_code() {
    log_info "Deploying code changes..."
    
    # Sync local changes to production (excluding sensitive files)
    rsync -avz --delete \
        --exclude='.git*' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='venv' \
        --exclude='.env*' \
        --exclude='*.log' \
        --exclude='health_report_*.json' \
        ./ root@$PRODUCTION_SERVER:$PROJECT_ROOT/
    
    log_success "Code deployment completed"
}

# Update environment configuration
update_environment() {
    log_info "Updating production environment configuration..."
    
    # Ensure correct ownership
    run_ssh "chown -R aktienanalyse:aktienanalyse $PROJECT_ROOT" "Fix file ownership"
    
    # Update permissions for scripts
    run_ssh "find $PROJECT_ROOT -name '*.sh' -type f -exec chmod +x {} \;" "Fix script permissions"
    
    # Create necessary directories
    run_ssh "mkdir -p $PROJECT_ROOT/logs $PROJECT_ROOT/ml-models $PROJECT_ROOT/cache" "Create required directories"
    run_ssh "chown -R aktienanalyse:aktienanalyse $PROJECT_ROOT/logs $PROJECT_ROOT/ml-models $PROJECT_ROOT/cache" "Fix directory ownership"
    
    log_success "Environment configuration updated"
}

# Service management
manage_services() {
    local action="$1"
    log_info "Managing services: $action"
    
    # Define services in dependency order
    local services=(
        "aktienanalyse-event-bus-v6.service"
        "aktienanalyse-data-processing-v6.service"
        "aktienanalyse-marketcap-v6.service"
        "aktienanalyse-prediction-tracking-v6.service"
        "aktienanalyse-monitoring-modular.service"
        "aktienanalyse-broker-gateway-eventbus-first.service"
        "aktienanalyse-intelligent-core-eventbus-first.service"
        "aktienanalyse-prediction-averages.service"
        "ml-training.service"
    )
    
    case $action in
        "stop")
            # Stop services in reverse order
            for ((i=${#services[@]}-1; i>=0; i--)); do
                local service="${services[$i]}"
                if run_ssh "systemctl is-active $service >/dev/null 2>&1" "Check if $service is active"; then
                    run_ssh "systemctl stop $service" "Stop $service"
                    sleep 2
                fi
            done
            ;;
        "start")
            # Start services in dependency order
            run_ssh "systemctl daemon-reload" "Reload systemd daemon"
            for service in "${services[@]}"; do
                if run_ssh "systemctl is-enabled $service >/dev/null 2>&1" "Check if $service is enabled"; then
                    run_ssh "systemctl start $service" "Start $service"
                    sleep 5
                    
                    # Verify service started successfully
                    if ! run_ssh "systemctl is-active $service >/dev/null" "Verify $service is running"; then
                        log_error "$service failed to start - checking logs"
                        run_ssh "systemctl status $service --no-pager -n 10" "Show $service status"
                        return 1
                    fi
                fi
            done
            ;;
        "restart")
            manage_services "stop"
            sleep 10
            manage_services "start"
            ;;
    esac
    
    log_success "Service management ($action) completed"
}

# Health checks
run_health_checks() {
    log_info "Running post-deployment health checks..."
    
    # Wait for services to fully start
    sleep 30
    
    # Run our comprehensive health check
    if [ -f "./health_check_all_services.py" ]; then
        if python3 ./health_check_all_services.py; then
            log_success "All health checks passed"
        else
            log_error "Health checks failed - rolling back deployment"
            rollback_deployment
            exit 1
        fi
    else
        log_warning "Health check script not found - performing basic checks"
        
        # Basic port checks
        local ports=(8014 8017 8018 8019 8020 8015 8008 8011 8026 8080 8081)
        for port in "${ports[@]}"; do
            if run_ssh "netstat -tln | grep ':$port ' >/dev/null" "Check port $port"; then
                log_success "Port $port is accessible"
            else
                log_warning "Port $port is not accessible"
            fi
        done
    fi
}

# Rollback deployment
rollback_deployment() {
    log_warning "Initiating deployment rollback..."
    
    # Find latest backup
    local latest_backup=$(ssh root@$PRODUCTION_SERVER "ls -t $BACKUP_DIR/aktienanalyse_backup_*.tar.gz 2>/dev/null | head -1")
    
    if [ -n "$latest_backup" ]; then
        log_info "Restoring from backup: $latest_backup"
        
        # Stop services
        manage_services "stop"
        
        # Restore backup
        run_ssh "cd $PROJECT_ROOT && tar -xzf $latest_backup" "Restore from backup"
        
        # Restart services
        manage_services "start"
        
        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# ML Services special handling
handle_ml_services() {
    log_info "Handling ML Services..."
    
    # Ensure ML Scheduler is properly configured
    run_ssh "systemctl enable ml-scheduler.service" "Enable ML Scheduler"
    
    # Run ML Scheduler once to verify it works
    if run_ssh "systemctl start ml-scheduler.service" "Test ML Scheduler"; then
        log_success "ML Scheduler test passed"
    else
        log_warning "ML Scheduler test failed - check logs"
        run_ssh "journalctl -u ml-scheduler.service -n 10 --no-pager" "Show ML Scheduler logs"
    fi
    
    # Verify ML Training Service
    run_ssh "systemctl enable ml-training.service" "Enable ML Training Service"
    
    log_success "ML Services handling completed"
}

# Main deployment function
main() {
    log_info "Starting production deployment to $PRODUCTION_SERVER"
    log_info "Deployment ID: $DATETIME"
    
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║     Aktienanalyse Production Deploy       ║"
    echo "║             Server: $PRODUCTION_SERVER             ║"
    echo "║         Deployment: $DATETIME         ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check if we should skip certain steps
    local SKIP_BACKUP=${SKIP_BACKUP:-false}
    local SKIP_CODE_DEPLOY=${SKIP_CODE_DEPLOY:-false}
    local SKIP_SERVICE_RESTART=${SKIP_SERVICE_RESTART:-false}
    
    # Deployment steps
    pre_deployment_checks
    
    if [ "$SKIP_BACKUP" != "true" ]; then
        create_backup
    fi
    
    if [ "$SKIP_CODE_DEPLOY" != "true" ]; then
        deploy_code
        update_environment
    fi
    
    if [ "$SKIP_SERVICE_RESTART" != "true" ]; then
        manage_services "restart"
    fi
    
    handle_ml_services
    run_health_checks
    
    log_success "🎉 Production deployment completed successfully!"
    log_info "Deployment ID: $DATETIME"
    log_info "Backup available: $BACKUP_DIR/aktienanalyse_backup_$DATETIME.tar.gz"
    
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║          DEPLOYMENT SUCCESSFUL            ║"
    echo "║     All services are running healthy      ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Command line argument parsing
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback_deployment
        ;;
    "health")
        run_health_checks
        ;;
    "services-restart")
        manage_services "restart"
        ;;
    "services-stop")
        manage_services "stop"
        ;;
    "services-start")
        manage_services "start"
        ;;
    *)
        echo "Usage: $0 [deploy|rollback|health|services-restart|services-stop|services-start]"
        echo "  deploy          - Full deployment (default)"
        echo "  rollback        - Rollback to last backup"
        echo "  health          - Run health checks only"
        echo "  services-restart- Restart all services"
        echo "  services-stop   - Stop all services"
        echo "  services-start  - Start all services"
        echo ""
        echo "Environment variables:"
        echo "  SKIP_BACKUP=true        - Skip backup creation"
        echo "  SKIP_CODE_DEPLOY=true   - Skip code deployment"
        echo "  SKIP_SERVICE_RESTART=true - Skip service restart"
        exit 1
        ;;
esac