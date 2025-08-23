# 🧩 Module & Services

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 📊 **Service-Module & Funktionsbeschreibungen**

---

## 🧠 **Intelligent Core Service (Port 8001)**

### 🎯 **Hauptfunktionen**
- **KI-basierte Aktienanalyse** mit Score-Berechnung (0-100)
- **Cross-System Intelligence** für service-übergreifende Korrelationen
- **Event-Orchestrierung** als zentrale Event-Processing-Engine
- **SOLL-IST Performance-Tracking** mit kontinuierlicher Validierung

### 📁 **Module-Struktur**
```python
intelligent_core_service/
├── main.py                           # FastAPI Application
├── intelligent_core_v1_1_0_20250823.py  # Core Engine
├── event_processor.py                # Event Processing
├── stock_analyzer.py                # AI Stock Analysis
├── cross_system_intelligence.py     # Inter-Service Correlation
├── performance_tracker.py           # SOLL-IST Analysis
└── models/
    ├── analysis_models.py           # Analysis Data Models
    ├── event_schemas.py             # Event Type Definitions
    └── intelligence_models.py       # Intelligence Models
```

### 🔧 **API-Endpoints**
```python
# Core Analysis Endpoints
POST /analyze/stock                  # Comprehensive stock analysis
GET  /analysis/history/{symbol}      # Historical analysis data
POST /intelligence/correlations      # Cross-asset correlation analysis
GET  /performance/tracking           # SOLL-IST comparison data

# Event Processing Endpoints
POST /events/publish                 # Manual event publishing
GET  /events/status                  # Event processing status
GET  /events/metrics                 # Event processing metrics

# System Intelligence Endpoints
GET  /intelligence/recommendations   # AI-generated recommendations
POST /intelligence/trigger           # Manual intelligence trigger
GET  /intelligence/patterns          # Detected pattern analysis
```

### 🎯 **Core Algorithmen**
1. **Technical Analysis Engine**: RSI, MACD, Bollinger Bands, Moving Averages
2. **Fundamental Analysis Engine**: P/E Ratio, Debt-to-Equity, ROE, Revenue Growth
3. **Sentiment Analysis Engine**: News sentiment, Social media sentiment
4. **AI Weighted Ensemble**: Dynamic weight adjustment based on market conditions
5. **Cross-System Intelligence**: Pattern recognition across multiple data sources

---

## 📈 **Data Processing Service (Port 8017)**

### 🎯 **Hauptfunktionen**
- **CSV-Middleware** mit 5-Spalten-Format (Symbol, Score, Confidence, Risk, LastUpdate)
- **Real-time Data Synchronization** zwischen externen APIs und internen Services
- **Datenvalidierung** mit umfassenden Qualitätsprüfungen
- **Format-Konvertierung** zwischen verschiedenen Datenformaten

### 📁 **Module-Struktur**
```python
data_processing_service/
├── main.py                          # FastAPI Entry Point
├── data_processing_v4_2_0_20250823.py  # Main Service Logic
├── csv_processor.py                 # 5-Column CSV Processing
├── data_validator.py               # Data Quality Validation
├── format_converter.py             # Multi-Format Conversion
├── sync_manager.py                 # Data Synchronization
└── schemas/
    ├── csv_schemas.py              # CSV Data Models
    ├── validation_rules.py         # Validation Rule Engine
    └── sync_schemas.py             # Synchronization Models
```

### 🔧 **API-Endpoints**
```python
# CSV Processing Endpoints
POST /csv/import                     # CSV file import with validation
GET  /csv/export                     # Real-time CSV export
POST /csv/validate                   # CSV data validation
GET  /csv/template                   # CSV template download

# Data Synchronization Endpoints
POST /data/sync/manual               # Manual data sync trigger
GET  /data/sync/status               # Sync status monitoring
GET  /data/sync/history              # Sync history and logs
POST /data/sync/configure            # Sync configuration

# Data Quality Endpoints
GET  /data/quality/report            # Data quality assessment
POST /data/quality/rules             # Custom validation rules
GET  /data/quality/metrics           # Quality metrics over time
```

### 🔍 **Datenvalidierungs-Regeln**
```python
VALIDATION_RULES = {
    "Symbol": {
        "type": str,
        "max_length": 10,
        "pattern": r"^[A-Z]{1,5}$",
        "required": True,
        "unique": True
    },
    "Score": {
        "type": float,
        "min_value": 0.0,
        "max_value": 100.0,
        "required": True,
        "precision": 2
    },
    "Confidence": {
        "type": float,
        "min_value": 0.0,
        "max_value": 1.0,
        "required": True,
        "precision": 4
    },
    "Risk": {
        "type": str,
        "allowed_values": ["LOW", "MEDIUM", "HIGH"],
        "required": True,
        "case_sensitive": True
    },
    "LastUpdate": {
        "type": datetime,
        "format": "ISO8601",
        "required": True,
        "not_future": True
    }
}
```

---

## 🤖 **ML Analytics Service (Port 8021)**

### 🎯 **Hauptfunktionen**
- **Multi-Horizon Predictions** (7d, 30d, 150d, 365d)
- **Ensemble Learning** mit LSTM, XGBoost, LightGBM
- **Automated Model Training** mit Performance-basiertem Retraining
- **Model Version Management** mit Rollback-Funktionalität

### 📁 **Module-Struktur**
```python
ml_analytics_service/
├── main.py                              # FastAPI ML API Server
├── ml_service_v1_0_0_20250823.py      # ML Pipeline Orchestrator
├── models/
│   ├── lstm_predictor.py               # LSTM Neural Network
│   ├── xgboost_predictor.py           # XGBoost Gradient Boosting
│   ├── lightgbm_predictor.py          # LightGBM Model
│   └── ensemble_predictor.py          # Meta-Ensemble Model
├── training/
│   ├── automated_trainer.py           # Automated Training Pipeline
│   ├── model_evaluator.py            # Performance Evaluation
│   ├── feature_engineer.py           # Feature Engineering
│   └── hyperparameter_optimizer.py   # Hyperparameter Tuning
├── storage/
│   ├── model_manager.py               # Model Version Management
│   ├── model_registry.py             # Model Metadata Registry
│   └── model_deployer.py             # Model Deployment
└── utils/
    ├── data_preprocessor.py           # Data Preprocessing
    ├── prediction_postprocessor.py   # Prediction Post-processing
    └── performance_analyzer.py       # Performance Analysis
```

### 🔧 **API-Endpoints (20+ Endpoints)**
```python
# Prediction Endpoints
POST /predict/single                 # Single symbol prediction
POST /predict/multi-horizon          # Multi-horizon predictions
POST /predict/batch                  # Batch prediction processing
GET  /predict/history/{symbol}       # Prediction history

# Model Management Endpoints
GET  /models/list                    # Available models
GET  /models/performance             # Model performance metrics
POST /models/train                   # Manual model training
POST /models/evaluate                # Model evaluation
GET  /models/versions                # Model version history
POST /models/rollback                # Model rollback
POST /models/deploy                  # Model deployment

# Feature Engineering Endpoints
GET  /features/available             # Available features
POST /features/engineer              # Custom feature engineering
GET  /features/importance            # Feature importance analysis
POST /features/select                # Feature selection

# Training & Optimization Endpoints
POST /training/start                 # Start training job
GET  /training/status/{job_id}       # Training job status
GET  /training/logs/{job_id}         # Training logs
POST /training/schedule              # Schedule automated training
GET  /hyperparameters/optimize       # Hyperparameter optimization
```

### 🧠 **ML-Model Details**

#### 🔮 **LSTM Neural Network**
```python
class LSTMPredictor:
    """
    Long Short-Term Memory Neural Network
    Specialized for time-series pattern recognition
    """
    
    architecture = {
        "input_layers": 2,          # LSTM Layers
        "hidden_units": [128, 64],  # Units per layer
        "dropout_rate": 0.2,        # Regularization
        "output_activation": "linear",
        "optimizer": "adam",
        "learning_rate": 0.001
    }
    
    training_config = {
        "epochs": 100,
        "batch_size": 32,
        "validation_split": 0.2,
        "early_stopping": True,
        "patience": 10
    }
    
    performance_metrics = {
        "7d_horizon": {"mape": 6.8, "accuracy": 0.74},
        "30d_horizon": {"mape": 12.3, "accuracy": 0.68},
        "150d_horizon": {"mape": 18.5, "accuracy": 0.61},
        "365d_horizon": {"mape": 25.2, "accuracy": 0.55}
    }
```

#### 🌳 **XGBoost Gradient Boosting**
```python
class XGBoostPredictor:
    """
    Extreme Gradient Boosting
    Excellent for feature interactions and non-linear patterns
    """
    
    parameters = {
        "n_estimators": 1000,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0
    }
    
    feature_importance = {
        "price_momentum": 0.18,
        "volume_profile": 0.15,
        "technical_indicators": 0.14,
        "market_sentiment": 0.12,
        "fundamental_ratios": 0.11,
        "sector_performance": 0.10,
        "macroeconomic_factors": 0.09,
        "news_sentiment": 0.08,
        "insider_trading": 0.03
    }
```

#### ⚡ **LightGBM Model**
```python
class LightGBMPredictor:
    """
    Light Gradient Boosting Machine
    Fast training and efficient memory usage
    """
    
    parameters = {
        "objective": "regression",
        "metric": "mae",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": 0
    }
    
    optimization_config = {
        "early_stopping_rounds": 100,
        "num_boost_round": 10000,
        "categorical_features": ["sector", "industry"],
        "gpu_use_dp": False
    }
```

---

## 📡 **Broker Gateway Service (Port 8012)**

### 🎯 **Hauptfunktionen**
- **Multi-Broker API Integration** (Bitpanda, Alpha Vantage)
- **Portfolio Synchronization** mit Real-time Updates
- **Order Management** mit Execution Tracking
- **Market Data Aggregation** von verschiedenen Quellen

### 📁 **Module-Struktur**
```python
broker_gateway_service/
├── main.py                          # FastAPI Gateway Server
├── broker_gateway_v2_0_1_20250823.py  # Main Gateway Logic
├── brokers/
│   ├── bitpanda_client.py           # Bitpanda API Client
│   ├── alpha_vantage_client.py      # Alpha Vantage API
│   ├── yahoo_finance_client.py      # Yahoo Finance API
│   └── base_broker.py               # Abstract Broker Class
├── portfolio/
│   ├── portfolio_manager.py         # Portfolio Management
│   ├── position_tracker.py          # Position Tracking
│   └── performance_calculator.py    # P&L Calculations
├── orders/
│   ├── order_manager.py             # Order Lifecycle Management
│   ├── execution_tracker.py         # Trade Execution
│   └── risk_manager.py              # Risk Controls
└── market_data/
    ├── data_aggregator.py           # Multi-source Data Aggregation
    ├── real_time_feed.py            # Real-time Data Feed
    └── historical_data.py           # Historical Data Manager
```

### 🔧 **API-Endpoints**
```python
# Portfolio Management
GET  /portfolio/summary              # Portfolio overview
GET  /portfolio/positions            # Current positions
GET  /portfolio/performance          # Performance metrics
POST /portfolio/sync                 # Force portfolio sync

# Order Management
POST /orders/create                  # Create new order
GET  /orders/list                    # List orders
GET  /orders/status/{order_id}       # Order status
DELETE /orders/cancel/{order_id}     # Cancel order
GET  /orders/history                 # Order history

# Market Data
GET  /market-data/{symbol}           # Real-time quotes
GET  /market-data/batch              # Batch quotes
GET  /historical/{symbol}            # Historical data
GET  /market-data/news/{symbol}      # Market news

# Account Information
GET  /account/info                   # Account information
GET  /account/balance                # Account balance
GET  /account/transactions           # Transaction history
```

### 🏪 **Broker Integration Details**

#### 💱 **Bitpanda Integration**
```python
class BitpandaClient:
    """
    Bitpanda Pro API Integration
    Primary trading platform
    """
    
    endpoints = {
        "base_url": "https://api.bitpanda.com/v1",
        "account_balance": "/account/balances",
        "create_order": "/account/orders",
        "order_history": "/account/orders/history",
        "trades": "/account/trades",
        "market_ticker": "/market/ticker/{instrument_code}"
    }
    
    rate_limits = {
        "requests_per_minute": 100,
        "burst_limit": 10,
        "order_rate_limit": "10/minute"
    }
    
    supported_operations = [
        "market_order", "limit_order", "stop_order",
        "portfolio_sync", "balance_inquiry", "trade_history"
    ]
```

#### 📊 **Alpha Vantage Integration**
```python
class AlphaVantageClient:
    """
    Alpha Vantage API Integration
    Market data and fundamentals provider
    """
    
    functions = {
        "TIME_SERIES_DAILY": "Daily stock prices",
        "TIME_SERIES_INTRADAY": "Intraday stock prices",
        "COMPANY_OVERVIEW": "Fundamental data",
        "EARNINGS": "Earnings data",
        "INCOME_STATEMENT": "Financial statements",
        "BALANCE_SHEET": "Balance sheet data"
    }
    
    rate_limits = {
        "free_tier": "5 requests/minute",
        "premium_tier": "75 requests/minute"
    }
```

---

## 🔍 **Monitoring Service (Port 8015)**

### 🎯 **Hauptfunktionen**
- **System Health Monitoring** mit Real-time Health Checks
- **Performance Metrics** Sammlung und Analyse
- **Alert Management** mit konfigurierbaren Thresholds
- **SLA Tracking** für 99.9% Verfügbarkeit

### 📁 **Module-Struktur**
```python
monitoring_service/
├── main.py                              # FastAPI Monitoring Server
├── monitoring_orchestrator_v2_0_0_20250821.py  # Main Orchestrator
├── health/
│   ├── health_checker.py               # Service Health Checks
│   ├── endpoint_monitor.py             # API Endpoint Monitoring
│   └── database_monitor.py             # Database Health
├── metrics/
│   ├── performance_collector.py        # Performance Metrics
│   ├── resource_monitor.py             # System Resource Usage
│   └── event_metrics.py                # Event Processing Metrics
├── alerts/
│   ├── alert_manager.py                # Alert Generation & Management
│   ├── notification_sender.py          # Alert Notifications
│   └── escalation_manager.py           # Alert Escalation
└── reporting/
    ├── sla_tracker.py                  # SLA Compliance Tracking
    ├── performance_reporter.py         # Performance Reports
    └── dashboard_data.py               # Dashboard Data Provider
```

### 🔧 **API-Endpoints**
```python
# System Health
GET  /health                         # Overall system health
GET  /health/services                # Individual service health
GET  /health/detailed                # Detailed health information
POST /health/check/{service}         # Manual health check

# Performance Metrics
GET  /metrics/system                 # System performance metrics
GET  /metrics/services               # Per-service metrics
GET  /metrics/events                 # Event processing metrics
GET  /metrics/database               # Database performance metrics

# Alert Management
GET  /alerts/active                  # Active alerts
GET  /alerts/history                 # Alert history
POST /alerts/acknowledge/{alert_id}  # Acknowledge alert
POST /alerts/configure               # Alert configuration
GET  /alerts/rules                   # Alert rules

# SLA & Reporting
GET  /sla/status                     # Current SLA status
GET  /sla/history                    # SLA compliance history
GET  /reports/performance            # Performance reports
GET  /reports/availability           # Availability reports
```

### 📊 **Monitoring Metriken**
```python
MONITORED_METRICS = {
    "system_metrics": {
        "cpu_usage_percent": {"threshold_warning": 70, "threshold_critical": 85},
        "memory_usage_percent": {"threshold_warning": 75, "threshold_critical": 90},
        "disk_usage_percent": {"threshold_warning": 80, "threshold_critical": 95},
        "network_io_mbps": {"threshold_warning": 100, "threshold_critical": 200}
    },
    
    "service_metrics": {
        "response_time_ms": {"threshold_warning": 200, "threshold_critical": 500},
        "error_rate_percent": {"threshold_warning": 5, "threshold_critical": 10},
        "requests_per_second": {"threshold_warning": 1000, "threshold_critical": 2000},
        "availability_percent": {"threshold_warning": 99.0, "threshold_critical": 98.0}
    },
    
    "business_metrics": {
        "event_processing_rate": {"threshold_warning": 500, "threshold_critical": 100},
        "database_query_time_ms": {"threshold_warning": 100, "threshold_critical": 500},
        "ml_prediction_accuracy": {"threshold_warning": 0.60, "threshold_critical": 0.50},
        "portfolio_sync_lag_minutes": {"threshold_warning": 5, "threshold_critical": 15}
    }
}
```

---

## 🚌 **Event Bus Service (Port 8014)**

### 🎯 **Hauptfunktionen**
- **Event-Driven Communication Hub** mit Redis Pub/Sub
- **Event Persistence** in PostgreSQL Event Store
- **Cross-Service Event Correlation** mit Correlation IDs
- **High-Throughput Processing** (1000+ Events/sec)

### 📁 **Module-Struktur**
```python
event_bus_service/
├── main.py                          # FastAPI Event Bus Server
├── event_bus_v1_1_0_20250823.py   # Main Event Bus Logic
├── publishers/
│   ├── event_publisher.py           # Event Publishing
│   ├── batch_publisher.py           # Batch Event Publishing
│   └── priority_publisher.py        # Priority Event Handling
├── subscribers/
│   ├── event_subscriber.py          # Event Subscription
│   ├── filtered_subscriber.py       # Filtered Subscriptions
│   └── consumer_group.py            # Consumer Group Management
├── persistence/
│   ├── event_store.py               # PostgreSQL Event Store
│   ├── event_cache.py               # Redis Event Cache
│   └── event_replay.py              # Event Replay Functionality
└── routing/
    ├── event_router.py              # Event Routing Logic
    ├── correlation_tracker.py       # Event Correlation
    └── dead_letter_queue.py         # Failed Event Handling
```

### 🔄 **Event Types & Handling**
```python
EVENT_PROCESSING_CONFIG = {
    "analysis.state.changed": {
        "persistence": True,
        "cache_ttl": 300,
        "priority": "high",
        "retry_attempts": 3,
        "dead_letter": True
    },
    
    "portfolio.state.changed": {
        "persistence": True,
        "cache_ttl": 60,
        "priority": "high",
        "retry_attempts": 5,
        "dead_letter": True
    },
    
    "trading.state.changed": {
        "persistence": True,
        "cache_ttl": 30,
        "priority": "critical",
        "retry_attempts": 3,
        "dead_letter": True
    },
    
    "system.alert.raised": {
        "persistence": True,
        "cache_ttl": 600,
        "priority": "high",
        "retry_attempts": 2,
        "dead_letter": False
    }
}
```

---

## 🔧 **Diagnostic Service (Port 8013)**

### 🎯 **Hauptfunktionen**
- **System Diagnostics** für Service-Dependencies
- **Database Connectivity Testing** (PostgreSQL & Redis)
- **External API Health Validation**
- **Event Flow Analysis** und Debugging

### 📁 **Module-Struktur**
```python
diagnostic_service/
├── main.py                          # FastAPI Diagnostic Server
├── diagnostic_v2_0_0_20250823.py   # Main Diagnostic Engine
├── connectivity/
│   ├── service_checker.py           # Inter-Service Connectivity
│   ├── database_checker.py          # Database Connectivity
│   └── api_checker.py               # External API Health
├── analysis/
│   ├── event_flow_analyzer.py       # Event Flow Analysis
│   ├── performance_analyzer.py      # Performance Analysis
│   └── dependency_mapper.py         # Service Dependency Mapping
└── reports/
    ├── diagnostic_reporter.py       # Diagnostic Reports
    ├── health_summarizer.py         # Health Summary
    └── troubleshooting_guide.py     # Automated Troubleshooting
```

---

## 💰 **Unified Profit Engine (Port 8025)**

### 🎯 **Hauptfunktionen**
- **Konsolidierte Gewinnanalyse** aus 4 ursprünglichen Implementierungen
- **Real-time P&L Berechnung** mit Portfolio-Integration
- **Tax Calculation** für steuerliche Gewinnermittlung
- **Performance Attribution** nach Asset-Klassen

### 📁 **Module-Struktur**
```python
unified_profit_engine/
├── main.py                          # FastAPI Profit Engine
├── unified_profit_v3_0_0_20250823.py  # Unified Engine Logic
├── calculators/
│   ├── pnl_calculator.py            # P&L Calculation Engine
│   ├── tax_calculator.py            # Tax Calculation
│   ├── performance_calculator.py    # Performance Metrics
│   └── risk_calculator.py           # Risk-Adjusted Returns
├── reporting/
│   ├── profit_reporter.py           # Profit Reports
│   ├── tax_reporter.py              # Tax Reports
│   └── performance_reporter.py      # Performance Reports
└── integrations/
    ├── broker_integration.py        # Broker Data Integration
    ├── market_data_integration.py   # Market Data Integration
    └── event_integration.py         # Event Bus Integration
```

---

## 🎨 **Frontend Service (Port 8080)**

### 🎯 **Hauptfunktionen**
- **Bootstrap 5 Web Interface** mit responsivem Design
- **Real-time Dashboard** mit WebSocket-Updates
- **Interactive CSV-Tabellen** im 5-Spalten-Format
- **Risk Assessment Visualization** mit Farb-Badges

### 📁 **Module-Struktur**
```python
frontend_service/
├── main.py                          # FastAPI Frontend Server
├── frontend_v7_0_1_20250823.py     # Main Frontend Logic
├── static/
│   ├── css/
│   │   ├── bootstrap.min.css        # Bootstrap 5 Styles
│   │   └── custom.css               # Custom Styles
│   ├── js/
│   │   ├── bootstrap.min.js         # Bootstrap JS
│   │   ├── dashboard.js             # Dashboard Logic
│   │   └── websocket.js             # WebSocket Client
│   └── images/                      # Static Images
├── templates/
│   ├── dashboard.html               # Main Dashboard
│   ├── analysis.html                # Analysis Views
│   ├── portfolio.html               # Portfolio Views
│   └── base.html                    # Base Template
└── api/
    ├── dashboard_api.py             # Dashboard API
    ├── csv_api.py                   # CSV Export API
    └── websocket_handler.py         # WebSocket Handler
```

### 🎨 **Frontend Features**
```javascript
// Real-time Dashboard Updates
const dashboardFeatures = {
    "real_time_updates": {
        "update_interval": "1 second",
        "websocket_connection": true,
        "auto_refresh": true
    },
    
    "interactive_tables": {
        "sorting": true,
        "filtering": true,
        "pagination": true,
        "export_csv": true
    },
    
    "visualization": {
        "risk_badges": ["success", "warning", "danger"],
        "progress_bars": true,
        "charts": "Chart.js integration",
        "responsive_design": true
    }
}
```

---

*Module & Services - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*