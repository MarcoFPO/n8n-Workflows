# 📖 System Overview

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 🌟 **Vision & Mission**
Ein **hochperformantes Event-Driven Microservices-System** für intelligente Aktienanalyse, 
automatisierte Trading-Signale und Portfolio-Optimierung mit **KI-basierter Vorhersage-Engine** 
und **Real-time Event Processing**.

---

## 🏗️ **Systemarchitektur**

### 📊 **Übersicht**
```
┌─────────────────────────────────────────────────────────────────┐
│                    🌐 Web Interface (Port 8080)                 │
│                     Bootstrap 5 UI + Dashboard                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                  🚌 Event Bus (Port 8014)                       │
│              Redis Event-Driven Communication                   │
└─┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬───┘
  │         │         │         │         │         │         │
  │ ┌───────▼──┐ ┌────▼───┐ ┌───▼───┐ ┌───▼────┐ ┌-─▼──────┐  │
  │ │🧠Core    │ │📡Broker│ │🔍Mon  │ │📈Data  │ │🎯Pred   │  │
  │ │(8001)    │ │(8012)  │ │(8015) │ │(8017)  │ │(8018)   │  │
  │ └────────-─┘ └────────┘ └───────┘ └────────┘ └───────-─┘  │
  │                                                           │
┌─▼──────────┐ ┌──────────────┐ ┌─────────────┐     ┌─────────▼──┐
│🔧Diagnostic│ │🤖ML Analytics│ │📊MarketCap  │     │💰Profit    │
│(8013)      │ │(8021)        │ │(8011)       │     │(8025)      │
└────────────┘ └──────────────┘ └─────────────┘     └────────────┘
                      │
         ┌────────────▼────────────┐
         │  💾 Data & Storage      │
         │  PostgreSQL Event-Store │
         │  Redis Event-Cache      │
         │  ML Models & Versions   │
         └─────────────────────────┘
```

---

## 🚀 **Kern-Features**

### 🎯 **Event-Driven Intelligence**
- **⚡ 0.12s Response Time**       - Ultra-schnelle Event-Verarbeitung
- **🔄 Real-time Processing**      - 1000+ Events/sec Durchsatz
- **🧠 Cross-System Intelligence** - Service-übergreifende Korrelationen
- **📊 Performance Tracking**      - Kontinuierliches SOLL-IST Monitoring

### 🤖 **Advanced ML Pipeline**
- **🔮 Multi-Horizon Predictions** - 7d, 30d, 150d, 365d Vorhersagen
- **🎯 Ensemble Learning**         - LSTM, XGBoost, LightGBM kombiniert
- **🔄 Auto-Retraining**           - Automated Model Performance Optimization
- **📈 Version Management**        - ML Model Rollback & Comparison

### 📊 **Trading Intelligence**
- **💹 KI-Aktienanalyse**          - Score-basierte Performance Predictions
- **🎯 Risk Assessment**           - Confidence-basierte Risiko-Bewertung
- **⚖️ SOLL-IST Analyse**          - Performance Tracking & Validation
- **📈 Portfolio Optimization**    - Automated Trading Recommendations

---

## 🏗️ **Service-Architektur (11 Services)**

| Service                      | Port | Version | Status     | Beschreibung                        |
|------------------------------|------|---------|------------|-------------------------------------|
| **🧠 Intelligent Core**      | 8001 | 1.1.0   | ✅ Running | AI Analytics & Event Processing     |
| **📡 Broker Gateway**        | 8012 | 2.0.1   | ✅ Running | Trading API Integration             |
| **🎨 Frontend Service**      | 8080 | 7.0.1   | ✅ Running | Bootstrap 5 Web UI Enhanced         |
| **🚌 Event Bus**             | 8014 | 1.1.0   | ✅ Running | Event-Driven Communication          |
| **🔍 Monitoring**            | 8015 | 2.0.0   | ✅ Running | System Health & Metrics             |
| **🔧 Diagnostic**            | 8013 | 2.0.0   | ✅ Running | System Diagnostics                  |
| **📈 Data Processing**       | 8017 | 4.2.0   | ✅ Running | CSV Middleware                      |
| **🎯 Prediction Tracking**   | 8018 | 1.0.1   | ✅ Running | SOLL-IST Analysis                   |
| **🤖 ML Analytics**          | 8021 | 1.0.0   | ✅ Running | Advanced ML Pipeline & Versioning   |
| **📊 MarketCap Service**     | 8011 | 1.0.0   | ✅ Running | Market Capitalization Data Provider |
| **💰 Unified Profit Engine** | 8025 | 3.0.0   | ⚠️ Config | Konsolidierte Gewinnanalyse          |

---

## 🔄 **Event-Driven Flow Architektur**

### 🚌 **8 Core Event-Types**
```python
# Real Trading Intelligence Events
1. analysis.state.changed     # Stock Analysis Lifecycle
2. portfolio.state.changed    # Portfolio Performance Updates
3. trading.state.changed      # Trading Activity Events  
4. intelligence.triggered     # Cross-System Intelligence
5. data.synchronized          # Data Sync Events
6. system.alert.raised        # Health & Alert Events
7. user.interaction.logged    # Frontend Interactions
8. config.updated             # Configuration Changes
```

### 📊 **Live Event Flow Example**
```python
# Echtes Trading Intelligence Beispiel:
1. analysis.state.changed (AAPL: Score 18.5) →
2. portfolio.performance.updated (Portfolio: +12.8%) →  
3. intelligence.triggered (Correlation detected) →
4. auto.import.recommendation (NVDA better than worst position) →
5. trading.order.executed (Auto-import with 0 balance) →
6. All systems updated in real-time (0.12s response)
```

---

## 💾 **Daten-Architektur**

### 🗄️ **PostgreSQL Event-Store (Single Source of Truth)**
```sql
event_store_db:
├── events                      # Chronological Event Log
├── materialized_views/         # Ultra-fast Query Views (>50ms)
│   ├── stock_analysis_unified  # Real-time Analysis + Performance
│   ├── portfolio_unified       # Real-time Portfolio Metrics
│   ├── trading_activity_unified# Real-time Orders + Trades
│   └── system_health_unified   # Cross-Service Health Status
└── indexes/                    # Performance-optimierte Indizes
    ├── event_type_time_idx     # Event-Type + Timestamp
    ├── entity_id_time_idx      # Entity-ID + Timestamp  
    └── correlation_id_idx      # Event-Correlation Tracking
```

### ⚡ **Redis Event-Cache (High-Speed Operations)**
```redis
Redis Cache-Layer:
├── event_cache:*              # Temporary Event Storage
├── session_data:*             # User Session Management
├── api_rate_limits:*          # External API Rate Limiting
└── ml_predictions_cache:*     # Cached ML Results
```

### 🤖 **ML Model Storage & Versioning**
```
/opt/aktienanalyse-ökosystem/ml-models/
├── versions/                 # Versioned Model Storage
│   ├── meta/1.0.0/           # Meta Ensemble Models
│   ├── technical/1.0.0/      # Technical Analysis Models
│   ├── sentiment/1.0.0/      # Sentiment Analysis Models
│   └── fundamental/1.0.0/    # Fundamental Analysis Models
├── backups/                  # Model Backup Storage
└── staging/                  # Development Models
```

---

## 🌐 **External Integrations**

### 📡 **Data Sources (9 External APIs)**
| Provider                    | Type            | Status    | Beschreibung               |
|-----------------------------|-----------------|-----------|----------------------------|
| **Alpha Vantage**           | 📊 Market Data  | ✅ Active | Stock Quotes, Fundamentals |
| **Bitpanda**                | 💱 Trading      | ✅ Active | Trading API Integration    |
| **Yahoo Finance**           | 📈 Real-time    | ✅ Active | Live Market Data           |
| **Financial Modeling Prep** | 📊 Fundamentals | ✅ Active | Company Financials         |
| **FRED Economic**           | 📉 Macro        | ✅ Active | Economic Indicators        |
| **IEX Cloud**               | 🏢 Corporate    | ✅ Active | Corporate Data             |
| **Twelve Data**             | 🌍 Global       | ✅ Active | Global Market Data         |
| **EOD Historical**          | 📜 History      | ✅ Active | Historical Data            |
| **Finnhub**                 | 📰 News         | ✅ Active | News & Sentiment           |

---

## 📊 **Performance-Metriken**

### ⚡ **System Performance**
- **Response Time**       : 0.12s (Event-driven optimiert)
- **Event Processing**    : 1000+ Events/sec
- **Database Queries**    : <50ms (Materialized Views)
- **Memory Usage**        : ~200MB pro Service (~4GB total)
- **CPU Usage**           : <50% under normal load

### 🏥 **Service Reliability**
- **Target SLA**          : 99.9% Verfügbarkeit
- **Auto-Recovery**       : systemd Restart=always
- **Health Monitoring**   : Real-time Service Health Checks
- **Graceful Degradation**: Service Fallback Mechanisms
- **Recovery Time**       : <10s automatic service restart

### 🤖 **ML Performance**
- **Model Accuracy**      : 70-89% (je nach Horizon)
- **Training Time**       : <30 minutes per model
- **Inference Time**      : <100ms per prediction
- **Model Versions**      : Automated versioning & rollback
- **Retraining Frequency**: Weekly/Monthly (configurable)

---

## 🚀 **Deployment Environment**

### 🏗️ **Infrastructure**
- **Server**              : Proxmox LXC Container 174
- **OS**                  : Debian 12 (Bookworm) 
- **IP**                  : 10.1.1.174 (Internal Network)
- **Reverse Proxy**       : Nginx (HTTPS Termination)
- **Container Type**      : LXC (NOT Docker - Native Performance)

### 🔧 **Technology Stack**
- **Backend**             : Python 3.11+ mit FastAPI/Uvicorn
- **Frontend**            : Bootstrap 5, HTML5, JavaScript ES6+
- **Database**            : PostgreSQL 15+ für Event-Store
- **Cache**               : Redis 7+ für Event-Cache
- **ML Stack**            : TensorFlow, scikit-learn, LightGBM, XGBoost
- **Message Queue**       : Redis Pub/Sub für Event-Bus
- **Service Management**  : systemd (Native Linux Services)

---

## 🎯 **Business Value**

### 💰 **ROI-oriented Features**
1. **Automated Trading Signals** - Reduziert manuelle Analyse-Zeit
2. **Risk Assessment**           - Minimiert Verlust-Risiken
3. **Portfolio Optimization**    - Maximiert Performance
4. **Real-time Monitoring**      - Sofortige Reaktion auf Marktänderungen
5. **Historical Analysis**       - Datenbasierte Entscheidungen

### 📈 **Competitive Advantages**
1. **Event-Driven Speed**        - 0.12s Response für Trading-Decisions
2. **Multi-Horizon Predictions** - Kurz- und Langfrist-Strategien
3. **AI-powered Intelligence**   - Machine Learning Ensemble Methods
4. **Cross-System Correlation**  - Service-übergreifende Insights
5. **Complete Automation**       - Hands-off Trading Intelligence

---

## 🔮 **Future Roadmap**

### 📅 **Planned Enhancements**
- **🤖 Advanced AI Models**      - Deep Learning, Neural Networks
- **🌍 Global Market Expansion** - International Stock Markets
- **📱 Mobile Interface**        - Responsive Mobile Dashboard
- **🔗 Blockchain Integration**  - DeFi Trading Support
- **☁️ Cloud Scaling**           - Multi-region Deployment

---

*System Overview - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*