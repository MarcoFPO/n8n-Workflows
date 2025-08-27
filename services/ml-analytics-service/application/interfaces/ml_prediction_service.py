#!/usr/bin/env python3
"""
ML Prediction Service Interface

Autor: Claude Code - Clean Architecture Interface Designer
Datum: 26. August 2025
Clean Architecture v6.0.0 - Application Layer
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from ...domain.entities.prediction import PredictionResult, EnsemblePrediction, PredictionTarget
from ...domain.entities.ml_engine import MLEngineType, PredictionHorizon


class IMLPredictionService(ABC):
    """Interface für ML Prediction Services"""
    
    @abstractmethod
    async def generate_single_prediction(self, 
                                       target: PredictionTarget,
                                       engine_type: MLEngineType) -> PredictionResult:
        """Generate single prediction using specified engine"""
        pass
    
    @abstractmethod
    async def generate_ensemble_prediction(self,
                                         target: PredictionTarget,
                                         engine_types: List[MLEngineType]) -> EnsemblePrediction:
        """Generate ensemble prediction using multiple engines"""
        pass
    
    @abstractmethod
    async def batch_predict(self,
                          symbols: List[str],
                          horizon: PredictionHorizon,
                          engine_types: List[MLEngineType]) -> List[PredictionResult]:
        """Generate batch predictions for multiple symbols"""
        pass
    
    @abstractmethod
    async def get_prediction_capabilities(self,
                                        engine_type: MLEngineType) -> Dict[str, Any]:
        """Get prediction capabilities of specified engine"""
        pass


class IStreamingAnalyticsService(ABC):
    """Interface für Real-time Streaming Analytics"""
    
    @abstractmethod
    async def start_streaming(self, symbols: List[str]) -> bool:
        """Start real-time streaming analytics for symbols"""
        pass
    
    @abstractmethod
    async def stop_streaming(self) -> bool:
        """Stop streaming analytics"""
        pass
    
    @abstractmethod
    async def get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        pass
    
    @abstractmethod
    async def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected streaming clients"""
        pass
    
    @abstractmethod
    async def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent trading signals from streaming"""
        pass


class IMLModelTrainingService(ABC):
    """Interface für ML Model Training"""
    
    @abstractmethod
    async def train_model(self,
                         engine_type: MLEngineType,
                         symbol: str,
                         background: bool = True) -> str:
        """Train ML model for specific symbol and engine type"""
        pass
    
    @abstractmethod
    async def retrain_outdated_models(self) -> List[Dict[str, Any]]:
        """Retrain all outdated models"""
        pass
    
    @abstractmethod
    async def get_training_status(self) -> Dict[str, Any]:
        """Get training status for all models"""
        pass
    
    @abstractmethod
    async def schedule_retraining(self,
                                engine_type: MLEngineType,
                                symbol: str,
                                priority: int = 1) -> str:
        """Schedule model retraining"""
        pass
    
    @abstractmethod
    async def get_training_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get training history"""
        pass


class IModelVersioningService(ABC):
    """Interface für Model Versioning"""
    
    @abstractmethod
    async def get_version_history(self,
                                engine_type: MLEngineType,
                                limit: int = 20) -> List[Dict[str, Any]]:
        """Get model version history"""
        pass
    
    @abstractmethod
    async def rollback_model(self,
                           engine_type: MLEngineType,
                           version: str) -> Dict[str, Any]:
        """Rollback model to specific version"""
        pass
    
    @abstractmethod
    async def compare_model_versions(self,
                                   engine_type: MLEngineType,
                                   version1: str,
                                   version2: str) -> Dict[str, Any]:
        """Compare two model versions"""
        pass
    
    @abstractmethod
    async def get_versioning_status(self) -> Dict[str, Any]:
        """Get versioning status for all models"""
        pass