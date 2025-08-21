#!/usr/bin/env python3
"""
ML Analytics Service Orchestrator v1.0.0
Hauptorchestrator für alle ML-Operationen im aktienanalyse-ökosystem

Integration: Event-Driven Architecture (Port 8021)
Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import signal
import sys
import traceback
import numpy as np
import asyncpg
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import configuration
from config.ml_service_config import ML_SERVICE_CONFIG

# Import ML modules
from basic_features_v1_0_0_20250818 import BasicFeatureEngine
from simple_lstm_model_v1_0_0_20250818 import SimpleLSTMModel
from multi_horizon_lstm_model_v1_0_0_20250818 import MultiHorizonLSTMModel
from multi_horizon_ensemble_v1_0_0_20250818 import MultiHorizonEnsembleManager
from synthetic_multi_horizon_trainer_v1_0_0_20250818 import SyntheticMultiHorizonTrainer
from sentiment_features_v1_0_0_20250818 import SentimentFeatureEngine
from sentiment_xgboost_model_v1_0_0_20250818 import SentimentXGBoostModel
from fundamental_features_v1_0_0_20250818 import FundamentalFeatureEngine
from fundamental_xgboost_model_v1_0_0_20250818 import FundamentalXGBoostModel
from meta_lightgbm_model_v1_0_0_20250818 import MetaLightGBMModel
from ml_event_publisher_v1_0_0_20250818 import ml_event_publisher

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='{"service": "ml-analytics", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
)
logger = logging.getLogger("ml-analytics")


class MLAnalyticsService:
    """
    ML Analytics Service Orchestrator
    Verwaltet alle ML-Operationen im Event-Driven System
    """
    
    def __init__(self):
        self.service_name = "ml-analytics"
        self.service_port = ML_SERVICE_CONFIG['service']['port']
        
        # Infrastructure
        self.database_pool = None
        self.feature_engine = None
        self.sentiment_engine = None
        self.fundamental_engine = None
        self.lstm_model = None
        self.sentiment_model = None
        self.fundamental_model = None
        self.meta_model = None
        self.multi_horizon_models = {}  # Dict für verschiedene Horizonte
        self.app = None
        
        # Service State
        self.is_healthy = False
        self.startup_time = None
        self.shutdown_requested = False
        
    async def initialize_components(self):
        """Initialisiert alle Service-Komponenten"""
        try:
            logger.info("Initializing ML Analytics Service components...")
            
            # Database Connection Pool
            await self._initialize_database()
            
            # Initialize Feature Engines
            self.feature_engine = BasicFeatureEngine(self.database_pool)
            logger.info("Technical Feature Engine initialized")
            
            self.sentiment_engine = SentimentFeatureEngine(self.database_pool)
            logger.info("Sentiment Feature Engine initialized")
            
            self.fundamental_engine = FundamentalFeatureEngine(self.database_pool)
            logger.info("Fundamental Feature Engine initialized")
            
            # Initialize ML Models
            model_storage_path = ML_SERVICE_CONFIG['storage']['model_storage_path']
            self.lstm_model = SimpleLSTMModel(self.database_pool, model_storage_path)
            logger.info("LSTM Model initialized")
            
            self.sentiment_model = SentimentXGBoostModel(self.database_pool, model_storage_path)
            logger.info("Sentiment XGBoost Model initialized")
            
            self.fundamental_model = FundamentalXGBoostModel(self.database_pool, model_storage_path)
            logger.info("Fundamental XGBoost Model initialized")
            
            self.meta_model = MetaLightGBMModel(self.database_pool, model_storage_path)
            logger.info("Meta LightGBM Model initialized")
            
            # Initialize Multi-Horizon LSTM Models
            supported_horizons = [7, 30, 150, 365]
            for horizon in supported_horizons:
                self.multi_horizon_models[horizon] = MultiHorizonLSTMModel(
                    self.database_pool, model_storage_path, horizon
                )
            logger.info(f"Multi-Horizon LSTM Models initialized for horizons: {supported_horizons}")
            
            # Initialize Multi-Horizon Ensemble Manager
            self.multi_horizon_ensemble = MultiHorizonEnsembleManager(self.database_pool)
            logger.info("Multi-Horizon Ensemble Manager initialized")
            
            # Initialize Synthetic Multi-Horizon Trainer
            self.synthetic_trainer = SyntheticMultiHorizonTrainer(self.database_pool, model_storage_path)
            logger.info("Synthetic Multi-Horizon Trainer initialized")
            
            # Initialize ML Event Publisher
            await ml_event_publisher.initialize()
            logger.info("ML Event Publisher initialized")
            
            logger.info("ML Analytics Service components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    async def _initialize_database(self):
        """Initialisiert PostgreSQL Database Pool"""
        try:
            db_config = ML_SERVICE_CONFIG['database']
            connection_url = (
                f"postgresql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
                f"?sslmode=disable"
            )
            
            self.database_pool = await asyncpg.create_pool(
                connection_url,
                min_size=db_config.get('min_connections', 5),
                max_size=db_config.get('max_connections', 20),
                command_timeout=60,
                server_settings={
                    'application_name': 'ml-analytics',
                    'jit': 'off'
                }
            )
            
            # Test connection and check ML schema
            async with self.database_pool.acquire() as conn:
                await conn.execute('SELECT 1')
                
                # Check ML tables
                ml_tables = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'ml_%'"
                )
                
                logger.info(f"Database connection established - {ml_tables} ML tables found")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def setup_event_handlers(self):
        """Konfiguriert Event-Handler für ML-Events"""
        try:
            # For now, just log that event handlers would be set up
            logger.info("Event handlers setup (placeholder)")
            
        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            raise
    
    def _calculate_recommendation_strength(self, predictions: Dict[str, Any]) -> str:
        """Berechnet Empfehlungsstärke basierend auf ML-Predictions (placeholder)"""
        return "NEUTRAL"
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive Health Check"""
        try:
            health_status = {
                'service': 'ml-analytics',
                'version': '1.0.0',
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds() if self.startup_time else 0,
                'port': self.service_port,
                'components': {}
            }
            
            # Database Health Check
            if self.database_pool:
                try:
                    async with self.database_pool.acquire() as conn:
                        start_time = datetime.utcnow()
                        await conn.execute('SELECT 1')
                        ping_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        health_status['components']['database'] = {
                            'status': 'healthy',
                            'ping_ms': round(ping_time, 2),
                            'pool_size': self.database_pool.get_size(),
                            'idle_connections': self.database_pool.get_idle_size()
                        }
                except Exception as e:
                    health_status['components']['database'] = {
                        'status': 'critical',
                        'error': str(e)
                    }
                    health_status['status'] = 'warning'
            else:
                health_status['components']['database'] = {
                    'status': 'not_connected'
                }
                health_status['status'] = 'warning'
            
            # Overall health status
            component_statuses = [comp.get('status', 'unknown') for comp in health_status['components'].values()]
            if any(status == 'critical' for status in component_statuses):
                health_status['status'] = 'critical'
                self.is_healthy = False
            elif any(status in ['warning', 'not_connected'] for status in component_statuses):
                health_status['status'] = 'warning'
                self.is_healthy = True
            else:
                health_status['status'] = 'healthy'
                self.is_healthy = True
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            self.is_healthy = False
            return {
                'service': 'ml-analytics',
                'status': 'critical',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def graceful_shutdown(self):
        """Graceful Service Shutdown"""
        try:
            logger.info("Starting graceful shutdown...")
            self.shutdown_requested = True
            
            # Stop accepting new requests
            if self.app:
                logger.info("Stopping FastAPI application...")
            
            # Close database pool
            if self.database_pool:
                await self.database_pool.close()
                logger.info("Database pool closed")
            
            # Close Event Publisher
            await ml_event_publisher.close()
            logger.info("ML Event Publisher closed")
            
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


# Global service instance
ml_service = MLAnalyticsService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan Manager"""
    # Startup
    try:
        logger.info("Starting ML Analytics Service...")
        ml_service.startup_time = datetime.utcnow()
        
        await ml_service.initialize_components()
        await ml_service.setup_event_handlers()
        
        logger.info(f"ML Analytics Service started successfully on port {ML_SERVICE_CONFIG['service']['port']}")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start service: {str(e)}")
        raise
    
    # Shutdown
    finally:
        await ml_service.graceful_shutdown()


# FastAPI Application
app = FastAPI(
    title="ML Analytics Service",
    description="Machine Learning Analytics Service für aktienanalyse-ökosystem",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://10.1.1.174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_endpoint():
    """Service Health Check"""
    return await ml_service.health_check()

# ML API endpoints
@app.get("/api/v1/status")
async def get_ml_status():
    """Get ML service status"""
    return {"status": "active", "service": "ml-analytics", "version": "1.0.0"}

@app.get("/api/v1/schema/info")
async def get_ml_schema_info():
    """Get ML database schema information"""
    try:
        if not ml_service.database_pool:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        async with ml_service.database_pool.acquire() as conn:
            # Get ML tables
            ml_tables = await conn.fetch("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public' AND table_name LIKE 'ml_%'
                ORDER BY table_name
            """)
            
            # Get schema version
            try:
                schema_version = await conn.fetchrow(
                    "SELECT version, deployed_at FROM ml_schema_version ORDER BY deployed_at DESC LIMIT 1"
                )
            except:
                schema_version = None
            
            return {
                "ml_tables": [dict(row) for row in ml_tables],
                "tables_count": len(ml_tables),
                "schema_version": dict(schema_version) if schema_version else None,
                "database_connected": True
            }
            
    except Exception as e:
        logger.error(f"Failed to get ML schema info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models/status")
async def get_models_status():
    """Get ML models status"""
    try:
        if not ml_service.database_pool:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        async with ml_service.database_pool.acquire() as conn:
            # Get model registry info
            models = await conn.fetch("""
                SELECT model_id, model_type, model_version, horizon_days, status, 
                       file_path, performance_metrics, created_at
                FROM ml_model_metadata
                WHERE status = 'active'
                ORDER BY model_type, horizon_days
            """)
            
            return {
                "active_models": [dict(row) for row in models],
                "models_count": len(models),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get models status: {str(e)}")
        # Return empty result if table doesn't exist yet
        return {
            "active_models": [],
            "models_count": 0,
            "message": "No models registered yet",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/v1/predictions/{symbol}")
async def get_predictions(symbol: str):
    """Get latest predictions for symbol"""
    try:
        if not ml_service.database_pool:
            raise HTTPException(status_code=503, detail="Database not connected")
        
        symbol = symbol.upper()
        
        async with ml_service.database_pool.acquire() as conn:
            # Get latest predictions
            predictions = await conn.fetch("""
                SELECT model_type, horizon_days, predicted_value, 
                       confidence_score, prediction_timestamp
                FROM ml_predictions
                WHERE symbol = $1 
                AND prediction_timestamp >= NOW() - INTERVAL '24 hours'
                ORDER BY prediction_timestamp DESC
                LIMIT 20
            """, symbol)
            
            return {
                "symbol": symbol,
                "predictions": [dict(row) for row in predictions],
                "predictions_count": len(predictions),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get predictions for {symbol}: {str(e)}")
        # Return empty result if table doesn't exist yet
        return {
            "symbol": symbol,
            "predictions": [],
            "predictions_count": 0,
            "message": "No predictions available yet",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/v1/features/calculate/{symbol}")
async def calculate_features(symbol: str):
    """Calculate technical features for symbol"""
    try:
        if not ml_service.feature_engine:
            raise HTTPException(status_code=503, detail="Feature engine not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Feature calculation requested for {symbol}")
        
        # Calculate features using the feature engine
        result = await ml_service.feature_engine.calculate_basic_features(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish feature calculation event
        if "features" in result:
            features = result["features"]
            quality_score = 0.92  # Default quality score
            await ml_event_publisher.publish_feature_calculated(symbol, features, quality_score)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/features/{symbol}")
async def get_features(symbol: str):
    """Get latest calculated features for symbol"""
    try:
        if not ml_service.feature_engine:
            raise HTTPException(status_code=503, detail="Feature engine not initialized")
        
        symbol = symbol.upper()
        
        # Get latest features
        result = await ml_service.feature_engine.get_latest_features(symbol)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/{symbol}")
async def train_lstm_model(symbol: str):
    """Train LSTM model for 7-day predictions"""
    try:
        if not ml_service.lstm_model:
            raise HTTPException(status_code=503, detail="LSTM model not initialized")
        
        symbol = symbol.upper()
        logger.info(f"LSTM training requested for {symbol}")
        
        # Publish training started event
        await ml_event_publisher.publish_model_training_started(symbol, "technical", 7)
        
        # Train LSTM model
        result = await ml_service.lstm_model.train_model(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish training completed event
        if "model_metrics" in result:
            model_id = "technical_7d_" + symbol.lower()
            metrics = result["model_metrics"]
            await ml_event_publisher.publish_model_training_completed(
                symbol, "technical", 7, model_id, metrics
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to train LSTM model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions/generate/{symbol}")
async def generate_prediction(symbol: str):
    """Generate 7-day prediction using trained LSTM model"""
    try:
        if not ml_service.lstm_model or not ml_service.feature_engine:
            raise HTTPException(status_code=503, detail="ML components not initialized")
        
        symbol = symbol.upper()
        
        # Get latest features
        features_result = await ml_service.feature_engine.get_latest_features(symbol)
        if "error" in features_result or not features_result.get("features"):
            raise HTTPException(status_code=400, detail="No features available - calculate features first")
        
        # Generate prediction
        prediction = await ml_service.lstm_model.predict(symbol, features_result["features"])
        
        if "error" in prediction:
            raise HTTPException(status_code=500, detail=prediction["error"])
        
        # Publish prediction generated event
        if "predicted_price" in prediction and "confidence_score" in prediction:
            await ml_event_publisher.publish_prediction_generated(
                symbol, "technical", 7, 
                prediction["predicted_price"], 
                prediction["confidence_score"]
            )
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Sentiment API Endpoints
@app.post("/api/v1/sentiment/calculate/{symbol}")
async def calculate_sentiment_features(symbol: str):
    """Calculate sentiment features for symbol"""
    try:
        if not ml_service.sentiment_engine:
            raise HTTPException(status_code=503, detail="Sentiment engine not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Sentiment feature calculation requested for {symbol}")
        
        # Calculate sentiment features
        result = await ml_service.sentiment_engine.calculate_sentiment_features(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish sentiment calculation event
        if "features" in result:
            features = result["features"]
            quality_score = 0.85  # Default sentiment quality score
            await ml_event_publisher.publish_feature_calculated(symbol, features, quality_score)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate sentiment features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sentiment/{symbol}")
async def get_sentiment_features(symbol: str):
    """Get latest sentiment features for symbol"""
    try:
        if not ml_service.sentiment_engine:
            raise HTTPException(status_code=503, detail="Sentiment engine not initialized")
        
        symbol = symbol.upper()
        result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sentiment features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/sentiment/{symbol}")
async def train_sentiment_model(symbol: str):
    """Train Sentiment XGBoost model for 7-day predictions"""
    try:
        if not ml_service.sentiment_model:
            raise HTTPException(status_code=503, detail="Sentiment model not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Sentiment XGBoost training requested for {symbol}")
        
        # Publish training started event
        await ml_event_publisher.publish_model_training_started(symbol, "sentiment", 7)
        
        # Train Sentiment model
        result = await ml_service.sentiment_model.train_model(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish training completed event
        if "model_metrics" in result:
            model_id = "sentiment_7d_" + symbol.lower()
            metrics = result["model_metrics"]
            await ml_event_publisher.publish_model_training_completed(
                symbol, "sentiment", 7, model_id, metrics
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to train sentiment model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions/sentiment/{symbol}")
async def generate_sentiment_prediction(symbol: str):
    """Generate 7-day prediction using sentiment XGBoost model"""
    try:
        if not ml_service.sentiment_model or not ml_service.sentiment_engine:
            raise HTTPException(status_code=503, detail="Sentiment components not initialized")
        
        symbol = symbol.upper()
        
        # Get latest sentiment features
        sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
        if "error" in sentiment_result:
            raise HTTPException(status_code=400, detail="No sentiment features available - calculate sentiment features first")
        
        # Get technical features for combination
        technical_result = await ml_service.feature_engine.get_latest_features(symbol)
        
        # Combine features
        combined_features = {}
        if "features" in sentiment_result:
            combined_features.update(sentiment_result["features"])
        if "features" in technical_result and not technical_result.get("error"):
            combined_features.update(technical_result["features"])
        
        if not combined_features:
            raise HTTPException(status_code=400, detail="No features available for prediction")
        
        # Generate sentiment prediction
        prediction = await ml_service.sentiment_model.predict(symbol, combined_features)
        
        if "error" in prediction:
            raise HTTPException(status_code=500, detail=prediction["error"])
        
        # Publish prediction generated event
        if "predicted_price" in prediction and "confidence_score" in prediction:
            await ml_event_publisher.publish_prediction_generated(
                symbol, "sentiment", 7, 
                prediction["predicted_price"], 
                prediction["confidence_score"]
            )
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate sentiment prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Fundamental API Endpoints
@app.post("/api/v1/fundamental/calculate/{symbol}")
async def calculate_fundamental_features(symbol: str):
    """Calculate fundamental features for symbol"""
    try:
        if not ml_service.fundamental_engine:
            raise HTTPException(status_code=503, detail="Fundamental engine not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Fundamental feature calculation requested for {symbol}")
        
        # Calculate fundamental features
        result = await ml_service.fundamental_engine.calculate_fundamental_features(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish fundamental calculation event
        if "features" in result:
            features = result["features"]
            quality_score = 0.88  # Default fundamental quality score
            await ml_event_publisher.publish_feature_calculated(symbol, features, quality_score)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate fundamental features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/fundamental/{symbol}")
async def get_fundamental_features(symbol: str):
    """Get latest fundamental features for symbol"""
    try:
        if not ml_service.fundamental_engine:
            raise HTTPException(status_code=503, detail="Fundamental engine not initialized")
        
        symbol = symbol.upper()
        result = await ml_service.fundamental_engine.get_latest_fundamental_features(symbol)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get fundamental features for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/models/train/fundamental/{symbol}")
async def train_fundamental_model(symbol: str):
    """Train Fundamental XGBoost model for 7-day predictions"""
    try:
        if not ml_service.fundamental_model:
            raise HTTPException(status_code=503, detail="Fundamental model not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Fundamental XGBoost training requested for {symbol}")
        
        # Publish training started event
        await ml_event_publisher.publish_model_training_started(symbol, "fundamental", 7)
        
        # Train Fundamental model
        result = await ml_service.fundamental_model.train_model(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish training completed event
        if "model_metrics" in result:
            model_id = "fundamental_7d_" + symbol.lower()
            metrics = result["model_metrics"]
            await ml_event_publisher.publish_model_training_completed(
                symbol, "fundamental", 7, model_id, metrics
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to train fundamental model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions/fundamental/{symbol}")
async def generate_fundamental_prediction(symbol: str):
    """Generate 7-day prediction using fundamental XGBoost model"""
    try:
        if not ml_service.fundamental_model or not ml_service.fundamental_engine:
            raise HTTPException(status_code=503, detail="Fundamental components not initialized")
        
        symbol = symbol.upper()
        
        # Get latest fundamental features
        fundamental_result = await ml_service.fundamental_engine.get_latest_fundamental_features(symbol)
        if "error" in fundamental_result:
            raise HTTPException(status_code=400, detail="No fundamental features available - calculate fundamental features first")
        
        # Get technical and sentiment features for combination
        technical_result = await ml_service.feature_engine.get_latest_features(symbol)
        sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
        
        # Combine all features
        combined_features = {}
        if "features" in fundamental_result:
            combined_features.update(fundamental_result["features"])
        if "features" in technical_result and not technical_result.get("error"):
            combined_features.update(technical_result["features"])
        if "features" in sentiment_result and not sentiment_result.get("error"):
            combined_features.update(sentiment_result["features"])
        
        if not combined_features:
            raise HTTPException(status_code=400, detail="No features available for prediction")
        
        # Generate fundamental prediction
        prediction = await ml_service.fundamental_model.predict(symbol, combined_features)
        
        if "error" in prediction:
            raise HTTPException(status_code=500, detail=prediction["error"])
        
        # Publish prediction generated event
        if "predicted_price" in prediction and "confidence_score" in prediction:
            await ml_event_publisher.publish_prediction_generated(
                symbol, "fundamental", 7, 
                prediction["predicted_price"], 
                prediction["confidence_score"]
            )
        
        return prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate fundamental prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Meta-Model API Endpoints
@app.post("/api/v1/models/train/meta/{symbol}")
async def train_meta_model(symbol: str):
    """Train Meta LightGBM model for ensemble predictions"""
    try:
        if not ml_service.meta_model:
            raise HTTPException(status_code=503, detail="Meta model not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Meta LightGBM training requested for {symbol}")
        
        # Publish training started event
        await ml_event_publisher.publish_model_training_started(symbol, "meta", 7)
        
        # Train Meta model
        result = await ml_service.meta_model.train_model(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish training completed event
        if "model_metrics" in result:
            model_id = "meta_7d_" + symbol.lower()
            metrics = result["model_metrics"]
            await ml_event_publisher.publish_model_training_completed(
                symbol, "meta", 7, model_id, metrics
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to train meta model for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Multi-Horizon LSTM Endpoints ===

@app.post("/api/v1/models/train/multi-horizon/{symbol}")
async def train_multi_horizon_model(symbol: str, horizon_days: int = 7):
    """Train Multi-Horizon LSTM model for specific horizon"""
    try:
        if horizon_days not in ml_service.multi_horizon_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported horizon: {horizon_days}. Supported: {list(ml_service.multi_horizon_models.keys())}"
            )
        
        symbol = symbol.upper()
        model = ml_service.multi_horizon_models[horizon_days]
        logger.info(f"Multi-Horizon LSTM training requested for {symbol} ({horizon_days} days)")
        
        # Publish training started event
        await ml_event_publisher.publish_model_training_started(symbol, f"multi_horizon_lstm_{horizon_days}d", horizon_days)
        
        result = await model.train_model(symbol)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Publish training completed event
        if "model_metrics" in result:
            model_id = f"multi_horizon_lstm_{horizon_days}d_" + symbol.lower()
            metrics = result["model_metrics"]
            await ml_event_publisher.publish_model_training_completed(
                symbol, f"multi_horizon_lstm_{horizon_days}d", horizon_days, model_id, metrics
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error training multi-horizon model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions/multi-horizon/{symbol}")
async def generate_multi_horizon_prediction(symbol: str, horizon_days: int = 7):
    """Generate Multi-Horizon prediction for specific horizon"""
    try:
        if horizon_days not in ml_service.multi_horizon_models:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported horizon: {horizon_days}. Supported: {list(ml_service.multi_horizon_models.keys())}"
            )
        
        symbol = symbol.upper()
        
        # Hole aktuelle Features
        features_result = await ml_service.feature_engine.calculate_basic_features(symbol)
        if "error" in features_result:
            raise HTTPException(status_code=500, detail=features_result["error"])
        
        model = ml_service.multi_horizon_models[horizon_days]
        logger.info(f"Multi-Horizon prediction requested for {symbol} ({horizon_days} days)")
        result = await model.predict(symbol, features_result["features"])
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Store prediction in database
        if "predicted_price" in result:
            try:
                await ml_service._store_prediction(
                    symbol, f"multi_horizon_lstm_{horizon_days}d", horizon_days,
                    result["predicted_price"], result.get("confidence_score", 0.8)
                )
            except Exception as e:
                logger.error(f"Failed to store multi-horizon prediction: {str(e)}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating multi-horizon prediction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/all-horizons/{symbol}")
async def get_all_horizon_predictions(symbol: str):
    """Get predictions for all supported horizons"""
    try:
        symbol = symbol.upper()
        logger.info(f"All-horizon predictions requested for {symbol}")
        
        # Hole aktuelle Features
        features_result = await ml_service.feature_engine.calculate_basic_features(symbol)
        if "error" in features_result:
            raise HTTPException(status_code=500, detail=features_result["error"])
        
        predictions = {}
        errors = {}
        
        for horizon_days, model in ml_service.multi_horizon_models.items():
            try:
                result = await model.predict(symbol, features_result["features"])
                if "error" in result:
                    errors[f"{horizon_days}d"] = result["error"]
                else:
                    predictions[f"{horizon_days}d"] = result
                    
                    # Store prediction in database
                    if "predicted_price" in result:
                        try:
                            await ml_service._store_prediction(
                                symbol, f"multi_horizon_lstm_{horizon_days}d", horizon_days,
                                result["predicted_price"], result.get("confidence_score", 0.8)
                            )
                        except Exception as e:
                            logger.error(f"Failed to store prediction for {horizon_days}d: {str(e)}")
                            
            except Exception as e:
                errors[f"{horizon_days}d"] = str(e)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": predictions,
            "errors": errors if errors else None,
            "horizons_available": len(predictions),
            "horizons_total": len(ml_service.multi_horizon_models),
            "supported_horizons": list(ml_service.multi_horizon_models.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all-horizon predictions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/predictions/meta/{symbol}")
async def generate_meta_prediction(symbol: str):
    """Generate 7-day ensemble prediction using Meta LightGBM model"""
    try:
        if not ml_service.meta_model:
            raise HTTPException(status_code=503, detail="Meta model not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Meta ensemble prediction requested for {symbol}")
        
        # Collect predictions from all base models
        base_predictions = {}
        
        # Get Technical prediction
        try:
            technical_result = await ml_service.feature_engine.get_latest_features(symbol)
            if "features" in technical_result and not technical_result.get("error"):
                tech_pred = await ml_service.lstm_model.predict(symbol, technical_result["features"])
                if "predicted_price" in tech_pred and "confidence_score" in tech_pred:
                    base_predictions['technical'] = {
                        'predicted_price': tech_pred['predicted_price'],
                        'confidence_score': tech_pred['confidence_score']
                    }
        except Exception as e:
            logger.warning(f"Failed to get technical prediction: {str(e)}")
        
        # Get Sentiment prediction
        try:
            sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
            if "features" in sentiment_result and not sentiment_result.get("error"):
                technical_result = await ml_service.feature_engine.get_latest_features(symbol)
                combined_features = {}
                if "features" in sentiment_result:
                    combined_features.update(sentiment_result["features"])
                if "features" in technical_result and not technical_result.get("error"):
                    combined_features.update(technical_result["features"])
                
                if combined_features:
                    sent_pred = await ml_service.sentiment_model.predict(symbol, combined_features)
                    if "predicted_price" in sent_pred and "confidence_score" in sent_pred:
                        base_predictions['sentiment'] = {
                            'predicted_price': sent_pred['predicted_price'],
                            'confidence_score': sent_pred['confidence_score']
                        }
        except Exception as e:
            logger.warning(f"Failed to get sentiment prediction: {str(e)}")
        
        # Get Fundamental prediction
        try:
            fundamental_result = await ml_service.fundamental_engine.get_latest_fundamental_features(symbol)
            if "features" in fundamental_result and not fundamental_result.get("error"):
                technical_result = await ml_service.feature_engine.get_latest_features(symbol)
                sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
                
                combined_features = {}
                if "features" in fundamental_result:
                    combined_features.update(fundamental_result["features"])
                if "features" in technical_result and not technical_result.get("error"):
                    combined_features.update(technical_result["features"])
                if "features" in sentiment_result and not sentiment_result.get("error"):
                    combined_features.update(sentiment_result["features"])
                
                if combined_features:
                    fund_pred = await ml_service.fundamental_model.predict(symbol, combined_features)
                    if "predicted_price" in fund_pred and "confidence_score" in fund_pred:
                        base_predictions['fundamental'] = {
                            'predicted_price': fund_pred['predicted_price'],
                            'confidence_score': fund_pred['confidence_score']
                        }
        except Exception as e:
            logger.warning(f"Failed to get fundamental prediction: {str(e)}")
        
        # Check if we have sufficient base predictions
        if len(base_predictions) < 2:
            raise HTTPException(status_code=400, detail=f"Insufficient base model predictions (need at least 2, got {len(base_predictions)})")
        
        # Generate meta prediction
        meta_prediction = await ml_service.meta_model.predict(symbol, base_predictions)
        
        if "error" in meta_prediction:
            raise HTTPException(status_code=500, detail=meta_prediction["error"])
        
        # Add base predictions info to response
        meta_prediction["base_predictions"] = base_predictions
        meta_prediction["base_models_count"] = len(base_predictions)
        
        # Publish meta prediction generated event
        if "predicted_price" in meta_prediction and "confidence_score" in meta_prediction:
            await ml_event_publisher.publish_prediction_generated(
                symbol, "meta", 7, 
                meta_prediction["predicted_price"], 
                meta_prediction["confidence_score"]
            )
        
        return meta_prediction
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate meta prediction for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/ensemble/{symbol}")
async def get_ensemble_overview(symbol: str):
    """Get comprehensive ensemble overview with all model predictions"""
    try:
        symbol = symbol.upper()
        logger.info(f"Ensemble overview requested for {symbol}")
        
        ensemble_overview = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "models": {},
            "ensemble_summary": {}
        }
        
        # Collect all individual model predictions
        models_data = []
        
        # Technical model
        try:
            technical_result = await ml_service.feature_engine.get_latest_features(symbol)
            if "features" in technical_result and not technical_result.get("error"):
                tech_pred = await ml_service.lstm_model.predict(symbol, technical_result["features"])
                if "predicted_price" in tech_pred:
                    ensemble_overview["models"]["technical"] = tech_pred
                    models_data.append(("technical", tech_pred["predicted_price"], tech_pred.get("confidence_score", 0.5)))
        except Exception as e:
            logger.warning(f"Technical model unavailable: {str(e)}")
        
        # Sentiment model
        try:
            sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
            if "features" in sentiment_result and not sentiment_result.get("error"):
                technical_result = await ml_service.feature_engine.get_latest_features(symbol)
                combined_features = {}
                if "features" in sentiment_result:
                    combined_features.update(sentiment_result["features"])
                if "features" in technical_result and not technical_result.get("error"):
                    combined_features.update(technical_result["features"])
                
                if combined_features:
                    sent_pred = await ml_service.sentiment_model.predict(symbol, combined_features)
                    if "predicted_price" in sent_pred:
                        ensemble_overview["models"]["sentiment"] = sent_pred
                        models_data.append(("sentiment", sent_pred["predicted_price"], sent_pred.get("confidence_score", 0.5)))
        except Exception as e:
            logger.warning(f"Sentiment model unavailable: {str(e)}")
        
        # Fundamental model
        try:
            fundamental_result = await ml_service.fundamental_engine.get_latest_fundamental_features(symbol)
            if "features" in fundamental_result and not fundamental_result.get("error"):
                technical_result = await ml_service.feature_engine.get_latest_features(symbol)
                sentiment_result = await ml_service.sentiment_engine.get_latest_sentiment_features(symbol)
                
                combined_features = {}
                if "features" in fundamental_result:
                    combined_features.update(fundamental_result["features"])
                if "features" in technical_result and not technical_result.get("error"):
                    combined_features.update(technical_result["features"])
                if "features" in sentiment_result and not sentiment_result.get("error"):
                    combined_features.update(sentiment_result["features"])
                
                if combined_features:
                    fund_pred = await ml_service.fundamental_model.predict(symbol, combined_features)
                    if "predicted_price" in fund_pred:
                        ensemble_overview["models"]["fundamental"] = fund_pred
                        models_data.append(("fundamental", fund_pred["predicted_price"], fund_pred.get("confidence_score", 0.5)))
        except Exception as e:
            logger.warning(f"Fundamental model unavailable: {str(e)}")
        
        # Calculate ensemble summary
        if models_data:
            prices = [data[1] for data in models_data]
            confidences = [data[2] for data in models_data]
            
            ensemble_overview["ensemble_summary"] = {
                "models_available": len(models_data),
                "models_list": [data[0] for data in models_data],
                "price_mean": round(sum(prices) / len(prices), 2),
                "price_min": round(min(prices), 2),
                "price_max": round(max(prices), 2),
                "price_std": round(float(np.std(prices)), 2) if len(prices) > 1 else 0.0,
                "confidence_mean": round(sum(confidences) / len(confidences), 3),
                "agreement_score": round(1.0 - (np.std(prices) / np.mean(prices)), 3) if np.mean(prices) > 0 else 0.0
            }
        else:
            ensemble_overview["ensemble_summary"] = {
                "models_available": 0,
                "error": "No model predictions available"
            }
        
        return ensemble_overview
        
    except Exception as e:
        logger.error(f"Failed to get ensemble overview for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === Synthetic Multi-Horizon Training Endpoints ===

@app.post("/api/v1/models/train/synthetic-multi-horizon/{symbol}")
async def train_synthetic_multi_horizon(symbol: str, background_tasks: BackgroundTasks):
    """Train all Multi-Horizon LSTM models using synthetic data"""
    try:
        if not ml_service.synthetic_trainer:
            raise HTTPException(status_code=503, detail="Synthetic trainer not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Synthetic multi-horizon training requested for {symbol}")
        
        # Start training in background
        background_tasks.add_task(
            _perform_synthetic_multi_horizon_training, symbol
        )
        
        return {
            "message": f"Synthetic multi-horizon training started for {symbol}",
            "symbol": symbol,
            "status": "training_started",
            "horizons": [7, 30, 150, 365],
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting synthetic multi-horizon training: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/predictions/ensemble-analysis/{symbol}")
async def get_ensemble_analysis(symbol: str):
    """Get comprehensive multi-horizon ensemble analysis"""
    try:
        if not ml_service.multi_horizon_ensemble:
            raise HTTPException(status_code=503, detail="Multi-horizon ensemble not initialized")
        
        symbol = symbol.upper()
        logger.info(f"Multi-horizon ensemble analysis requested for {symbol}")
        
        # Get all-horizon predictions first
        predictions = {}
        for horizon in ml_service.multi_horizon_models:
            try:
                # Get features
                features = await ml_service.feature_engine.get_latest_features(symbol)
                if "features" in features and not features.get("error"):
                    # Get prediction
                    pred = await ml_service.multi_horizon_models[horizon].predict(symbol, features["features"])
                    if "predicted_price" in pred and "confidence_score" in pred:
                        predictions[f"{horizon}d"] = pred
            except Exception as e:
                logger.warning(f"Failed to get prediction for {horizon}d horizon: {str(e)}")
        
        if not predictions:
            return {
                "symbol": symbol,
                "error": "No predictions available for ensemble analysis",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Perform ensemble analysis
        analysis = await ml_service.multi_horizon_ensemble.get_multi_horizon_analysis(symbol, predictions)
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ensemble analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _perform_synthetic_multi_horizon_training(symbol: str):
    """Background task for synthetic multi-horizon training"""
    try:
        logger.info(f"Starting background synthetic multi-horizon training for {symbol}")
        
        # Publish training started events
        for horizon in [7, 30, 150, 365]:
            await ml_event_publisher.publish_model_training_started(
                symbol, f"synthetic_multi_horizon_lstm_{horizon}d", horizon
            )
        
        # Perform training
        result = await ml_service.synthetic_trainer.train_all_horizons(symbol)
        
        # Publish training completed events
        if "results" in result:
            for horizon_key, horizon_result in result["results"].items():
                if "error" not in horizon_result and "model_metrics" in horizon_result:
                    horizon_days = int(horizon_key.replace('d', ''))
                    model_id = f"synthetic_multi_horizon_lstm_{horizon_days}d_" + symbol.lower()
                    metrics = horizon_result["model_metrics"]
                    await ml_event_publisher.publish_model_training_completed(
                        symbol, f"synthetic_multi_horizon_lstm_{horizon_days}d", horizon_days, model_id, metrics
                    )
        
        logger.info(f"Background synthetic multi-horizon training completed for {symbol}")
        logger.info(f"Training summary: {result.get('summary', {})}")
        
    except Exception as e:
        logger.error(f"Background synthetic multi-horizon training failed for {symbol}: {str(e)}")

# Store app reference
ml_service.app = app


def signal_handler(signum, frame):
    """Signal Handler for Graceful Shutdown"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    asyncio.create_task(ml_service.graceful_shutdown())
    sys.exit(0)


if __name__ == "__main__":
    # Signal Handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start Service
        uvicorn.run(
            "ml_analytics_orchestrator_v1_0_0_20250817:app",
            host=ML_SERVICE_CONFIG['service']['host'],
            port=ML_SERVICE_CONFIG['service']['port'],
            workers=1,  # Single worker für ML-Service
            log_level="info",
            access_log=True,
            reload=False
        )
        
    except Exception as e:
        logger.error(f"Failed to start ML Analytics Service: {str(e)}")
        sys.exit(1)