# 🔗 Ressourcen & Konfiguration

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 🌐 **Ports, Datenbanken & Systemressourcen**

---

## 🔌 **Port-Konfiguration**

### 📊 **Service-Port-Mapping**
| Service | Port | Protokoll | Status | Beschreibung |
|---------|------|-----------|--------|--------------|
| **🧠 Intelligent Core** | 8001 | HTTP/WS | ✅ Active | AI Analytics & Event Processing |
| **📊 MarketCap Service** | 8011 | HTTP | ✅ Active | Market Capitalization Data Provider |
| **📡 Broker Gateway** | 8012 | HTTP | ✅ Active | Trading API Integration |
| **🔧 Diagnostic** | 8013 | HTTP | ✅ Active | System Diagnostics |
| **🚌 Event Bus** | 8014 | HTTP | ✅ Active | Event-Driven Communication |
| **🔍 Monitoring** | 8015 | HTTP | ✅ Active | System Health & Metrics |
| **📈 Data Processing** | 8017 | HTTP | ✅ Active | CSV Middleware |
| **🎯 Prediction Tracking** | 8018 | HTTP | ✅ Active | SOLL-IST Analysis |
| **🤖 ML Analytics** | 8021 | HTTP | ✅ Active | Advanced ML Pipeline |
| **💰 Unified Profit Engine** | 8025 | HTTP | ⚠️ Config | Profit Calculation |
| **🎨 Frontend Service** | 8080 | HTTP/WS | ✅ Active | Bootstrap 5 Web UI |

### 🌐 **Netzwerk-Konfiguration**
```yaml
server_ip: "10.1.1.174"
network_range: "10.1.1.0/24"
container_type: "LXC Container 174"
reverse_proxy: "Nginx (HTTPS Termination)"

internal_endpoints:
  - "http://10.1.1.174:8001"  # Intelligent Core
  - "http://10.1.1.174:8011"  # MarketCap Service
  - "http://10.1.1.174:8012"  # Broker Gateway
  - "http://10.1.1.174:8013"  # Diagnostic
  - "http://10.1.1.174:8014"  # Event Bus
  - "http://10.1.1.174:8015"  # Monitoring
  - "http://10.1.1.174:8017"  # Data Processing
  - "http://10.1.1.174:8018"  # Prediction Tracking
  - "http://10.1.1.174:8021"  # ML Analytics
  - "http://10.1.1.174:8025"  # Unified Profit Engine
  - "http://10.1.1.174:8080"  # Frontend Service

external_endpoints:
  - "https://10.1.1.174"       # Main Web Interface
  - "http://10.1.1.174:8021/docs"  # ML Analytics Swagger
  - "http://10.1.1.174:8015/health" # System Health
```

### 🔒 **Firewall & Security**
```bash
# iptables Configuration (Internal Network Only)
# /etc/iptables/rules.v4

# Allow loopback
-A INPUT -i lo -j ACCEPT

# Allow established connections
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow internal network (10.1.1.0/24)
-A INPUT -s 10.1.1.0/24 -j ACCEPT

# Allow HTTP/HTTPS on service ports
-A INPUT -p tcp --dport 8001 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8011 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8012 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8013 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8014 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8015 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8017 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8018 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8021 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8025 -s 10.1.1.0/24 -j ACCEPT
-A INPUT -p tcp --dport 8080 -s 10.1.1.0/24 -j ACCEPT

# Allow SSH from management network
-A INPUT -p tcp --dport 22 -s 10.1.1.0/24 -j ACCEPT

# Drop all other traffic
-A INPUT -j DROP
```

---

## 💾 **Datenbank-Konfiguration**

### 🐘 **PostgreSQL Event-Store**

#### 📊 **Database Structure**
```yaml
database_name: "event_store_db"
host: "localhost"
port: 5432
user: "aktienanalyse"
connection_pool_size: 20
max_connections: 100
shared_buffers: "256MB"
effective_cache_size: "1GB"

# Main Tables
tables:
  events:
    description: "Central event store for all system events"
    estimated_size: "~50GB (5M+ events)"
    indexes: 6
    partitioning: "Monthly by created_at"
    
  materialized_views:
    stock_analysis_unified:
      refresh_interval: "5 minutes"
      size: "~100MB"
      records: "~10K active stocks"
    
    portfolio_unified:
      refresh_interval: "2 minutes"  
      size: "~10MB"
      records: "~1K portfolio snapshots"
    
    trading_activity_unified:
      refresh_interval: "1 minute"
      size: "~500MB"
      records: "~100K trades (90 days)"
    
    system_health_unified:
      refresh_interval: "10 minutes"
      size: "~50MB" 
      records: "~50K health checks (24h)"
```

#### 🔧 **PostgreSQL Configuration**
```ini
# /etc/postgresql/15/main/postgresql.conf

# Connection Settings
listen_addresses = 'localhost,10.1.1.174'
port = 5432
max_connections = 100
superuser_reserved_connections = 3

# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Performance Settings
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB

# Logging Settings
logging_collector = on
log_directory = '/var/log/postgresql'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'ddl'
log_min_duration_statement = 1000

# Connection Pooling (via pgbouncer)
# /etc/pgbouncer/pgbouncer.ini
event_store_db = host=localhost port=5432 dbname=event_store_db
pool_mode = transaction
default_pool_size = 25
max_client_conn = 100
```

### 🔴 **Redis Event-Cache & Session Store**

#### ⚡ **Redis Configuration**
```yaml
redis_instances:
  main:
    port: 6379
    host: "localhost"
    databases: 16
    memory_limit: "1GB"
    persistence: "RDB + AOF"
    
  cache_databases:
    db_0: "Event Bus (Pub/Sub)"
    db_1: "Event Cache (TTL: 300s)"  
    db_2: "Session Data (TTL: 3600s)"
    db_3: "API Rate Limits (TTL: 60s)"
    db_4: "ML Predictions Cache (TTL: 1800s)"
    db_5: "Market Data Cache (TTL: 300s)"
    db_6: "Portfolio Cache (TTL: 60s)"
    db_7: "System Metrics Cache (TTL: 600s)"
```

#### 🔧 **Redis Memory Usage**
```ini
# /etc/redis/redis.conf - Production Settings

# Memory Management
maxmemory 1gb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence Strategy
save 900 1      # Save after 900 sec if at least 1 key changed
save 300 10     # Save after 300 sec if at least 10 keys changed  
save 60 10000   # Save after 60 sec if at least 10000 keys changed

# AOF Configuration
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Network & Performance
tcp-keepalive 300
tcp-backlog 511
timeout 0
databases 16

# Pub/Sub Settings
notify-keyspace-events "Ex"
client-output-buffer-limit pubsub 32mb 8mb 60
```

---

## 🗂️ **Dateiverzeichnis-Struktur**

### 📁 **Projekt-Verzeichnisse**
```
/opt/aktienanalyse-ökosystem/
├── documentation/                    # 📚 Konsolidierte Dokumentation
│   ├── README.md                    # Navigation & Übersicht
│   ├── REQUIREMENTS.md              # Systemanforderungen
│   ├── SYSTEM_OVERVIEW.md           # Systemarchitektur
│   ├── HLD.md                       # High-Level Design
│   ├── LLD.md                       # Low-Level Design
│   ├── COMMUNICATION.md             # API-Endpoints & Events
│   ├── RESOURCES.md                 # Ports & Konfiguration
│   ├── MODULES.md                   # Services & Funktionen
│   └── TESTING.md                   # Test-Strategien
│
├── services/                        # 🔧 Service-Implementierungen
│   ├── intelligent_core_service/
│   ├── broker_gateway_service/
│   ├── event_bus_service/
│   ├── monitoring_service/
│   ├── diagnostic_service/
│   ├── data_processing_service/
│   ├── prediction_tracking_service/
│   ├── ml_analytics_service/
│   ├── marketcap_service/
│   ├── unified_profit_engine/
│   └── frontend_service/
│
├── shared/                          # 📦 Gemeinsame Module
│   ├── models/                      # Pydantic Data Models
│   ├── database/                    # Database Utilities
│   ├── event_bus/                   # Event Bus Client
│   ├── external_apis/               # External API Clients
│   └── utils/                       # Helper Functions
│
├── ml-models/                       # 🤖 ML Model Storage
│   ├── versions/                    # Versionierte Modelle
│   │   ├── meta/1.0.0/
│   │   ├── technical/1.0.0/
│   │   ├── sentiment/1.0.0/
│   │   └── fundamental/1.0.0/
│   ├── backups/                     # Model Backups
│   └── staging/                     # Development Models
│
├── database/                        # 🗄️ Database Scripts
│   ├── schema.sql                   # PostgreSQL Schema
│   ├── migrations/                  # Database Migrations
│   ├── seeds/                       # Test Data
│   └── backups/                     # Automated Backups
│
├── systemd/                         # ⚙️ Service Definitions
│   ├── aktienanalyse-intelligent-core.service
│   ├── aktienanalyse-broker-gateway.service
│   ├── aktienanalyse-event-bus.service
│   └── ... (11 service files total)
│
├── scripts/                         # 🔧 Management Scripts
│   ├── deploy.sh                    # Full System Deployment
│   ├── manage_services.sh           # Service Management
│   ├── backup_database.sh           # Database Backup
│   ├── health_check.sh              # System Health Check
│   └── update_system.sh             # System Updates
│
├── logs/                           # 📝 Application Logs
│   ├── intelligent-core/
│   ├── ml-analytics/
│   ├── broker-gateway/
│   └── ... (per-service log dirs)
│
├── config/                         # ⚙️ Configuration Files
│   ├── nginx/                      # Reverse Proxy Config
│   ├── postgresql/                 # Database Config
│   ├── redis/                      # Cache Config
│   └── monitoring/                 # Monitoring Config
│
├── venv/                          # 🐍 Python Virtual Environment
├── requirements.txt               # Python Dependencies
├── .env                          # Environment Variables
├── README.md                     # Project Overview
└── VERSION                       # Current Version (v5.1)
```

### 📊 **Disk Usage Analysis**
```bash
# Estimated disk usage per component
/opt/aktienanalyse-ökosystem/     # Total: ~15GB
├── documentation/          # 50MB   (Consolidated docs)
├── services/              # 200MB   (Python code)
├── shared/                # 100MB   (Common libraries)
├── ml-models/             # 5GB     (Trained models + versions)
├── database/              # 100MB   (Scripts + migrations)
├── logs/                  # 2GB     (Application logs, rotated)
├── venv/                  # 1.5GB   (Python packages)
└── config/                # 10MB    (Configuration files)

# PostgreSQL Data Directory
/var/lib/postgresql/15/main/       # ~50GB (Event store data)

# Redis Data Directory  
/var/lib/redis/                    # ~1GB (Cache + persistence)

# System Logs
/var/log/                         # ~500MB (System logs)
```

---

## 🔧 **Systemd Service-Konfiguration**

### ⚙️ **Service-Definitionen**

#### 🧠 **Intelligent Core Service**
```ini
# /etc/systemd/system/aktienanalyse-intelligent-core.service
[Unit]
Description=Aktienanalyse Intelligent Core - AI Analytics & Event Processing
Documentation=file:///opt/aktienanalyse-ökosystem/documentation/MODULES.md
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service
PartOf=aktienanalyse.target

[Service]
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/services/intelligent_core_service
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
EnvironmentFile=/opt/aktienanalyse-ökosystem/.env

# Service Execution
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Auto-Restart Configuration
Restart=always
RestartSec=5
StartLimitBurst=3
StartLimitInterval=60

# Resource Limits
MemoryMax=300M
CPUQuota=30%
TasksMax=100

# Security Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs
PrivateNetwork=false
PrivateDevices=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true

# Logging
StandardOutput=journal+console
StandardError=journal+console
SyslogIdentifier=aktienanalyse-intelligent-core

[Install]
WantedBy=multi-user.target aktienanalyse.target
```

#### 🎯 **Service Target (Group Management)**
```ini
# /etc/systemd/system/aktienanalyse.target
[Unit]
Description=Aktienanalyse Trading Intelligence System v5.1
Documentation=file:///opt/aktienanalyse-ökosystem/documentation/README.md
Requires=postgresql.service redis.service
After=postgresql.service redis.service

[Install]
WantedBy=multi-user.target
```

### 📊 **Service-Status-Monitoring**
```bash
# Service Management Commands
systemctl status aktienanalyse.target        # Overall system status
systemctl start aktienanalyse.target         # Start all services
systemctl stop aktienanalyse.target          # Stop all services
systemctl restart aktienanalyse.target       # Restart all services

# Individual Service Commands
systemctl status aktienanalyse-intelligent-core
systemctl status aktienanalyse-ml-analytics
systemctl status aktienanalyse-broker-gateway

# Service Logs
journalctl -u aktienanalyse-intelligent-core -f    # Follow logs
journalctl -u aktienanalyse.target --since="1 hour ago"  # Recent logs
```

---

## 🌐 **Environment Variables**

### 📝 **Complete .env Configuration**
```bash
# /opt/aktienanalyse-ökosystem/.env
# Event-Driven Trading Intelligence System v5.1 Configuration

# =============================================================================
# SERVICE PORTS CONFIGURATION
# =============================================================================
INTELLIGENT_CORE_PORT=8001
MARKETCAP_SERVICE_PORT=8011
BROKER_GATEWAY_PORT=8012
DIAGNOSTIC_PORT=8013
EVENT_BUS_PORT=8014
MONITORING_PORT=8015
DATA_PROCESSING_PORT=8017
PREDICTION_TRACKING_PORT=8018
ML_ANALYTICS_PORT=8021
UNIFIED_PROFIT_ENGINE_PORT=8025
FRONTEND_PORT=8080

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# PostgreSQL Event Store
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=event_store_db
POSTGRES_USER=aktienanalyse
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_POOL_SIZE=20
POSTGRES_TIMEOUT=30
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# Redis Event Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}
REDIS_EVENT_DB=0
REDIS_CACHE_DB=1
REDIS_SESSION_DB=2
REDIS_RATELIMIT_DB=3
REDIS_ML_CACHE_DB=4
REDIS_MARKET_CACHE_DB=5

# =============================================================================
# EXTERNAL API CONFIGURATION
# =============================================================================
# Alpha Vantage API
ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}
ALPHA_VANTAGE_BASE_URL=https://www.alphavantage.co/query

# Bitpanda Trading API
BITPANDA_API_KEY=${BITPANDA_API_KEY}
BITPANDA_API_SECRET=${BITPANDA_API_SECRET}
BITPANDA_BASE_URL=https://api.bitpanda.com/v1

# Yahoo Finance API  
YAHOO_FINANCE_BASE_URL=https://query1.finance.yahoo.com/v8/finance

# Financial Modeling Prep
FMP_API_KEY=${FMP_API_KEY}
FMP_BASE_URL=https://financialmodelingprep.com/api/v3

# IEX Cloud
IEX_CLOUD_TOKEN=${IEX_CLOUD_TOKEN}
IEX_CLOUD_BASE_URL=https://cloud.iexapis.com/stable

# =============================================================================
# ML & ANALYTICS CONFIGURATION
# =============================================================================
ML_MODEL_PATH=/opt/aktienanalyse-ökosystem/ml-models
ML_MODEL_VERSION=1.0.0
ML_TRAINING_ENABLED=true
ML_AUTO_RETRAIN_THRESHOLD=0.70
ML_PREDICTION_HORIZONS=7,30,150,365
ML_ENSEMBLE_WEIGHTS=0.4,0.35,0.25  # LSTM, XGBoost, LightGBM

# Model Storage
MODEL_BACKUP_PATH=/opt/aktienanalyse-ökosystem/ml-models/backups
MODEL_STAGING_PATH=/opt/aktienanalyse-ökosystem/ml-models/staging

# =============================================================================
# EVENT BUS CONFIGURATION
# =============================================================================
EVENT_BUS_BATCH_SIZE=100
EVENT_CACHE_TTL=300
EVENT_PROCESSING_TIMEOUT=5
EVENT_CORRELATION_ENABLED=true
EVENT_METRICS_ENABLED=true

# Event Types
EVENT_TYPES=analysis.state.changed,portfolio.state.changed,trading.state.changed,intelligence.triggered,data.synchronized,system.alert.raised,user.interaction.logged,config.updated

# =============================================================================
# SYSTEM PERFORMANCE CONFIGURATION
# =============================================================================
# HTTP Client Settings
HTTP_TIMEOUT=10
HTTP_MAX_CONNECTIONS=100
HTTP_RETRY_COUNT=3
HTTP_BACKOFF_FACTOR=2

# Response Time Targets
TARGET_RESPONSE_TIME_MS=120
TARGET_EVENT_PROCESSING_TIME_MS=120
TARGET_DB_QUERY_TIME_MS=50

# Memory & CPU Limits
SERVICE_MEMORY_LIMIT_MB=256
SERVICE_CPU_QUOTA_PCT=30
SYSTEM_MEMORY_LIMIT_GB=4

# =============================================================================
# LOGGING & MONITORING CONFIGURATION
# =============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=JSON
LOG_ROTATION_SIZE=100MB
LOG_RETENTION_DAYS=30
LOG_PATH=/opt/aktienanalyse-ökosystem/logs

# Monitoring Settings
HEALTH_CHECK_INTERVAL=30
METRICS_RETENTION_HOURS=168  # 7 days
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=85
ALERT_THRESHOLD_RESPONSE_TIME=500

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
# Network Security
ALLOWED_ORIGINS=http://10.1.1.174:8080,https://10.1.1.174
CORS_ORIGINS=http://10.1.1.174:*,https://10.1.1.174
INTERNAL_NETWORK=10.1.1.0/24

# API Security
API_RATE_LIMIT_PER_MINUTE=1000
API_RATE_LIMIT_BURST=100
API_KEY_ROTATION_DAYS=90

# Session Management
SESSION_TIMEOUT_HOURS=24
SESSION_CLEANUP_INTERVAL_HOURS=6

# =============================================================================
# DEVELOPMENT & DEBUG CONFIGURATION
# =============================================================================
DEBUG=false
DEVELOPMENT_MODE=false
TEST_MODE=false
PROFILING_ENABLED=false

# Feature Flags
FEATURE_ML_PREDICTIONS=true
FEATURE_AUTO_TRADING=false  # Disabled for safety
FEATURE_ADVANCED_ANALYTICS=true
FEATURE_REAL_TIME_UPDATES=true

# =============================================================================
# BACKUP & MAINTENANCE CONFIGURATION
# =============================================================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_PATH=/opt/aktienanalyse-ökosystem/database/backups

# Maintenance Windows
MAINTENANCE_ENABLED=true
MAINTENANCE_SCHEDULE="0 3 * * 0"  # Weekly Sunday 3 AM
MAINTENANCE_DURATION_MINUTES=30

# =============================================================================
# VERSION & BUILD INFORMATION
# =============================================================================
SYSTEM_VERSION=5.1
BUILD_DATE=2025-08-23
DEPLOYMENT_ENVIRONMENT=production
CONTAINER_ID=lxc-174
SERVER_IP=10.1.1.174
```

### 🔒 **Secrets Management**
```bash
# /opt/aktienanalyse-ökosystem/.env.secrets (chmod 600)
# This file contains actual API keys and passwords
# Never commit to version control!

POSTGRES_PASSWORD=secure_db_password_2025
ALPHA_VANTAGE_API_KEY=YOUR_ALPHA_VANTAGE_KEY
BITPANDA_API_KEY=YOUR_BITPANDA_API_KEY
BITPANDA_API_SECRET=YOUR_BITPANDA_SECRET
FMP_API_KEY=YOUR_FMP_API_KEY
IEX_CLOUD_TOKEN=YOUR_IEX_CLOUD_TOKEN

# JWT Secrets (if implemented in future)
JWT_SECRET_KEY=ultra_secure_jwt_secret_key_2025
ENCRYPTION_KEY=secure_encryption_key_for_sensitive_data

# Backup Encryption
BACKUP_ENCRYPTION_KEY=secure_backup_encryption_key_2025
```

---

## 🔧 **System Resource Requirements**

### 💻 **Hardware Specifications**
```yaml
# LXC Container 174 Specifications
cpu_cores: 4
memory_gb: 8
storage_gb: 100
network: "10.1.1.174/24"

# Resource Allocation per Service
service_resources:
  intelligent_core: {memory_mb: 300, cpu_percent: 30}
  ml_analytics: {memory_mb: 512, cpu_percent: 50}
  broker_gateway: {memory_mb: 256, cpu_percent: 20}
  data_processing: {memory_mb: 256, cpu_percent: 25}
  event_bus: {memory_mb: 128, cpu_percent: 10}
  monitoring: {memory_mb: 128, cpu_percent: 10}
  frontend: {memory_mb: 128, cpu_percent: 15}
  
# Database Resources
postgresql: {memory_mb: 1024, cpu_percent: 40, storage_gb: 60}
redis: {memory_mb: 1024, cpu_percent: 20, storage_gb: 5}

# Total System Usage (Peak)
total_memory_usage: "~4GB (50% of available)"
total_cpu_usage: "~60% (under normal load)"
total_storage: "~70GB (including logs and backups)"
```

### 📊 **Performance Monitoring Targets**
```yaml
# SLA Targets
availability: 99.9%  # 8.76 hours downtime/year
response_time: 120ms  # 95th percentile
event_processing: 1000_events_per_second
database_query_time: 50ms  # Average
recovery_time: 10s  # Automatic service restart

# Resource Utilization Alerts
cpu_warning: 70%
cpu_critical: 85%
memory_warning: 75%
memory_critical: 90%
disk_warning: 80%
disk_critical: 95%

# Service Health Thresholds
healthy_response_time: "<200ms"
degraded_response_time: "200-500ms"  
unhealthy_response_time: ">500ms"
```

---

*Ressourcen & Konfiguration - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*