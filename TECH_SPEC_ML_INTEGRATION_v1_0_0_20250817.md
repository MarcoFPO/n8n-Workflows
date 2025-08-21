# 🤖 Technische Spezifikation: ML-Integration v1.0.0

**Projekt**: Aktienanalyse-Ökosystem ML-Erweiterung  
**Version**: 1.0.0  
**Datum**: 17. August 2025  
**Status**: Technische Implementierungsanweisungen  
**Deployment**: 10.1.1.174 (LXC 174)  

---

## 📋 **Überarbeitete LLD-Dokumentation**

### **LLD 1: Technisches Modell - Event-Bus Integration**

#### **1.1. Angepasste Architektur für Event-Driven System**
```python
# Service: ML Analytics Service (Port 8019)
# Modul: ml_technical_model_v1_0_0_20250817.py

class TechnicalModelService(ServiceBase):
    def __init__(self):
        super().__init__("ml-analytics-technical", 8019)
        self.event_bus = EventBusConnection()
        self.model_cache = {}
        
    def on_market_data_updated(self, event):
        """Reagiert auf market.data.updated Events"""
        symbol = event.payload.get('symbol')
        self.generate_technical_prediction(symbol)
```

#### **1.2. Integration in bestehende Datenströme**
**Input-Datenquellen (Bestehende Services):**
- **Twelve Data Service**: OHLCV über Event-Bus
- **Alpha Vantage Service**: Zusätzliche technische Indikatoren
- **Data Processing Service**: Feature Engineering Pipeline

**Event-Integration:**
```python
# Event-Flow für Technisches Modell
market.data.updated (symbol=AAPL) →
ml.features.technical.calculated (features=[RSI, MACD, BB]) →
ml.technical.prediction.generated (prediction_7d, prediction_30d) →
ml.ensemble.input.ready (technical_prediction)
```

#### **1.3. Erweiterte Feature-Pipeline**
```python
# Modul: ml_feature_engineering_v1_0_0_20250817.py

TECHNICAL_FEATURES = {
    'momentum': ['RSI_14', 'MACD_12_26_9', 'STOCH_14_3'],
    'trend': ['SMA_20', 'SMA_50', 'SMA_200', 'EMA_20', 'EMA_50'],
    'volatility': ['BB_UPPER_20', 'BB_LOWER_20', 'ATR_14'],
    'volume': ['VOLUME_SMA_20', 'VOLUME_RATIO'],
    'price_action': ['DAILY_RETURN', 'WEEKLY_RETURN', 'HIGH_LOW_RATIO']
}

def calculate_technical_features(ohlcv_data):
    """Berechnet alle technischen Indikatoren für Event-Bus"""
    features = {}
    
    for category, indicators in TECHNICAL_FEATURES.items():
        features[category] = calculate_indicators(ohlcv_data, indicators)
    
    return features
```

#### **1.4. LSTM-Architektur für Multi-Horizon Prediction**
```python
# Erweiterte Architektur für 4 Prognosehorizonte
def build_multi_horizon_lstm(sequence_length=60, n_features=25):
    model = Sequential([
        InputLayer(shape=(sequence_length, n_features)),
        
        # Shared LSTM Layers
        LSTM(128, return_sequences=True, name='lstm_shared_1'),
        Dropout(0.2),
        LSTM(64, return_sequences=True, name='lstm_shared_2'),
        Dropout(0.2),
        LSTM(32, return_sequences=False, name='lstm_shared_3'),
        Dropout(0.2),
        
        # Multi-Head Output für verschiedene Horizonte
        Dense(64, activation='relu', name='dense_shared'),
        Dropout(0.1)
    ])
    
    # Separate Output-Heads für jeden Horizont
    output_7d = Dense(7, activation='linear', name='pred_7d')(model.output)
    output_30d = Dense(30, activation='linear', name='pred_30d')(model.output)
    output_150d = Dense(150, activation='linear', name='pred_150d')(model.output)
    output_365d = Dense(365, activation='linear', name='pred_365d')(model.output)
    
    return Model(inputs=model.input, 
                outputs=[output_7d, output_30d, output_150d, output_365d])
```

---

### **LLD 2: Datenbank-Schema für Event-Store Integration**

#### **2.1. Erweiterte PostgreSQL-Tabellen**
```sql
-- ML Feature Tables (TimescaleDB Hypertables)
CREATE TABLE ml_features_technical_daily (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    security_id INTEGER REFERENCES securities(security_id),
    
    -- Momentum Features
    rsi_14 NUMERIC(8,4),
    macd_signal_12_26_9 NUMERIC(8,4),
    macd_histogram_12_26_9 NUMERIC(8,4),
    stoch_k_14_3 NUMERIC(8,4),
    stoch_d_14_3 NUMERIC(8,4),
    
    -- Trend Features  
    sma_20 NUMERIC(12,4),
    sma_50 NUMERIC(12,4),
    sma_200 NUMERIC(12,4),
    ema_20 NUMERIC(12,4),
    ema_50 NUMERIC(12,4),
    
    -- Volatility Features
    bb_upper_20_2 NUMERIC(12,4),
    bb_middle_20_2 NUMERIC(12,4),
    bb_lower_20_2 NUMERIC(12,4),
    atr_14 NUMERIC(8,4),
    
    -- Volume Features
    volume_sma_20 BIGINT,
    volume_ratio NUMERIC(6,4),
    
    -- Price Action Features
    daily_return NUMERIC(8,6),
    weekly_return NUMERIC(8,6),
    high_low_ratio NUMERIC(8,4),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    event_correlation_id UUID,
    
    PRIMARY KEY (timestamp, symbol)
);

-- ML Predictions Table
CREATE TABLE ml_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'technical', 'sentiment', 'fundamental', 'ensemble'
    horizon_days INTEGER NOT NULL,   -- 7, 30, 150, 365
    
    -- Prediction Values (JSON for flexibility)
    prediction_values JSONB NOT NULL, -- [day1_pct, day2_pct, ..., dayN_pct]
    confidence_score NUMERIC(5,4),
    
    -- Model Metadata
    model_version VARCHAR(50) NOT NULL,
    feature_importance JSONB,
    
    -- Event Integration
    event_correlation_id UUID,
    trigger_event_type VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    INDEX (symbol, prediction_timestamp),
    INDEX (model_type, horizon_days),
    INDEX (event_correlation_id)
);

-- ML Model Metadata
CREATE TABLE ml_model_metadata (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type VARCHAR(50) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    horizon_days INTEGER NOT NULL,
    
    -- Model Configuration
    architecture_config JSONB NOT NULL,
    training_config JSONB NOT NULL,
    hyperparameters JSONB NOT NULL,
    
    -- Performance Metrics
    training_metrics JSONB,
    validation_metrics JSONB,
    test_metrics JSONB,
    
    -- File Paths
    model_file_path VARCHAR(500),
    scaler_file_path VARCHAR(500),
    
    -- Status
    status VARCHAR(20) DEFAULT 'training', -- 'training', 'active', 'deprecated'
    
    -- Timestamps
    training_started_at TIMESTAMPTZ,
    training_completed_at TIMESTAMPTZ,
    deployed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (model_type, model_version, horizon_days)
);

-- ML Training History
CREATE TABLE ml_training_history (
    training_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID REFERENCES ml_model_metadata(model_id),
    
    -- Training Configuration
    training_data_start_date DATE NOT NULL,
    training_data_end_date DATE NOT NULL,
    validation_split NUMERIC(3,2),
    test_split NUMERIC(3,2),
    
    -- Training Results
    final_training_loss NUMERIC(10,6),
    final_validation_loss NUMERIC(10,6),
    epochs_trained INTEGER,
    training_duration_seconds INTEGER,
    
    -- Performance Metrics
    mae_score NUMERIC(8,6),
    mse_score NUMERIC(8,6),
    directional_accuracy NUMERIC(5,4),
    
    -- Event Integration
    triggered_by_event_id UUID,
    
    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create Hypertables
SELECT create_hypertable('ml_features_technical_daily', 'timestamp');
SELECT create_hypertable('ml_predictions', 'prediction_timestamp');
```

#### **2.2. Event-Store Schema-Erweiterung**
```sql
-- Neue Event-Types für ML-Integration
INSERT INTO event_types (event_type, description, schema_version) VALUES
('ml.features.technical.calculated', 'Technical features calculated for symbol', '1.0'),
('ml.features.sentiment.calculated', 'Sentiment features calculated for symbol', '1.0'),
('ml.features.fundamental.calculated', 'Fundamental features calculated for symbol', '1.0'),
('ml.model.technical.predicted', 'Technical model prediction generated', '1.0'),
('ml.model.sentiment.predicted', 'Sentiment model prediction generated', '1.0'),
('ml.model.fundamental.predicted', 'Fundamental model prediction generated', '1.0'),
('ml.ensemble.prediction.generated', 'Ensemble prediction generated', '1.0'),
('ml.model.training.started', 'Model training process started', '1.0'),
('ml.model.training.completed', 'Model training process completed', '1.0'),
('ml.model.deployed', 'New model version deployed', '1.0'),
('ml.prediction.validated', 'Prediction accuracy validated against actual', '1.0');

-- Materialized Views für ML-Performance
CREATE MATERIALIZED VIEW ml_prediction_performance_unified AS
SELECT 
    p.symbol,
    p.model_type,
    p.horizon_days,
    COUNT(*) as total_predictions,
    AVG(p.confidence_score) as avg_confidence,
    AVG(CASE WHEN v.actual_outcome IS NOT NULL 
        THEN ABS(v.actual_outcome - p.prediction_values->0::text::numeric) 
        END) as avg_absolute_error,
    AVG(CASE WHEN v.actual_outcome IS NOT NULL AND 
        ((v.actual_outcome > 0 AND p.prediction_values->0::text::numeric > 0) OR
         (v.actual_outcome < 0 AND p.prediction_values->0::text::numeric < 0))
        THEN 1 ELSE 0 END) as directional_accuracy,
    DATE_TRUNC('day', p.prediction_timestamp) as prediction_date
FROM ml_predictions p
LEFT JOIN ml_prediction_validations v ON p.prediction_id = v.prediction_id
WHERE p.created_at >= NOW() - INTERVAL '30 days'
GROUP BY p.symbol, p.model_type, p.horizon_days, DATE_TRUNC('day', p.prediction_timestamp)
ORDER BY prediction_date DESC;
```

---

### **LLD 3: Event-Bus Schema für ML-Events**

#### **3.1. Erweiterte Event-Types**
```python
# ml_event_schemas_v1_0_0_20250817.py

ML_EVENT_SCHEMAS = {
    'ml.features.technical.calculated': {
        'version': '1.0',
        'payload': {
            'symbol': 'str',
            'timestamp': 'datetime',
            'features': {
                'momentum': 'dict',
                'trend': 'dict', 
                'volatility': 'dict',
                'volume': 'dict',
                'price_action': 'dict'
            },
            'feature_count': 'int',
            'calculation_duration_ms': 'int'
        }
    },
    
    'ml.model.technical.predicted': {
        'version': '1.0',
        'payload': {
            'symbol': 'str',
            'model_version': 'str',
            'prediction_timestamp': 'datetime',
            'horizons': {
                '7d': 'list[float]',
                '30d': 'list[float]',
                '150d': 'list[float]',
                '365d': 'list[float]'
            },
            'confidence_scores': {
                '7d': 'float',
                '30d': 'float', 
                '150d': 'float',
                '365d': 'float'
            },
            'feature_importance': 'dict',
            'inference_duration_ms': 'int'
        }
    },
    
    'ml.ensemble.prediction.generated': {
        'version': '1.0',
        'payload': {
            'symbol': 'str',
            'prediction_id': 'uuid',
            'ensemble_timestamp': 'datetime',
            'individual_predictions': {
                'technical': 'dict',
                'sentiment': 'dict',
                'fundamental': 'dict'
            },
            'final_predictions': {
                '7d': 'list[float]',
                '30d': 'list[float]',
                '150d': 'list[float]',
                '365d': 'list[float]'
            },
            'ensemble_confidence': 'float',
            'model_weights': 'dict'
        }
    }
}
```

#### **3.2. Event-Bus Routing Configuration**
```python
# ml_event_routing_v1_0_0_20250817.py

ML_EVENT_ROUTING = {
    # Feature Calculation Events
    'market.data.updated': [
        'ml-analytics:calculate_technical_features',
        'data-processing:update_ml_features'
    ],
    
    # Prediction Events
    'ml.features.technical.calculated': [
        'ml-analytics:generate_technical_prediction',
        'monitoring:track_feature_calculation'
    ],
    
    'ml.model.technical.predicted': [
        'intelligent-core:ensemble_prediction',
        'prediction-tracking:store_prediction'
    ],
    
    # Training Events
    'ml.model.training.completed': [
        'ml-analytics:deploy_new_model',
        'monitoring:update_model_status',
        'frontend:notify_model_update'
    ],
    
    # Validation Events
    'ml.prediction.validated': [
        'ml-analytics:update_model_performance',
        'intelligent-core:adjust_ensemble_weights'
    ]
}
```

---

### **LLD 4: ML Analytics Service Spezifikation**

#### **4.1. Service-Architektur**
```python
# ml_analytics_service_v1_0_0_20250817.py

class MLAnalyticsService(ServiceBase):
    """
    ML Analytics Service - Port 8019
    Verantwortlich für ML-Modell Training, Inferenz und Feature Engineering
    """
    
    def __init__(self):
        super().__init__("ml-analytics", 8019)
        self.feature_engineers = {
            'technical': TechnicalFeatureEngineer(),
            'sentiment': SentimentFeatureEngineer(), 
            'fundamental': FundamentalFeatureEngineer()
        }
        self.models = {
            'technical': TechnicalModelManager(),
            'sentiment': SentimentModelManager(),
            'fundamental': FundamentalModelManager()
        }
        self.prediction_cache = PredictionCache()
        
    async def handle_market_data_updated(self, event):
        """Reagiert auf market.data.updated Events"""
        symbol = event.payload['symbol']
        
        # Feature Engineering
        features = await self.calculate_all_features(symbol)
        
        # Feature Events senden
        await self.event_bus.publish('ml.features.technical.calculated', {
            'symbol': symbol,
            'features': features['technical'],
            'timestamp': datetime.utcnow()
        })
        
    async def handle_prediction_request(self, event):
        """Generiert Predictions für alle Horizonte"""
        symbol = event.payload['symbol']
        model_type = event.payload.get('model_type', 'technical')
        
        predictions = await self.models[model_type].predict_all_horizons(symbol)
        
        await self.event_bus.publish(f'ml.model.{model_type}.predicted', {
            'symbol': symbol,
            'predictions': predictions,
            'model_version': self.models[model_type].version
        })
        
    async def start_training_pipeline(self, model_type, symbols):
        """Startet Training-Pipeline für Modell-Typ"""
        training_id = str(uuid.uuid4())
        
        await self.event_bus.publish('ml.model.training.started', {
            'training_id': training_id,
            'model_type': model_type,
            'symbols': symbols
        })
        
        # Asynchrones Training
        asyncio.create_task(self._train_model_async(model_type, symbols, training_id))
```

#### **4.2. API-Endpoints**
```python
# ml_analytics_api_v1_0_0_20250817.py

@app.route('/health', methods=['GET'])
async def health_check():
    """Service Health Check"""
    return {
        'service': 'ml-analytics',
        'status': 'healthy',
        'version': '1.0.0',
        'models_loaded': len(self.models),
        'active_predictions': self.prediction_cache.size(),
        'event_bus_connected': self.event_bus.is_connected()
    }

@app.route('/api/v1/predict/<symbol>', methods=['POST'])
async def predict_symbol(symbol):
    """Generiert Prediction für Symbol"""
    data = await request.get_json()
    horizons = data.get('horizons', [7, 30, 150, 365])
    model_type = data.get('model_type', 'ensemble')
    
    predictions = await generate_predictions(symbol, horizons, model_type)
    
    return {
        'symbol': symbol,
        'predictions': predictions,
        'generated_at': datetime.utcnow().isoformat(),
        'model_type': model_type
    }

@app.route('/api/v1/models/performance', methods=['GET'])
async def get_model_performance():
    """Aktuelle Modell-Performance"""
    performance = await self.db.query("""
        SELECT model_type, horizon_days, avg_confidence, directional_accuracy
        FROM ml_prediction_performance_unified
        WHERE prediction_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY model_type, horizon_days
    """)
    
    return {
        'performance_data': performance,
        'last_updated': datetime.utcnow().isoformat()
    }

@app.route('/api/v1/features/<symbol>', methods=['GET'])
async def get_features(symbol):
    """Aktuelle Features für Symbol"""
    features = await self.db.query("""
        SELECT * FROM ml_features_technical_daily 
        WHERE symbol = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, [symbol])
    
    return {
        'symbol': symbol,
        'features': features[0] if features else None,
        'retrieved_at': datetime.utcnow().isoformat()
    }

@app.route('/api/v1/training/start', methods=['POST'])
async def start_training():
    """Startet Modell-Training"""
    data = await request.get_json()
    model_type = data.get('model_type', 'technical')
    symbols = data.get('symbols', ['AAPL'])
    
    training_id = await self.start_training_pipeline(model_type, symbols)
    
    return {
        'training_id': training_id,
        'status': 'started',
        'model_type': model_type,
        'symbols': symbols
    }
```

---

### **LLD 5: Frontend-Integration Spezifikation**

#### **5.1. GUI-Erweiterungen**
```javascript
// ml_prediction_component_v1_0_0_20250817.js

class MLPredictionComponent {
    constructor(symbol) {
        this.symbol = symbol;
        this.predictions = {};
        this.eventSource = new EventSource('/api/v1/predictions/stream');
        this.setupEventHandlers();
    }
    
    async loadPredictions() {
        const response = await fetch(`/api/v1/predict/${this.symbol}`);
        this.predictions = await response.json();
        this.renderPredictions();
    }
    
    renderPredictions() {
        const container = document.getElementById('ml-predictions');
        
        // 4 Karten für die verschiedenen Horizonte
        const horizons = [
            {days: 7, label: '1 Woche', color: 'success'},
            {days: 30, label: '1 Monat', color: 'info'}, 
            {days: 150, label: '5 Monate', color: 'warning'},
            {days: 365, label: '12 Monate', color: 'danger'}
        ];
        
        horizons.forEach(horizon => {
            const prediction = this.predictions[`${horizon.days}d`];
            if (prediction) {
                container.appendChild(this.createPredictionCard(horizon, prediction));
            }
        });
    }
    
    createPredictionCard(horizon, prediction) {
        const avgChange = prediction.reduce((a, b) => a + b, 0) / prediction.length;
        const confidence = this.predictions.confidence_scores[`${horizon.days}d`];
        
        return `
            <div class="col-md-3">
                <div class="card border-${horizon.color}">
                    <div class="card-header bg-${horizon.color} text-white">
                        <h6 class="mb-0">${horizon.label}</h6>
                    </div>
                    <div class="card-body">
                        <h4 class="text-${avgChange >= 0 ? 'success' : 'danger'}">
                            ${avgChange > 0 ? '+' : ''}${avgChange.toFixed(2)}%
                        </h4>
                        <div class="progress mb-2">
                            <div class="progress-bar bg-${horizon.color}" 
                                 style="width: ${confidence * 100}%"></div>
                        </div>
                        <small class="text-muted">
                            Vertrauen: ${(confidence * 100).toFixed(1)}%
                        </small>
                    </div>
                </div>
            </div>
        `;
    }
}
```

#### **5.2. Frontend API-Erweiterungen**
```python
# frontend_ml_endpoints_v1_0_0_20250817.py

@app.route('/api/content/ml-predictions', methods=['GET'])
async def get_ml_predictions_content():
    """ML-Predictions Content für Frontend"""
    symbol = request.args.get('symbol', 'AAPL')
    
    # ML Analytics Service abfragen
    ml_response = await http_client.get(f'http://localhost:8019/api/v1/predict/{symbol}')
    predictions = ml_response.json()
    
    # Performance-Daten abrufen
    performance_response = await http_client.get('http://localhost:8019/api/v1/models/performance')
    performance = performance_response.json()
    
    return {
        'symbol': symbol,
        'predictions': predictions,
        'model_performance': performance,
        'last_updated': datetime.utcnow().isoformat(),
        'page_title': f'KI-Prognosen für {symbol}'
    }

@app.route('/api/content/ml-dashboard', methods=['GET'])
async def get_ml_dashboard():
    """ML-Dashboard Content"""
    # Top Predictions
    top_predictions = await db.query("""
        SELECT symbol, 
               AVG(CASE WHEN horizon_days = 7 
                   THEN (prediction_values->0)::numeric END) as pred_7d,
               AVG(confidence_score) as avg_confidence
        FROM ml_predictions 
        WHERE prediction_timestamp >= CURRENT_DATE
        GROUP BY symbol
        ORDER BY avg_confidence DESC
        LIMIT 10
    """)
    
    # Model Health
    model_health = await db.query("""
        SELECT model_type, 
               COUNT(*) as predictions_today,
               AVG(confidence_score) as avg_confidence,
               MAX(created_at) as last_prediction
        FROM ml_predictions 
        WHERE DATE(prediction_timestamp) = CURRENT_DATE
        GROUP BY model_type
    """)
    
    return {
        'top_predictions': top_predictions,
        'model_health': model_health,
        'page_title': 'KI-Prognose Dashboard'
    }
```

---

### **LLD 6: Systemd Integration**

#### **6.1. ML Analytics Service Configuration**
```ini
# /etc/systemd/system/aktienanalyse-ml-analytics-modular.service

[Unit]
Description=Aktienanalyse ML Analytics Service v1.0.0
After=network.target postgresql.service redis.service
Wants=network.target
Requires=postgresql.service

[Service]
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem

# Virtual Environment
Environment=PATH=/opt/aktienanalyse-ökosystem/venv/bin
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python services/ml-analytics-service-modular/ml_analytics_orchestrator_v1_0_0_20250817.py

# Resource Limits
MemoryLimit=2G
CPUQuota=200%

# Auto-Restart
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aktienanalyse-ml-analytics

# Environment Variables
Environment=ML_SERVICE_PORT=8019
Environment=EVENT_BUS_URL=redis://localhost:6379/1
Environment=DATABASE_URL=postgresql://aktienanalyse:password@localhost/aktienanalyse_ml
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=CUDA_VISIBLE_DEVICES=0

[Install]
WantedBy=multi-user.target
```

#### **6.2. ML Training Pipeline Service**
```ini
# /etc/systemd/system/aktienanalyse-ml-training-pipeline.service

[Unit]
Description=Aktienanalyse ML Training Pipeline
After=network.target postgresql.service aktienanalyse-ml-analytics-modular.service

[Service]
Type=oneshot
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem

# Training Script
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python services/ml-analytics-service-modular/training/scheduled_training_v1_0_0_20250817.py

# Resource Limits
MemoryLimit=4G
CPUQuota=400%
TimeoutStartSec=3600

# Environment Variables
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
Environment=DATABASE_URL=postgresql://aktienanalyse:password@localhost/aktienanalyse_ml
Environment=TRAINING_DATA_DAYS=730
Environment=VALIDATION_SPLIT=0.15
Environment=TEST_SPLIT=0.15

[Install]
WantedBy=multi-user.target
```

#### **6.3. ML Training Timer**
```ini
# /etc/systemd/system/aktienanalyse-ml-training-pipeline.timer

[Unit]
Description=ML Training Pipeline Timer
Requires=aktienanalyse-ml-training-pipeline.service

[Timer]
# Wöchentliches Retraining - Sonntags um 02:00
OnCalendar=Sun 02:00
Persistent=true
RandomizedDelaySec=1800

[Install]
WantedBy=timers.target
```

---

## 📊 **Performance und Monitoring Spezifikation**

### **Performance-Targets:**
```yaml
# ml_performance_targets_v1_0_0_20250817.yaml

response_times:
  feature_calculation: 
    target: 500ms
    warning: 1000ms
    critical: 2000ms
    
  model_inference:
    technical_model: 200ms
    sentiment_model: 150ms  
    fundamental_model: 100ms
    ensemble_prediction: 800ms
    
  api_endpoints:
    predict_single: 1000ms
    predict_batch: 5000ms
    model_performance: 300ms

resource_usage:
  memory:
    ml_analytics_service: 1.5GB
    training_pipeline: 3.0GB
    
  cpu:
    normal_operation: 30%
    training_operation: 80%
    
  disk:
    model_storage: 500MB
    feature_data_daily: 10MB
    
accuracy_targets:
  directional_accuracy:
    7_day: 0.60
    30_day: 0.58
    150_day: 0.55
    365_day: 0.52
    
  confidence_thresholds:
    high_confidence: 0.80
    medium_confidence: 0.60
    low_confidence: 0.40
```

### **Health Check Implementierung:**
```python
# ml_health_monitor_v1_0_0_20250817.py

class MLHealthMonitor:
    async def check_ml_system_health(self):
        health_status = {
            'overall_status': 'healthy',
            'services': {},
            'models': {},
            'performance': {},
            'last_check': datetime.utcnow().isoformat()
        }
        
        # Service Health
        health_status['services']['ml_analytics'] = await self.check_service_health(8019)
        health_status['services']['event_bus'] = await self.check_event_bus_health()
        health_status['services']['database'] = await self.check_database_health()
        
        # Model Health
        for model_type in ['technical', 'sentiment', 'fundamental']:
            health_status['models'][model_type] = await self.check_model_health(model_type)
            
        # Performance Metrics
        health_status['performance'] = await self.get_performance_metrics()
        
        return health_status
        
    async def check_model_health(self, model_type):
        # Letzte Prediction-Zeit
        last_prediction = await self.db.query("""
            SELECT MAX(prediction_timestamp) as last_prediction,
                   COUNT(*) as predictions_today,
                   AVG(confidence_score) as avg_confidence
            FROM ml_predictions 
            WHERE model_type = %s 
            AND DATE(prediction_timestamp) = CURRENT_DATE
        """, [model_type])
        
        return {
            'status': 'healthy' if last_prediction[0]['predictions_today'] > 0 else 'warning',
            'last_prediction': last_prediction[0]['last_prediction'],
            'predictions_today': last_prediction[0]['predictions_today'],
            'avg_confidence': float(last_prediction[0]['avg_confidence'] or 0)
        }
```

---

## ✅ **Deployment-Checklist**

### **Phase 1 - PoC Deployment:**
- [ ] PostgreSQL ML-Schema erstellen
- [ ] ML Analytics Service (Port 8019) deployen
- [ ] Event-Bus Schema erweitern
- [ ] systemd Services konfigurieren
- [ ] Health-Monitoring aktivieren
- [ ] Technisches Modell für AAPL trainieren
- [ ] Frontend ML-Tab implementieren

### **Phase 2 - Vollständiges Ensemble:**
- [ ] Sentiment-Datenquellen integrieren
- [ ] Fundamental-Makro-Modelle implementieren
- [ ] Meta-Modell in Intelligent Core
- [ ] Alle 4 Prognosehorizonte aktivieren
- [ ] Performance-Monitoring erweitern

### **Phase 3 - Produktiv-Optimierung:**
- [ ] Hyperparameter-Tuning
- [ ] Automatisches Retraining
- [ ] Load-Testing durchführen
- [ ] Monitoring-Alerts konfigurieren

---

*Technische Spezifikation erstellt: 17. August 2025*  
*Version: 1.0.0*  
*Kompatibel mit: Production System v5.1 FINAL*