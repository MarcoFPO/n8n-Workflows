# 🤖 ML Analytics Service Spezifikation v1.0.0

**Service**: ML Analytics Service  
**Port**: 8019  
**Version**: 1.0.0  
**Datum**: 17. August 2025  
**Integration**: Event-Driven aktienanalyse-ökosystem  

---

## 📋 **Service-Übersicht**

### **Zweck und Verantwortlichkeiten:**
- **KI-Modell-Management**: Training, Deployment und Lifecycle-Management aller ML-Modelle
- **Feature Engineering**: Berechnung und Bereitstellung von ML-Features für alle Modelle
- **Prediction Generation**: Erstellung von Einzelmodell- und Ensemble-Prognosen
- **Model Performance Tracking**: Überwachung und Optimierung der Modell-Performance
- **Event-Bus Integration**: Nahtlose Integration in bestehende Event-Driven Architecture

### **Service-Position in der Architektur:**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│ Data Processing │───▶│  ML Analytics   │
│   (8 Services)  │    │   Service 8017  │    │   Service 8019  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │◀───│ Intelligent Core│◀───│   Event Bus     │
│   Service 8080  │    │   Service 8001  │    │   Service 8014  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 🏗️ **Service-Architektur**

### **Modular Component Design:**
```python
# ml_analytics_service_architecture_v1_0_0_20250817.py

class MLAnalyticsService(ServiceBase):
    """
    Hauptorchestrator für alle ML-Operationen
    Folgt bestehender Service-Architektur des Ökosystems
    """
    
    def __init__(self):
        super().__init__("ml-analytics", 8019)
        
        # Core Components
        self.feature_engine = FeatureEngineeringEngine()
        self.model_manager = ModelManager()
        self.prediction_engine = PredictionEngine()
        self.training_orchestrator = TrainingOrchestrator()
        self.performance_tracker = PerformanceTracker()
        
        # Event-Bus Integration
        self.event_handlers = MLEventHandlers()
        self.event_publisher = MLEventPublisher()
        
        # Storage and Caching
        self.database = DatabaseConnection()
        self.model_cache = ModelCache()
        self.prediction_cache = PredictionCache()
```

### **Module-Struktur (Versioned):**
```
services/ml-analytics-service-modular/
├── ml_analytics_orchestrator_v1_0_0_20250817.py    # Haupt-Service
├── modules/
│   ├── feature_engineering/
│   │   ├── technical_feature_engine_v1_0_0_20250817.py
│   │   ├── sentiment_feature_engine_v1_0_0_20250817.py
│   │   └── fundamental_feature_engine_v1_0_0_20250817.py
│   ├── model_management/
│   │   ├── model_manager_v1_0_0_20250817.py
│   │   ├── technical_model_handler_v1_0_0_20250817.py
│   │   ├── sentiment_model_handler_v1_0_0_20250817.py
│   │   └── fundamental_model_handler_v1_0_0_20250817.py
│   ├── prediction_engine/
│   │   ├── prediction_orchestrator_v1_0_0_20250817.py
│   │   ├── ensemble_predictor_v1_0_0_20250817.py
│   │   └── prediction_validator_v1_0_0_20250817.py
│   ├── training/
│   │   ├── training_orchestrator_v1_0_0_20250817.py
│   │   ├── model_trainer_v1_0_0_20250817.py
│   │   └── hyperparameter_optimizer_v1_0_0_20250817.py
│   └── monitoring/
│       ├── performance_tracker_v1_0_0_20250817.py
│       └── model_health_monitor_v1_0_0_20250817.py
├── api/
│   ├── ml_api_endpoints_v1_0_0_20250817.py
│   └── ml_websocket_handlers_v1_0_0_20250817.py
├── config/
│   ├── ml_service_config.py
│   └── model_configurations.py
└── requirements.txt
```

---

## 🔧 **Core Components Spezifikation**

### **1. Feature Engineering Engine**
```python
# technical_feature_engine_v1_0_0_20250817.py

class TechnicalFeatureEngine:
    """
    Berechnet technische Indikatoren für ML-Modelle
    Integration mit bestehenden Datenquellen über Event-Bus
    """
    
    def __init__(self):
        self.indicators = {
            'momentum': MomentumIndicators(),
            'trend': TrendIndicators(),
            'volatility': VolatilityIndicators(),
            'volume': VolumeIndicators(),
            'price_action': PriceActionIndicators()
        }
        self.feature_cache = FeatureCache()
        
    async def calculate_features(self, symbol: str, market_data: dict) -> dict:
        """
        Berechnet alle technischen Features für ein Symbol
        
        Args:
            symbol: Trading Symbol (z.B. 'AAPL')
            market_data: OHLCV-Daten vom Data Processing Service
            
        Returns:
            dict: Berechnete Features nach Kategorien
        """
        features = {}
        
        # Momentum Indicators
        features['momentum'] = await self.indicators['momentum'].calculate({
            'rsi_14': self._calculate_rsi(market_data, 14),
            'macd_signal': self._calculate_macd_signal(market_data),
            'stoch_k': self._calculate_stochastic(market_data)
        })
        
        # Trend Indicators  
        features['trend'] = await self.indicators['trend'].calculate({
            'sma_20': self._calculate_sma(market_data, 20),
            'sma_50': self._calculate_sma(market_data, 50),
            'sma_200': self._calculate_sma(market_data, 200),
            'ema_20': self._calculate_ema(market_data, 20),
            'ema_50': self._calculate_ema(market_data, 50)
        })
        
        # Volatility Indicators
        features['volatility'] = await self.indicators['volatility'].calculate({
            'bb_upper': self._calculate_bollinger_upper(market_data),
            'bb_lower': self._calculate_bollinger_lower(market_data),
            'atr_14': self._calculate_atr(market_data, 14)
        })
        
        # Feature Quality Check
        quality_score = self._assess_feature_quality(features)
        features['metadata'] = {
            'quality_score': quality_score,
            'calculation_timestamp': datetime.utcnow(),
            'data_points_used': len(market_data),
            'missing_values_count': self._count_missing_values(features)
        }
        
        # Cache für Performance
        await self.feature_cache.store(symbol, features)
        
        return features
    
    def _calculate_rsi(self, data: dict, period: int) -> float:
        """RSI-Berechnung mit pandas_ta"""
        import pandas_ta as ta
        df = pd.DataFrame(data)
        rsi = ta.rsi(df['close'], length=period)
        return float(rsi.iloc[-1]) if not rsi.empty else None
    
    def _assess_feature_quality(self, features: dict) -> float:
        """Bewertet Qualität der berechneten Features"""
        quality_checks = []
        
        for category, feature_dict in features.items():
            if category == 'metadata':
                continue
                
            # Check for NaN values
            nan_count = sum(1 for v in feature_dict.values() if pd.isna(v))
            quality_checks.append(1.0 - (nan_count / len(feature_dict)))
            
            # Check for extreme outliers
            values = [v for v in feature_dict.values() if not pd.isna(v)]
            if values:
                outlier_ratio = self._detect_outliers(values)
                quality_checks.append(1.0 - outlier_ratio)
        
        return sum(quality_checks) / len(quality_checks) if quality_checks else 0.0
```

### **2. Model Manager**
```python
# model_manager_v1_0_0_20250817.py

class ModelManager:
    """
    Verwaltet Lifecycle aller ML-Modelle
    Kompatibel mit bestehendem Modul-Versioning-System
    """
    
    def __init__(self):
        self.active_models = {}
        self.model_registry = {}
        self.deployment_queue = asyncio.Queue()
        
    async def load_model(self, model_type: str, horizon_days: int) -> dict:
        """
        Lädt aktives Modell für Typ und Horizont
        
        Args:
            model_type: 'technical', 'sentiment', 'fundamental'
            horizon_days: 7, 30, 150, 365
            
        Returns:
            dict: Modell-Objekt und Metadaten
        """
        model_key = f"{model_type}_{horizon_days}d"
        
        # Aus Cache laden falls verfügbar
        if model_key in self.active_models:
            model_info = self.active_models[model_key]
            if self._is_model_valid(model_info):
                return model_info
        
        # Aus Datenbank laden
        model_metadata = await self._load_model_metadata(model_type, horizon_days)
        if not model_metadata:
            raise ModelNotFoundError(f"No active model for {model_type} {horizon_days}d")
        
        # Modell-Artefakte laden
        model_artifacts = await self._load_model_artifacts(model_metadata)
        
        # In Cache speichern
        self.active_models[model_key] = {
            'model': model_artifacts['model'],
            'scaler': model_artifacts['scaler'],
            'metadata': model_metadata,
            'loaded_at': datetime.utcnow(),
            'version': model_metadata['model_version'],
            'performance': model_metadata['production_metrics']
        }
        
        return self.active_models[model_key]
    
    async def deploy_new_model(self, model_id: str) -> bool:
        """
        Deployed neues Modell nach erfolgreichem Training
        
        Args:
            model_id: UUID des neuen Modells
            
        Returns:
            bool: Erfolg des Deployments
        """
        try:
            # Neues Modell validieren
            new_model_metadata = await self._get_model_metadata(model_id)
            validation_result = await self._validate_model(new_model_metadata)
            
            if not validation_result['valid']:
                logger.error(f"Model {model_id} validation failed: {validation_result['errors']}")
                return False
            
            # Performance-Vergleich mit aktuellem Modell
            current_model = await self.load_model(
                new_model_metadata['model_type'],
                new_model_metadata['horizon_days']
            )
            
            performance_improvement = await self._compare_model_performance(
                new_model_metadata, current_model['metadata']
            )
            
            if performance_improvement['improvement_ratio'] > 0.02:  # 2% Verbesserung erforderlich
                # Altes Modell deprecaten
                await self._deprecate_model(current_model['metadata']['model_id'])
                
                # Neues Modell als aktiv markieren
                await self._activate_model(model_id)
                
                # Cache invalidieren
                model_key = f"{new_model_metadata['model_type']}_{new_model_metadata['horizon_days']}d"
                if model_key in self.active_models:
                    del self.active_models[model_key]
                
                # Deployment-Event publizieren
                await self.event_publisher.publish('ml.model.deployed', {
                    'model_id': model_id,
                    'model_type': new_model_metadata['model_type'],
                    'model_version': new_model_metadata['model_version'],
                    'horizon_days': new_model_metadata['horizon_days'],
                    'performance_improvement': performance_improvement,
                    'deployed_at': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Successfully deployed model {model_id}")
                return True
            else:
                logger.info(f"Model {model_id} does not meet performance threshold")
                return False
                
        except Exception as e:
            logger.error(f"Model deployment failed: {str(e)}")
            return False
```

### **3. Prediction Engine**
```python
# prediction_orchestrator_v1_0_0_20250817.py

class PredictionOrchestrator:
    """
    Orchestriert Prediction-Generation für alle Modelle und Horizonte
    Event-driven Integration mit bestehenden Services
    """
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.ensemble_predictor = EnsemblePredictor()
        self.prediction_validator = PredictionValidator()
        
    async def generate_predictions(self, symbol: str, features: dict) -> dict:
        """
        Generiert Predictions für alle Modelle und Horizonte
        
        Args:
            symbol: Trading Symbol
            features: Berechnete Features von Feature Engine
            
        Returns:
            dict: Predictions aller Modelle nach Horizonten
        """
        predictions = {}
        correlation_id = str(uuid.uuid4())
        
        # Individual Model Predictions
        for model_type in ['technical', 'sentiment', 'fundamental']:
            try:
                model_predictions = await self._generate_model_predictions(
                    model_type, symbol, features, correlation_id
                )
                predictions[model_type] = model_predictions
                
                # Event für Individual Prediction
                await self.event_publisher.publish('ml.model.prediction.generated', {
                    'symbol': symbol,
                    'model_type': model_type,
                    'predictions': model_predictions,
                    'correlation_id': correlation_id
                })
                
            except Exception as e:
                logger.error(f"Failed to generate {model_type} predictions for {symbol}: {str(e)}")
                predictions[model_type] = self._generate_fallback_prediction()
        
        # Ensemble Predictions
        try:
            ensemble_predictions = await self.ensemble_predictor.predict(
                symbol, predictions, correlation_id
            )
            
            # Event für Ensemble Prediction
            await self.event_publisher.publish('ml.ensemble.prediction.ready', {
                'symbol': symbol,
                'individual_predictions': predictions,
                'final_predictions': ensemble_predictions,
                'correlation_id': correlation_id
            })
            
            return {
                'individual': predictions,
                'ensemble': ensemble_predictions,
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'correlation_id': correlation_id,
                    'symbol': symbol
                }
            }
            
        except Exception as e:
            logger.error(f"Ensemble prediction failed for {symbol}: {str(e)}")
            return predictions
    
    async def _generate_model_predictions(self, model_type: str, symbol: str, 
                                        features: dict, correlation_id: str) -> dict:
        """Generiert Predictions für einen spezifischen Modell-Typ"""
        model_predictions = {}
        
        for horizon_days in [7, 30, 150, 365]:
            try:
                # Modell laden
                model_info = await self.model_manager.load_model(model_type, horizon_days)
                
                # Features für Modell vorbereiten
                model_features = self._prepare_features_for_model(
                    features, model_type, model_info['metadata']
                )
                
                # Prediction generieren
                prediction_values = await self._run_inference(
                    model_info['model'], model_info['scaler'], model_features
                )
                
                # Confidence Score berechnen
                confidence_score = await self._calculate_confidence(
                    model_info, model_features, prediction_values
                )
                
                model_predictions[f"{horizon_days}d"] = {
                    'prediction_values': prediction_values.tolist(),
                    'confidence_score': float(confidence_score),
                    'model_version': model_info['version'],
                    'feature_importance': await self._get_feature_importance(
                        model_info, model_features
                    )
                }
                
            except Exception as e:
                logger.error(f"Failed to generate {model_type} {horizon_days}d prediction: {str(e)}")
                model_predictions[f"{horizon_days}d"] = self._generate_fallback_prediction()
        
        return model_predictions
```

### **4. Training Orchestrator**
```python
# training_orchestrator_v1_0_0_20250817.py

class TrainingOrchestrator:
    """
    Orchestriert Modell-Training mit Event-Integration
    Automatisches und manuelles Retraining
    """
    
    def __init__(self):
        self.model_trainer = ModelTrainer()
        self.hyperparameter_optimizer = HyperparameterOptimizer()
        self.training_queue = asyncio.Queue()
        self.active_trainings = {}
        
    async def start_training(self, model_type: str, horizon_days: int, 
                           symbols: list = None, trigger_event_id: str = None) -> str:
        """
        Startet Training für spezifischen Modell-Typ
        
        Args:
            model_type: 'technical', 'sentiment', 'fundamental'
            horizon_days: 7, 30, 150, 365
            symbols: Liste von Symbolen (None = alle)
            trigger_event_id: ID des auslösenden Events
            
        Returns:
            str: Training-ID für Tracking
        """
        training_id = str(uuid.uuid4())
        
        # Training-Konfiguration erstellen
        training_config = await self._create_training_config(
            model_type, horizon_days, symbols
        )
        
        # Training-Event publizieren
        await self.event_publisher.publish('ml.model.training.started', {
            'training_id': training_id,
            'model_type': model_type,
            'horizon_days': horizon_days,
            'symbols': symbols or 'all',
            'trigger_event_id': trigger_event_id,
            'training_config': training_config
        })
        
        # Training in Background starten
        training_task = asyncio.create_task(
            self._execute_training(training_id, training_config)
        )
        self.active_trainings[training_id] = training_task
        
        return training_id
    
    async def _execute_training(self, training_id: str, config: dict):
        """Führt das eigentliche Training durch"""
        try:
            start_time = datetime.utcnow()
            
            # 1. Trainingsdaten laden
            training_data = await self._load_training_data(config)
            
            # 2. Data Preprocessing
            processed_data = await self._preprocess_training_data(training_data, config)
            
            # 3. Hyperparameter Optimization (falls aktiviert)
            if config.get('optimize_hyperparameters', True):
                optimized_params = await self.hyperparameter_optimizer.optimize(
                    config['model_type'], processed_data
                )
                config['hyperparameters'].update(optimized_params)
            
            # 4. Model Training
            training_results = await self.model_trainer.train(
                config, processed_data
            )
            
            # 5. Model Validation
            validation_results = await self._validate_trained_model(
                training_results, processed_data
            )
            
            # 6. Model Artifacts speichern
            model_id = await self._save_model_artifacts(
                training_results, validation_results, config
            )
            
            # 7. Training-Completion-Event
            completion_payload = {
                'training_id': training_id,
                'model_id': model_id,
                'model_type': config['model_type'],
                'model_version': f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'horizon_days': config['horizon_days'],
                'training_duration_seconds': (datetime.utcnow() - start_time).total_seconds(),
                'training_results': training_results['metrics'],
                'validation_results': validation_results,
                'ready_for_deployment': validation_results['meets_deployment_criteria']
            }
            
            await self.event_publisher.publish('ml.model.training.completed', completion_payload)
            
            # 8. Auto-Deployment falls Performance-Kriterien erfüllt
            if validation_results['meets_deployment_criteria']:
                await self.model_manager.deploy_new_model(model_id)
            
        except Exception as e:
            logger.error(f"Training {training_id} failed: {str(e)}")
            await self.event_publisher.publish('ml.model.training.failed', {
                'training_id': training_id,
                'error': str(e),
                'failed_at': datetime.utcnow().isoformat()
            })
        finally:
            # Cleanup
            if training_id in self.active_trainings:
                del self.active_trainings[training_id]
```

---

## 🔌 **API-Endpoints Spezifikation**

### **Health und Status Endpoints:**
```python
# ml_api_endpoints_v1_0_0_20250817.py

@app.route('/health', methods=['GET'])
async def health_check():
    """Umfassender Health-Check für ML Analytics Service"""
    health_status = {
        'service': 'ml-analytics',
        'version': '1.0.0',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    # Component Health Checks
    health_status['components']['database'] = await check_database_health()
    health_status['components']['event_bus'] = await check_event_bus_health()
    health_status['components']['model_cache'] = await check_model_cache_health()
    health_status['components']['active_models'] = await check_active_models_health()
    
    # System Resources
    health_status['resources'] = {
        'memory_usage_mb': psutil.virtual_memory().used / 1024 / 1024,
        'cpu_percent': psutil.cpu_percent(interval=1),
        'disk_usage_gb': psutil.disk_usage('/').used / 1024 / 1024 / 1024
    }
    
    # Overall Status
    component_statuses = [comp['status'] for comp in health_status['components'].values()]
    if all(status == 'healthy' for status in component_statuses):
        health_status['status'] = 'healthy'
    elif any(status == 'critical' for status in component_statuses):
        health_status['status'] = 'critical'
    else:
        health_status['status'] = 'warning'
    
    return health_status

@app.route('/api/v1/status/models', methods=['GET'])
async def get_models_status():
    """Status aller aktiven Modelle"""
    models_status = {}
    
    for model_type in ['technical', 'sentiment', 'fundamental']:
        models_status[model_type] = {}
        for horizon in [7, 30, 150, 365]:
            try:
                model_info = await model_manager.load_model(model_type, horizon)
                models_status[model_type][f"{horizon}d"] = {
                    'status': 'active',
                    'version': model_info['version'],
                    'loaded_at': model_info['loaded_at'].isoformat(),
                    'performance': model_info['performance']
                }
            except Exception as e:
                models_status[model_type][f"{horizon}d"] = {
                    'status': 'error',
                    'error': str(e)
                }
    
    return {
        'models_status': models_status,
        'total_active_models': sum(
            1 for model_type in models_status.values()
            for horizon_status in model_type.values()
            if horizon_status.get('status') == 'active'
        ),
        'last_updated': datetime.utcnow().isoformat()
    }
```

### **Prediction Endpoints:**
```python
@app.route('/api/v1/predict/<symbol>', methods=['POST'])
async def predict_symbol(symbol):
    """Generiert Predictions für ein Symbol"""
    try:
        data = await request.get_json()
        horizons = data.get('horizons', [7, 30, 150, 365])
        model_types = data.get('model_types', ['technical', 'sentiment', 'fundamental', 'ensemble'])
        
        # Features von Data Processing Service abrufen oder berechnen
        features = await feature_engine.get_latest_features(symbol)
        if not features:
            # Fallback: Features neu berechnen
            market_data = await data_service.get_market_data(symbol)
            features = await feature_engine.calculate_features(symbol, market_data)
        
        # Predictions generieren
        predictions = await prediction_orchestrator.generate_predictions(symbol, features)
        
        # Response formatieren
        response = {
            'symbol': symbol,
            'predictions': {},
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'horizons_requested': horizons,
                'models_used': model_types,
                'features_quality': features.get('metadata', {}).get('quality_score', 0.0)
            }
        }
        
        # Nur angeforderte Modelle und Horizonte zurückgeben
        for model_type in model_types:
            if model_type == 'ensemble':
                response['predictions']['ensemble'] = {
                    horizon: predictions['ensemble'][horizon]
                    for horizon in [f"{h}d" for h in horizons]
                    if horizon in predictions['ensemble']
                }
            elif model_type in predictions['individual']:
                response['predictions'][model_type] = {
                    horizon: predictions['individual'][model_type][horizon]
                    for horizon in [f"{h}d" for h in horizons]
                    if horizon in predictions['individual'][model_type]
                }
        
        return response
        
    except Exception as e:
        logger.error(f"Prediction generation failed for {symbol}: {str(e)}")
        return {
            'error': 'prediction_failed',
            'message': str(e),
            'symbol': symbol
        }, 500

@app.route('/api/v1/predictions/batch', methods=['POST'])
async def predict_batch():
    """Batch-Predictions für mehrere Symbole"""
    try:
        data = await request.get_json()
        symbols = data.get('symbols', [])
        horizons = data.get('horizons', [7, 30])  # Reduziert für Batch
        
        if len(symbols) > 50:
            return {'error': 'too_many_symbols', 'max_allowed': 50}, 400
        
        batch_predictions = {}
        
        # Parallel processing für bessere Performance
        async def predict_single_symbol(symbol):
            try:
                features = await feature_engine.get_latest_features(symbol)
                if features:
                    predictions = await prediction_orchestrator.generate_predictions(symbol, features)
                    return symbol, predictions
            except Exception as e:
                logger.error(f"Batch prediction failed for {symbol}: {str(e)}")
                return symbol, None
        
        # Concurrent execution
        tasks = [predict_single_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        for symbol, predictions in results:
            if predictions:
                batch_predictions[symbol] = {
                    'ensemble': {
                        horizon: predictions['ensemble'][horizon]
                        for horizon in [f"{h}d" for h in horizons]
                        if horizon in predictions['ensemble']
                    }
                }
        
        return {
            'batch_predictions': batch_predictions,
            'successful_predictions': len(batch_predictions),
            'total_requested': len(symbols),
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': 'batch_prediction_failed', 'message': str(e)}, 500
```

### **Training und Model Management Endpoints:**
```python
@app.route('/api/v1/training/start', methods=['POST'])
async def start_training():
    """Startet Model-Training"""
    try:
        data = await request.get_json()
        model_type = data.get('model_type', 'technical')
        horizon_days = data.get('horizon_days', 7)
        symbols = data.get('symbols', None)
        
        # Validierung
        if model_type not in ['technical', 'sentiment', 'fundamental']:
            return {'error': 'invalid_model_type'}, 400
        if horizon_days not in [7, 30, 150, 365]:
            return {'error': 'invalid_horizon'}, 400
        
        # Training starten
        training_id = await training_orchestrator.start_training(
            model_type, horizon_days, symbols
        )
        
        return {
            'training_id': training_id,
            'status': 'started',
            'model_type': model_type,
            'horizon_days': horizon_days,
            'symbols': symbols or 'all',
            'started_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': 'training_start_failed', 'message': str(e)}, 500

@app.route('/api/v1/training/<training_id>/status', methods=['GET'])
async def get_training_status(training_id):
    """Status eines laufenden Trainings"""
    try:
        # Aus Datenbank oder Cache laden
        training_status = await database.query("""
            SELECT th.*, mm.status as model_status, mm.deployed_at
            FROM ml_training_history th
            LEFT JOIN ml_model_metadata mm ON th.model_id = mm.model_id
            WHERE th.training_id = %s
        """, [training_id])
        
        if not training_status:
            return {'error': 'training_not_found'}, 404
        
        status_info = training_status[0]
        
        # Live-Status für aktive Trainings
        if training_id in training_orchestrator.active_trainings:
            task = training_orchestrator.active_trainings[training_id]
            status_info['live_status'] = 'running' if not task.done() else 'completed'
        
        return {
            'training_id': training_id,
            'status': status_info,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': 'status_retrieval_failed', 'message': str(e)}, 500

@app.route('/api/v1/models/performance', methods=['GET'])
async def get_models_performance():
    """Performance-Metriken aller Modelle"""
    try:
        # Performance aus materialized view
        performance_data = await database.query("""
            SELECT model_type, horizon_days, 
                   avg_confidence, directional_accuracy,
                   prediction_date, total_predictions
            FROM ml_prediction_performance_unified
            WHERE prediction_date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY model_type, horizon_days, prediction_date DESC
        """)
        
        # Strukturiert nach Modell-Typ gruppieren
        structured_performance = {}
        for row in performance_data:
            model_type = row['model_type']
            horizon = f"{row['horizon_days']}d"
            
            if model_type not in structured_performance:
                structured_performance[model_type] = {}
            if horizon not in structured_performance[model_type]:
                structured_performance[model_type][horizon] = []
            
            structured_performance[model_type][horizon].append({
                'date': row['prediction_date'].isoformat(),
                'avg_confidence': float(row['avg_confidence']),
                'directional_accuracy': float(row['directional_accuracy']),
                'total_predictions': int(row['total_predictions'])
            })
        
        return {
            'performance_data': structured_performance,
            'time_period_days': 30,
            'retrieved_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': 'performance_retrieval_failed', 'message': str(e)}, 500
```

---

## 🔄 **Event-Handler Implementation**

### **ML Event Handlers:**
```python
# ml_event_handlers_v1_0_0_20250817.py

class MLEventHandlers:
    """Event-Handler für alle ML-relevanten Events"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.feature_engine = orchestrator.feature_engine
        self.prediction_engine = orchestrator.prediction_engine
        self.training_orchestrator = orchestrator.training_orchestrator
        
    async def handle_market_data_updated(self, event):
        """Reagiert auf market.data.updated Events"""
        try:
            symbol = event.payload.get('symbol')
            market_data = event.payload.get('data')
            
            # Features berechnen
            features = await self.feature_engine.calculate_features(symbol, market_data)
            
            # Feature-Event publizieren
            await self.orchestrator.event_publisher.publish('ml.features.calculated', {
                'symbol': symbol,
                'feature_type': 'technical',
                'features': features,
                'calculation_timestamp': datetime.utcnow().isoformat(),
                'triggered_by_event': event.event_id
            })
            
        except Exception as e:
            logger.error(f"Failed to handle market_data_updated: {str(e)}")
    
    async def handle_ml_features_calculated(self, event):
        """Reagiert auf ml.features.calculated Events"""
        try:
            symbol = event.payload.get('symbol')
            features = event.payload.get('features')
            
            # Predictions generieren für alle Modelle
            predictions = await self.prediction_engine.generate_predictions(symbol, features)
            
            # Individual Model Events bereits im PredictionOrchestrator publiziert
            # Hier nur Logging
            logger.info(f"Generated predictions for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to handle ml_features_calculated: {str(e)}")
    
    async def handle_ml_performance_threshold_crossed(self, event):
        """Reagiert auf Performance-Threshold-Events"""
        try:
            model_type = event.payload.get('model_type')
            horizon_days = event.payload.get('horizon_days')
            performance_metric = event.payload.get('metric')
            threshold_direction = event.payload.get('direction')  # 'below' or 'above'
            
            if threshold_direction == 'below' and performance_metric == 'directional_accuracy':
                # Performance zu schlecht -> Retraining auslösen
                logger.warning(f"Performance threshold crossed for {model_type} {horizon_days}d")
                
                training_id = await self.training_orchestrator.start_training(
                    model_type, horizon_days, trigger_event_id=event.event_id
                )
                
                logger.info(f"Triggered retraining {training_id} due to performance degradation")
            
        except Exception as e:
            logger.error(f"Failed to handle performance_threshold_crossed: {str(e)}")
    
    async def handle_intelligence_triggered(self, event):
        """Integration mit bestehendem Intelligent Core Service"""
        try:
            # Cross-System Intelligence mit ML-Insights anreichern
            symbol = event.payload.get('symbol')
            if symbol:
                # Aktuelle ML-Predictions abrufen
                latest_predictions = await self._get_latest_predictions(symbol)
                if latest_predictions:
                    # Erweiterte Intelligence-Response mit ML-Daten
                    enhanced_payload = {
                        **event.payload,
                        'ml_insights': {
                            'predictions': latest_predictions,
                            'confidence_level': latest_predictions.get('ensemble', {}).get('7d', {}).get('ensemble_confidence', 0.0),
                            'recommendation_strength': self._calculate_recommendation_strength(latest_predictions)
                        }
                    }
                    
                    # Enhanced Intelligence Event publizieren
                    await self.orchestrator.event_publisher.publish('intelligence.ml.enhanced', enhanced_payload)
            
        except Exception as e:
            logger.error(f"Failed to handle intelligence_triggered: {str(e)}")
```

---

## ⚙️ **Configuration und Deployment**

### **Service-Konfiguration:**
```python
# ml_service_config.py

ML_SERVICE_CONFIG = {
    'service': {
        'name': 'ml-analytics',
        'version': '1.0.0',
        'port': 8019,
        'host': '0.0.0.0',
        'workers': 4,
        'max_connections': 100
    },
    
    'models': {
        'technical': {
            'architecture': 'lstm',
            'input_sequence_length': 60,
            'feature_count': 25,
            'epochs': 100,
            'batch_size': 32,
            'validation_split': 0.15
        },
        'sentiment': {
            'architecture': 'xgboost',
            'n_estimators': 1000,
            'max_depth': 6,
            'learning_rate': 0.1,
            'validation_split': 0.15
        },
        'fundamental': {
            'architecture': 'xgboost',
            'n_estimators': 500,
            'max_depth': 8,
            'learning_rate': 0.05,
            'validation_split': 0.15
        }
    },
    
    'performance_thresholds': {
        'directional_accuracy_min': 0.55,
        'confidence_score_min': 0.40,
        'prediction_freshness_hours': 6,
        'model_retrain_frequency_days': 7
    },
    
    'caching': {
        'feature_cache_ttl_hours': 2,
        'prediction_cache_ttl_hours': 6,
        'model_cache_max_size': 10
    },
    
    'event_bus': {
        'redis_url': 'redis://localhost:6379/2',
        'consumer_group': 'ml-analytics-group',
        'streams': ['ml-features-stream', 'ml-predictions-stream', 'ml-training-stream'],
        'batch_size': 10,
        'timeout_ms': 5000
    }
}
```

### **Requirements.txt:**
```
# Core ML Framework
tensorflow==2.16.1
scikit-learn==1.4.2
xgboost==2.0.3
lightgbm==4.3.0

# Data Processing
pandas==2.2.2
numpy==1.26.4
pandas-ta==0.3.14b0

# Event-Bus Integration
redis==5.0.1
aioredis==2.0.1

# Database
psycopg2-binary==2.9.9
asyncpg==0.29.0

# API Framework
fastapi==0.110.0
uvicorn==0.27.0
websockets==12.0

# Monitoring
psutil==5.9.8
prometheus-client==0.19.0

# Utilities
pydantic==2.6.1
uuid==1.30
```

---

## 📊 **Performance und Monitoring**

### **Service-Metriken:**
```python
# ml_performance_metrics_v1_0_0_20250817.py

ML_SERVICE_METRICS = {
    'response_times': {
        'feature_calculation_ms': 500,
        'single_prediction_ms': 200,
        'batch_prediction_ms': 5000,
        'model_loading_ms': 3000
    },
    
    'throughput': {
        'predictions_per_minute': 1000,
        'features_per_minute': 500,
        'concurrent_requests': 50
    },
    
    'resource_usage': {
        'memory_limit_gb': 2.0,
        'cpu_limit_percent': 80,
        'disk_usage_gb': 10.0
    },
    
    'accuracy_targets': {
        'directional_accuracy_7d': 0.60,
        'directional_accuracy_30d': 0.58,
        'directional_accuracy_150d': 0.55,
        'directional_accuracy_365d': 0.52
    }
}
```

---

## ✅ **Deployment-Checklist**

### **Service-Deployment:**
- [ ] ML Analytics Service Code deployen
- [ ] Requirements installieren
- [ ] Datenbank-Schema erweitern
- [ ] Redis-Streams konfigurieren
- [ ] systemd Service konfigurieren
- [ ] Health-Checks implementieren
- [ ] Event-Handler registrieren
- [ ] Performance-Monitoring aktivieren

### **Integration-Tests:**
- [ ] Event-Bus Integration testen
- [ ] Database-Queries testen
- [ ] API-Endpoints testen
- [ ] Model-Loading testen
- [ ] Feature-Calculation testen
- [ ] Prediction-Generation testen

---

*ML Analytics Service Spezifikation erstellt: 17. August 2025*  
*Version: 1.0.0*  
*Port: 8019*  
*Integriert mit: Event-Driven aktienanalyse-ökosystem v5.1*