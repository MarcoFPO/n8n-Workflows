# 🚌 Event-Bus Schema für ML-Integration v1.0.0

**Projekt**: Aktienanalyse-Ökosystem ML-Event-Bus  
**Version**: 1.0.0  
**Datum**: 17. August 2025  
**Integration**: Bestehende Event-Driven Architecture erweitern  

---

## 📋 **ML-Event-Types Erweiterung**

### **Bestehende Event-Types (8 Core Types):**
```python
# Bestehende Core Events bleiben unverändert
EXISTING_CORE_EVENTS = [
    'analysis.state.changed',      # Stock Analysis Lifecycle
    'portfolio.state.changed',     # Portfolio Performance Updates  
    'trading.state.changed',       # Trading Activity Events
    'intelligence.triggered',      # Cross-System Intelligence
    'data.synchronized',           # Data Sync Events
    'system.alert.raised',         # Health & Alert Events
    'user.interaction.logged',     # Frontend Interactions
    'config.updated'               # Configuration Changes
]
```

### **Neue ML-Event-Types (11 Neue Types):**
```python
# ML-spezifische Event-Erweiterung
ML_EVENT_TYPES = [
    'ml.features.calculated',          # Feature Engineering abgeschlossen
    'ml.model.prediction.generated',   # Modell-Prediction erstellt
    'ml.ensemble.prediction.ready',    # Ensemble-Prediction verfügbar
    'ml.model.training.started',       # Training-Prozess gestartet
    'ml.model.training.completed',     # Training abgeschlossen
    'ml.model.deployed',               # Neues Modell deployed
    'ml.prediction.validated',         # Prediction gegen Realität validiert
    'ml.performance.threshold.crossed', # Performance-Schwellwert über-/unterschritten
    'ml.data.drift.detected',         # Data-Drift in Features erkannt
    'ml.model.deprecated',             # Modell als veraltet markiert
    'ml.ensemble.weights.updated'      # Ensemble-Gewichtung angepasst
]
```

---

## 🎯 **ML-Event Schema Definitionen**

### **1. ml.features.calculated**
```json
{
  "event_type": "ml.features.calculated",
  "version": "1.0",
  "schema": {
    "event_id": "uuid",
    "correlation_id": "uuid",
    "timestamp": "datetime_iso8601",
    "source_service": "string",
    "payload": {
      "symbol": "string",
      "feature_type": "string", // 'technical', 'sentiment', 'fundamental'
      "calculation_timestamp": "datetime_iso8601",
      "features": {
        "technical": {
          "momentum": {
            "rsi_14": "number",
            "macd_signal": "number",
            "stoch_k": "number"
          },
          "trend": {
            "sma_20": "number",
            "sma_50": "number", 
            "ema_20": "number"
          },
          "volatility": {
            "bb_upper": "number",
            "bb_lower": "number",
            "atr_14": "number"
          }
        },
        "sentiment": {
          "avg_sentiment_score": "number", // -1 to +1
          "sentiment_volume": "integer",
          "positive_ratio": "number",
          "news_sentiment": "number",
          "social_sentiment": "number"
        },
        "fundamental": {
          "eps_ttm": "number",
          "pe_ratio": "number",
          "debt_to_equity": "number",
          "vix_level": "number",
          "fed_rate": "number"
        }
      },
      "feature_count": "integer",
      "data_quality_score": "number", // 0.0 to 1.0
      "calculation_duration_ms": "integer"
    }
  }
}
```

### **2. ml.model.prediction.generated**
```json
{
  "event_type": "ml.model.prediction.generated",
  "version": "1.0", 
  "schema": {
    "event_id": "uuid",
    "correlation_id": "uuid",
    "timestamp": "datetime_iso8601",
    "source_service": "string",
    "payload": {
      "prediction_id": "uuid",
      "symbol": "string",
      "model_type": "string", // 'technical', 'sentiment', 'fundamental'
      "model_version": "string", // 'v1.0.0_20250817'
      "prediction_timestamp": "datetime_iso8601",
      "horizons": {
        "7d": {
          "prediction_values": ["number"], // [day1_pct, day2_pct, ..., day7_pct]
          "confidence_score": "number",    // 0.0 to 1.0
          "volatility_estimate": "number"
        },
        "30d": {
          "prediction_values": ["number"],
          "confidence_score": "number",
          "volatility_estimate": "number"
        },
        "150d": {
          "prediction_values": ["number"],
          "confidence_score": "number",
          "volatility_estimate": "number"
        },
        "365d": {
          "prediction_values": ["number"],
          "confidence_score": "number",
          "volatility_estimate": "number"
        }
      },
      "feature_importance": {
        "top_features": [
          {
            "feature_name": "string",
            "importance_score": "number"
          }
        ]
      },
      "inference_duration_ms": "integer",
      "triggered_by_event_id": "uuid"
    }
  }
}
```

### **3. ml.ensemble.prediction.ready**
```json
{
  "event_type": "ml.ensemble.prediction.ready",
  "version": "1.0",
  "schema": {
    "event_id": "uuid",
    "correlation_id": "uuid", 
    "timestamp": "datetime_iso8601",
    "source_service": "string",
    "payload": {
      "ensemble_prediction_id": "uuid",
      "symbol": "string",
      "ensemble_timestamp": "datetime_iso8601",
      "individual_predictions": {
        "technical": {
          "prediction_id": "uuid",
          "confidence": "number",
          "weight_in_ensemble": "number"
        },
        "sentiment": {
          "prediction_id": "uuid", 
          "confidence": "number",
          "weight_in_ensemble": "number"
        },
        "fundamental": {
          "prediction_id": "uuid",
          "confidence": "number", 
          "weight_in_ensemble": "number"
        }
      },
      "final_predictions": {
        "7d": {
          "prediction_values": ["number"],
          "ensemble_confidence": "number",
          "prediction_interval": {
            "lower_bound": ["number"],
            "upper_bound": ["number"]
          }
        },
        "30d": {
          "prediction_values": ["number"],
          "ensemble_confidence": "number",
          "prediction_interval": {
            "lower_bound": ["number"],
            "upper_bound": ["number"]
          }
        },
        "150d": {
          "prediction_values": ["number"],
          "ensemble_confidence": "number",
          "prediction_interval": {
            "lower_bound": ["number"],
            "upper_bound": ["number"]
          }
        },
        "365d": {
          "prediction_values": ["number"],
          "ensemble_confidence": "number",
          "prediction_interval": {
            "lower_bound": ["number"],
            "upper_bound": ["number"]
          }
        }
      },
      "ensemble_method": "string", // 'weighted_average', 'meta_model'
      "ensemble_duration_ms": "integer"
    }
  }
}
```

### **4. ml.model.training.completed**
```json
{
  "event_type": "ml.model.training.completed",
  "version": "1.0",
  "schema": {
    "event_id": "uuid",
    "correlation_id": "uuid",
    "timestamp": "datetime_iso8601", 
    "source_service": "string",
    "payload": {
      "training_id": "uuid",
      "model_id": "uuid",
      "model_type": "string",
      "model_version": "string",
      "horizon_days": "integer",
      "training_config": {
        "training_data_start": "date",
        "training_data_end": "date",
        "validation_split": "number",
        "test_split": "number",
        "hyperparameters": "object"
      },
      "training_results": {
        "epochs_trained": "integer",
        "final_training_loss": "number",
        "final_validation_loss": "number",
        "training_duration_seconds": "integer",
        "convergence_achieved": "boolean"
      },
      "performance_metrics": {
        "mae_score": "number",
        "mse_score": "number", 
        "directional_accuracy": "number",
        "r2_score": "number",
        "sharpe_ratio": "number"
      },
      "model_artifacts": {
        "model_file_path": "string",
        "scaler_file_path": "string",
        "artifact_checksum": "string"
      },
      "ready_for_deployment": "boolean"
    }
  }
}
```

### **5. ml.prediction.validated**
```json
{
  "event_type": "ml.prediction.validated",
  "version": "1.0",
  "schema": {
    "event_id": "uuid",
    "correlation_id": "uuid",
    "timestamp": "datetime_iso8601",
    "source_service": "string",
    "payload": {
      "validation_id": "uuid",
      "original_prediction_id": "uuid",
      "symbol": "string",
      "model_type": "string",
      "horizon_days": "integer",
      "prediction_date": "date",
      "validation_date": "date",
      "original_prediction": {
        "prediction_values": ["number"],
        "confidence_score": "number"
      },
      "actual_outcome": {
        "actual_values": ["number"], // Tatsächliche Kursentwicklung
        "actual_volatility": "number"
      },
      "validation_metrics": {
        "absolute_error": "number",
        "relative_error": "number", 
        "directional_accuracy": "boolean",
        "confidence_calibration": "number" // Wie gut war die Confidence-Schätzung
      },
      "model_performance_impact": {
        "should_retrain": "boolean",
        "performance_degradation": "number",
        "recommendation": "string"
      }
    }
  }
}
```

---

## 🔄 **Event-Routing-Konfiguration**

### **ML-Event-Routing erweitert bestehende Konfiguration:**
```python
# ml_event_routing_v1_0_0_20250817.py

# Bestehende Routing-Regeln bleiben unverändert
EXISTING_ROUTING = {
    'analysis.state.changed': ['frontend', 'portfolio-analytics', 'trading-interface'],
    'portfolio.state.changed': ['frontend', 'risk-assessment', 'performance-tracking'],
    'trading.state.changed': ['broker-gateway', 'portfolio-analytics', 'risk-assessment'],
    # ... weitere bestehende Regeln
}

# Neue ML-Routing-Regeln
ML_EVENT_ROUTING = {
    # Feature Engineering Events
    'market.data.updated': [
        'data-processing:calculate_ml_features',
        'ml-analytics:trigger_feature_calculation'
    ],
    
    'ml.features.calculated': [
        'ml-analytics:generate_model_predictions',
        'monitoring:track_feature_quality',
        'data-processing:store_ml_features'
    ],
    
    # Prediction Events
    'ml.model.prediction.generated': [
        'intelligent-core:ensemble_prediction',
        'prediction-tracking:store_individual_prediction',
        'frontend:update_prediction_display',
        'monitoring:track_prediction_metrics'
    ],
    
    'ml.ensemble.prediction.ready': [
        'frontend:display_final_prediction',
        'prediction-tracking:store_ensemble_prediction',
        'trading-interface:consider_prediction_signal',
        'portfolio-analytics:incorporate_ml_insights'
    ],
    
    # Training Events
    'ml.model.training.started': [
        'monitoring:track_training_progress',
        'frontend:show_training_status'
    ],
    
    'ml.model.training.completed': [
        'ml-analytics:evaluate_new_model',
        'ml-analytics:deploy_if_better',
        'monitoring:update_model_registry',
        'frontend:notify_model_update'
    ],
    
    'ml.model.deployed': [
        'all-services:use_new_model_version',
        'monitoring:activate_model_monitoring',
        'frontend:show_model_deployment_success'
    ],
    
    # Validation Events
    'ml.prediction.validated': [
        'ml-analytics:update_model_performance',
        'intelligent-core:adjust_ensemble_weights',
        'monitoring:alert_if_performance_degraded',
        'prediction-tracking:update_accuracy_metrics'
    ],
    
    # Performance Events
    'ml.performance.threshold.crossed': [
        'ml-analytics:trigger_retraining',
        'monitoring:alert_performance_issue',
        'intelligent-core:adjust_model_weights'
    ],
    
    'ml.data.drift.detected': [
        'ml-analytics:trigger_feature_analysis',
        'data-processing:investigate_data_sources',
        'monitoring:alert_data_quality_issue'
    ]
}

# Zusammengeführte Routing-Konfiguration
COMPLETE_EVENT_ROUTING = {**EXISTING_ROUTING, **ML_EVENT_ROUTING}
```

---

## 📊 **Event-Performance-Konfiguration**

### **ML-Event-Performance-Targets:**
```python
# ml_event_performance_v1_0_0_20250817.py

ML_EVENT_PERFORMANCE_TARGETS = {
    'ml.features.calculated': {
        'processing_time_ms': 500,
        'payload_size_kb': 50,
        'subscribers': ['ml-analytics', 'monitoring', 'data-processing'],
        'delivery_guarantee': 'at_least_once',
        'retention_hours': 24
    },
    
    'ml.model.prediction.generated': {
        'processing_time_ms': 200,
        'payload_size_kb': 20,
        'subscribers': ['intelligent-core', 'prediction-tracking', 'frontend', 'monitoring'],
        'delivery_guarantee': 'exactly_once',
        'retention_hours': 168  # 7 Tage
    },
    
    'ml.ensemble.prediction.ready': {
        'processing_time_ms': 100,
        'payload_size_kb': 30,
        'subscribers': ['frontend', 'prediction-tracking', 'trading-interface', 'portfolio-analytics'],
        'delivery_guarantee': 'exactly_once',
        'retention_hours': 720  # 30 Tage
    },
    
    'ml.model.training.completed': {
        'processing_time_ms': 1000,
        'payload_size_kb': 100,
        'subscribers': ['ml-analytics', 'monitoring', 'frontend'],
        'delivery_guarantee': 'at_least_once',
        'retention_hours': 8760  # 365 Tage
    },
    
    'ml.prediction.validated': {
        'processing_time_ms': 300,
        'payload_size_kb': 15,
        'subscribers': ['ml-analytics', 'intelligent-core', 'monitoring', 'prediction-tracking'],
        'delivery_guarantee': 'exactly_once',
        'retention_hours': 8760  # 365 Tage - wichtig für Performance-Tracking
    }
}
```

### **Event-Bus-Kapazitäts-Planung:**
```python
# ml_event_capacity_planning_v1_0_0_20250817.py

ML_EVENT_VOLUME_ESTIMATES = {
    'daily_estimates': {
        'ml.features.calculated': 1000,      # Pro Symbol, 3 Feature-Types
        'ml.model.prediction.generated': 300, # Pro Symbol, 3 Modelle
        'ml.ensemble.prediction.ready': 100,  # Pro Symbol, finales Ensemble
        'ml.prediction.validated': 50,        # Validierung nach N Tagen
        'ml.model.training.completed': 5,     # Wöchentliches Retraining
    },
    
    'peak_estimates': {
        'market_open_burst': '5x daily_average',
        'training_completion_burst': '10x during training windows',
        'validation_batch_burst': '20x during nightly validation runs'
    },
    
    'storage_requirements': {
        'event_retention_gb_per_month': 2.5,
        'ml_feature_data_gb_per_month': 15.0,
        'prediction_data_gb_per_month': 8.0,
        'model_artifacts_gb_per_month': 5.0
    }
}
```

---

## 🔍 **Event-Monitoring und Alerting**

### **ML-Event Health-Checks:**
```python
# ml_event_monitoring_v1_0_0_20250817.py

class MLEventMonitoring:
    def __init__(self):
        self.alert_thresholds = {
            'feature_calculation_delay_minutes': 15,
            'prediction_generation_delay_minutes': 5,
            'ensemble_completion_delay_minutes': 2,
            'model_training_timeout_hours': 6,
            'validation_backlog_count': 100
        }
    
    async def monitor_ml_event_health(self):
        health_metrics = {}
        
        # Feature Calculation Health
        health_metrics['feature_calculation'] = await self.check_feature_calculation_health()
        
        # Prediction Generation Health
        health_metrics['prediction_generation'] = await self.check_prediction_health()
        
        # Model Training Health
        health_metrics['model_training'] = await self.check_training_health()
        
        # Event-Bus Performance
        health_metrics['event_bus_performance'] = await self.check_event_bus_performance()
        
        return health_metrics
    
    async def check_feature_calculation_health(self):
        """Überprüft Health der Feature-Calculation-Pipeline"""
        last_features = await self.event_store.query("""
            SELECT symbol, MAX(timestamp) as last_calculation
            FROM events e
            WHERE e.event_type = 'ml.features.calculated'
            AND e.timestamp >= NOW() - INTERVAL '1 hour'
            GROUP BY symbol
        """)
        
        delayed_symbols = []
        for symbol_data in last_features:
            delay_minutes = (datetime.utcnow() - symbol_data['last_calculation']).total_seconds() / 60
            if delay_minutes > self.alert_thresholds['feature_calculation_delay_minutes']:
                delayed_symbols.append({
                    'symbol': symbol_data['symbol'],
                    'delay_minutes': delay_minutes
                })
        
        return {
            'status': 'healthy' if not delayed_symbols else 'warning',
            'delayed_symbols': delayed_symbols,
            'total_symbols_processed': len(last_features)
        }
```

### **Event-Schema-Validierung:**
```python
# ml_event_validation_v1_0_0_20250817.py

from jsonschema import validate, ValidationError

class MLEventValidator:
    def __init__(self):
        self.schemas = self.load_ml_event_schemas()
    
    def validate_ml_event(self, event_type, event_payload):
        """Validiert ML-Event gegen Schema"""
        try:
            schema = self.schemas.get(event_type)
            if not schema:
                raise ValueError(f"Unknown ML event type: {event_type}")
            
            validate(instance=event_payload, schema=schema)
            return {'valid': True, 'errors': []}
            
        except ValidationError as e:
            return {
                'valid': False,
                'errors': [str(e)],
                'schema_path': e.schema_path
            }
    
    def load_ml_event_schemas(self):
        """Lädt alle ML-Event-Schemas"""
        return {
            'ml.features.calculated': ML_FEATURES_SCHEMA,
            'ml.model.prediction.generated': ML_PREDICTION_SCHEMA,
            'ml.ensemble.prediction.ready': ML_ENSEMBLE_SCHEMA,
            'ml.model.training.completed': ML_TRAINING_SCHEMA,
            'ml.prediction.validated': ML_VALIDATION_SCHEMA
        }
```

---

## 🚀 **Event-Bus Deployment-Updates**

### **Redis-Konfiguration für ML-Events:**
```python
# ml_redis_config_v1_0_0_20250817.py

ML_REDIS_CONFIG = {
    'ml_events_db': 2,  # Separate DB für ML-Events
    'ml_cache_db': 3,   # Separate DB für ML-Cache
    
    'stream_config': {
        'ml-features-stream': {
            'maxlen': 10000,
            'retention_hours': 24
        },
        'ml-predictions-stream': {
            'maxlen': 50000,
            'retention_hours': 168  # 7 Tage
        },
        'ml-training-stream': {
            'maxlen': 1000,
            'retention_hours': 8760  # 365 Tage
        }
    },
    
    'consumer_groups': {
        'ml-analytics-group': ['ml-features-stream', 'ml-predictions-stream'],
        'monitoring-ml-group': ['ml-features-stream', 'ml-predictions-stream', 'ml-training-stream'],
        'frontend-ml-group': ['ml-predictions-stream']
    }
}
```

### **Event-Bus Service-Update:**
```python
# event_bus_ml_integration_v1_5_0_20250817.py

class EventBusMLIntegration:
    def __init__(self):
        self.ml_event_handlers = {}
        self.ml_event_validators = MLEventValidator()
        self.ml_performance_tracker = MLEventPerformanceTracker()
    
    async def publish_ml_event(self, event_type, payload, correlation_id=None):
        """Publiziert ML-Events mit Validierung und Performance-Tracking"""
        
        # Event-Validierung
        validation_result = self.ml_event_validators.validate_ml_event(event_type, payload)
        if not validation_result['valid']:
            raise ValueError(f"Invalid ML event: {validation_result['errors']}")
        
        # Performance-Tracking starten
        perf_start = time.time()
        
        # Event erstellen
        event = {
            'event_id': str(uuid.uuid4()),
            'event_type': event_type,
            'correlation_id': correlation_id or str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'source_service': self.service_name,
            'payload': payload
        }
        
        # Event publizieren
        await self.publish_to_stream(f"ml-{event_type.split('.')[1]}-stream", event)
        
        # Performance-Tracking beenden
        duration_ms = (time.time() - perf_start) * 1000
        await self.ml_performance_tracker.track_event_performance(event_type, duration_ms)
        
        return event['event_id']
```

---

## ✅ **Integration-Checklist**

### **Event-Bus-Schema-Deployment:**
- [ ] ML-Event-Types in Event-Store registrieren
- [ ] Redis-Streams für ML-Events konfigurieren
- [ ] Consumer-Groups für alle Services erstellen
- [ ] Event-Schema-Validierung aktivieren
- [ ] Performance-Monitoring für ML-Events einrichten

### **Service-Integration:**
- [ ] ML Analytics Service: Event-Handlers implementieren
- [ ] Data Processing Service: ML-Feature-Events hinzufügen
- [ ] Intelligent Core Service: Ensemble-Events integrieren
- [ ] Frontend Service: ML-Prediction-Events abonnieren
- [ ] Monitoring Service: ML-Health-Checks hinzufügen

### **Testing und Validation:**
- [ ] End-to-End Event-Flow testen
- [ ] Performance-Benchmarks durchführen
- [ ] Schema-Validierung testen
- [ ] Event-Retention und Cleanup testen

---

*ML Event-Bus Schema erstellt: 17. August 2025*  
*Version: 1.0.0*  
*Integriert mit: Event-Bus Service v1.5.0*