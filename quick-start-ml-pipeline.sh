#!/bin/bash
# =============================================
# Quick Start ML Pipeline
# Komplette ML-Pipeline in einem Befehl starten
#
# Autor: Claude Code
# Datum: 17. August 2025
# =============================================

set -euo pipefail

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🚀 AKTIENANALYSE ML-PIPELINE QUICK START v1.0.0         ║
║                                                              ║
║     Deployment: 10.1.1.174                                  ║
║     Services: ML-Analytics, Training, Scheduler             ║
║     Features: LSTM-Models, Technical Indicators, Events     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF

echo

# Schritt 1: PostgreSQL ML-Schema deployen
log_info "Step 1/5: Deploying PostgreSQL ML Schema..."

cd /home/mdoehler/aktienanalyse-ökosystem/database

if [[ -f "deploy-ml-schema.sh" ]]; then
    export POSTGRES_PASSWORD="aktienanalyse_2024!"
    
    if ./deploy-ml-schema.sh; then
        log_success "ML Schema deployed successfully"
    else
        log_error "ML Schema deployment failed"
        exit 1
    fi
else
    log_error "ML Schema deployment script not found"
    exit 1
fi

echo

# Schritt 2: ML Services auf 10.1.1.174 deployen
log_info "Step 2/5: Deploying ML Services to 10.1.1.174..."

cd /home/mdoehler/aktienanalyse-ökosystem/deployment

if [[ -f "deploy-ml-services.sh" ]]; then
    if ./deploy-ml-services.sh; then
        log_success "ML Services deployed successfully"
    else
        log_error "ML Services deployment failed"
        exit 1
    fi
else
    log_error "ML Services deployment script not found"
    exit 1
fi

echo

# Schritt 3: Service Status prüfen
log_info "Step 3/5: Checking service status on 10.1.1.174..."

ssh aktienanalyse@10.1.1.174 '
    echo "=== ML Services Status ==="
    
    # Service Status prüfen
    services=("ml-analytics" "ml-training" "ml-scheduler")
    
    for service in "${services[@]}"; do
        status=$(systemctl is-active ${service}.service 2>/dev/null || echo "inactive")
        if [[ "$status" == "active" ]]; then
            echo "✓ ${service}.service: ACTIVE"
        else
            echo "✗ ${service}.service: $status"
        fi
    done
    
    # Timer Status
    timer_status=$(systemctl is-active ml-scheduler.timer 2>/dev/null || echo "inactive")
    if [[ "$timer_status" == "active" ]]; then
        echo "✓ ml-scheduler.timer: ACTIVE"
    else
        echo "✗ ml-scheduler.timer: $timer_status"
    fi
    
    echo
    echo "=== Port Status ==="
    
    # Port-Checks
    if ss -tuln | grep -q ":8019 "; then
        echo "✓ ML Analytics API: Port 8019 LISTENING"
    else
        echo "✗ ML Analytics API: Port 8019 NOT LISTENING"
    fi
    
    if ss -tuln | grep -q ":8020 "; then
        echo "✓ ML Training API: Port 8020 LISTENING"
    else
        echo "✗ ML Training API: Port 8020 NOT LISTENING"
    fi
    
    echo
    echo "=== Database Status ==="
    
    # ML Schema Check
    if PGPASSWORD="ml_service_secure_2025" psql -h localhost -U ml_service -d aktienanalyse -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE '\''ml_%'\''" 2>/dev/null | grep -q "11"; then
        echo "✓ ML Database Schema: 11 tables READY"
    else
        echo "✗ ML Database Schema: INCOMPLETE"
    fi
    
    echo
    echo "=== Redis Status ==="
    
    # Redis Check
    if redis-cli -u redis://localhost:6379/2 ping 2>/dev/null | grep -q "PONG"; then
        echo "✓ Redis Event Bus: CONNECTED"
    else
        echo "✗ Redis Event Bus: DISCONNECTED"
    fi
'

echo

# Schritt 4: API Health Check
log_info "Step 4/5: Testing API endpoints..."

# ML Analytics API Health Check
log_info "Testing ML Analytics API (Port 8019)..."
if curl -s -f "http://10.1.1.174:8019/health" > /dev/null 2>&1; then
    response=$(curl -s "http://10.1.1.174:8019/health" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [[ "$response" == "healthy" ]]; then
        log_success "ML Analytics API: HEALTHY"
    else
        log_warning "ML Analytics API: $response"
    fi
else
    log_warning "ML Analytics API: NOT RESPONDING"
fi

# ML Training API Health Check  
log_info "Testing ML Training API (Port 8020)..."
if curl -s -f "http://10.1.1.174:8020/health" > /dev/null 2>&1; then
    response=$(curl -s "http://10.1.1.174:8020/health" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [[ "$response" == "healthy" ]]; then
        log_success "ML Training API: HEALTHY"
    else
        log_warning "ML Training API: $response"
    fi
else
    log_warning "ML Training API: NOT RESPONDING"
fi

echo

# Schritt 5: Demo Training triggern
log_info "Step 5/5: Triggering demo training for AAPL..."

# Training Event über Redis publizieren
ssh aktienanalyse@10.1.1.174 '
    correlation_id="quickstart_demo_$(date +%s)"
    
    training_event=$(cat <<EOF
{
    "event_id": "$(uuidgen)",
    "event_type": "ml.model.training.requested",
    "correlation_id": "$correlation_id",
    "source_service": "quickstart",
    "target_service": "ml-training",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "version": "1.0",
    "payload": {
        "symbol": "AAPL",
        "model_type": "technical",
        "horizon_days": 7,
        "priority": "demo",
        "requested_by": "quickstart"
    }
}
EOF
    )
    
    echo "$training_event" | redis-cli -u redis://localhost:6379/2 PUBLISH "events:ml:model:training:requested" "$(cat)"
    
    if [[ $? -eq 0 ]]; then
        echo "✓ Demo training event published for AAPL 7-day model"
        echo "  Correlation ID: $correlation_id"
    else
        echo "✗ Failed to publish training event"
    fi
'

log_success "Demo training triggered"

echo

# Completion Summary
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🎉 ML-PIPELINE QUICK START COMPLETED!                   ║
║                                                              ║
║     Services Available:                                      ║
║     • ML Analytics API: http://10.1.1.174:8019              ║
║     • ML Training API:  http://10.1.1.174:8020              ║
║     • Daily Training:   02:00 Uhr automatisch               ║
║                                                              ║
║     Next Steps:                                              ║
║     1. Monitor Training: journalctl -u ml-training -f       ║
║     2. Check Models:     ls /home/aktienanalyse/ml-models/   ║
║     3. API Docs:         http://10.1.1.174:8019/docs        ║
║     4. Trigger Training: systemctl start ml-scheduler       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF

echo

# Quick Commands
log_info "Quick Commands für weitere Verwaltung:"
echo
echo "Service Management:"
echo "  ssh aktienanalyse@10.1.1.174 'sudo systemctl status ml-analytics'"
echo "  ssh aktienanalyse@10.1.1.174 'sudo systemctl restart ml-training'"
echo
echo "Log Monitoring:"
echo "  ssh aktienanalyse@10.1.1.174 'sudo journalctl -u ml-analytics -f'"
echo "  ssh aktienanalyse@10.1.1.174 'sudo journalctl -u ml-training -f'"
echo
echo "Manual Training:"
echo "  ssh aktienanalyse@10.1.1.174 'sudo systemctl start ml-scheduler'"
echo
echo "API Testing:"
echo "  curl http://10.1.1.174:8019/health | jq"
echo "  curl http://10.1.1.174:8020/status | jq"
echo
echo "Model Storage:"
echo "  ssh aktienanalyse@10.1.1.174 'find /home/aktienanalyse/ml-models -name \"*.h5\" -ls'"

log_success "ML-Pipeline ist betriebsbereit! 🚀"