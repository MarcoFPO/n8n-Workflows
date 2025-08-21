# 🧠 Konzeptanpassung: KI-Vorhersage Integration

**Projekt**: Aktienanalyse-Ökosystem  
**Deployment**: 10.1.1.174 (LXC 174)  
**Status**: Angepasstes Konzept für KI-Vorhersage und Datenerhebung  
**Datum**: 17. August 2025  

---

## 📊 **Ausgangssituation**

### Bestehende Architektur (Production Ready):
- **8 Microservices** in Event-Driven Architecture
- **PostgreSQL Event-Store** mit Redis Event-Cache
- **8 Datenquellen** bereits konfiguriert und aktiv
- **systemd Integration** mit Auto-Recovery
- **GUI v7.0.1** mit CSV-Datenintegration

### Vorhersage-Anforderungen:
- **4 Prognosehorizonte**: 7, 30, 150, 365 Kalendertage
- **4-Modell-Ensemble**: Technisch (LSTM), Sentiment (XGBoost), Fundamental-Makro (XGBoost), Meta-Modell (LightGBM)
- **Variable Zeiträume** mit prozentualer Kursveränderung als Output

---

## 🏗️ **Angepasste Service-Architektur**

### Bestehende Services (Erweitert):
| Service | Port | Erweiterung | ML-Integration |
|---------|------|-------------|----------------|
| 🧠 **Intelligent Core** | 8001 | ✅ Erweitert | Meta-Modell Orchestrierung |
| 📡 **Data Processing** | 8017 | ✅ Erweitert | ML Feature Engineering |
| 🎯 **Prediction Tracking** | 8018 | ✅ Erweitert | Prognose-Performance Tracking |
| 🚌 **Event Bus** | 8014 | ✅ Erweitert | ML Event-Types |

### Neuer Service:
| Service | Port | Status | Beschreibung |
|---------|------|--------|--------------|
| 🤖 **ML Analytics** | 8019 | 🆕 Neu | KI-Modell Training & Inferenz |

---

## 📈 **Datenerhebung - Integration bestehender Quellen**

### Bestehende Datenquellen (Optimal nutzbar):
| Quelle | Verwendung ML | Modell-Integration |
|--------|---------------|-------------------|
| **Alpha Vantage** | ✅ Fundamentaldaten | Fundamental-Makro-Modell |
| **Twelve Data** | ✅ Globale Märkte | Technisches Modell (OHLCV) |
| **Finnhub** | ✅ Fundamentals + Sentiment | Sentiment + Fundamental-Modell |
| **ECB Macroeconomics** | ✅ Makroökonomie | Fundamental-Makro-Modell |
| **Marketstack** | ✅ Globale Börsen | Technisches Modell |
| **EOD Historical** | ✅ Historische Daten | Alle Modelle (Backtesting) |

### Neue Datenströme (Event-Bus Integration):
| Quelle | Event-Type | Zweck |
|--------|------------|-------|
| **NewsAPI** | `ml.sentiment.news.received` | Sentiment-Analyse |
| **Reddit API** | `ml.sentiment.social.received` | Social Media Sentiment |
| **FRED** | `ml.macro.fed.updated` | US-Makrodaten |

---

## 🤖 **ML-Modell Integration**

### Ensemble-Architektur:
```python
# Event-Driven ML Pipeline
1. data.ml.features.engineered → 
2. ml.model.technical.predicted →
3. ml.model.sentiment.predicted →  
4. ml.model.fundamental.predicted →
5. ml.ensemble.meta.predicted →
6. prediction.result.published
```

### Modell-Services:
| Modell | Framework | Service-Integration | Event-Output |
|--------|-----------|-------------------|--------------|
| **Technisches Modell** | TensorFlow/Keras LSTM | ML Analytics (8019) | `ml.technical.prediction.ready` |
| **Sentiment-Modell** | XGBoost | ML Analytics (8019) | `ml.sentiment.prediction.ready` |
| **Fundamental-Makro** | XGBoost | ML Analytics (8019) | `ml.fundamental.prediction.ready` |
| **Meta-Modell** | LightGBM | Intelligent Core (8001) | `ml.ensemble.prediction.final` |

---

## 🗄️ **Datenbank-Schema Erweiterung**

### Neue PostgreSQL Tabellen:
```sql
-- ML Feature Tables
ml_features_technical_daily     # Technische Indikatoren
ml_features_sentiment_daily     # Sentiment Scores
ml_features_fundamental_daily   # Fundamental + Makro Features

-- ML Output Tables  
ml_predictions                  # Alle Modell-Vorhersagen
ml_model_metadata              # Modell-Versionen und Parameter
ml_training_history            # Training-Logs und Performance

-- Event-Store Erweiterung
events                         # Neue ML Event-Types
materialized_views/
├── ml_prediction_performance  # Real-time ML Performance
├── ml_feature_importance      # Feature-Wichtigkeit
└── ml_ensemble_accuracy       # Ensemble-Genauigkeit
```

### Event-Store Integration:
- **Neue Event-Types**: `ml.prediction.*`, `ml.training.*`, `ml.evaluation.*`
- **Correlation-IDs**: Verknüpfung ML-Events mit Trading-Events
- **Performance Tracking**: Automatische SOLL-IST Vergleiche

---

## 🚀 **Implementierungsplan**

### **Phase 1: PoC Integration (1-2 Wochen)**
**Scope**: Technisches Modell für 7-Tage-Prognosen

**Arbeitspakete:**
1. **ML Analytics Service** erstellen (Port 8019)
2. **LSTM-Modell** für AAPL implementieren  
3. **Feature Engineering** in Data Processing Service
4. **Event-Bus Integration** für ML-Events
5. **systemd Service** konfigurieren

**Deliverable**: Funktionsfähige 7-Tage-Prognose für eine Aktie

### **Phase 2: Vollständiges Ensemble (2-3 Wochen)**
**Scope**: Alle 4 Modelle und 4 Prognosehorizonte

**Arbeitspakete:**
1. **Sentiment-Modell** (NewsAPI + Reddit Integration)
2. **Fundamental-Makro-Modell** (bestehende Datenquellen erweitern)
3. **Meta-Modell** in Intelligent Core Service
4. **GUI-Integration**: Neue Prognose-Tabs
5. **Alle Horizonte**: 7, 30, 150, 365 Tage

**Deliverable**: Vollständiges Ensemble-System

### **Phase 3: Produktiv-Optimierung (1 Woche)**
**Scope**: Performance und Automatisierung

**Arbeitspakete:**
1. **Hyperparameter-Tuning** für alle Modelle
2. **Automatisches Retraining** (tägliche/wöchentliche Pipeline)
3. **Performance-Monitoring** und Alerting
4. **Load-Testing** und Skalierung

**Deliverable**: Production-ready ML-System

---

## 📋 **Compliance mit bestehender Architektur**

### **Modul Versioning (VERPFLICHTEND):**
```bash
# Beispiel neuer ML-Module
ml_technical_model_v1_0_0_20250817.py
ml_sentiment_analyzer_v1_0_0_20250817.py  
ml_feature_engineer_v1_0_0_20250817.py
ml_ensemble_predictor_v1_0_0_20250817.py
```

### **Event-Driven Integration:**
- **Keine Breaking Changes** in bestehende Services
- **Backward Compatibility** für alle APIs
- **Asynchrone Verarbeitung** über Event-Bus

### **systemd Integration:**
```bash
# Neue Service-Files
aktienanalyse-ml-analytics-modular.service
aktienanalyse-ml-training-pipeline.service
```

### **No-Docker Policy:**
- **Native Python Services** mit systemd
- **Virtual Environment** Integration  
- **Native ML Libraries** (TensorFlow, XGBoost, LightGBM)

---

## 📊 **Performance-Ziele**

### **Response-Time Targets:**
- **Feature Engineering**: <500ms
- **Model Inference**: <200ms pro Modell
- **Ensemble Prediction**: <1s total
- **GUI Integration**: <2s für Prognose-Display

### **Accuracy Targets (Baseline):**
- **Directional Accuracy**: >55% (besser als Zufall)
- **7-Tage Prognosen**: >60% DA
- **30-Tage Prognosen**: >58% DA  
- **Längere Horizonte**: Best-Effort (hochspekulativ)

### **System Performance:**
- **Memory Usage**: +100MB für ML-Services
- **CPU Usage**: <70% unter ML-Load
- **Database Growth**: ~10MB/Tag für ML-Features

---

## 🎯 **Integration in bestehende GUI**

### **Neue Frontend-Features:**
| Feature | Integration | Beschreibung |
|---------|-------------|--------------|
| **Prognose-Tab** | Dashboard Extension | 4 Zeiträume mit Visualisierung |
| **Modell-Insights** | API Extension | Feature-Wichtigkeit und Confidence |
| **Performance-Tracking** | Existing SOLL-IST | ML-Prognose vs. Realität |
| **Model-Health** | Monitoring Integration | Modell-Status und Alerts |

### **API-Erweiterungen:**
```bash
# Neue Endpoints (Frontend Service 8080)
GET /api/ml/predictions/{symbol}        # Aktuelle Prognosen
GET /api/ml/models/performance          # Modell-Performance  
GET /api/ml/features/importance         # Feature-Wichtigkeit
POST /api/ml/models/retrain             # Manuelles Retraining
```

---

## 💾 **Memory MCP Integration**

### **Projekt-spezifische Persistierung:**
```python
# Memory Bank: aktienanalyse-ml-knowledge-20250817
{
    "ml_model_architectures": "LSTM + XGBoost + LightGBM Details",
    "training_hyperparameters": "Optimierte Parameter pro Modell", 
    "performance_benchmarks": "Baseline und Target-Metriken",
    "data_pipeline_config": "Feature Engineering Pipelines",
    "integration_events": "ML Event-Bus Schema"
}
```

---

## ✅ **Angepasstes Konzept - Fazit**

### **Optimale Integration:**
- **Bestehende Architektur**: Vollständig kompatibel
- **Event-Driven Design**: Nahtlose ML-Integration
- **Datenquellen**: 80% bereits verfügbar
- **Service-Pattern**: Konsistent mit bestehendem Design

### **Vorteile der Anpassung:**
1. **Inkrementelle Einführung** ohne System-Disruption
2. **Wiederverwendung** bestehender Infrastruktur
3. **Event-Bus Skalierung** für ML-Workloads
4. **Monitoring Integration** in bestehende Health-Checks

### **Nächster Schritt:**
**Phase 1 PoC** kann sofort begonnen werden - alle erforderlichen Komponenten sind verfügbar.

---

*Konzeptanpassung erstellt: 17. August 2025*  
*Kompatibel mit: Production System v5.1 FINAL*