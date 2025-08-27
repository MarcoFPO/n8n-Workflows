#!/bin/bash
# ===============================================================================
# Enhanced Averages GUI Deployment Script v1.0.0
# Deployment der Durchschnittswerte-Integration für KI-Prognosen GUI
# 
# CLEAN ARCHITECTURE DEPLOYMENT:
# 1. Database Migration (PostgreSQL Schema Update)
# 2. Enhanced Backend Service (Prediction-Tracking v6.2.0)
# 3. Enhanced Frontend Service (v8.1.0)
# 4. Service Health Validation
# 5. Performance Testing
#
# Autor: Claude Code
# Datum: 26. August 2025
# Version: 1.0.0
# ===============================================================================

set -euo pipefail  # Strict error handling

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_LOG="/opt/aktienanalyse-ökosystem/logs/enhanced_averages_deployment.log"
DATABASE_HOST="${DB_HOST:-localhost}"
DATABASE_NAME="${DB_NAME:-aktienanalyse}"
DATABASE_USER="${DB_USER:-aktienanalyse}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"
PREDICTION_TRACKING_PORT="${PREDICTION_TRACKING_PORT:-8018}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$DEPLOYMENT_LOG"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" | tee -a "$DEPLOYMENT_LOG"
    exit 1
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}" | tee -a "$DEPLOYMENT_LOG"
}

info() {
    echo -e "${BLUE}INFO: $1${NC}" | tee -a "$DEPLOYMENT_LOG"
}

warning() {
    echo -e "${YELLOW}WARNING: $1${NC}" | tee -a "$DEPLOYMENT_LOG"
}

# ===============================================================================
# PREREQUISITE CHECKS
# ===============================================================================

check_prerequisites() {
    info "🔍 Checking deployment prerequisites..."
    
    # Check PostgreSQL connection
    if ! command -v psql &> /dev/null; then
        error "PostgreSQL client (psql) not found"
    fi
    
    # Test database connection
    if ! PGPASSWORD="aktienanalyse2024" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c "SELECT 1;" &> /dev/null; then
        error "Cannot connect to PostgreSQL database"
    fi
    
    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        error "Python3 not found"
    fi
    
    # Check required Python packages
    if ! python3 -c "import asyncpg, fastapi, uvicorn" &> /dev/null; then
        warning "Some Python packages may be missing. Installing..."
        pip3 install asyncpg fastapi uvicorn aiohttp --quiet || error "Failed to install Python packages"
    fi
    
    # Create log directory
    mkdir -p "$(dirname "$DEPLOYMENT_LOG")"
    
    success "Prerequisites check completed"
}

# ===============================================================================
# DATABASE MIGRATION
# ===============================================================================

deploy_database_migration() {
    info "🗄️ Deploying database migration for enhanced averages..."
    
    local migration_file="$SCRIPT_DIR/database/migrations/enhanced_predictions_averages_gui_v1_0_0.sql"
    
    if [[ ! -f "$migration_file" ]]; then
        error "Migration file not found: $migration_file"
    fi
    
    # Create backup first
    local backup_file="/tmp/aktienanalyse_backup_$(date +%Y%m%d_%H%M%S).sql"
    info "Creating database backup: $backup_file"
    
    PGPASSWORD="aktienanalyse2024" pg_dump -h "$DATABASE_HOST" -U "$DATABASE_USER" "$DATABASE_NAME" > "$backup_file" || error "Database backup failed"
    
    # Apply migration
    info "Applying enhanced averages migration..."
    PGPASSWORD="aktienanalyse2024" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -f "$migration_file" || error "Migration failed"
    
    # Verify migration
    local test_query="SELECT COUNT(*) FROM mv_ki_prognosen_averages;"
    if PGPASSWORD="aktienanalyse2024" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c "$test_query" &> /dev/null; then
        success "Database migration completed successfully"
    else
        error "Migration verification failed"
    fi
}

# ===============================================================================
# ENHANCED BACKEND SERVICE DEPLOYMENT
# ===============================================================================

deploy_enhanced_backend() {
    info "🚀 Deploying Enhanced Prediction-Tracking Service v6.2.0..."
    
    local service_file="$SCRIPT_DIR/services/prediction-tracking-service/main_v6_2_0_enhanced_averages.py"
    local service_target="/opt/aktienanalyse-ökosystem/services/prediction-tracking-service/main_enhanced.py"
    
    if [[ ! -f "$service_file" ]]; then
        error "Enhanced backend service file not found: $service_file"
    fi
    
    # Stop existing service if running
    if systemctl is-active --quiet prediction-tracking-service; then
        info "Stopping existing prediction-tracking service..."
        sudo systemctl stop prediction-tracking-service || warning "Failed to stop existing service"
    fi
    
    # Deploy new service
    sudo cp "$service_file" "$service_target" || error "Failed to copy enhanced backend service"
    sudo chown aktienanalyse:aktienanalyse "$service_target"
    sudo chmod +x "$service_target"
    
    # Create enhanced systemd service file
    cat > /tmp/enhanced-prediction-tracking.service << EOF
[Unit]
Description=Enhanced Prediction Tracking Service v6.2.0 - Durchschnittswerte
After=network.target postgresql.service

[Service]
Type=exec
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/prediction-tracking-service
ExecStart=/usr/bin/python3 main_enhanced.py
Restart=always
RestartSec=10
Environment=DB_HOST=${DATABASE_HOST}
Environment=DB_NAME=${DATABASE_NAME}  
Environment=DB_USER=${DATABASE_USER}
Environment=DB_PASSWORD=aktienanalyse2024
Environment=SERVICE_PORT=${PREDICTION_TRACKING_PORT}
Environment=LOG_LEVEL=INFO
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/enhanced-prediction-tracking.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable enhanced-prediction-tracking.service
    
    success "Enhanced backend service deployed"
}

# ===============================================================================
# ENHANCED FRONTEND SERVICE DEPLOYMENT
# ===============================================================================

deploy_enhanced_frontend() {
    info "🖥️ Deploying Enhanced Frontend Service v8.1.0..."
    
    local frontend_file="$SCRIPT_DIR/services/frontend-service/main_v8_1_0_enhanced_averages.py"
    local frontend_target="/opt/aktienanalyse-ökosystem/services/frontend-service/main_enhanced.py"
    
    if [[ ! -f "$frontend_file" ]]; then
        error "Enhanced frontend service file not found: $frontend_file"
    fi
    
    # Stop existing frontend service if running
    if systemctl is-active --quiet aktienanalyse-frontend; then
        info "Stopping existing frontend service..."
        sudo systemctl stop aktienanalyse-frontend || warning "Failed to stop existing frontend service"
    fi
    
    # Deploy new frontend
    sudo cp "$frontend_file" "$frontend_target" || error "Failed to copy enhanced frontend service"
    sudo chown aktienanalyse:aktienanalyse "$frontend_target"
    sudo chmod +x "$frontend_target"
    
    # Update systemd service file for enhanced frontend
    cat > /tmp/enhanced-aktienanalyse-frontend.service << EOF
[Unit]
Description=Enhanced Aktienanalyse Frontend Service v8.1.0 - Durchschnittswerte Integration
After=network.target enhanced-prediction-tracking.service

[Service]
Type=exec
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/frontend-service
ExecStart=/usr/bin/python3 main_enhanced.py
Restart=always
RestartSec=5
Environment=FRONTEND_PORT=${FRONTEND_PORT}
Environment=FRONTEND_HOST=0.0.0.0
Environment=ENHANCED_PREDICTION_TRACKING_URL=http://localhost:${PREDICTION_TRACKING_PORT}
Environment=LOG_LEVEL=INFO
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo mv /tmp/enhanced-aktienanalyse-frontend.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable enhanced-aktienanalyse-frontend.service
    
    success "Enhanced frontend service deployed"
}

# ===============================================================================
# SERVICE STARTUP & VALIDATION
# ===============================================================================

start_enhanced_services() {
    info "🔄 Starting enhanced services..."
    
    # Start backend service first
    info "Starting enhanced prediction-tracking service..."
    sudo systemctl start enhanced-prediction-tracking.service || error "Failed to start enhanced backend service"
    
    # Wait for backend to be ready
    local backend_ready=false
    for i in {1..30}; do
        if curl -s "http://localhost:${PREDICTION_TRACKING_PORT}/health" > /dev/null; then
            backend_ready=true
            break
        fi
        info "Waiting for enhanced backend service to be ready... ($i/30)"
        sleep 2
    done
    
    if [[ "$backend_ready" == false ]]; then
        error "Enhanced backend service failed to start within 60 seconds"
    fi
    
    # Start frontend service
    info "Starting enhanced frontend service..."
    sudo systemctl start enhanced-aktienanalyse-frontend.service || error "Failed to start enhanced frontend service"
    
    # Wait for frontend to be ready
    local frontend_ready=false
    for i in {1..15}; do
        if curl -s "http://localhost:${FRONTEND_PORT}/health" > /dev/null; then
            frontend_ready=true
            break
        fi
        info "Waiting for enhanced frontend service to be ready... ($i/15)"
        sleep 2
    done
    
    if [[ "$frontend_ready" == false ]]; then
        error "Enhanced frontend service failed to start within 30 seconds"
    fi
    
    success "Enhanced services started successfully"
}

# ===============================================================================
# HEALTH VALIDATION
# ===============================================================================

validate_deployment() {
    info "✅ Validating enhanced deployment..."
    
    # Test backend health
    local backend_health
    backend_health=$(curl -s "http://localhost:${PREDICTION_TRACKING_PORT}/health" | jq -r '.status' 2>/dev/null || echo "error")
    if [[ "$backend_health" != "healthy" ]]; then
        error "Enhanced backend service health check failed"
    fi
    
    # Test frontend health
    local frontend_health  
    frontend_health=$(curl -s "http://localhost:${FRONTEND_PORT}/health" | jq -r '.status' 2>/dev/null || echo "error")
    if [[ "$frontend_health" != "healthy" ]]; then
        error "Enhanced frontend service health check failed"
    fi
    
    # Test enhanced predictions endpoint
    info "Testing enhanced predictions endpoint..."
    local predictions_response
    predictions_response=$(curl -s "http://localhost:${PREDICTION_TRACKING_PORT}/api/v1/data/predictions?timeframe=1M" 2>/dev/null || echo "error")
    if [[ "$predictions_response" == "error" ]]; then
        warning "Enhanced predictions endpoint test failed - may be expected if no data"
    else
        # Check for enhanced features
        if echo "$predictions_response" | jq -e '.enhanced_features.averages_support' > /dev/null 2>&1; then
            success "Enhanced predictions with averages support confirmed"
        else
            warning "Enhanced predictions endpoint working but averages support not confirmed"
        fi
    fi
    
    # Test frontend GUI
    info "Testing enhanced frontend GUI..."
    local gui_response
    gui_response=$(curl -s "http://localhost:${FRONTEND_PORT}/prognosen" 2>/dev/null || echo "error")
    if [[ "$gui_response" == "error" ]]; then
        error "Enhanced frontend GUI test failed"
    else
        if echo "$gui_response" | grep -q "Durchschnittswerte"; then
            success "Enhanced GUI with Durchschnittswerte confirmed"
        else
            warning "Enhanced GUI working but Durchschnittswerte feature not confirmed"
        fi
    fi
    
    success "Deployment validation completed"
}

# ===============================================================================
# PERFORMANCE TESTING
# ===============================================================================

performance_test() {
    info "⚡ Running performance tests..."
    
    # Test database query performance
    info "Testing database query performance..."
    local db_query_time
    db_query_time=$(PGPASSWORD="aktienanalyse2024" psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c "
        \\timing on
        SELECT * FROM get_ki_prognosen_with_averages('1M', 15);
        " 2>&1 | grep "Time:" | awk '{print $2}' || echo "unknown")
    info "Database query time: $db_query_time"
    
    # Test API response times
    info "Testing API response times..."
    local api_start api_end api_time
    api_start=$(date +%s.%N)
    curl -s "http://localhost:${PREDICTION_TRACKING_PORT}/api/v1/data/predictions?timeframe=1M" > /dev/null
    api_end=$(date +%s.%N)
    api_time=$(echo "$api_end - $api_start" | bc -l | xargs printf "%.3f")
    info "API response time: ${api_time}s"
    
    if (( $(echo "$api_time > 2.0" | bc -l) )); then
        warning "API response time is slower than expected (${api_time}s > 2.0s)"
    else
        success "API response time is acceptable (${api_time}s)"
    fi
    
    # Test GUI load times
    info "Testing GUI load times..."
    local gui_start gui_end gui_time
    gui_start=$(date +%s.%N)
    curl -s "http://localhost:${FRONTEND_PORT}/prognosen" > /dev/null
    gui_end=$(date +%s.%N)
    gui_time=$(echo "$gui_end - $gui_start" | bc -l | xargs printf "%.3f")
    info "GUI load time: ${gui_time}s"
    
    if (( $(echo "$gui_time > 3.0" | bc -l) )); then
        warning "GUI load time is slower than expected (${gui_time}s > 3.0s)"
    else
        success "GUI load time is acceptable (${gui_time}s)"
    fi
    
    success "Performance tests completed"
}

# ===============================================================================
# MAIN DEPLOYMENT FUNCTION
# ===============================================================================

main() {
    info "🚀 Starting Enhanced Averages GUI Deployment v1.0.0"
    info "📊 Features: KI-Prognosen mit Durchschnittswerten, Timeline-Navigation, Enhanced UI"
    
    log "=============================================================================="
    log "ENHANCED AVERAGES GUI DEPLOYMENT - $(date)"
    log "=============================================================================="
    
    check_prerequisites
    deploy_database_migration
    deploy_enhanced_backend
    deploy_enhanced_frontend
    start_enhanced_services
    validate_deployment
    performance_test
    
    success "🎉 Enhanced Averages GUI Deployment completed successfully!"
    info "📊 GUI URL: http://localhost:${FRONTEND_PORT}/prognosen"
    info "🔧 API URL: http://localhost:${PREDICTION_TRACKING_PORT}/api/v1/data/predictions"
    info "📋 View logs: sudo journalctl -u enhanced-prediction-tracking.service -f"
    info "📋 View logs: sudo journalctl -u enhanced-aktienanalyse-frontend.service -f"
    
    log "=============================================================================="
    log "DEPLOYMENT COMPLETED SUCCESSFULLY - $(date)"
    log "=============================================================================="
}

# ===============================================================================
# ERROR HANDLING
# ===============================================================================

cleanup_on_error() {
    error "Deployment failed. Attempting cleanup..."
    
    # Stop services if they were started
    sudo systemctl stop enhanced-prediction-tracking.service 2>/dev/null || true
    sudo systemctl stop enhanced-aktienanalyse-frontend.service 2>/dev/null || true
    
    # Disable services
    sudo systemctl disable enhanced-prediction-tracking.service 2>/dev/null || true
    sudo systemctl disable enhanced-aktienanalyse-frontend.service 2>/dev/null || true
    
    # Remove systemd files
    sudo rm -f /etc/systemd/system/enhanced-prediction-tracking.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/enhanced-aktienanalyse-frontend.service 2>/dev/null || true
    sudo systemctl daemon-reload
    
    error "Cleanup completed. Check logs for details: $DEPLOYMENT_LOG"
}

# Set error trap
trap cleanup_on_error ERR

# ===============================================================================
# SCRIPT EXECUTION
# ===============================================================================

# Check if script is run as root or with sudo capabilities
if [[ $EUID -eq 0 ]]; then
    error "This script should not be run as root directly. Use a user with sudo privileges."
fi

# Verify sudo access
if ! sudo -n true 2>/dev/null; then
    error "This script requires sudo privileges. Please run with a user that has sudo access."
fi

# Run main function
main "$@"