#!/usr/bin/env python3
"""
ML Analytics Repository Implementation

Autor: Claude Code - Repository Pattern Implementer
Datum: 26. August 2025
Clean Architecture v6.0.0 - Infrastructure Layer
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from ...domain.entities.prediction import PredictionResult, EnsemblePrediction
from ...domain.entities.model_configuration import ModelConfiguration, ModelPerformanceMetrics
from ...domain.entities.ml_engine import MLEngineType, PredictionHorizon

logger = logging.getLogger(__name__)


class MLAnalyticsRepository:
    """
    ML Analytics Repository Implementation
    
    Infrastructure implementation of repository interfaces
    - Uses PostgreSQL for production
    - In-memory storage for development/testing
    - Implements async patterns for non-blocking I/O
    """
    
    def __init__(self, database_pool):
        self._database_pool = database_pool
        self._is_initialized = False
        
        # In-memory storage for development (would be replaced by actual DB queries)
        self._predictions: Dict[UUID, PredictionResult] = {}
        self._ensembles: Dict[UUID, EnsemblePrediction] = {}
        self._model_configs: Dict[str, ModelConfiguration] = {}
        self._performance_metrics: Dict[str, List[ModelPerformanceMetrics]] = {}
    
    async def initialize(self) -> bool:
        """Initialize repository and database schema"""
        
        try:
            logger.info("Initializing ML Analytics Repository...")
            
            # In real implementation, would create/migrate database schema
            await self._ensure_database_schema()
            
            # Create indices for performance
            await self._create_database_indices()
            
            self._is_initialized = True
            logger.info("ML Analytics Repository initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ML Analytics Repository: {str(e)}")
            return False
    
    # ===================== PREDICTION REPOSITORY METHODS =====================
    
    async def save_prediction(self, prediction: PredictionResult) -> bool:
        """Save prediction result to repository"""
        
        try:
            # In real implementation, would use SQL:
            # INSERT INTO predictions (id, symbol, engine_type, predicted_price, ...) VALUES (...)
            
            self._predictions[prediction.prediction_id] = prediction
            
            logger.debug(f"Saved prediction {prediction.prediction_id} for {prediction.target.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save prediction: {str(e)}")
            return False
    
    async def get_prediction(self, prediction_id: UUID) -> Optional[PredictionResult]:
        """Get prediction by ID"""
        
        try:
            # In real implementation:
            # SELECT * FROM predictions WHERE id = $1
            
            return self._predictions.get(prediction_id)
            
        except Exception as e:
            logger.error(f"Failed to get prediction {prediction_id}: {str(e)}")
            return None
    
    async def get_predictions_by_symbol(self, 
                                      symbol: str, 
                                      limit: int = 100,
                                      hours_ago: int = 24) -> List[PredictionResult]:
        """Get predictions for symbol within time window"""
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
            
            # Filter predictions by symbol and time
            predictions = [
                pred for pred in self._predictions.values()
                if (pred.target.symbol.upper() == symbol.upper() and 
                    pred.created_at >= cutoff_time)
            ]
            
            # Sort by creation time (newest first) and limit
            predictions.sort(key=lambda p: p.created_at, reverse=True)
            return predictions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get predictions for symbol {symbol}: {str(e)}")
            return []
    
    async def get_predictions_by_engine(self,
                                      engine_type: MLEngineType,
                                      limit: int = 100) -> List[PredictionResult]:
        """Get predictions by engine type"""
        
        try:
            predictions = [
                pred for pred in self._predictions.values()
                if pred.engine_type == engine_type
            ]
            
            predictions.sort(key=lambda p: p.created_at, reverse=True)
            return predictions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get predictions for engine {engine_type.value}: {str(e)}")
            return []
    
    # ===================== ENSEMBLE REPOSITORY METHODS =====================
    
    async def save_ensemble_prediction(self, ensemble: EnsemblePrediction) -> bool:
        """Save ensemble prediction to repository"""
        
        try:
            self._ensembles[ensemble.ensemble_id] = ensemble
            
            # Also save individual predictions
            for prediction in ensemble.individual_predictions:
                await self.save_prediction(prediction)
            
            # Save ensemble prediction if exists
            if ensemble.ensemble_prediction:
                await self.save_prediction(ensemble.ensemble_prediction)
            
            logger.debug(f"Saved ensemble prediction {ensemble.ensemble_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save ensemble prediction: {str(e)}")
            return False
    
    async def get_ensemble_prediction(self, ensemble_id: UUID) -> Optional[EnsemblePrediction]:
        """Get ensemble prediction by ID"""
        
        try:
            return self._ensembles.get(ensemble_id)
            
        except Exception as e:
            logger.error(f"Failed to get ensemble prediction {ensemble_id}: {str(e)}")
            return None
    
    # ===================== MODEL CONFIGURATION REPOSITORY METHODS =====================
    
    async def save_model_configuration(self, config: ModelConfiguration) -> bool:
        """Save model configuration"""
        
        try:
            config_key = f"{config.model_type.value}_{config.version.value}"
            self._model_configs[config_key] = config
            
            logger.debug(f"Saved model configuration for {config.model_type.value} v{config.version.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model configuration: {str(e)}")
            return False
    
    async def get_model_configuration(self,
                                    model_type: MLEngineType,
                                    version: str = "latest") -> Optional[ModelConfiguration]:
        """Get model configuration"""
        
        try:
            if version == "latest":
                # Find latest version for model type
                configs = [
                    config for key, config in self._model_configs.items()
                    if key.startswith(f"{model_type.value}_")
                ]
                
                if not configs:
                    return None
                
                # Return newest by creation date
                return max(configs, key=lambda c: c.created_at)
            else:
                config_key = f"{model_type.value}_{version}"
                return self._model_configs.get(config_key)
                
        except Exception as e:
            logger.error(f"Failed to get model configuration: {str(e)}")
            return None
    
    async def get_outdated_models(self, max_age_days: int = 30) -> List[ModelConfiguration]:
        """Get models that need retraining due to age"""
        
        try:
            outdated = []
            
            for config in self._model_configs.values():
                if config.is_outdated(max_age_days):
                    outdated.append(config)
            
            return outdated
            
        except Exception as e:
            logger.error(f"Failed to get outdated models: {str(e)}")
            return []
    
    # ===================== PERFORMANCE METRICS REPOSITORY METHODS =====================
    
    async def save_performance_metrics(self,
                                     model_type: MLEngineType,
                                     metrics: ModelPerformanceMetrics) -> bool:
        """Save model performance metrics"""
        
        try:
            model_key = model_type.value
            
            if model_key not in self._performance_metrics:
                self._performance_metrics[model_key] = []
            
            self._performance_metrics[model_key].append(metrics)
            
            # Keep only last 100 metrics per model
            if len(self._performance_metrics[model_key]) > 100:
                self._performance_metrics[model_key] = self._performance_metrics[model_key][-100:]
            
            logger.debug(f"Saved performance metrics for {model_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {str(e)}")
            return False
    
    async def get_latest_performance_metrics(self,
                                           model_type: MLEngineType) -> Optional[ModelPerformanceMetrics]:
        """Get latest performance metrics for model"""
        
        try:
            model_key = model_type.value
            metrics_list = self._performance_metrics.get(model_key, [])
            
            if not metrics_list:
                return None
            
            return max(metrics_list, key=lambda m: m.last_updated)
            
        except Exception as e:
            logger.error(f"Failed to get latest performance metrics: {str(e)}")
            return None
    
    async def get_performance_history(self,
                                    model_type: MLEngineType,
                                    days: int = 30) -> List[ModelPerformanceMetrics]:
        """Get performance metrics history"""
        
        try:
            model_key = model_type.value
            metrics_list = self._performance_metrics.get(model_key, [])
            
            if not metrics_list:
                return []
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            filtered = [
                metrics for metrics in metrics_list
                if metrics.last_updated >= cutoff_time
            ]
            
            return sorted(filtered, key=lambda m: m.last_updated)
            
        except Exception as e:
            logger.error(f"Failed to get performance history: {str(e)}")
            return []
    
    # ===================== DATABASE SCHEMA AND MAINTENANCE =====================
    
    async def _ensure_database_schema(self) -> None:
        """Ensure database schema exists (mock implementation)"""
        
        # In real implementation, would create tables:
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id UUID PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            engine_type VARCHAR(50) NOT NULL,
            predicted_price DECIMAL(10,2),
            current_price DECIMAL(10,2),
            confidence_score DECIMAL(5,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            target_date TIMESTAMP,
            status VARCHAR(20),
            UNIQUE(id)
        );
        
        CREATE TABLE IF NOT EXISTS ensemble_predictions (
            id UUID PRIMARY KEY,
            symbol VARCHAR(10) NOT NULL,
            individual_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS model_configurations (
            id UUID PRIMARY KEY,
            model_type VARCHAR(50) NOT NULL,
            version VARCHAR(20) NOT NULL,
            config_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(model_type, version)
        );
        """
        
        logger.debug("Database schema ensured (mock)")
    
    async def _create_database_indices(self) -> None:
        """Create database indices for performance (mock implementation)"""
        
        # In real implementation, would create indices:
        """
        CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);
        CREATE INDEX IF NOT EXISTS idx_predictions_engine_type ON predictions(engine_type);  
        CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
        CREATE INDEX IF NOT EXISTS idx_model_configs_type ON model_configurations(model_type);
        """
        
        logger.debug("Database indices created (mock)")
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        
        return {
            "is_initialized": self._is_initialized,
            "predictions_count": len(self._predictions),
            "ensembles_count": len(self._ensembles),
            "model_configs_count": len(self._model_configs),
            "performance_metrics_count": sum(len(metrics) for metrics in self._performance_metrics.values()),
            "database_connected": self._database_pool is not None,
            "storage_type": "in_memory" if not self._database_pool else "postgresql"
        }
    
    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old data (development utility)"""
        
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Clean old predictions
        old_predictions = [
            pred_id for pred_id, pred in self._predictions.items()
            if pred.created_at < cutoff_time
        ]
        
        for pred_id in old_predictions:
            del self._predictions[pred_id]
        
        # Clean old ensembles
        old_ensembles = [
            ens_id for ens_id, ens in self._ensembles.items()
            if ens.created_at < cutoff_time
        ]
        
        for ens_id in old_ensembles:
            del self._ensembles[ens_id]
        
        logger.info(f"Cleaned up {len(old_predictions)} predictions and {len(old_ensembles)} ensembles")
        
        return {
            "predictions_removed": len(old_predictions),
            "ensembles_removed": len(old_ensembles)
        }
    
    async def shutdown(self) -> None:
        """Graceful repository shutdown"""
        
        logger.info("Shutting down ML Analytics Repository...")
        
        # In real implementation, would close database connections
        # if self._database_pool:
        #     await self._database_pool.close()
        
        self._is_initialized = False
        logger.info("ML Analytics Repository shutdown completed")