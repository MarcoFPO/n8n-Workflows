# 🏗️ High-Level Design (HLD)

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 📊 **Architektur-Übersicht**

#### 🌐 **System-Topologie**
```
┌─────────────────────────────────────────────────────────────────┐
│                    🌐 Web Interface Layer                       │
│                     (Bootstrap 5 UI - Port 8080)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────┴───────────────────────────────────────────┐
│                  🚌 Event Bus Layer                             │
│              (Redis Pub/Sub - Port 8014)                        │
│              Event-Driven Communication Hub                     │
└─┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────┬──┘
  │      │      │      │      │      │      │      │      │    │
┌─▼──┐ ┌▼───┐ ┌▼───┐ ┌▼────┐ ┌▼────┐ ┌▼───┐ ┌▼───┐ ┌▼───┐ ┌▼─┐ ┌▼──┐
│🧠  │ │📡  │ │🔍  │ │🔧   │ │📈  │ │🎯  │ │🤖  │ │📊  │ │💰│ │?   │
│Core│ │Broker│Mon │ │Diag │ │Data│ │Pred│ │ML  │ │Cap │ │PE│ │?   │
│8001│ │8012  │8015│ │8013 │ │8017│ │8018│ │8021│ │8011│ │8025│8?  │
└────┘ └────┘ └────┘ └─────┘ └────┘ └────┘ └────┘ └────┘ └───┘ └───┘
```

---

## 🏛️ **Service-Architektur**

### 🧠 **Core Services (Event Processing)**

#### 🧠 **Intelligent Core Service (Port 8001)**
```python
# Service: intelligent-core-service
# Purpose: Zentrale AI Analytics & Event Orchestration
Components:
├── Event Processing Engine     # Event-Driven Intelligence
├── Stock Analysis Pipeline     # KI-basierte Aktienanalyse  
├── Cross-System Intelligence   # Service-übergreifende Korrelationen
├── Performance Tracking        # SOLL-IST Monitoring
└── API Gateway                 # Central API Coordination
```

#### 🚌 **Event Bus Service (Port 8014)**
```python
# Service: event-bus-service
# Purpose: Event-Driven Communication Hub
Components:
├── Redis Pub/Sub Engine        # Event Distribution
├── Event Type Management       # 8 Core Event Types
├── Correlation ID Tracking     # Cross-Service Event Correlation
├── Event Persistence          # PostgreSQL Event Store Integration
└── Real-time Broadcasting     # 0.12s Response Time
```

### 📊 **Data & Analytics Services**

#### 📈 **Data Processing Service (Port 8017)**
```python
# Service: data-processing-service
# Purpose: CSV Middleware & Data Transformation
Components:
├── CSV Import/Export Engine    # 5-Spalten Format Processing
├── Real-time Data Sync        # Multi-Source Integration
├── Data Validation Pipeline   # Quality Assurance
├── Format Conversion          # Cross-Service Data Exchange
└── Batch Processing          # Large Dataset Handling
```

#### 🤖 **ML Analytics Service (Port 8021)**
```python
# Service: ml-analytics-service
# Purpose: Advanced ML Pipeline & Model Management
Components:
├── Multi-Horizon Predictions  # 7d, 30d, 150d, 365d
├── Ensemble Learning Engine   # LSTM, XGBoost, LightGBM
├── Automated Model Training   # Performance-based Retraining
├── Model Version Management   # Rollback & Comparison
├── Prediction Confidence     # Risk Assessment Scoring
└── ML API Endpoints (20+)    # Comprehensive ML Services
```

#### 📊 **MarketCap Service (Port 8011)**
```python
# Service: marketcap-service
# Purpose: Market Capitalization Data Provider
Components:
├── Market Data Aggregation    # Multi-Source Market Cap
├── Real-time Updates         # Live Market Data
├── Historical Data Storage   # Time-series Analysis
├── Comparative Analysis      # Market Position Tracking
└── API Integration          # External Market Data Sources
```

### 🎯 **Trading & Portfolio Services**

#### 📡 **Broker Gateway Service (Port 8012)**
```python
# Service: broker-gateway-service
# Purpose: Trading API Integration & Order Management
Components:
├── Bitpanda API Integration   # Primary Trading Platform
├── Alpha Vantage API         # Market Data Provider
├── Order Execution Engine    # Automated Trading
├── Portfolio Synchronization # Real-time Position Tracking
└── Risk Management          # Trading Safety Mechanisms
```

#### 🎯 **Prediction Tracking Service (Port 8018)**
```python
# Service: prediction-tracking-service
# Purpose: SOLL-IST Analysis & Performance Validation
Components:
├── Prediction Validation     # Model Performance Tracking
├── SOLL-IST Comparison      # Expected vs Actual Results
├── Performance Metrics      # Accuracy & Confidence Scoring
├── Model Feedback Loop      # Training Data Enhancement
└── Alert Generation         # Performance Deviation Alerts
```

#### 💰 **Unified Profit Engine (Port 8025)**
```python
# Service: unified-profit-engine
# Purpose: Konsolidierte Gewinnanalyse & ROI Tracking
Components:
├── Portfolio Performance     # Real-time P&L Calculation
├── Trade Impact Analysis    # Individual Trade Performance
├── Risk-Adjusted Returns    # Sharpe Ratio & Risk Metrics
├── Tax Calculation         # Steuerliche Gewinnermittlung
└── Performance Reports     # Comprehensive ROI Analysis
```

### 🔧 **System Management Services**

#### 🔍 **Monitoring Service (Port 8015)**
```python
# Service: monitoring-service
# Purpose: System Health & Performance Monitoring
Components:
├── Service Health Checks     # Real-time Status Monitoring
├── Performance Metrics      # Response Time & Throughput
├── Alert Management         # Critical Issue Notifications
├── System Resource Monitor  # CPU, Memory, Disk Usage
└── SLA Tracking            # 99.9% Availability Monitoring
```

#### 🔧 **Diagnostic Service (Port 8013)**
```python
# Service: diagnostic-service
# Purpose: System Diagnostics & Troubleshooting
Components:
├── Service Dependency Check # Inter-Service Communication Test
├── Database Connectivity    # PostgreSQL & Redis Health
├── API Endpoint Testing     # External API Status Validation
├── Event Flow Analysis      # Event-Driven Communication Debug
└── Performance Profiling    # System Bottleneck Identification
```

#### 🎨 **Frontend Service (Port 8080)**
```python
# Service: frontend-service
# Purpose: Bootstrap 5 Web Interface & Dashboard
Components:
├── Real-time Dashboard      # Live System Status Display
├── Interactive CSV Tables   # 5-Spalten Format Visualization
├── Risk Assessment UI       # Grün/Orange/Rot Badges
├── API Documentation       # Swagger/OpenAPI Interface
└── WebSocket Integration   # Real-time Updates (1s refresh)
```

---

## 🔄 **Event-Driven Flow Architecture**

### 🚌 **Event Types & Processing**

#### 📋 **Core Event Types (8 Types)**
```python
EVENT_TYPES = {
    "analysis.state.changed": {
        "purpose": "Stock Analysis Lifecycle Events",
        "services": ["intelligent-core", "prediction-tracking", "ml-analytics"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "portfolio.state.changed": {
        "purpose": "Portfolio Performance Updates",
        "services": ["broker-gateway", "unified-profit-engine", "monitoring"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "trading.state.changed": {
        "purpose": "Trading Activity Events",
        "services": ["broker-gateway", "intelligent-core", "prediction-tracking"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "intelligence.triggered": {
        "purpose": "Cross-System Intelligence Events",
        "services": ["intelligent-core", "ml-analytics", "data-processing"],
        "frequency": "On-Demand",
        "persistence": "PostgreSQL Event Store"
    },
    "data.synchronized": {
        "purpose": "Data Sync Events",
        "services": ["data-processing", "marketcap-service", "broker-gateway"],
        "frequency": "Scheduled + Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "system.alert.raised": {
        "purpose": "Health & Alert Events",
        "services": ["monitoring", "diagnostic", "intelligent-core"],
        "frequency": "Threshold-based",
        "persistence": "PostgreSQL Event Store"
    },
    "user.interaction.logged": {
        "purpose": "Frontend Interaction Events",
        "services": ["frontend", "intelligent-core", "monitoring"],
        "frequency": "User-driven",
        "persistence": "PostgreSQL Event Store"
    },
    "config.updated": {
        "purpose": "Configuration Change Events",
        "services": ["ALL"], 
        "frequency": "Administrative",
        "persistence": "PostgreSQL Event Store"
    }
}
```

### 🔄 **Event Processing Flow**

#### 🎯 **Typical Trading Intelligence Flow**
```python
# Real Trading Intelligence Event Chain
1. Data Sync Event → data.synchronized
   ├── MarketCap Service: Fresh market data received
   ├── Data Processing: CSV middleware transformation
   └── Event Bus: Broadcasting to interested services

2. Analysis Trigger → analysis.state.changed
   ├── Intelligent Core: KI-basierte Aktienanalyse (Score 18.5)
   ├── ML Analytics: Multi-horizon predictions
   └── Prediction Tracking: SOLL-IST comparison

3. Intelligence Event → intelligence.triggered
   ├── Cross-System: Correlation detected
   ├── Pattern Recognition: Better alternative identified
   └── Decision Engine: Auto-import recommendation

4. Portfolio Update → portfolio.state.changed
   ├── Broker Gateway: Portfolio sync
   ├── Unified Profit Engine: P&L calculation (+12.8%)
   └── Real-time Dashboard: UI update

5. Trading Decision → trading.state.changed
   ├── Order Execution: Auto-import with 0 balance
   ├── Risk Assessment: Confidence-based validation
   └── All Systems Updated: 0.12s response time
```

---

## 💾 **Data Architecture**

### 🗄️ **PostgreSQL Event-Store Design**

#### 📊 **Database Schema**
```sql
-- Event Store Database: event_store_db
CREATE DATABASE event_store_db;

-- Core Event Table
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100),
    correlation_id UUID,
    event_data JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    version INTEGER DEFAULT 1
);

-- Performance Indexes
CREATE INDEX event_type_time_idx ON events (event_type, created_at);
CREATE INDEX entity_id_time_idx ON events (entity_id, created_at);
CREATE INDEX correlation_id_idx ON events (correlation_id);

-- Materialized Views für Ultra-Fast Queries (<50ms)
CREATE MATERIALIZED VIEW stock_analysis_unified AS
SELECT DISTINCT ON (entity_id)
    entity_id as stock_symbol,
    (event_data->>'score')::NUMERIC as analysis_score,
    (event_data->>'confidence')::NUMERIC as confidence_level,
    (event_data->>'risk_category') as risk_assessment,
    created_at as last_analysis
FROM events 
WHERE event_type = 'analysis.state.changed'
ORDER BY entity_id, created_at DESC;

CREATE MATERIALIZED VIEW portfolio_unified AS
SELECT 
    (event_data->>'total_value')::NUMERIC as portfolio_value,
    (event_data->>'performance_pct')::NUMERIC as performance_percent,
    (event_data->>'positions')::INTEGER as position_count,
    created_at as last_update
FROM events 
WHERE event_type = 'portfolio.state.changed'
ORDER BY created_at DESC
LIMIT 1;

-- Refresh Strategy (Every 5 minutes)
REFRESH MATERIALIZED VIEW CONCURRENTLY stock_analysis_unified;
REFRESH MATERIALIZED VIEW CONCURRENTLY portfolio_unified;
```

### ⚡ **Redis Event-Cache Architecture**

#### 🔧 **Cache Strategy**
```redis
# Redis Deployment auf Port 6379
# High-Speed Event Processing & Session Management

# Event Cache Pattern
event_cache:analysis:* 
├── TTL: 300 seconds
├── Data: Latest analysis results
└── Pattern: event_cache:analysis:{stock_symbol}

# Session Management
session_data:*
├── TTL: 3600 seconds  
├── Data: User session state
└── Pattern: session_data:{session_id}

# API Rate Limiting
api_rate_limits:*
├── TTL: 60 seconds
├── Data: Request counter
└── Pattern: api_rate_limits:{api_name}:{client_id}

# ML Predictions Cache
ml_predictions_cache:*
├── TTL: 1800 seconds
├── Data: Cached predictions
└── Pattern: ml_predictions_cache:{model}:{symbol}:{horizon}
```

---

## 🌐 **External Integration Architecture**

### 📡 **API Integration Pattern**

#### 🔌 **Multi-Provider Strategy**
```python
EXTERNAL_APIS = {
    "alpha_vantage": {
        "purpose": "Stock Data & Fundamentals",
        "endpoints": ["TIME_SERIES", "COMPANY_OVERVIEW", "EARNINGS"],
        "rate_limit": "5 calls/minute",
        "fallback": "yahoo_finance"
    },
    "bitpanda": {
        "purpose": "Trading API",
        "endpoints": ["ORDERS", "PORTFOLIO", "MARKET_DATA"],
        "rate_limit": "100 calls/minute",
        "fallback": "manual_trading"
    },
    "yahoo_finance": {
        "purpose": "Real-time Market Data",
        "endpoints": ["QUOTES", "HISTORICAL", "NEWS"],
        "rate_limit": "2000 calls/hour",
        "fallback": "iex_cloud"
    },
    "financial_modeling_prep": {
        "purpose": "Company Financials",
        "endpoints": ["FINANCIALS", "RATIOS", "DCF"],
        "rate_limit": "250 calls/day",
        "fallback": "alpha_vantage"
    }
}
```

---

## ⚡ **Performance Architecture**

### 🎯 **Performance Targets**

#### 📊 **System Performance Goals**
```yaml
performance_sla:
  response_time:
    event_processing: "≤ 0.12s"
    database_queries: "< 50ms"
    api_endpoints: "< 200ms"
    ui_updates: "< 1s"
  
  throughput:
    event_bus: "1000+ events/sec"
    database: "500+ queries/sec"
    concurrent_users: "50+ simultaneous"
  
  resource_limits:
    memory_per_service: "~200MB"
    total_system_memory: "< 4GB"
    cpu_usage: "< 50% normal load"
  
  availability:
    sla_target: "99.9%"
    recovery_time: "< 10s"
    health_check_interval: "30s"
```

### 🚀 **Optimization Strategies**

#### ⚡ **High-Performance Techniques**
1. **Event-Driven Processing**: Asynchrone Event-Verarbeitung
2. **Materialized Views**: Pre-computed Query Results  
3. **Redis Caching**: High-Speed Data Access
4. **Connection Pooling**: Database Connection Optimization
5. **Async I/O**: Non-blocking Service Communication
6. **Load Balancing**: Request Distribution (Future)

---

## 🔒 **Security Architecture**

### 🛡️ **Security Model (Private Environment)**

#### 🔐 **Security Strategy**
```yaml
security_approach: "Private Environment Optimized"
authentication: "Internal Network Only"
encryption: "HTTPS Termination at Reverse Proxy"
network_isolation: "LXC Container (10.1.1.174)"
api_security: "Environment-based API Keys"

security_controls:
  network:
    - "Internal Network Access Only (10.1.1.x)"
    - "Nginx Reverse Proxy with HTTPS"
    - "LXC Container Isolation"
  
  application:
    - "Environment Variables for Secrets"
    - "No Hardcoded API Keys"
    - "CORS Policy for Internal Ranges"
  
  data:
    - "PostgreSQL ACID Compliance"
    - "Redis Memory-only Storage"
    - "No Sensitive Data in Logs"
```

---

## 🚀 **Deployment Architecture**

### 🏗️ **Native Linux Deployment**

#### 🔧 **systemd Service Management**
```yaml
deployment_strategy: "Native Linux Services (NO Docker)"
service_management: "systemd with auto-restart"
process_isolation: "Python virtual environments"
service_discovery: "Port-based static configuration"

systemd_configuration:
  restart_policy: "RestartSec=5s"
  dependency_management: "After=postgresql.service redis.service"
  environment_loading: "EnvironmentFile=/opt/aktienanalyse/.env"
  logging: "Journal + File-based logs"
  monitoring: "systemctl status + health endpoints"
```

---

*High-Level Design - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*