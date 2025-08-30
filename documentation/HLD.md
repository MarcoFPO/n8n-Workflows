# 🏗️ High-Level Design (HLD)

## 🎯 **Event-Driven Trading Intelligence System v6.0 - Clean Architecture Enhanced**

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

#### 📈 **Data Processing Service Enhanced (Port 8017)**
```python
# Service: data-processing-service-enhanced
# Purpose: CSV Middleware & Data Transformation + Advanced Timeframe Aggregation v7.1
Components:
├── CSV Import/Export Engine            # 5-Spalten Format Processing
├── Real-time Data Sync                # Multi-Source Integration
├── Data Validation Pipeline           # Quality Assurance
├── Format Conversion                  # Cross-Service Data Exchange
├── Batch Processing                   # Large Dataset Handling
├── Timeframe Aggregation Engine v7.1  # ENHANCED: Clean Architecture Aggregation
│   ├── TimeframeAggregationService    # Domain Service für Business Logic
│   ├── MathematicalValidationService  # Advanced Statistical Validation
│   ├── AggregationStrategyEngine      # Strategy Pattern Implementation
│   ├── QualityAssessmentService       # Multi-dimensional Quality Control
│   ├── Performance-Optimized Cache    # Redis + PostgreSQL Hybrid
│   └── Event-Driven Notifications     # 4 neue Event-Types
├── Clean Architecture Layers          # SOLID Principles Compliance
│   ├── Domain Layer                   # Entities, Value Objects, Services
│   ├── Application Layer              # Use Cases, DTOs, Interfaces
│   ├── Infrastructure Layer           # Repositories, External Services
│   └── Presentation Layer             # REST Controllers, API Models
├── Advanced Quality Control           # Mathematical + Statistical Validation
│   ├── IQR-based Outlier Detection   # Statistical Anomaly Removal
│   ├── Confidence Score Calculation   # Multi-factor Reliability Assessment
│   ├── Data Completeness Validation   # Comprehensive Data Quality
│   └── Cross-Validation Framework     # Model Performance Validation
└── Performance Monitoring             # Real-time SLA Compliance (<300ms/150ms)
```

#### 🤖 **ML Analytics Service Enhanced (Port 8021)**
```python
# Service: ml-analytics-service-enhanced
# Purpose: Clean Architecture ML Pipeline & Global Market Analysis
Components:
├── Multi-Horizon Predictions  # 1W, 1M, 3M, 12M (Updated Horizons)
├── Global Market Integration  # 11+ Regions, 220+ Predictions
├── Ensemble Learning Engine   # LSTM, XGBoost, LightGBM
├── Yahoo Finance Data Source  # Real Market Data via yfinance
├── Clean Architecture Layers  # Domain, Application, Infrastructure
├── Automated Model Training   # Performance-based Retraining
├── Model Version Management   # Rollback & Comparison
├── Prediction Confidence     # Risk Assessment Scoring
└── ML API Endpoints (25+)    # Enhanced ML Services + Global Markets
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

#### 💰 **Unified Profit Engine Enhanced (Port 8025)**
```python
# Service: unified-profit-engine-enhanced
# Purpose: Clean Architecture Gewinnanalyse & Multi-Horizon SOLL-IST Tracking
Components:
├── Multi-Horizon Predictions # 1W, 1M, 3M, 12M Target Calculations
├── SOLL-IST Performance      # Target vs Actual Profit Tracking
├── PostgreSQL Integration    # soll_ist_gewinn_tracking Table
├── Real Market Data Engine   # Yahoo Finance Integration
├── Portfolio Performance     # Real-time P&L Calculation
├── Trade Impact Analysis    # Individual Trade Performance
├── Risk-Adjusted Returns    # Sharpe Ratio & Risk Metrics
├── Tax Calculation         # Steuerliche Gewinnermittlung
├── Clean Architecture Core  # Domain, Application, Infrastructure Layers
└── Performance Reports     # Comprehensive ROI Analysis + SOLL-IST Reports
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
        "services": ["intelligent-core", "prediction-tracking", "ml-analytics-enhanced"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "analysis.prediction.generated": {
        "purpose": "Multi-Horizon Prediction Events",
        "services": ["unified-profit-engine-enhanced", "ml-analytics-enhanced", "prediction-tracking"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "aggregation.calculation.requested": {
        "purpose": "Timeframe-specific Aggregation Request Events",
        "services": ["data-processing-enhanced", "intelligent-core", "prediction-tracking"],
        "frequency": "On-Demand + Scheduled",
        "persistence": "PostgreSQL Event Store"
    },
    "aggregation.calculation.completed": {
        "purpose": "Aggregation Results Available Events",
        "services": ["data-processing-enhanced", "frontend", "monitoring"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "aggregation.quality.validated": {
        "purpose": "Aggregation Quality Assessment Events",
        "services": ["data-processing-enhanced", "intelligent-core", "monitoring"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "aggregation.cache.updated": {
        "purpose": "Aggregation Cache Invalidation Events",
        "services": ["data-processing-enhanced", "frontend", "monitoring"],
        "frequency": "Real-time",
        "persistence": "Redis Cache Store"
    },
    "portfolio.state.changed": {
        "purpose": "Portfolio Performance Updates", 
        "services": ["broker-gateway", "unified-profit-engine-enhanced", "monitoring"],
        "frequency": "Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "profit.calculation.completed": {
        "purpose": "SOLL-IST Profit Tracking Events",
        "services": ["unified-profit-engine-enhanced", "prediction-tracking", "intelligent-core"],
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
        "services": ["data-processing", "marketcap-service", "broker-gateway", "ml-analytics-enhanced"],
        "frequency": "Scheduled + Real-time",
        "persistence": "PostgreSQL Event Store"
    },
    "market.data.synchronized": {
        "purpose": "Global Market Data Sync Events",
        "services": ["ml-analytics-enhanced", "unified-profit-engine-enhanced", "data-processing"],
        "frequency": "Real-time + Scheduled",
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

#### 🎯 **Enhanced Trading Intelligence Flow v7.1**
```python
# Enhanced Trading Intelligence Event Chain v7.1 - Clean Architecture Integration
1. Global Market Data Sync → market.data.synchronized
   ├── ML Analytics Enhanced: 11+ regions, 220+ symbols via Yahoo Finance
   ├── Data Processing Enhanced: Advanced CSV middleware transformation
   └── Event Bus: Broadcasting to interested services (0.06s optimized)

2. Aggregation Workflow Initiation → aggregation.calculation.requested
   ├── Clean Architecture Trigger: Domain-driven aggregation request
   ├── Strategy Pattern Selection: weighted_average|median|ensemble
   ├── Quality Threshold Configuration: Statistical validation parameters
   ├── Performance Target Setting: <300ms (1M), <150ms (1W) SLA
   └── Event Correlation ID: Cross-service tracking enabled

3. Domain-Driven Aggregation Processing → aggregation.calculation.processing
   ├── TimeframeAggregationService: SOLID principles business logic
   ├── MathematicalValidationService: IQR outlier detection, confidence scoring
   ├── Data Repository Access: Clean architecture data access patterns
   ├── Strategy Pattern Execution: Configurable aggregation algorithms
   └── Real-time Performance Monitoring: Sub-millisecond tracking

4. Quality Assurance Validation → aggregation.quality.validated
   ├── Multi-dimensional Assessment: Data/Prediction/Statistical quality
   ├── Quality Score Calculation: 0.0-1.0 comprehensive scoring
   ├── Threshold Compliance Check: Configurable quality standards
   ├── Issue Detection & Reporting: Automated problem identification
   └── Recommendation Engine: Quality improvement suggestions

5. Aggregation Results Completion → aggregation.calculation.completed
   ├── Entity Persistence: PostgreSQL aggregated_predictions table
   ├── Cache Strategy Update: Redis high-performance caching (85%+ hit rate)
   ├── Event Publishing: Cross-service result notification
   ├── Performance SLA Validation: Response time compliance verification
   └── Quality Metrics Recording: Comprehensive quality tracking

6. Cache Management Update → aggregation.cache.updated
   ├── TTL-based Cache Invalidation: Intelligent cache lifecycle management
   ├── Cache Hit Rate Optimization: Performance-driven caching strategy
   ├── Memory Usage Monitoring: Redis resource utilization tracking
   ├── Cache Key Strategy: Deterministic key generation for consistency
   └── Cache Performance Metrics: Real-time cache effectiveness monitoring

7. Multi-Horizon Analysis Integration → analysis.prediction.generated
   ├── Unified Profit Engine Enhanced: Clean Architecture predictions (1W, 1M, 3M, 12M)
   ├── ML Analytics Enhanced: Global market ensemble predictions
   ├── Aggregation Results Integration: Enhanced prediction accuracy
   └── PostgreSQL: soll_ist_gewinn_tracking table updates with aggregated insights

8. SOLL-IST Calculation Enhancement → profit.calculation.completed
   ├── Target Date Calculation: heute + horizon_days with aggregation insights
   ├── Enhanced Profit Forecast: Aggregation-improved accuracy
   ├── Quality-Weighted Analysis: Confidence-based profit predictions
   └── Performance Tracking: Aggregation-enhanced SOLL-IST analysis

9. Intelligence Event Processing → intelligence.triggered
   ├── Cross-System Analysis: Aggregation pattern recognition
   ├── Quality-Based Decision Making: High-confidence action triggers
   ├── Multi-region Correlation: Global aggregation insights
   └── Decision Engine: Aggregation-enhanced recommendations

10. Portfolio Update with Aggregation Insights → portfolio.state.changed
    ├── Broker Gateway: Multi-market portfolio sync with aggregation data
    ├── Unified Profit Engine Enhanced: Aggregation-improved P&L calculations
    ├── Risk Assessment: Quality-score-based risk evaluation
    └── Real-time Dashboard: Aggregation-enhanced performance UI

11. Trading Decision Enhancement → trading.state.changed
    ├── Quality-Driven Order Execution: High-confidence-only trading
    ├── Aggregation-Based Risk Assessment: Multi-dimensional risk scoring
    ├── Clean Architecture Confidence: SOLID-principles-based decision making
    └── All Systems Updated: 0.07s response time (aggregation-optimized)

# Performance Targets v7.1:
# - Aggregation Processing: <300ms (1M), <150ms (1W)
# - Event Publishing Latency: <50ms
# - Cache Hit Rate: >85%
# - Quality Score Threshold: >0.8
# - Overall System Response: <70ms (improved by 22%)
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
    (event_data->>'market_region') as market_region,
    (event_data->>'prediction_horizons') as multi_horizon_data,
    created_at as last_analysis
FROM events 
WHERE event_type IN ('analysis.state.changed', 'analysis.prediction.generated')
ORDER BY entity_id, created_at DESC;

-- Enhanced SOLL-IST Tracking View with Aggregation Integration
CREATE MATERIALIZED VIEW soll_ist_performance_unified AS
SELECT 
    (event_data->>'symbol') as stock_symbol,
    (event_data->>'datum')::DATE as tracking_date,
    (event_data->>'ist_gewinn')::NUMERIC as actual_profit,
    (event_data->>'soll_gewinn_1w')::NUMERIC as target_profit_1w,
    (event_data->>'soll_gewinn_1m')::NUMERIC as target_profit_1m,
    (event_data->>'soll_gewinn_3m')::NUMERIC as target_profit_3m,
    (event_data->>'soll_gewinn_12m')::NUMERIC as target_profit_12m,
    -- NEW: Aggregation-enhanced fields
    (event_data->>'aggregation_quality_score')::NUMERIC as quality_score,
    (event_data->>'aggregation_confidence')::NUMERIC as aggregation_confidence,
    (event_data->>'data_points_used')::INTEGER as aggregation_data_points,
    (event_data->>'aggregation_strategy') as aggregation_method,
    created_at as last_update
FROM events 
WHERE event_type = 'profit.calculation.completed'
ORDER BY created_at DESC;

-- NEW: Aggregated Predictions Performance View
CREATE MATERIALIZED VIEW aggregated_predictions_performance_unified AS
SELECT 
    (event_data->>'symbol') as stock_symbol,
    (event_data->>'timeframe_display') as timeframe,
    (event_data->>'predicted_value')::NUMERIC as predicted_value,
    (event_data->>'confidence_score')::NUMERIC as confidence_score,
    (event_data->>'quality_score')::NUMERIC as quality_score,
    (event_data->>'data_points_count')::INTEGER as data_points_count,
    (event_data->>'aggregation_strategy') as strategy_used,
    (event_data->>'processing_time_ms')::INTEGER as processing_time_ms,
    created_at as aggregation_timestamp
FROM events 
WHERE event_type = 'aggregation.calculation.completed'
ORDER BY created_at DESC;

-- NEW: Quality Metrics Tracking View
CREATE MATERIALIZED VIEW aggregation_quality_unified AS
SELECT 
    (event_data->>'symbol') as stock_symbol,
    (event_data->>'overall_quality_score')::NUMERIC as overall_quality,
    (event_data->>'quality_status') as quality_status,
    (event_data->>'validation_passed')::BOOLEAN as validation_passed,
    (event_data->>'quality_dimensions'->>'data_quality_score')::NUMERIC as data_quality,
    (event_data->>'quality_dimensions'->>'prediction_quality_score')::NUMERIC as prediction_quality,
    (event_data->>'quality_dimensions'->>'data_completeness')::NUMERIC as data_completeness,
    (event_data->>'quality_dimensions'->>'data_consistency')::NUMERIC as data_consistency,
    (event_data->>'issues_found')::INTEGER as issues_count,
    created_at as quality_assessment_time
FROM events 
WHERE event_type = 'aggregation.quality.validated'
ORDER BY created_at DESC;

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

-- Refresh Strategy (Every 3 minutes for enhanced performance)
REFRESH MATERIALIZED VIEW CONCURRENTLY stock_analysis_unified;
REFRESH MATERIALIZED VIEW CONCURRENTLY soll_ist_performance_unified;
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
        "purpose": "Primary Global Market Data Provider",
        "endpoints": ["QUOTES", "HISTORICAL", "NEWS", "GLOBAL_MARKETS"],
        "coverage": "11+ regions, 220+ symbols",
        "rate_limit": "2000 calls/hour", 
        "integration": "yfinance library",
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
    event_processing: "≤ 0.09s"    # Enhanced with Clean Architecture
    database_queries: "< 40ms"      # Optimized materialized views
    api_endpoints: "< 180ms"        # Global market data caching
    ui_updates: "< 0.8s"           # Multi-horizon real-time updates
  
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

---

## 🚀 **Clean Architecture Integration Summary**

### **✅ Neue Features in v6.0:**
1. **Multi-Horizon SOLL-IST Tracking** - 1W, 1M, 3M, 12M Gewinnvorhersagen
2. **Global Market Integration** - 11+ Regionen, 220+ Aktien-Symbole
3. **Real Market Data Engine** - Yahoo Finance Integration via yfinance
4. **Clean Architecture Core** - Domain, Application, Infrastructure Layers
5. **Enhanced Event Types** - 3 neue Event-Typen für erweiterte Funktionalität
6. **PostgreSQL SOLL-IST Table** - Dedizierte Multi-Horizon Tracking Tabelle

### **🔄 Migration Path:**
- **Clean Service (Port 8002)** → **Integration in bestehende Services**
- **Event-Driven Communication** → **Über Redis Event-Bus (Port 8014)**
- **Backward Compatibility** → **Existing APIs bleiben erhalten**

---

*High-Level Design - Event-Driven Trading Intelligence System v6.0*  
*Clean Architecture Enhanced - Multi-Horizon Global Market Analysis*  
*Letzte Aktualisierung: 24. August 2025*