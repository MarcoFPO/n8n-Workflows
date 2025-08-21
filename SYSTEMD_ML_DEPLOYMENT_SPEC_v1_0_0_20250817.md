# 🚀 systemd ML-Deployment Spezifikation v1.0.0

**Deployment**: systemd Integration für ML-Services  
**Version**: 1.0.0  
**Datum**: 17. August 2025  
**Target**: 10.1.1.174 (LXC 174)  
**Integration**: Bestehende systemd-Architektur erweitern  

---

## 📋 **systemd Services Übersicht**

### **Bestehende Services (8 Services - bleiben unverändert):**
```bash
# Bestehende Production Services
● aktienanalyse-intelligent-core-eventbus-first.service
● aktienanalyse-broker-gateway-eventbus-first.service  
● aktienanalyse-frontend.service
● aktienanalyse-event-bus-modular.service
● aktienanalyse-monitoring-modular.service
● aktienanalyse-diagnostic.service
● aktienanalyse-data-processing-modular.service
● aktienanalyse-prediction-tracking.service
```

### **Neue ML-Services (3 Neue Services):**
```bash
# Neue ML-Services
● aktienanalyse-ml-analytics-modular.service        # ML Analytics Service (Port 8019)
● aktienanalyse-ml-training-pipeline.service        # ML Training Pipeline (On-Demand)
● aktienanalyse-ml-model-validator.service          # ML Model Validation (Scheduled)
```

### **Neue systemd Timers (2 Timer):**
```bash
# Automated ML Operations
● aktienanalyse-ml-training-pipeline.timer          # Wöchentliches Retraining
● aktienanalyse-ml-model-validator.timer            # Tägliche Model-Validation
```

---

## 🔧 **ML Analytics Service Configuration**

### **aktienanalyse-ml-analytics-modular.service**
```ini
[Unit]
Description=Aktienanalyse ML Analytics Service v1.0.0
Documentation=https://docs.aktienanalyse.local/ml-analytics
After=network.target postgresql.service redis.service aktienanalyse-event-bus-modular.service
Wants=network.target
Requires=postgresql.service redis.service
PartOf=aktienanalyse-ecosystem.target

[Service]
# Service Type
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem

# Environment Setup
Environment=PATH=/opt/aktienanalyse-ökosystem/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=PYTHONUNBUFFERED=1

# Service Configuration
Environment=ML_SERVICE_PORT=8019
Environment=ML_SERVICE_HOST=0.0.0.0
Environment=ML_SERVICE_NAME=ml-analytics
Environment=ML_SERVICE_VERSION=1.0.0

# Database Configuration
Environment=DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_events
Environment=ML_DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_ml

# Event-Bus Configuration
Environment=EVENT_BUS_REDIS_URL=redis://localhost:6379/2
Environment=ML_REDIS_CACHE_URL=redis://localhost:6379/3
Environment=EVENT_BUS_CONSUMER_GROUP=ml-analytics-group

# ML-Specific Configuration
Environment=ML_MODEL_STORAGE_PATH=/opt/aktienanalyse-ökosystem/models
Environment=ML_FEATURE_CACHE_TTL_HOURS=2
Environment=ML_PREDICTION_CACHE_TTL_HOURS=6
Environment=ML_TRAINING_DATA_RETENTION_DAYS=730

# Performance Configuration
Environment=ML_MAX_CONCURRENT_PREDICTIONS=50
Environment=ML_BATCH_SIZE=32
Environment=ML_INFERENCE_TIMEOUT_SECONDS=30

# CUDA Configuration (falls GPU verfügbar)
Environment=CUDA_VISIBLE_DEVICES=0
Environment=TF_CPP_MIN_LOG_LEVEL=2

# Security Configuration
Environment=ML_API_KEY_REQUIRED=false
Environment=ML_CORS_ENABLED=true
Environment=ML_CORS_ORIGINS=http://localhost:8080,https://10.1.1.174

# Executable
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python \
          services/ml-analytics-service-modular/ml_analytics_orchestrator_v1_0_0_20250817.py

# Resource Limits
MemoryLimit=2G
MemoryHigh=1.8G
CPUQuota=200%
TasksMax=500

# File Limits
LimitNOFILE=65536
LimitNPROC=4096

# Auto-Restart Configuration
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# Graceful Shutdown
TimeoutStartSec=60
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

# Logging Configuration
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aktienanalyse-ml-analytics
SyslogLevel=info

# Security Restrictions
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/models
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs
ReadWritePaths=/tmp

# Network Security
PrivateNetwork=false
IPAddressDeny=any
IPAddressAllow=localhost
IPAddressAllow=10.1.1.0/24

[Install]
WantedBy=multi-user.target
WantedBy=aktienanalyse-ecosystem.target
```

---

## 🎯 **ML Training Pipeline Service**

### **aktienanalyse-ml-training-pipeline.service**
```ini
[Unit]
Description=Aktienanalyse ML Training Pipeline v1.0.0
Documentation=https://docs.aktienanalyse.local/ml-training
After=network.target postgresql.service aktienanalyse-ml-analytics-modular.service
Requires=postgresql.service
PartOf=aktienanalyse-ecosystem.target

[Service]
# Service Type (OneShot für Training-Jobs)
Type=oneshot
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem

# Environment Setup
Environment=PATH=/opt/aktienanalyse-ökosystem/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=PYTHONUNBUFFERED=1

# Training Configuration
Environment=ML_TRAINING_MODE=scheduled
Environment=ML_TRAINING_MODEL_TYPES=technical,sentiment,fundamental
Environment=ML_TRAINING_HORIZONS=7,30,150,365
Environment=ML_TRAINING_SYMBOLS=all

# Database Configuration
Environment=DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_events
Environment=ML_DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_ml

# Training Data Configuration
Environment=ML_TRAINING_DATA_START_DAYS_AGO=730
Environment=ML_TRAINING_VALIDATION_SPLIT=0.15
Environment=ML_TRAINING_TEST_SPLIT=0.15

# Performance Configuration
Environment=ML_TRAINING_BATCH_SIZE=64
Environment=ML_TRAINING_EPOCHS=100
Environment=ML_TRAINING_EARLY_STOPPING=true
Environment=ML_TRAINING_PATIENCE=10

# Hyperparameter Optimization
Environment=ML_HYPEROPT_ENABLED=true
Environment=ML_HYPEROPT_TRIALS=50
Environment=ML_HYPEROPT_TIMEOUT_HOURS=2

# Model Selection
Environment=ML_DEPLOYMENT_THRESHOLD_IMPROVEMENT=0.02
Environment=ML_DEPLOYMENT_AUTO_DEPLOY=true

# CUDA Configuration
Environment=CUDA_VISIBLE_DEVICES=0
Environment=TF_FORCE_GPU_ALLOW_GROWTH=true

# Executable
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python \
          services/ml-analytics-service-modular/training/scheduled_training_v1_0_0_20250817.py

# Resource Limits (Höher für Training)
MemoryLimit=4G
MemoryHigh=3.5G
CPUQuota=400%
TasksMax=1000

# Timeouts (Training kann lange dauern)
TimeoutStartSec=300
TimeoutStopSec=60

# No Restart (OneShot Service)
Restart=no

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aktienanalyse-ml-training
SyslogLevel=info

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/models
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
```

### **aktienanalyse-ml-training-pipeline.timer**
```ini
[Unit]
Description=ML Training Pipeline Timer
Documentation=https://docs.aktienanalyse.local/ml-training-schedule
Requires=aktienanalyse-ml-training-pipeline.service

[Timer]
# Wöchentliches Retraining - Sonntags um 02:00
OnCalendar=Sun 02:00:00
Persistent=true
RandomizedDelaySec=1800

# Prevent overlap
AccuracySec=60

[Install]
WantedBy=timers.target
```

---

## 🔍 **ML Model Validator Service**

### **aktienanalyse-ml-model-validator.service**
```ini
[Unit]
Description=Aktienanalyse ML Model Validator v1.0.0
Documentation=https://docs.aktienanalyse.local/ml-validation
After=network.target postgresql.service aktienanalyse-ml-analytics-modular.service
Requires=postgresql.service
PartOf=aktienanalyse-ecosystem.target

[Service]
# Service Type
Type=oneshot
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem

# Environment Setup
Environment=PATH=/opt/aktienanalyse-ökosystem/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=PYTHONUNBUFFERED=1

# Validation Configuration
Environment=ML_VALIDATION_MODE=scheduled
Environment=ML_VALIDATION_LOOKBACK_DAYS=7
Environment=ML_VALIDATION_MIN_PREDICTIONS=10

# Database Configuration
Environment=DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_events
Environment=ML_DATABASE_URL=postgresql://aktienanalyse:${POSTGRES_PASSWORD}@localhost/aktienanalyse_ml

# Performance Thresholds
Environment=ML_VALIDATION_DA_THRESHOLD_7D=0.60
Environment=ML_VALIDATION_DA_THRESHOLD_30D=0.58
Environment=ML_VALIDATION_DA_THRESHOLD_150D=0.55
Environment=ML_VALIDATION_DA_THRESHOLD_365D=0.52

# Alert Configuration
Environment=ML_VALIDATION_ALERT_ENABLED=true
Environment=ML_VALIDATION_ALERT_WEBHOOK=http://localhost:8015/api/alerts/ml

# Executable
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python \
          services/ml-analytics-service-modular/validation/model_validator_v1_0_0_20250817.py

# Resource Limits
MemoryLimit=1G
CPUQuota=100%

# Timeouts
TimeoutStartSec=120
TimeoutStopSec=30

# No Restart
Restart=no

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aktienanalyse-ml-validator
SyslogLevel=info

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/opt/aktienanalyse-ökosystem/models

[Install]
WantedBy=multi-user.target
```

### **aktienanalyse-ml-model-validator.timer**
```ini
[Unit]
Description=ML Model Validator Timer
Documentation=https://docs.aktienanalyse.local/ml-validation-schedule
Requires=aktienanalyse-ml-model-validator.service

[Timer]
# Tägliche Validierung - 06:00 Uhr
OnCalendar=*-*-* 06:00:00
Persistent=true
RandomizedDelaySec=600

# Prevent overlap
AccuracySec=60

[Install]
WantedBy=timers.target
```

---

## 🎯 **Ecosystem Target Configuration**

### **aktienanalyse-ecosystem.target**
```ini
[Unit]
Description=Aktienanalyse Complete Ecosystem (ML Enhanced)
Documentation=https://docs.aktienanalyse.local/
Wants=aktienanalyse-intelligent-core-eventbus-first.service
Wants=aktienanalyse-broker-gateway-eventbus-first.service
Wants=aktienanalyse-frontend.service
Wants=aktienanalyse-event-bus-modular.service
Wants=aktienanalyse-monitoring-modular.service
Wants=aktienanalyse-diagnostic.service
Wants=aktienanalyse-data-processing-modular.service
Wants=aktienanalyse-prediction-tracking.service
Wants=aktienanalyse-ml-analytics-modular.service

[Install]
WantedBy=multi-user.target
```

---

## 📊 **Environment Variables Management**

### **ML Environment Variables File**
```bash
# /opt/aktienanalyse-ökosystem/config/ml-environment.conf

# Database Configuration
POSTGRES_PASSWORD=secure_ml_password_2025
ML_DATABASE_NAME=aktienanalyse_ml

# Redis Configuration  
REDIS_ML_PASSWORD=secure_redis_ml_password_2025

# Model Storage
ML_MODEL_STORAGE_PATH=/opt/aktienanalyse-ökosystem/models
ML_MODEL_BACKUP_PATH=/opt/aktienanalyse-ökosystem/models/backups

# API Keys (falls externe APIs verwendet werden)
ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_KEY}
NEWSAPI_API_KEY=${NEWSAPI_KEY}
REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}

# Performance Tuning
ML_TENSORFLOW_INTRA_OP_PARALLELISM=4
ML_TENSORFLOW_INTER_OP_PARALLELISM=2
ML_NUMPY_NUM_THREADS=4

# Monitoring
ML_METRICS_ENABLED=true
ML_METRICS_PORT=9090
ML_HEALTH_CHECK_INTERVAL_SECONDS=30

# Debugging
ML_DEBUG_MODE=false
ML_LOG_LEVEL=INFO
ML_PROFILING_ENABLED=false
```

### **Environment Loading in Services**
```ini
# In allen ML Service-Files hinzufügen:
EnvironmentFile=-/opt/aktienanalyse-ökosystem/config/ml-environment.conf
EnvironmentFile=-/opt/aktienanalyse-ökosystem/config/global-environment.conf
```

---

## 🔄 **Service Dependencies und Start-Reihenfolge**

### **Start-Dependency-Graph:**
```
1. postgresql.service
2. redis.service
   ↓
3. aktienanalyse-event-bus-modular.service
   ↓
4. aktienanalyse-data-processing-modular.service
   ↓
5. aktienanalyse-ml-analytics-modular.service
   ↓
6. aktienanalyse-intelligent-core-eventbus-first.service
7. aktienanalyse-frontend.service
8. [Andere bestehende Services parallel]
```

### **Service-Override für ML-Dependencies**
```bash
# Bestehende Services erweitern um ML-Dependencies

# /etc/systemd/system/aktienanalyse-intelligent-core-eventbus-first.service.d/ml-dependencies.conf
[Unit]
After=aktienanalyse-ml-analytics-modular.service
Wants=aktienanalyse-ml-analytics-modular.service

# /etc/systemd/system/aktienanalyse-frontend.service.d/ml-dependencies.conf  
[Unit]
After=aktienanalyse-ml-analytics-modular.service
Wants=aktienanalyse-ml-analytics-modular.service
```

---

## 🏥 **Health-Check Integration**

### **ML Health-Check Service**
```bash
#!/bin/bash
# /opt/aktienanalyse-ökosystem/scripts/ml-health-check.sh

set -euo pipefail

# Configuration
ML_ANALYTICS_URL="http://localhost:8019"
HEALTH_CHECK_TIMEOUT=10
LOG_FILE="/var/log/aktienanalyse/ml-health.log"

# Function: Log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function: Check ML Analytics Service
check_ml_analytics() {
    local response
    local status_code
    
    response=$(curl -s -w "%{http_code}" -m "$HEALTH_CHECK_TIMEOUT" "$ML_ANALYTICS_URL/health" || echo "000")
    status_code="${response: -3}"
    
    if [[ "$status_code" == "200" ]]; then
        log "ML Analytics Service: HEALTHY"
        return 0
    else
        log "ML Analytics Service: UNHEALTHY (HTTP $status_code)"
        return 1
    fi
}

# Function: Check Model Status
check_models() {
    local response
    local active_models
    
    response=$(curl -s -m "$HEALTH_CHECK_TIMEOUT" "$ML_ANALYTICS_URL/api/v1/status/models" || echo '{"total_active_models": 0}')
    active_models=$(echo "$response" | jq -r '.total_active_models // 0')
    
    if [[ "$active_models" -ge 6 ]]; then  # Mindestens 6 Modelle (2 Typen x 3 Horizonte)
        log "Model Status: HEALTHY ($active_models active models)"
        return 0
    else
        log "Model Status: WARNING (Only $active_models active models)"
        return 1
    fi
}

# Function: Check Event Bus Connection
check_event_bus() {
    local redis_status
    
    redis_status=$(redis-cli -p 6379 ping 2>/dev/null || echo "PONG")
    
    if [[ "$redis_status" == "PONG" ]]; then
        log "Event Bus: HEALTHY"
        return 0
    else
        log "Event Bus: UNHEALTHY"
        return 1
    fi
}

# Main Health Check
main() {
    log "Starting ML Health Check..."
    
    local checks_passed=0
    local total_checks=3
    
    check_ml_analytics && ((checks_passed++))
    check_models && ((checks_passed++))
    check_event_bus && ((checks_passed++))
    
    if [[ $checks_passed -eq $total_checks ]]; then
        log "ML Health Check: ALL SYSTEMS HEALTHY ($checks_passed/$total_checks)"
        exit 0
    else
        log "ML Health Check: ISSUES DETECTED ($checks_passed/$total_checks healthy)"
        exit 1
    fi
}

main "$@"
```

### **Health-Check Service Configuration**
```ini
# /etc/systemd/system/aktienanalyse-ml-health-check.service
[Unit]
Description=Aktienanalyse ML Health Check
After=aktienanalyse-ml-analytics-modular.service

[Service]
Type=oneshot
User=aktienanalyse
ExecStart=/opt/aktienanalyse-ökosystem/scripts/ml-health-check.sh
StandardOutput=journal
SyslogIdentifier=ml-health-check

# /etc/systemd/system/aktienanalyse-ml-health-check.timer
[Unit]
Description=ML Health Check Timer
Requires=aktienanalyse-ml-health-check.service

[Timer]
OnCalendar=*:0/5  # Alle 5 Minuten
Persistent=true

[Install]
WantedBy=timers.target
```

---

## 🚀 **Deployment-Scripts**

### **ML Services Deployment Script**
```bash
#!/bin/bash
# /opt/aktienanalyse-ökosystem/scripts/deploy-ml-services.sh

set -euo pipefail

# Configuration
DEPLOY_LOG="/var/log/aktienanalyse/ml-deployment.log"
SERVICE_USER="aktienanalyse"
SYSTEMD_DIR="/etc/systemd/system"
PROJECT_DIR="/opt/aktienanalyse-ökosystem"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOY_LOG"
}

# Function: Copy systemd service files
deploy_systemd_services() {
    log "Deploying systemd service files..."
    
    # Copy service files
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-analytics-modular.service" "$SYSTEMD_DIR/"
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-training-pipeline.service" "$SYSTEMD_DIR/"
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-model-validator.service" "$SYSTEMD_DIR/"
    
    # Copy timer files
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-training-pipeline.timer" "$SYSTEMD_DIR/"
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-model-validator.timer" "$SYSTEMD_DIR/"
    cp "$PROJECT_DIR/systemd/aktienanalyse-ml-health-check.timer" "$SYSTEMD_DIR/"
    
    # Update ecosystem target
    cp "$PROJECT_DIR/systemd/aktienanalyse-ecosystem.target" "$SYSTEMD_DIR/"
    
    # Set permissions
    chmod 644 "$SYSTEMD_DIR"/aktienanalyse-ml-*.service
    chmod 644 "$SYSTEMD_DIR"/aktienanalyse-ml-*.timer
    chmod 644 "$SYSTEMD_DIR/aktienanalyse-ecosystem.target"
    
    log "systemd service files deployed successfully"
}

# Function: Create directories
create_directories() {
    log "Creating ML directories..."
    
    # Model storage
    mkdir -p "$PROJECT_DIR/models"/{technical,sentiment,fundamental,ensemble}
    mkdir -p "$PROJECT_DIR/models/backups"
    
    # Logs
    mkdir -p "$PROJECT_DIR/logs/ml-analytics"
    mkdir -p "$PROJECT_DIR/logs/ml-training"
    mkdir -p "$PROJECT_DIR/logs/ml-validation"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/models"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/logs"
    
    log "Directories created successfully"
}

# Function: Install Python dependencies
install_dependencies() {
    log "Installing ML Python dependencies..."
    
    cd "$PROJECT_DIR"
    sudo -u "$SERVICE_USER" "$PROJECT_DIR/venv/bin/pip" install -r services/ml-analytics-service-modular/requirements.txt
    
    log "Python dependencies installed successfully"
}

# Function: Setup database
setup_database() {
    log "Setting up ML database schema..."
    
    # Execute ML database schema
    sudo -u postgres psql -d aktienanalyse_events -f "$PROJECT_DIR/database/ml-schema-extension.sql"
    
    log "Database schema setup completed"
}

# Function: Reload and enable services
enable_services() {
    log "Enabling ML services..."
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable aktienanalyse-ml-analytics-modular.service
    systemctl enable aktienanalyse-ml-training-pipeline.timer
    systemctl enable aktienanalyse-ml-model-validator.timer
    systemctl enable aktienanalyse-ml-health-check.timer
    
    # Update ecosystem target
    systemctl enable aktienanalyse-ecosystem.target
    
    log "Services enabled successfully"
}

# Function: Start services
start_services() {
    log "Starting ML services..."
    
    # Start ML Analytics Service
    systemctl start aktienanalyse-ml-analytics-modular.service
    
    # Start timers
    systemctl start aktienanalyse-ml-training-pipeline.timer
    systemctl start aktienanalyse-ml-model-validator.timer
    systemctl start aktienanalyse-ml-health-check.timer
    
    # Check status
    sleep 5
    if systemctl is-active --quiet aktienanalyse-ml-analytics-modular.service; then
        log "ML Analytics Service started successfully"
    else
        log "ERROR: ML Analytics Service failed to start"
        exit 1
    fi
    
    log "All ML services started successfully"
}

# Main deployment function
main() {
    log "Starting ML services deployment..."
    
    create_directories
    deploy_systemd_services
    install_dependencies
    setup_database
    enable_services
    start_services
    
    log "ML services deployment completed successfully!"
    
    # Show service status
    echo
    echo "=== ML Services Status ==="
    systemctl status aktienanalyse-ml-analytics-modular.service --no-pager -l
    echo
    systemctl list-timers aktienanalyse-ml-* --no-pager
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

---

## 📊 **Service Management Commands**

### **Häufig verwendete Befehle:**
```bash
# Service Status
systemctl status aktienanalyse-ml-analytics-modular.service
systemctl status aktienanalyse-ml-training-pipeline.service

# Logs anzeigen
journalctl -u aktienanalyse-ml-analytics-modular.service -f
journalctl -u aktienanalyse-ml-training-pipeline.service --since "1 hour ago"

# Services starten/stoppen
systemctl start aktienanalyse-ml-analytics-modular.service
systemctl stop aktienanalyse-ml-analytics-modular.service
systemctl restart aktienanalyse-ml-analytics-modular.service

# Timer verwalten
systemctl start aktienanalyse-ml-training-pipeline.timer
systemctl list-timers aktienanalyse-ml-*

# Training manuell auslösen
systemctl start aktienanalyse-ml-training-pipeline.service

# Komplettes Ecosystem starten/stoppen
systemctl start aktienanalyse-ecosystem.target
systemctl stop aktienanalyse-ecosystem.target

# Service-Abhängigkeiten anzeigen
systemctl list-dependencies aktienanalyse-ml-analytics-modular.service
```

### **Monitoring und Debugging:**
```bash
# Performance-Monitoring
systemctl show aktienanalyse-ml-analytics-modular.service --property=MemoryCurrent,CPUUsageNSec
ps aux | grep ml_analytics

# Failed Services anzeigen
systemctl --failed | grep aktienanalyse

# Service-Configuration anzeigen
systemctl cat aktienanalyse-ml-analytics-modular.service

# Environment-Variables anzeigen
systemctl show-environment
```

---

## ✅ **Deployment-Validierung**

### **Post-Deployment Checks:**
```bash
#!/bin/bash
# Validation Script

echo "=== ML Services Deployment Validation ==="

# 1. Services Running
echo "1. Checking service status..."
systemctl is-active aktienanalyse-ml-analytics-modular.service
systemctl is-enabled aktienanalyse-ml-analytics-modular.service

# 2. Port Binding
echo "2. Checking port binding..."
ss -tuln | grep :8019

# 3. Health Check
echo "3. Testing health endpoint..."
curl -f http://localhost:8019/health

# 4. Database Connection
echo "4. Testing database connection..."
sudo -u aktienanalyse psql -d aktienanalyse_ml -c "SELECT COUNT(*) FROM ml_model_metadata;"

# 5. Event Bus Connection
echo "5. Testing Event Bus..."
redis-cli -p 6379 ping

# 6. File Permissions
echo "6. Checking file permissions..."
ls -la /opt/aktienanalyse-ökosystem/models/

echo "=== Validation Complete ==="
```

---

## 🔧 **Troubleshooting Guide**

### **Häufige Probleme:**

1. **Service startet nicht:**
   ```bash
   journalctl -u aktienanalyse-ml-analytics-modular.service --no-pager
   systemctl status aktienanalyse-ml-analytics-modular.service
   ```

2. **Port bereits in Verwendung:**
   ```bash
   ss -tuln | grep :8019
   fuser -n tcp 8019
   ```

3. **Speicher-Probleme:**
   ```bash
   systemctl show aktienanalyse-ml-analytics-modular.service --property=MemoryCurrent
   free -h
   ```

4. **GPU-Probleme:**
   ```bash
   nvidia-smi
   echo $CUDA_VISIBLE_DEVICES
   ```

---

## ✅ **Deployment-Checklist**

### **Pre-Deployment:**
- [ ] Backup existing system
- [ ] Check disk space (mindestens 10GB frei)
- [ ] Verify Python dependencies
- [ ] Test database connectivity
- [ ] Validate systemd service files

### **Deployment:**
- [ ] Deploy systemd service files
- [ ] Create required directories
- [ ] Install Python dependencies
- [ ] Setup database schema
- [ ] Enable and start services
- [ ] Verify health checks

### **Post-Deployment:**
- [ ] Test all API endpoints
- [ ] Verify event bus integration
- [ ] Check log files for errors
- [ ] Monitor resource usage
- [ ] Test automatic restart functionality

---

*systemd ML-Deployment Spezifikation erstellt: 17. August 2025*  
*Version: 1.0.0*  
*Kompatibel mit: aktienanalyse-ökosystem v5.1 FINAL*