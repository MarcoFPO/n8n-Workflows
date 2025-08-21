#!/bin/bash
# =============================================
# ML Services Deployment Script
# Deployed alle ML-Services auf 10.1.1.174
#
# Autor: Claude Code
# Datum: 17. August 2025
# =============================================

set -euo pipefail

# Konfiguration
TARGET_HOST="10.1.1.174"
TARGET_USER="aktienanalyse"
SERVICE_DIR="/home/aktienanalyse/aktienanalyse-ökosystem"
ML_MODELS_DIR="/home/aktienanalyse/ml-models"
LOGS_DIR="/home/aktienanalyse/aktienanalyse-ökosystem/logs"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
echo "========================================"
echo "   ML Services Deployment v1.0.0"
echo "   Target: $TARGET_HOST"
echo "   User: $TARGET_USER"
echo "========================================"
echo

# SSH-Verbindung testen
log_info "Testing SSH connection to $TARGET_HOST..."

if ! ssh -o ConnectTimeout=10 "$TARGET_USER@$TARGET_HOST" "echo 'SSH connection successful'" > /dev/null 2>&1; then
    log_error "SSH connection to $TARGET_HOST failed"
    echo "Please ensure:"
    echo "  1. SSH key is properly configured"
    echo "  2. Host $TARGET_HOST is reachable"
    echo "  3. User $TARGET_USER exists on target host"
    exit 1
fi

log_success "SSH connection verified"

# Verzeichnisse auf Target erstellen
log_info "Creating directories on target host..."

ssh "$TARGET_USER@$TARGET_HOST" "
    mkdir -p $ML_MODELS_DIR/{technical,sentiment,fundamental}/{7d,30d,150d,365d}
    mkdir -p $LOGS_DIR
    mkdir -p $SERVICE_DIR/deployment/{systemd,scripts}
    chown -R $TARGET_USER:$TARGET_USER $ML_MODELS_DIR $LOGS_DIR
"

log_success "Directories created"

# Python Dependencies installieren
log_info "Installing Python dependencies on target host..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Virtual Environment erstellen falls nicht vorhanden
    if [[ ! -d $SERVICE_DIR/venv ]]; then
        python3 -m venv $SERVICE_DIR/venv
    fi
    
    # Dependencies installieren
    source $SERVICE_DIR/venv/bin/activate
    
    # ML Dependencies
    pip install --upgrade pip
    pip install tensorflow==2.15.0
    pip install scikit-learn==1.3.2
    pip install pandas==2.1.4
    pip install numpy==1.24.3
    pip install talib-binary==0.4.26
    
    # Database Dependencies
    pip install asyncpg==0.29.0
    pip install psycopg2-binary==2.9.9
    
    # Redis Dependencies
    pip install redis[hiredis]==5.0.1
    
    # Additional Dependencies
    pip install fastapi==0.104.1
    pip install uvicorn==0.24.0
    pip install pydantic==2.5.1
    pip install python-multipart==0.0.6
    pip install aiofiles==23.2.1
    pip install joblib==1.3.2
"

if [[ $? -eq 0 ]]; then
    log_success "Python dependencies installed"
else
    log_error "Failed to install Python dependencies"
    exit 1
fi

# ML Service Files synchronisieren
log_info "Synchronizing ML service files..."

# Services synchronisieren
rsync -avz --delete \
    ./services/ml-analytics-service-modular/ \
    "$TARGET_USER@$TARGET_HOST:$SERVICE_DIR/services/ml-analytics-service-modular/"

# Database Migration synchronisieren
rsync -avz \
    ./database/ \
    "$TARGET_USER@$TARGET_HOST:$SERVICE_DIR/database/"

# Deployment Files synchronisieren
rsync -avz \
    ./deployment/ \
    "$TARGET_USER@$TARGET_HOST:$SERVICE_DIR/deployment/"

log_success "Service files synchronized"

# Permissions setzen
log_info "Setting file permissions..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Executable permissions für Python Scripts
    find $SERVICE_DIR/services/ml-analytics-service-modular -name '*.py' -exec chmod +x {} \;
    
    # Executable permissions für Scripts
    chmod +x $SERVICE_DIR/deployment/scripts/*.sh
    chmod +x $SERVICE_DIR/database/*.sh
    
    # Service Files permissions
    chmod 644 $SERVICE_DIR/deployment/systemd/*.service
    chmod 644 $SERVICE_DIR/deployment/systemd/*.timer
"

log_success "File permissions set"

# systemd Services installieren
log_info "Installing systemd services..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Service Files nach systemd kopieren
    sudo cp $SERVICE_DIR/deployment/systemd/ml-analytics.service /etc/systemd/system/
    sudo cp $SERVICE_DIR/deployment/systemd/ml-training.service /etc/systemd/system/
    sudo cp $SERVICE_DIR/deployment/systemd/ml-scheduler.service /etc/systemd/system/
    sudo cp $SERVICE_DIR/deployment/systemd/ml-scheduler.timer /etc/systemd/system/
    
    # systemd reload
    sudo systemctl daemon-reload
    
    # Services enablen
    sudo systemctl enable ml-analytics.service
    sudo systemctl enable ml-training.service
    sudo systemctl enable ml-scheduler.service
    sudo systemctl enable ml-scheduler.timer
"

log_success "systemd services installed"

# ML Schema deployen (falls noch nicht geschehen)
log_info "Checking ML schema deployment..."

ssh "$TARGET_USER@$TARGET_HOST" "
    cd $SERVICE_DIR/database
    
    # Prüfen ob ML Schema bereits deployed ist
    if ! PGPASSWORD='$POSTGRES_PASSWORD' psql -h localhost -U aktienanalyse -d aktienanalyse -t -c \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'ml_features')\" 2>/dev/null | grep -q 't'; then
        echo 'ML schema not found, deploying...'
        
        # Schema deployen
        export POSTGRES_PASSWORD='aktienanalyse_2024!'
        if ./deploy-ml-schema.sh; then
            echo 'ML schema deployed successfully'
        else
            echo 'ML schema deployment failed'
            exit 1
        fi
    else
        echo 'ML schema already deployed'
    fi
"

log_success "ML schema verified"

# Environment Variables Setup
log_info "Setting up environment variables..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Environment file für ML Services erstellen
    cat > $SERVICE_DIR/.env << 'EOF'
# ML Service Configuration
ML_SERVICE_NAME=ml-analytics
ML_SERVICE_PORT=8019
ML_SERVICE_TRAINING_PORT=8020

# Database Configuration
ML_DATABASE_HOST=localhost
ML_DATABASE_PORT=5432
ML_DATABASE_NAME=aktienanalyse
ML_DATABASE_USER=ml_service
ML_DATABASE_PASSWORD=ml_service_secure_2025

# Redis Configuration
ML_REDIS_URL=redis://localhost:6379/2

# Model Storage
ML_MODEL_STORAGE_PATH=/home/aktienanalyse/ml-models

# Training Configuration
ML_TRAINING_EPOCHS=50
ML_TRAINING_BATCH_SIZE=32
ML_TRAINING_LEARNING_RATE=0.001

# Performance Configuration
ML_ENABLE_GPU=false
ML_MIXED_PRECISION=false
ML_LOG_LEVEL=INFO

# Feature Engineering
ML_FEATURE_CACHE_TTL_HOURS=6
ML_PREDICTION_CACHE_TTL_HOURS=1

# Event Bus
ML_EVENT_TTL_SECONDS=3600
ML_HEARTBEAT_INTERVAL=30
EOF

    # Source environment in bashrc
    if ! grep -q 'source.*\.env' ~/.bashrc; then
        echo 'source $SERVICE_DIR/.env' >> ~/.bashrc
    fi
"

log_success "Environment variables configured"

# Services Health Check vor Start
log_info "Performing pre-start health checks..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # PostgreSQL prüfen
    if ! systemctl is-active --quiet postgresql; then
        echo 'PostgreSQL is not active, starting...'
        sudo systemctl start postgresql
        sleep 5
    fi
    
    # Redis prüfen
    if ! systemctl is-active --quiet redis; then
        echo 'Redis is not active, starting...'
        sudo systemctl start redis
        sleep 3
    fi
    
    # Database connection testen
    if ! PGPASSWORD='ml_service_secure_2025' psql -h localhost -U ml_service -d aktienanalyse -c 'SELECT 1' > /dev/null 2>&1; then
        echo 'Database connection failed'
        exit 1
    fi
    
    # Redis connection testen
    if ! redis-cli -u 'redis://localhost:6379/2' ping > /dev/null 2>&1; then
        echo 'Redis connection failed'
        exit 1
    fi
    
    echo 'Health checks passed'
"

log_success "Pre-start health checks passed"

# ML Services starten
log_info "Starting ML services..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Services stoppen falls sie laufen
    sudo systemctl stop ml-analytics.service 2>/dev/null || true
    sudo systemctl stop ml-training.service 2>/dev/null || true
    sudo systemctl stop ml-scheduler.timer 2>/dev/null || true
    
    sleep 5
    
    # Services starten
    sudo systemctl start ml-analytics.service
    sleep 10
    
    sudo systemctl start ml-training.service
    sleep 5
    
    sudo systemctl start ml-scheduler.timer
    sleep 3
"

# Service Status prüfen
log_info "Checking service status..."

ssh "$TARGET_USER@$TARGET_HOST" "
    echo '=== Service Status ==='
    
    echo -n 'ML Analytics Service: '
    systemctl is-active ml-analytics.service
    
    echo -n 'ML Training Service: '
    systemctl is-active ml-training.service
    
    echo -n 'ML Scheduler Timer: '
    systemctl is-active ml-scheduler.timer
    
    echo
    echo '=== Service Logs (last 10 lines) ==='
    echo 'ML Analytics:'
    sudo journalctl -u ml-analytics.service --no-pager -n 10
    
    echo 'ML Training:'
    sudo journalctl -u ml-training.service --no-pager -n 10
"

log_success "Service status checked"

# Deployment-Verifikation
log_info "Performing deployment verification..."

ssh "$TARGET_USER@$TARGET_HOST" "
    # Port-Checks
    echo 'Checking service ports...'
    
    # ML Analytics Port 8019
    if ss -tuln | grep -q ':8019 '; then
        echo 'ML Analytics Service listening on port 8019'
    else
        echo 'WARNING: ML Analytics Service not listening on port 8019'
    fi
    
    # ML Training Port 8020
    if ss -tuln | grep -q ':8020 '; then
        echo 'ML Training Service listening on port 8020'
    else
        echo 'WARNING: ML Training Service not listening on port 8020'
    fi
    
    # Files Check
    echo 'Checking critical files...'
    
    if [[ -f '$SERVICE_DIR/services/ml-analytics-service-modular/ml_analytics_orchestrator_v1_0_0_20250817.py' ]]; then
        echo 'ML Analytics Orchestrator: OK'
    else
        echo 'ERROR: ML Analytics Orchestrator missing'
    fi
    
    if [[ -f '$SERVICE_DIR/services/ml-analytics-service-modular/training_service_v1_0_0_20250817.py' ]]; then
        echo 'ML Training Service: OK'
    else
        echo 'ERROR: ML Training Service missing'
    fi
    
    echo 'Deployment verification completed'
"

echo
echo "=== DEPLOYMENT SUMMARY ==="
echo "Target Host: $TARGET_HOST"
echo "Services Deployed:"
echo "  ✓ ML Analytics Service (Port 8019)"
echo "  ✓ ML Training Service (Port 8020)"
echo "  ✓ ML Scheduler Timer (Daily 02:00)"
echo
echo "Next Steps:"
echo "1. Monitor service logs: sudo journalctl -u ml-analytics.service -f"
echo "2. Test API endpoints: curl http://$TARGET_HOST:8019/health"
echo "3. Trigger manual training: systemctl start ml-scheduler.service"
echo "4. Check model storage: ls -la $ML_MODELS_DIR"
echo

log_success "ML Services deployment completed successfully!"

echo "========================================"