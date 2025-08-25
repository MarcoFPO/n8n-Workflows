#!/usr/bin/env python3
"""
ML Analytics Service v6.1.0 - PostgreSQL ML Repository
Clean Architecture v6.1.0 - Database Manager Integration

Comprehensive PostgreSQL Implementation für ML Repository
- Konsolidiert 6 SQLite-Datenbanken in eine optimierte PostgreSQL-Struktur
- Database Manager für Verbindungsmanagement
- Async Repository Pattern mit Connection Pooling
- Optimierte Indexing-Strategie für ML-Queries

Konsolidierte Tabellen:
- ml_models: Model metadata und versions
- ml_predictions: Prediction storage und retrieval
- ml_training_jobs: Training job lifecycle (placeholder)
- ml_performance_metrics: Performance tracking (placeholder)
- ml_risk_metrics: Risk assessment (placeholder)
- ml_features_cache: Feature engineering cache (placeholder)

Autor: Claude Code
Datum: 25. August 2025
Version: 6.1.0
"""

import structlog
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager

from ...domain.entities.ml_entities import (
    MLModel,
    MLPrediction, 
    MLModelType,
    MLPredictionHorizon,
    ModelConfiguration
)
from ...domain.repositories.ml_repository import (
    IMLModelRepository,
    IMLPredictionRepository,
    IMLAnalyticsRepository
)

logger = structlog.get_logger(__name__)


# =============================================================================
# POSTGRESQL ML MODEL REPOSITORY
# =============================================================================

class PostgreSQLMLModelRepository(IMLModelRepository):
    """PostgreSQL implementation of ML Model Repository"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operations_count = 0

    async def initialize_schema(self) -> bool:
        """Initialize ML models schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create ml_models table with comprehensive schema
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS ml_models (
                        model_id UUID PRIMARY KEY,
                        model_type VARCHAR(50) NOT NULL,
                        version VARCHAR(20) NOT NULL,
                        configuration JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        last_trained_at TIMESTAMPTZ,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        model_metadata JSONB DEFAULT '{}',
                        training_window_days INTEGER DEFAULT 252,
                        prediction_horizon VARCHAR(20),
                        feature_set TEXT[],
                        hyperparameters JSONB DEFAULT '{}',
                        model_size_bytes BIGINT DEFAULT 0,
                        performance_score DECIMAL(5,4),
                        CONSTRAINT valid_model_type CHECK (model_type IN (
                            'lstm_basic', 'lstm_multi_horizon', 'xgboost_sentiment',
                            'xgboost_fundamental', 'lightgbm_meta', 'ensemble_multi_horizon',
                            'risk_management', 'esg_analytics', 'market_intelligence',
                            'quantum_enhanced', 'portfolio_optimizer', 'correlation_engine',
                            'microstructure_engine', 'options_pricing', 'derivatives_engine',
                            'streaming_analytics'
                        )),
                        CONSTRAINT valid_horizon CHECK (prediction_horizon IN (
                            'intraday', 'short_term', 'medium_term', 'long_term', 'multi_horizon'
                        )),
                        CONSTRAINT positive_training_window CHECK (training_window_days > 0),
                        CONSTRAINT valid_performance CHECK (performance_score IS NULL OR (performance_score >= 0 AND performance_score <= 1))
                    )
                ''')
                
                # Create optimized indices for ML operations
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_type_active 
                    ON ml_models(model_type, is_active)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_last_trained 
                    ON ml_models(last_trained_at DESC NULLS LAST) 
                    WHERE is_active = true
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_performance 
                    ON ml_models(performance_score DESC NULLS LAST) 
                    WHERE is_active = true
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_horizon 
                    ON ml_models(prediction_horizon)
                ''')
                
                # GIN index for configuration and metadata JSONB queries
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_config_gin 
                    ON ml_models USING gin(configuration)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_metadata_gin 
                    ON ml_models USING gin(model_metadata)
                ''')
                
                # GIN index for feature_set array queries
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_models_features_gin 
                    ON ml_models USING gin(feature_set)
                ''')
                
                logger.info("ML models schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize ML models schema", error=str(e))
            return False
    
    async def save(self, model: MLModel) -> bool:
        """Save or update ML model with UPSERT functionality"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                await connection.execute(
                    '''INSERT INTO ml_models 
                       (model_id, model_type, version, configuration, created_at, 
                        last_trained_at, is_active, model_metadata, training_window_days,
                        prediction_horizon, feature_set, hyperparameters)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                       ON CONFLICT (model_id) 
                       DO UPDATE SET 
                           model_type = EXCLUDED.model_type,
                           version = EXCLUDED.version,
                           configuration = EXCLUDED.configuration,
                           last_trained_at = EXCLUDED.last_trained_at,
                           is_active = EXCLUDED.is_active,
                           model_metadata = EXCLUDED.model_metadata,
                           training_window_days = EXCLUDED.training_window_days,
                           prediction_horizon = EXCLUDED.prediction_horizon,
                           feature_set = EXCLUDED.feature_set,
                           hyperparameters = EXCLUDED.hyperparameters''',
                    model.model_id,
                    model.model_type.value,
                    model.version,
                    json.dumps(model.configuration.__dict__),
                    model.created_at,
                    model.last_trained_at,
                    model.is_active,
                    json.dumps(model.model_metadata),
                    model.configuration.training_window_days,
                    model.configuration.prediction_horizon.value,
                    model.configuration.feature_set,
                    json.dumps(model.configuration.hyperparameters)
                )
                
                logger.info("ML model saved successfully", model_id=model.model_id)
                return True
                
        except Exception as e:
            logger.error("Failed to save ML model", error=str(e), model_id=model.model_id)
            return False
    
    async def get_by_id(self, model_id: str) -> Optional[MLModel]:
        """Retrieve ML model by ID"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow(
                    '''SELECT model_id, model_type, version, configuration, created_at,
                              last_trained_at, is_active, model_metadata
                       FROM ml_models 
                       WHERE model_id = $1''',
                    model_id
                )
                
                if row:
                    return self._row_to_model(row)
                
                logger.debug("ML model not found", model_id=model_id)
                return None
                
        except Exception as e:
            logger.error("Failed to get ML model by ID", error=str(e), model_id=model_id)
            return None
    
    async def get_by_type(self, model_type: MLModelType) -> List[MLModel]:
        """Retrieve all models of specific type"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT model_id, model_type, version, configuration, created_at,
                              last_trained_at, is_active, model_metadata
                       FROM ml_models 
                       WHERE model_type = $1
                       ORDER BY created_at DESC''',
                    model_type.value
                )
                
                models = [self._row_to_model(row) for row in rows]
                logger.debug("Retrieved models by type", model_type=model_type.value, count=len(models))
                return models
                
        except Exception as e:
            logger.error("Failed to get models by type", error=str(e), model_type=model_type.value)
            return []
    
    async def get_active_models(self) -> List[MLModel]:
        """Retrieve all active ML models"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT model_id, model_type, version, configuration, created_at,
                              last_trained_at, is_active, model_metadata
                       FROM ml_models 
                       WHERE is_active = true
                       ORDER BY last_trained_at DESC NULLS LAST''',
                )
                
                models = [self._row_to_model(row) for row in rows]
                logger.debug("Retrieved active models", count=len(models))
                return models
                
        except Exception as e:
            logger.error("Failed to get active models", error=str(e))
            return []
    
    async def get_outdated_models(self, max_age_days: int = 30) -> List[MLModel]:
        """Retrieve outdated models that need retraining"""
        try:
            self._operations_count += 1
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT model_id, model_type, version, configuration, created_at,
                              last_trained_at, is_active, model_metadata
                       FROM ml_models 
                       WHERE is_active = true 
                       AND (last_trained_at IS NULL OR last_trained_at < $1)
                       ORDER BY created_at ASC''',
                    cutoff_time
                )
                
                models = [self._row_to_model(row) for row in rows]
                logger.debug("Retrieved outdated models", max_age_days=max_age_days, count=len(models))
                return models
                
        except Exception as e:
            logger.error("Failed to get outdated models", error=str(e))
            return []
    
    async def update_last_trained_at(self, model_id: str, trained_at: datetime) -> bool:
        """Update model's last training timestamp"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute(
                    '''UPDATE ml_models 
                       SET last_trained_at = $1, is_active = true 
                       WHERE model_id = $2''',
                    trained_at, model_id
                )
                
                logger.info("Updated model training timestamp", model_id=model_id, trained_at=trained_at)
                return True
                
        except Exception as e:
            logger.error("Failed to update training timestamp", error=str(e), model_id=model_id)
            return False
    
    async def deactivate_model(self, model_id: str) -> bool:
        """Deactivate ML model"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute(
                    'UPDATE ml_models SET is_active = false WHERE model_id = $1',
                    model_id
                )
                
                logger.info("Model deactivated", model_id=model_id)
                return True
                
        except Exception as e:
            logger.error("Failed to deactivate model", error=str(e), model_id=model_id)
            return False
    
    async def delete(self, model_id: str) -> bool:
        """Delete ML model"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute(
                    'DELETE FROM ml_models WHERE model_id = $1',
                    model_id
                )
                
                logger.warning("Model deleted", model_id=model_id)
                return True
                
        except Exception as e:
            logger.error("Failed to delete model", error=str(e), model_id=model_id)
            return False
    
    async def get_model_versions(self, model_type: MLModelType) -> List[MLModel]:
        """Get all versions of specific model type"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT model_id, model_type, version, configuration, created_at,
                              last_trained_at, is_active, model_metadata
                       FROM ml_models 
                       WHERE model_type = $1
                       ORDER BY version DESC, created_at DESC''',
                    model_type.value
                )
                
                models = [self._row_to_model(row) for row in rows]
                logger.debug("Retrieved model versions", model_type=model_type.value, count=len(models))
                return models
                
        except Exception as e:
            logger.error("Failed to get model versions", error=str(e), model_type=model_type.value)
            return []
    
    def _row_to_model(self, row) -> MLModel:
        """Convert database row to MLModel entity"""
        config_dict = json.loads(row['configuration']) if row['configuration'] else {}
        
        configuration = ModelConfiguration(
            model_type=MLModelType(config_dict.get('model_type', row['model_type'])),
            hyperparameters=config_dict.get('hyperparameters', {}),
            feature_set=config_dict.get('feature_set', []),
            training_window_days=config_dict.get('training_window_days', 252),
            prediction_horizon=MLPredictionHorizon(config_dict.get('prediction_horizon', 'short_term'))
        )
        
        return MLModel(
            model_id=str(row['model_id']),
            model_type=MLModelType(row['model_type']),
            version=row['version'],
            configuration=configuration,
            created_at=row['created_at'],
            last_trained_at=row['last_trained_at'],
            is_active=row['is_active'],
            model_metadata=json.loads(row['model_metadata']) if row['model_metadata'] else {}
        )


# =============================================================================
# POSTGRESQL ML PREDICTION REPOSITORY  
# =============================================================================

class PostgreSQLMLPredictionRepository(IMLPredictionRepository):
    """PostgreSQL implementation of ML Prediction Repository"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operations_count = 0

    async def initialize_schema(self) -> bool:
        """Initialize ML predictions schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create ml_predictions table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS ml_predictions (
                        prediction_id UUID PRIMARY KEY,
                        model_id UUID NOT NULL,
                        symbol VARCHAR(10) NOT NULL,
                        predicted_price DECIMAL(12,4) NOT NULL CHECK (predicted_price > 0),
                        confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
                        prediction_horizon VARCHAR(20) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        expires_at TIMESTAMPTZ,
                        features_used TEXT[],
                        prediction_metadata JSONB DEFAULT '{}',
                        actual_price DECIMAL(12,4),
                        prediction_error DECIMAL(8,4),
                        is_validated BOOLEAN DEFAULT false,
                        CONSTRAINT valid_prediction_horizon CHECK (prediction_horizon IN (
                            'intraday', 'short_term', 'medium_term', 'long_term', 'multi_horizon'
                        )),
                        FOREIGN KEY (model_id) REFERENCES ml_models(model_id) ON DELETE CASCADE
                    )
                ''')
                
                # Create optimized indices for prediction queries
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_symbol_created 
                    ON ml_predictions(symbol, created_at DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_model_created 
                    ON ml_predictions(model_id, created_at DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_confidence 
                    ON ml_predictions(confidence_score DESC, created_at DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_horizon 
                    ON ml_predictions(prediction_horizon, created_at DESC)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_expires 
                    ON ml_predictions(expires_at) 
                    WHERE expires_at IS NOT NULL
                ''')
                
                # GIN index for features and metadata
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_features_gin 
                    ON ml_predictions USING gin(features_used)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_ml_predictions_metadata_gin 
                    ON ml_predictions USING gin(prediction_metadata)
                ''')
                
                logger.info("ML predictions schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error("Failed to initialize ML predictions schema", error=str(e))
            return False
    
    async def save(self, prediction: MLPrediction) -> bool:
        """Save ML prediction with calculated expiration"""
        try:
            self._operations_count += 1
            
            # Calculate expiration based on horizon
            expires_at = self._calculate_expiration(prediction)
            
            async with self.db_manager.get_connection() as connection:
                await connection.execute(
                    '''INSERT INTO ml_predictions 
                       (prediction_id, model_id, symbol, predicted_price, confidence_score,
                        prediction_horizon, created_at, expires_at, features_used, prediction_metadata)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                       ON CONFLICT (prediction_id) 
                       DO UPDATE SET 
                           predicted_price = EXCLUDED.predicted_price,
                           confidence_score = EXCLUDED.confidence_score,
                           expires_at = EXCLUDED.expires_at,
                           features_used = EXCLUDED.features_used,
                           prediction_metadata = EXCLUDED.prediction_metadata''',
                    prediction.prediction_id,
                    prediction.model_id,
                    prediction.symbol,
                    prediction.predicted_price,
                    prediction.confidence_score,
                    prediction.prediction_horizon.value,
                    prediction.created_at,
                    expires_at,
                    prediction.features_used,
                    json.dumps(prediction.prediction_metadata)
                )
                
                logger.info("ML prediction saved successfully", 
                          prediction_id=prediction.prediction_id, symbol=prediction.symbol)
                return True
                
        except Exception as e:
            logger.error("Failed to save ML prediction", 
                        error=str(e), prediction_id=prediction.prediction_id)
            return False
    
    def _calculate_expiration(self, prediction: MLPrediction) -> datetime:
        """Calculate prediction expiration based on horizon"""
        horizon_days = {
            MLPredictionHorizon.INTRADAY: 1/24,  # 1 hour
            MLPredictionHorizon.SHORT_TERM: 7,
            MLPredictionHorizon.MEDIUM_TERM: 28,
            MLPredictionHorizon.LONG_TERM: 365,
            MLPredictionHorizon.MULTI_HORIZON: 365
        }
        
        days = horizon_days.get(prediction.prediction_horizon, 7)
        return prediction.created_at + timedelta(days=days)
    
    async def get_by_id(self, prediction_id: str) -> Optional[MLPrediction]:
        """Retrieve prediction by ID"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                row = await connection.fetchrow(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE prediction_id = $1''',
                    prediction_id
                )
                
                if row:
                    return self._row_to_prediction(row)
                
                return None
                
        except Exception as e:
            logger.error("Failed to get prediction by ID", error=str(e), prediction_id=prediction_id)
            return None
    
    async def get_by_symbol(self, symbol: str, limit: int = 100) -> List[MLPrediction]:
        """Retrieve predictions for specific symbol"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE symbol = $1
                       ORDER BY created_at DESC 
                       LIMIT $2''',
                    symbol.upper(), limit
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved predictions by symbol", symbol=symbol, count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get predictions by symbol", error=str(e), symbol=symbol)
            return []
    
    async def get_by_model(self, model_id: str, limit: int = 100) -> List[MLPrediction]:
        """Retrieve predictions from specific model"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE model_id = $1
                       ORDER BY created_at DESC 
                       LIMIT $2''',
                    model_id, limit
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved predictions by model", model_id=model_id, count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get predictions by model", error=str(e), model_id=model_id)
            return []
    
    async def get_high_confidence_predictions(self, min_confidence: float = 0.8, limit: int = 50) -> List[MLPrediction]:
        """Retrieve high confidence predictions"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE confidence_score >= $1
                       ORDER BY confidence_score DESC, created_at DESC 
                       LIMIT $2''',
                    min_confidence, limit
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved high confidence predictions", 
                           min_confidence=min_confidence, count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get high confidence predictions", error=str(e))
            return []
    
    async def get_expired_predictions(self) -> List[MLPrediction]:
        """Retrieve expired predictions for cleanup"""
        try:
            self._operations_count += 1
            now = datetime.now(timezone.utc)
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE expires_at IS NOT NULL AND expires_at <= $1
                       ORDER BY expires_at ASC''',
                    now
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved expired predictions", count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get expired predictions", error=str(e))
            return []
    
    async def get_predictions_by_horizon(self, horizon: MLPredictionHorizon, limit: int = 100) -> List[MLPrediction]:
        """Retrieve predictions by horizon type"""
        try:
            self._operations_count += 1
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE prediction_horizon = $1
                       ORDER BY created_at DESC 
                       LIMIT $2''',
                    horizon.value, limit
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved predictions by horizon", 
                           horizon=horizon.value, count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get predictions by horizon", error=str(e), horizon=horizon.value)
            return []
    
    async def get_recent_predictions(self, hours: int = 24, limit: int = 100) -> List[MLPrediction]:
        """Retrieve recent predictions"""
        try:
            self._operations_count += 1
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch(
                    '''SELECT prediction_id, model_id, symbol, predicted_price, confidence_score,
                              prediction_horizon, created_at, features_used, prediction_metadata
                       FROM ml_predictions 
                       WHERE created_at >= $1
                       ORDER BY created_at DESC 
                       LIMIT $2''',
                    cutoff_time, limit
                )
                
                predictions = [self._row_to_prediction(row) for row in rows]
                logger.debug("Retrieved recent predictions", hours=hours, count=len(predictions))
                return predictions
                
        except Exception as e:
            logger.error("Failed to get recent predictions", error=str(e))
            return []
    
    async def delete_expired_predictions(self) -> int:
        """Delete expired predictions"""
        try:
            self._operations_count += 1
            now = datetime.now(timezone.utc)
            
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute(
                    'DELETE FROM ml_predictions WHERE expires_at IS NOT NULL AND expires_at <= $1',
                    now
                )
                
                # Extract number of deleted rows from result
                deleted_count = int(result.split()[-1]) if result else 0
                
                logger.info("Deleted expired predictions", deleted_count=deleted_count)
                return deleted_count
                
        except Exception as e:
            logger.error("Failed to delete expired predictions", error=str(e))
            return 0
    
    def _row_to_prediction(self, row) -> MLPrediction:
        """Convert database row to MLPrediction entity"""
        return MLPrediction(
            prediction_id=str(row['prediction_id']),
            model_id=str(row['model_id']),
            symbol=row['symbol'],
            predicted_price=Decimal(str(row['predicted_price'])),
            confidence_score=float(row['confidence_score']),
            prediction_horizon=MLPredictionHorizon(row['prediction_horizon']),
            created_at=row['created_at'],
            features_used=list(row['features_used']) if row['features_used'] else [],
            prediction_metadata=json.loads(row['prediction_metadata']) if row['prediction_metadata'] else {}
        )


# =============================================================================
# AGGREGATE REPOSITORY IMPLEMENTATION
# =============================================================================

class PostgreSQLMLAnalyticsRepository(IMLAnalyticsRepository):
    """
    PostgreSQL implementation of ML Analytics Repository
    
    Manages consolidated ML operations in a single PostgreSQL database
    with optimized schema design and indexing strategy.
    """
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        
        # Initialize individual repositories
        self._models_repo = PostgreSQLMLModelRepository(db_manager)
        self._predictions_repo = PostgreSQLMLPredictionRepository(db_manager)
    
    @property
    def models(self) -> IMLModelRepository:
        """Get ML model repository"""
        return self._models_repo
    
    @property
    def predictions(self) -> IMLPredictionRepository:
        """Get ML prediction repository"""
        return self._predictions_repo
    
    @property
    def training_jobs(self):
        """Get training job repository - placeholder"""
        # In full implementation, would return PostgreSQLMLTrainingJobRepository
        raise NotImplementedError("Training jobs repository not implemented in this migration")
    
    @property
    def performance(self):
        """Get performance metrics repository - placeholder"""
        # In full implementation, would return PostgreSQLMLPerformanceRepository
        raise NotImplementedError("Performance repository not implemented in this migration")
    
    @property
    def risk(self):
        """Get risk metrics repository - placeholder"""
        # In full implementation, would return PostgreSQLMLRiskRepository
        raise NotImplementedError("Risk repository not implemented in this migration")
    
    async def initialize_schemas(self) -> bool:
        """Initialize database schemas for all repositories"""
        try:
            # Initialize models schema
            if not await self._models_repo.initialize_schema():
                return False
                
            # Initialize predictions schema
            if not await self._predictions_repo.initialize_schema():
                return False
            
            logger.info("ML Analytics repository schemas initialized")
            return True
            
        except Exception as e:
            logger.error("Error initializing repository schemas", error=str(e))
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get repository health status"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Get model counts
                model_count = await connection.fetchval(
                    'SELECT COUNT(*) FROM ml_models'
                ) or 0
                
                active_model_count = await connection.fetchval(
                    'SELECT COUNT(*) FROM ml_models WHERE is_active = true'
                ) or 0
                
                # Get prediction counts
                prediction_count = await connection.fetchval(
                    'SELECT COUNT(*) FROM ml_predictions'
                ) or 0
                
                recent_prediction_count = await connection.fetchval(
                    '''SELECT COUNT(*) FROM ml_predictions 
                       WHERE created_at >= NOW() - INTERVAL '24 hours' '''
                ) or 0
                
                return {
                    "status": "healthy",
                    "database": "PostgreSQL",
                    "statistics": {
                        "total_models": model_count,
                        "active_models": active_model_count,
                        "total_predictions": prediction_count,
                        "recent_predictions_24h": recent_prediction_count
                    },
                    "operations_count": (
                        self._models_repo._operations_count + 
                        self._predictions_repo._operations_count
                    )
                }
            
        except Exception as e:
            logger.error("Failed to get health status", error=str(e))
            return {
                "status": "unhealthy",
                "database": "PostgreSQL",
                "error": str(e)
            }
    
    async def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """Cleanup old data from all repositories"""
        try:
            cleanup_results = {}
            
            # Cleanup expired predictions
            deleted_predictions = await self._predictions_repo.delete_expired_predictions()
            cleanup_results["predictions_deleted"] = deleted_predictions
            
            logger.info("Cleaned up old ML data", cleanup_results=cleanup_results)
            return cleanup_results
            
        except Exception as e:
            logger.error("Error during ML data cleanup", error=str(e))
            return {"error": str(e)}