"""
Data Processing Service - ML Service Provider Interface
Clean Architecture v6.0.0

Interface für Machine Learning Service Integration
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from domain.entities.prediction_entities import (
    StockData, ModelPrediction, PredictionModelType
)


class IMLServiceProvider(ABC):
    """Interface für ML Model Service Provider"""

    @abstractmethod
    async def generate_prediction(
        self,
        model_type: PredictionModelType,
        symbol: str,
        historical_data: List[StockData],
        prediction_horizon_days: int = 1
    ) -> ModelPrediction:
        """Generate prediction using specified ML model"""
        pass

    @abstractmethod
    async def train_model(
        self,
        model_type: PredictionModelType,
        symbol: str,
        training_data: List[StockData],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Train ML model with provided data"""
        pass

    @abstractmethod
    async def evaluate_model_performance(
        self,
        model_type: PredictionModelType,
        symbol: str,
        test_data: List[StockData]
    ) -> Dict[str, float]:
        """Evaluate model performance on test data"""
        pass

    @abstractmethod
    async def get_model_metadata(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get model metadata and configuration"""
        pass

    @abstractmethod
    async def get_feature_importance(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, float]]:
        """Get feature importance scores for model"""
        pass

    @abstractmethod
    async def is_model_available(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> bool:
        """Check if trained model is available for symbol"""
        pass

    @abstractmethod
    async def get_supported_models(self) -> List[PredictionModelType]:
        """Get list of supported model types"""
        pass

    @abstractmethod
    async def get_model_health_status(self) -> Dict[str, Any]:
        """Get health status of ML service"""
        pass