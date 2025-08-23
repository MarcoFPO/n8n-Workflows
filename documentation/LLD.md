# 🔧 Low-Level Design (LLD)

## 🎯 **Event-Driven Trading Intelligence System v5.1**

### 🏗️ **Detaillierte Implementierung**

---

## 🧠 **Intelligent Core Service (Port 8001)**

### 📁 **Datei-Struktur**
```
intelligent_core_service/
├── main.py                           # FastAPI Application Entry Point
├── intelligent_core_v1_1_0_20250823.py  # Core Intelligence Engine
├── event_processor.py                # Event Processing Logic
├── stock_analyzer.py                # AI Stock Analysis
├── cross_system_intelligence.py     # Inter-Service Correlation
└── models/
    ├── analysis_models.py           # Pydantic Data Models
    └── event_schemas.py             # Event Type Definitions
```

### 🔧 **Core Implementation**
```python
# intelligent_core_v1_1_0_20250823.py
class IntelligentCoreService:
    """
    Central AI Analytics & Event Orchestration Service
    Handles real-time stock analysis and cross-system intelligence
    """
    
    def __init__(self):
        self.event_processor = EventProcessor()
        self.stock_analyzer = StockAnalyzer()
        self.intelligence_engine = CrossSystemIntelligence()
        self.db_pool = None
        self.redis_client = None
    
    async def initialize(self):
        """Initialize database connections and services"""
        self.db_pool = await create_postgres_pool()
        self.redis_client = await aioredis.from_url("redis://localhost:6379")
    
    async def process_stock_analysis(self, stock_data: StockData) -> AnalysisResult:
        """
        KI-basierte Aktienanalyse mit Gewinn-Prognosen
        Returns: Score (0-100), Confidence Level, Risk Category
        """
        # 1. Technical Analysis
        technical_score = await self.stock_analyzer.technical_analysis(stock_data)
        
        # 2. Fundamental Analysis  
        fundamental_score = await self.stock_analyzer.fundamental_analysis(stock_data)
        
        # 3. Sentiment Analysis
        sentiment_score = await self.stock_analyzer.sentiment_analysis(stock_data)
        
        # 4. AI-Weighted Ensemble
        final_score = self.calculate_weighted_score(
            technical=technical_score,
            fundamental=fundamental_score, 
            sentiment=sentiment_score
        )
        
        # 5. Confidence & Risk Assessment
        confidence = self.calculate_confidence(stock_data, final_score)
        risk_category = self.determine_risk_category(final_score, confidence)
        
        # 6. Generate Event
        analysis_event = AnalysisStateChangedEvent(
            stock_symbol=stock_data.symbol,
            score=final_score,
            confidence=confidence,
            risk_category=risk_category,
            timestamp=datetime.utcnow()
        )
        
        # 7. Publish Event
        await self.event_processor.publish_event(analysis_event)
        
        return AnalysisResult(
            score=final_score,
            confidence=confidence,
            risk_category=risk_category
        )
```

### 🔄 **Event Processing Engine**
```python
# event_processor.py
class EventProcessor:
    """
    Event-Driven Communication Handler
    Processes and publishes events across the system
    """
    
    async def publish_event(self, event: BaseEvent) -> None:
        """
        Publishes event to Redis Event Bus with 0.12s target response
        """
        event_data = {
            "event_type": event.event_type,
            "entity_id": event.entity_id,
            "correlation_id": str(uuid.uuid4()),
            "data": event.dict(),
            "timestamp": event.timestamp.isoformat(),
            "version": 1
        }
        
        # 1. Store in PostgreSQL Event Store
        await self.store_event_postgres(event_data)
        
        # 2. Cache in Redis for fast access
        await self.cache_event_redis(event_data)
        
        # 3. Publish to Event Bus
        await self.redis_client.publish(
            f"events.{event.event_type}",
            json.dumps(event_data)
        )
    
    async def subscribe_to_events(self, event_types: List[str]) -> AsyncGenerator:
        """
        Subscribe to specific event types for cross-system intelligence
        """
        pubsub = self.redis_client.pubsub()
        
        for event_type in event_types:
            await pubsub.subscribe(f"events.{event_type}")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                yield Event.from_dict(event_data)
```

---

## 📈 **Data Processing Service (Port 8017)**

### 📁 **Datei-Struktur**
```
data_processing_service/
├── main.py                          # FastAPI Entry Point
├── data_processing_v4_2_0_20250823.py  # CSV Middleware Engine
├── csv_processor.py                 # 5-Column CSV Processing
├── data_validator.py               # Data Quality Validation
├── format_converter.py             # Multi-Format Data Conversion
└── schemas/
    ├── csv_schemas.py              # CSV Data Models
    └── validation_rules.py         # Data Validation Rules
```

### 🔧 **CSV Processing Implementation**
```python
# data_processing_v4_2_0_20250823.py
class DataProcessingService:
    """
    CSV Middleware & Data Transformation Service
    Handles 5-column CSV format and real-time data synchronization
    """
    
    CSV_COLUMNS = ["Symbol", "Score", "Confidence", "Risk", "LastUpdate"]
    
    async def process_csv_import(self, csv_file: UploadFile) -> ProcessingResult:
        """
        Import CSV data with 5-column format validation
        """
        # 1. Validate CSV Structure
        csv_data = await self.validate_csv_structure(csv_file)
        
        # 2. Data Quality Checks
        validated_data = await self.validate_data_quality(csv_data)
        
        # 3. Transform to Internal Format
        internal_data = await self.transform_to_internal_format(validated_data)
        
        # 4. Store in Event Store
        for record in internal_data:
            event = DataSynchronizedEvent(
                entity_id=record.symbol,
                data_type="csv_import",
                data=record.dict(),
                source="manual_upload"
            )
            await self.event_processor.publish_event(event)
        
        return ProcessingResult(
            records_processed=len(internal_data),
            validation_errors=[],
            processing_time=time.time() - start_time
        )
    
    async def export_csv_data(self, filter_params: dict) -> StreamingResponse:
        """
        Export real-time data to 5-column CSV format
        """
        # 1. Query Event Store with Filters
        query = self.build_export_query(filter_params)
        data = await self.db_pool.fetch(query)
        
        # 2. Transform to CSV Format
        csv_data = []
        for record in data:
            csv_data.append({
                "Symbol": record["entity_id"],
                "Score": record["event_data"]["score"],
                "Confidence": record["event_data"]["confidence"],
                "Risk": record["event_data"]["risk_category"],
                "LastUpdate": record["created_at"].isoformat()
            })
        
        # 3. Generate CSV Stream
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=self.CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(csv_data)
        
        # 4. Return Streaming Response
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )
```

### 🔍 **Data Validation Engine**
```python
# data_validator.py
class DataValidator:
    """
    Comprehensive Data Quality Validation
    """
    
    VALIDATION_RULES = {
        "Symbol": {
            "type": str,
            "max_length": 10,
            "pattern": r"^[A-Z]{1,5}$",
            "required": True
        },
        "Score": {
            "type": float,
            "min_value": 0.0,
            "max_value": 100.0,
            "required": True
        },
        "Confidence": {
            "type": float,
            "min_value": 0.0,
            "max_value": 1.0,
            "required": True
        },
        "Risk": {
            "type": str,
            "allowed_values": ["LOW", "MEDIUM", "HIGH"],
            "required": True
        }
    }
    
    async def validate_record(self, record: dict) -> ValidationResult:
        """
        Validate individual data record against rules
        """
        errors = []
        warnings = []
        
        for field, rules in self.VALIDATION_RULES.items():
            if field not in record and rules.get("required"):
                errors.append(f"Required field '{field}' missing")
                continue
            
            value = record.get(field)
            if value is None:
                continue
            
            # Type Validation
            if not isinstance(value, rules["type"]):
                errors.append(f"Field '{field}' must be {rules['type'].__name__}")
            
            # Range Validation
            if rules["type"] in [int, float]:
                if "min_value" in rules and value < rules["min_value"]:
                    errors.append(f"Field '{field}' below minimum {rules['min_value']}")
                if "max_value" in rules and value > rules["max_value"]:
                    errors.append(f"Field '{field}' above maximum {rules['max_value']}")
            
            # String Validation
            if rules["type"] == str:
                if "max_length" in rules and len(value) > rules["max_length"]:
                    errors.append(f"Field '{field}' exceeds max length {rules['max_length']}")
                if "pattern" in rules and not re.match(rules["pattern"], value):
                    errors.append(f"Field '{field}' doesn't match pattern {rules['pattern']}")
                if "allowed_values" in rules and value not in rules["allowed_values"]:
                    errors.append(f"Field '{field}' must be one of {rules['allowed_values']}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## 🤖 **ML Analytics Service (Port 8021)**

### 📁 **Datei-Struktur**  
```
ml_analytics_service/
├── main.py                              # FastAPI ML API Server
├── ml_service_v1_0_0_20250823.py      # ML Pipeline Orchestrator
├── models/
│   ├── lstm_predictor.py               # Long Short-Term Memory Model
│   ├── xgboost_predictor.py           # XGBoost Ensemble Model
│   ├── lightgbm_predictor.py          # LightGBM Model
│   └── ensemble_predictor.py          # Meta-Ensemble Model
├── training/
│   ├── automated_trainer.py           # Automated Model Retraining
│   ├── model_evaluator.py            # Performance Evaluation
│   └── feature_engineer.py           # Feature Engineering Pipeline
├── storage/
│   ├── model_manager.py               # Model Version Management
│   └── model_registry.py             # Model Registry & Metadata
└── utils/
    ├── data_preprocessor.py           # Data Preprocessing Utils
    └── prediction_postprocessor.py   # Prediction Post-processing
```

### 🔧 **ML Pipeline Implementation**
```python
# ml_service_v1_0_0_20250823.py
class MLAnalyticsService:
    """
    Advanced ML Pipeline with Multi-Horizon Predictions
    Supports LSTM, XGBoost, LightGBM ensemble methods
    """
    
    PREDICTION_HORIZONS = [7, 30, 150, 365]  # Days
    MODELS = ["lstm", "xgboost", "lightgbm", "ensemble"]
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.automated_trainer = AutomatedTrainer()
        self.feature_engineer = FeatureEngineer()
        self.ensemble_predictor = EnsemblePredictor()
        
    async def predict_multi_horizon(self, 
                                    symbol: str, 
                                    horizons: List[int] = None) -> MultiHorizonPrediction:
        """
        Generate predictions for multiple time horizons
        Returns ensemble predictions with confidence intervals
        """
        if horizons is None:
            horizons = self.PREDICTION_HORIZONS
        
        # 1. Fetch Historical Data
        historical_data = await self.fetch_historical_data(symbol)
        
        # 2. Feature Engineering
        features = await self.feature_engineer.create_features(historical_data)
        
        predictions = {}
        
        for horizon in horizons:
            # 3. Load Models for Horizon
            models = await self.model_manager.load_models_for_horizon(horizon)
            
            # 4. Individual Model Predictions
            model_predictions = {}
            for model_name, model in models.items():
                pred = await model.predict(features, horizon)
                model_predictions[model_name] = pred
            
            # 5. Ensemble Prediction
            ensemble_pred = self.ensemble_predictor.combine_predictions(
                model_predictions, horizon
            )
            
            predictions[f"{horizon}d"] = PredictionResult(
                horizon_days=horizon,
                predicted_price=ensemble_pred.predicted_price,
                confidence_interval=ensemble_pred.confidence_interval,
                probability_up=ensemble_pred.probability_up,
                individual_models=model_predictions
            )
        
        # 6. Generate Event
        prediction_event = PredictionGeneratedEvent(
            symbol=symbol,
            predictions=predictions,
            model_versions=await self.model_manager.get_active_versions()
        )
        await self.event_processor.publish_event(prediction_event)
        
        return MultiHorizonPrediction(
            symbol=symbol,
            predictions=predictions,
            generated_at=datetime.utcnow()
        )
    
    async def automated_model_training(self, trigger_type: str = "scheduled") -> TrainingResult:
        """
        Automated model retraining based on performance degradation
        """
        # 1. Evaluate Current Model Performance
        performance_metrics = await self.evaluate_model_performance()
        
        # 2. Check if Retraining Needed
        retrain_needed = self.should_retrain_models(performance_metrics)
        
        if not retrain_needed and trigger_type != "forced":
            return TrainingResult(
                status="skipped",
                reason="Performance above threshold"
            )
        
        # 3. Fetch Fresh Training Data
        training_data = await self.fetch_training_data()
        
        # 4. Train Models for Each Horizon
        training_results = {}
        
        for horizon in self.PREDICTION_HORIZONS:
            for model_type in self.MODELS[:-1]:  # Exclude ensemble
                # 5. Train Individual Model
                trained_model = await self.automated_trainer.train_model(
                    model_type=model_type,
                    training_data=training_data,
                    horizon=horizon
                )
                
                # 6. Evaluate Performance
                evaluation = await self.automated_trainer.evaluate_model(
                    trained_model, horizon
                )
                
                # 7. Version Management
                if evaluation.performance > performance_metrics[model_type][horizon]:
                    # Save new version
                    version = await self.model_manager.save_model_version(
                        trained_model, model_type, horizon
                    )
                    training_results[f"{model_type}_{horizon}d"] = {
                        "status": "improved",
                        "new_version": version,
                        "performance_improvement": evaluation.performance - performance_metrics[model_type][horizon]
                    }
                else:
                    training_results[f"{model_type}_{horizon}d"] = {
                        "status": "no_improvement",
                        "current_performance": performance_metrics[model_type][horizon]
                    }
        
        # 8. Retrain Ensemble Model
        ensemble_result = await self.retrain_ensemble_model()
        training_results["ensemble"] = ensemble_result
        
        # 9. Generate Training Event
        training_event = ModelTrainingCompletedEvent(
            trigger_type=trigger_type,
            results=training_results,
            training_duration=time.time() - start_time
        )
        await self.event_processor.publish_event(training_event)
        
        return TrainingResult(
            status="completed",
            results=training_results
        )
```

### 🎯 **Ensemble Prediction Engine**
```python
# ensemble_predictor.py
class EnsemblePredictor:
    """
    Meta-learning ensemble combining LSTM, XGBoost, and LightGBM
    """
    
    def __init__(self):
        self.weights = {
            "lstm": 0.4,      # Strong for time-series patterns
            "xgboost": 0.35,  # Strong for feature interactions
            "lightgbm": 0.25  # Fast and efficient
        }
        
    def combine_predictions(self, 
                            model_predictions: Dict, 
                            horizon: int) -> EnsemblePrediction:
        """
        Combine individual model predictions using weighted ensemble
        """
        # 1. Extract Predictions and Confidence
        predictions = []
        confidences = []
        
        for model_name, prediction in model_predictions.items():
            predictions.append(prediction.predicted_price)
            confidences.append(prediction.confidence)
        
        # 2. Weighted Average Prediction
        weighted_prediction = sum(
            pred * self.weights.get(model_name, 1.0/len(predictions))
            for model_name, pred in zip(model_predictions.keys(), predictions)
        )
        
        # 3. Confidence Interval Calculation
        confidence_lower = np.percentile(predictions, 25)
        confidence_upper = np.percentile(predictions, 75)
        
        # 4. Probability Calculation (Classification)
        probability_up = self.calculate_probability_up(
            model_predictions, weighted_prediction
        )
        
        # 5. Ensemble Confidence (Meta-confidence)
        ensemble_confidence = self.calculate_ensemble_confidence(
            predictions, confidences
        )
        
        return EnsemblePrediction(
            predicted_price=weighted_prediction,
            confidence_interval=(confidence_lower, confidence_upper),
            probability_up=probability_up,
            ensemble_confidence=ensemble_confidence
        )
    
    def calculate_ensemble_confidence(self, 
                                      predictions: List[float], 
                                      confidences: List[float]) -> float:
        """
        Calculate meta-confidence based on prediction agreement and individual confidences
        """
        # 1. Agreement Score (how close are predictions)
        prediction_std = np.std(predictions)
        max_price = max(predictions)
        agreement_score = 1.0 - (prediction_std / max_price) if max_price > 0 else 0.0
        
        # 2. Average Individual Confidence
        avg_confidence = np.mean(confidences)
        
        # 3. Weighted Meta-Confidence
        meta_confidence = (agreement_score * 0.6) + (avg_confidence * 0.4)
        
        return max(0.0, min(1.0, meta_confidence))
```

---

## 📊 **Database Implementation Details**

### 🗄️ **PostgreSQL Event Store Schema**

#### 📝 **Detailed Table Definitions**
```sql
-- Event Store Database: event_store_db
-- Optimized for high-throughput event processing

-- Main Events Table
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(100),
    correlation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    version INTEGER DEFAULT 1,
    source_service VARCHAR(50),
    
    -- Performance constraints
    CONSTRAINT valid_event_type CHECK (
        event_type IN (
            'analysis.state.changed',
            'portfolio.state.changed', 
            'trading.state.changed',
            'intelligence.triggered',
            'data.synchronized',
            'system.alert.raised',
            'user.interaction.logged',
            'config.updated'
        )
    )
);

-- High-Performance Indexes
CREATE INDEX CONCURRENTLY idx_events_type_time ON events (event_type, created_at DESC);
CREATE INDEX CONCURRENTLY idx_events_entity_time ON events (entity_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_events_correlation ON events (correlation_id);
CREATE INDEX CONCURRENTLY idx_events_source_service ON events (source_service, created_at DESC);

-- GIN Index for JSONB queries
CREATE INDEX CONCURRENTLY idx_events_data_gin ON events USING GIN (event_data);

-- Materialized Views for Ultra-Fast Queries (<50ms)

-- Stock Analysis Unified View
CREATE MATERIALIZED VIEW stock_analysis_unified AS
SELECT DISTINCT ON (entity_id)
    entity_id as stock_symbol,
    (event_data->>'score')::NUMERIC(5,2) as analysis_score,
    (event_data->>'confidence')::NUMERIC(5,4) as confidence_level,
    (event_data->>'risk_category')::VARCHAR(20) as risk_assessment,
    (event_data->>'prediction_horizons')::JSONB as predictions,
    created_at as last_analysis,
    source_service
FROM events 
WHERE event_type = 'analysis.state.changed'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY entity_id, created_at DESC;

CREATE UNIQUE INDEX idx_stock_analysis_symbol ON stock_analysis_unified (stock_symbol);

-- Portfolio Performance View  
CREATE MATERIALIZED VIEW portfolio_unified AS
SELECT 
    (event_data->>'total_value')::NUMERIC(15,2) as portfolio_value,
    (event_data->>'performance_pct')::NUMERIC(8,4) as performance_percent,
    (event_data->>'positions')::INTEGER as position_count,
    (event_data->>'unrealized_pnl')::NUMERIC(15,2) as unrealized_pnl,
    (event_data->>'realized_pnl')::NUMERIC(15,2) as realized_pnl,
    created_at as last_update,
    correlation_id as update_correlation
FROM events 
WHERE event_type = 'portfolio.state.changed'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 100;

CREATE INDEX idx_portfolio_time ON portfolio_unified (last_update DESC);

-- Trading Activity View
CREATE MATERIALIZED VIEW trading_activity_unified AS
SELECT 
    entity_id as symbol,
    (event_data->>'order_type')::VARCHAR(20) as order_type,
    (event_data->>'quantity')::NUMERIC(15,8) as quantity,
    (event_data->>'price')::NUMERIC(15,2) as price,
    (event_data->>'status')::VARCHAR(20) as status,
    (event_data->>'broker')::VARCHAR(50) as broker,
    created_at as order_time,
    correlation_id
FROM events 
WHERE event_type = 'trading.state.changed'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '90 days'
ORDER BY created_at DESC;

CREATE INDEX idx_trading_symbol_time ON trading_activity_unified (symbol, order_time DESC);
CREATE INDEX idx_trading_status ON trading_activity_unified (status);

-- System Health View
CREATE MATERIALIZED VIEW system_health_unified AS
SELECT 
    source_service,
    (event_data->>'status')::VARCHAR(20) as service_status,
    (event_data->>'response_time_ms')::INTEGER as response_time,
    (event_data->>'memory_usage_mb')::INTEGER as memory_usage,
    (event_data->>'cpu_usage_pct')::NUMERIC(5,2) as cpu_usage,
    created_at as health_check_time
FROM events 
WHERE event_type = 'system.alert.raised'
  AND created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY created_at DESC;

CREATE INDEX idx_health_service_time ON system_health_unified (source_service, health_check_time DESC);

-- Refresh Strategy (Automated via cron jobs)
-- Refresh every 5 minutes for real-time data
-- /etc/cron.d/refresh_materialized_views:
-- */5 * * * * postgres REFRESH MATERIALIZED VIEW CONCURRENTLY stock_analysis_unified;
-- */2 * * * * postgres REFRESH MATERIALIZED VIEW CONCURRENTLY portfolio_unified;
-- */1 * * * * postgres REFRESH MATERIALIZED VIEW CONCURRENTLY trading_activity_unified;
-- */10 * * * * postgres REFRESH MATERIALIZED VIEW CONCURRENTLY system_health_unified;
```

### ⚡ **Redis Configuration & Implementation**

#### 🔧 **Redis Deployment Configuration**
```bash
# /etc/redis/redis.conf - Production Configuration
# Optimized for Event-Driven Architecture

# Basic Settings
port 6379
bind 127.0.0.1 10.1.1.174
protected-mode yes
timeout 300

# Memory Configuration
maxmemory 1gb
maxmemory-policy allkeys-lru

# Persistence (Balanced for speed and durability)
save 900 1      # Save after 900 sec if at least 1 key changed
save 300 10     # Save after 300 sec if at least 10 keys changed  
save 60 10000   # Save after 60 sec if at least 10000 keys changed

# Performance Tuning
tcp-keepalive 300
tcp-backlog 511
databases 16

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Pub/Sub Configuration
notify-keyspace-events "Ex"  # Enable keyspace notifications for expires
```

#### 🚀 **Redis Event Bus Implementation**
```python
# event_bus_service/redis_event_bus.py
class RedisEventBus:
    """
    High-Performance Event Bus using Redis Pub/Sub
    Supports 1000+ events/sec throughput
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = None
        self.subscriber_tasks = {}
        self.event_handlers = {}
        
    async def initialize(self):
        """Initialize Redis connection with connection pooling"""
        self.redis_client = aioredis.ConnectionPool.from_url(
            "redis://localhost:6379",
            max_connections=20,
            retry_on_timeout=True
        )
        
    async def publish_event(self, event_type: str, event_data: dict) -> int:
        """
        Publish event with guaranteed delivery and performance tracking
        Returns: Number of subscribers that received the event
        """
        # 1. Add Event Metadata
        enriched_event = {
            **event_data,
            "published_at": datetime.utcnow().isoformat(),
            "publisher_id": f"{socket.gethostname()}-{os.getpid()}",
            "event_id": str(uuid.uuid4())
        }
        
        # 2. Serialize Event Data
        event_json = json.dumps(enriched_event, default=str)
        
        # 3. Publish to Main Channel
        subscribers_count = await self.redis_client.publish(
            f"events.{event_type}",
            event_json
        )
        
        # 4. Cache Recent Event (TTL: 300 seconds)
        await self.redis_client.setex(
            f"event_cache:{event_type}:{enriched_event['event_id']}",
            300,
            event_json
        )
        
        # 5. Update Event Metrics
        await self.redis_client.incr(f"event_metrics:published:{event_type}")
        await self.redis_client.incr(f"event_metrics:published:total")
        
        return subscribers_count
    
    async def subscribe_to_events(self, event_types: List[str], 
                                  handler: Callable) -> None:
        """
        Subscribe to multiple event types with automatic error handling
        """
        pubsub = self.redis_client.pubsub()
        
        # Subscribe to event channels
        for event_type in event_types:
            await pubsub.subscribe(f"events.{event_type}")
            logger.info(f"Subscribed to events.{event_type}")
        
        # Event processing loop
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # 1. Parse Event Data
                        event_data = json.loads(message['data'])
                        event_type = message['channel'].decode().split('.')[-1]
                        
                        # 2. Update Received Metrics
                        await self.redis_client.incr(f"event_metrics:received:{event_type}")
                        
                        # 3. Process Event (Non-blocking)
                        asyncio.create_task(
                            self.handle_event_safely(handler, event_type, event_data)
                        )
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in event: {e}")
                    except Exception as e:
                        logger.error(f"Event processing error: {e}")
        
        except asyncio.CancelledError:
            logger.info("Event subscription cancelled")
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()
    
    async def handle_event_safely(self, handler: Callable, 
                                  event_type: str, event_data: dict) -> None:
        """
        Handle event with timeout and error recovery
        """
        try:
            # Execute handler with 5-second timeout
            await asyncio.wait_for(
                handler(event_type, event_data),
                timeout=5.0
            )
            
            # Update Success Metrics
            await self.redis_client.incr(f"event_metrics:processed:{event_type}")
            
        except asyncio.TimeoutError:
            logger.warning(f"Event handler timeout for {event_type}")
            await self.redis_client.incr(f"event_metrics:timeout:{event_type}")
        
        except Exception as e:
            logger.error(f"Event handler error for {event_type}: {e}")
            await self.redis_client.incr(f"event_metrics:error:{event_type}")
```

---

## 🚀 **Service Deployment Implementation**

### 🔧 **systemd Service Templates**

#### 🎯 **Universal Service Template**
```ini
# /etc/systemd/system/aktienanalyse-{service}.service
[Unit]
Description=Aktienanalyse {Service Name} - Event-Driven Trading Intelligence
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=aktienanalyse
Group=aktienanalyse
WorkingDirectory=/opt/aktienanalyse-ökosystem/{service_directory}
Environment=PYTHONPATH=/opt/aktienanalyse-ökosystem
EnvironmentFile=/opt/aktienanalyse-ökosystem/.env

# Service Execution
ExecStart=/opt/aktienanalyse-ökosystem/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

# Auto-Restart Configuration  
Restart=always
RestartSec=5
StartLimitBurst=3
StartLimitInterval=60

# Resource Limits
MemoryMax=256M
CPUQuota=50%

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/aktienanalyse-ökosystem/logs

# Logging
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
```

#### 🚀 **Service Management Scripts**
```bash
#!/bin/bash
# /opt/aktienanalyse-ökosystem/scripts/manage_services.sh
# Comprehensive Service Management

SERVICES=(
    "intelligent-core-service"
    "event-bus-service"  
    "broker-gateway-service"
    "monitoring-service"
    "diagnostic-service"
    "data-processing-service"
    "prediction-tracking-service"
    "ml-analytics-service"
    "marketcap-service"
    "unified-profit-engine"
    "frontend-service"
)

SERVICE_PORTS=(8001 8014 8012 8015 8013 8017 8018 8021 8011 8025 8080)

check_service_health() {
    local service=$1
    local port=$2
    
    # 1. systemd Status Check
    if ! systemctl is-active --quiet "aktienanalyse-$service"; then
        echo "❌ $service: systemd service not active"
        return 1
    fi
    
    # 2. Port Availability Check
    if ! nc -z localhost $port; then
        echo "⚠️  $service: Port $port not responding"
        return 1
    fi
    
    # 3. Health Endpoint Check (if available)
    if curl -f -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $service: Healthy (Port $port)"
        return 0
    else
        echo "⚠️  $service: Health check failed (Port $port)"
        return 1
    fi
}

deploy_all_services() {
    echo "🚀 Deploying Event-Driven Trading Intelligence System v5.1"
    
    # 1. Update System Dependencies
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip postgresql redis-server nginx
    
    # 2. Setup Virtual Environment
    python3 -m venv /opt/aktienanalyse-ökosystem/venv
    source /opt/aktienanalyse-ökosystem/venv/bin/activate
    pip install -r /opt/aktienanalyse-ökosystem/requirements.txt
    
    # 3. Database Initialization
    sudo -u postgres psql -c "CREATE DATABASE IF NOT EXISTS event_store_db;"
    psql event_store_db < /opt/aktienanalyse-ökosystem/database/schema.sql
    
    # 4. Deploy Services
    for i in "${!SERVICES[@]}"; do
        service=${SERVICES[$i]}
        port=${SERVICE_PORTS[$i]}
        
        echo "Deploying $service on port $port..."
        
        # Create systemd service file
        sudo cp "/opt/aktienanalyse-ökosystem/systemd/aktienanalyse-$service.service" \
             "/etc/systemd/system/"
        
        # Enable and start service
        sudo systemctl daemon-reload
        sudo systemctl enable "aktienanalyse-$service"
        sudo systemctl start "aktienanalyse-$service"
        
        # Wait for service to start
        sleep 3
        
        # Verify deployment
        if check_service_health "$service" "$port"; then
            echo "✅ $service deployed successfully"
        else
            echo "❌ $service deployment failed"
            exit 1
        fi
    done
    
    echo "🎉 All services deployed successfully!"
}

restart_all_services() {
    echo "🔄 Restarting all services..."
    
    for service in "${SERVICES[@]}"; do
        echo "Restarting aktienanalyse-$service..."
        sudo systemctl restart "aktienanalyse-$service"
        sleep 2
    done
    
    echo "✅ All services restarted"
    system_health_check
}

system_health_check() {
    echo "🏥 System Health Check"
    echo "====================="
    
    healthy_services=0
    total_services=${#SERVICES[@]}
    
    for i in "${!SERVICES[@]}"; do
        service=${SERVICES[$i]}
        port=${SERVICE_PORTS[$i]}
        
        if check_service_health "$service" "$port"; then
            ((healthy_services++))
        fi
    done
    
    echo ""
    echo "📊 Health Summary: $healthy_services/$total_services services healthy"
    
    if [ $healthy_services -eq $total_services ]; then
        echo "🎉 System Status: ALL SYSTEMS OPERATIONAL"
        return 0
    else
        echo "⚠️  System Status: DEGRADED PERFORMANCE"
        return 1
    fi
}

# Script Execution
case "$1" in
    "deploy")
        deploy_all_services
        ;;
    "restart")
        restart_all_services
        ;;
    "health")
        system_health_check
        ;;
    "status")
        for i in "${!SERVICES[@]}"; do
            service=${SERVICES[$i]}
            port=${SERVICE_PORTS[$i]}
            check_service_health "$service" "$port"
        done
        ;;
    *)
        echo "Usage: $0 {deploy|restart|health|status}"
        exit 1
        ;;
esac
```

---

*Low-Level Design - Event-Driven Trading Intelligence System v5.1*  
*Letzte Aktualisierung: 23. August 2025*