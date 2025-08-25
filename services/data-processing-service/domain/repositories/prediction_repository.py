"""
Data Processing Service - Repository Interfaces
Clean Architecture v6.0.0

Repository Interfaces für Prediction Data Persistence
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from domain.entities.prediction_entities import (
    StockData, ModelPrediction, EnsemblePrediction, 
    PredictionJob, DataProcessingMetrics, 
    PredictionModelType, PredictionStatus
)


class IStockDataRepository(ABC):
    """Repository Interface für Stock Market Data"""

    @abstractmethod
    async def store_stock_data(self, stock_data_list: List[StockData]) -> bool:
        """Store multiple stock data points"""
        pass

    @abstractmethod
    async def get_stock_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[StockData]:
        """Get stock data for symbol within date range"""
        pass

    @abstractmethod
    async def get_latest_stock_data(self, symbol: str) -> Optional[StockData]:
        """Get most recent stock data for symbol"""
        pass

    @abstractmethod
    async def get_stock_data_count(self, symbol: str) -> int:
        """Get total count of stock data points for symbol"""
        pass

    @abstractmethod
    async def cleanup_old_stock_data(self, days_to_keep: int = 365) -> int:
        """Clean up old stock data, return number of deleted records"""
        pass

    @abstractmethod
    async def get_available_symbols(self) -> List[str]:
        """Get list of all available stock symbols"""
        pass

    @abstractmethod
    async def get_data_quality_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get data quality metrics for symbol"""
        pass


class IModelPredictionRepository(ABC):
    """Repository Interface für Individual Model Predictions"""

    @abstractmethod
    async def store_prediction(self, prediction: ModelPrediction) -> bool:
        """Store individual model prediction"""
        pass

    @abstractmethod
    async def get_predictions_by_symbol(
        self, 
        symbol: str, 
        model_type: Optional[PredictionModelType] = None,
        limit: int = 100
    ) -> List[ModelPrediction]:
        """Get predictions for symbol, optionally filtered by model type"""
        pass

    @abstractmethod
    async def get_prediction_by_id(self, prediction_id: str) -> Optional[ModelPrediction]:
        """Get specific prediction by ID"""
        pass

    @abstractmethod
    async def get_recent_predictions(
        self, 
        hours: int = 24,
        model_type: Optional[PredictionModelType] = None
    ) -> List[ModelPrediction]:
        """Get recent predictions within specified hours"""
        pass

    @abstractmethod
    async def get_model_performance_statistics(
        self, 
        model_type: PredictionModelType,
        symbol: Optional[str] = None
    ) -> Dict[str, float]:
        """Get performance statistics for specific model type"""
        pass

    @abstractmethod
    async def cleanup_old_predictions(self, days_to_keep: int = 90) -> int:
        """Clean up old predictions, return number of deleted records"""
        pass

    @abstractmethod
    async def get_prediction_accuracy_trend(
        self, 
        model_type: PredictionModelType,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get accuracy trend for model over time"""
        pass


class IEnsemblePredictionRepository(ABC):
    """Repository Interface für Ensemble Predictions"""

    @abstractmethod
    async def store_ensemble_prediction(self, ensemble: EnsemblePrediction) -> bool:
        """Store ensemble prediction with individual predictions"""
        pass

    @abstractmethod
    async def get_ensemble_by_id(self, ensemble_id: str) -> Optional[EnsemblePrediction]:
        """Get ensemble prediction by ID"""
        pass

    @abstractmethod
    async def get_ensemble_predictions_by_symbol(
        self, 
        symbol: str,
        limit: int = 50
    ) -> List[EnsemblePrediction]:
        """Get ensemble predictions for symbol"""
        pass

    @abstractmethod
    async def get_latest_ensemble_prediction(self, symbol: str) -> Optional[EnsemblePrediction]:
        """Get most recent ensemble prediction for symbol"""
        pass

    @abstractmethod
    async def get_ensemble_performance_comparison(
        self, 
        symbols: List[str],
        days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """Compare ensemble performance across symbols"""
        pass

    @abstractmethod
    async def get_consensus_strength_statistics(self) -> Dict[str, float]:
        """Get overall consensus strength statistics"""
        pass

    @abstractmethod
    async def cleanup_old_ensembles(self, days_to_keep: int = 180) -> int:
        """Clean up old ensemble predictions, return number of deleted records"""
        pass


class IPredictionJobRepository(ABC):
    """Repository Interface für Prediction Processing Jobs"""

    @abstractmethod
    async def create_job(self, job: PredictionJob) -> bool:
        """Create new prediction job"""
        pass

    @abstractmethod
    async def update_job(self, job: PredictionJob) -> bool:
        """Update existing prediction job"""
        pass

    @abstractmethod
    async def get_job_by_id(self, job_id: str) -> Optional[PredictionJob]:
        """Get job by ID"""
        pass

    @abstractmethod
    async def get_jobs_by_status(self, status: PredictionStatus) -> List[PredictionJob]:
        """Get all jobs with specific status"""
        pass

    @abstractmethod
    async def get_jobs_by_symbol(self, symbol: str, limit: int = 20) -> List[PredictionJob]:
        """Get jobs for specific symbol"""
        pass

    @abstractmethod
    async def get_pending_jobs(self, limit: int = 10) -> List[PredictionJob]:
        """Get pending jobs ready for processing"""
        pass

    @abstractmethod
    async def get_expired_jobs(self, expiry_hours: int = 24) -> List[PredictionJob]:
        """Get expired jobs for cleanup"""
        pass

    @abstractmethod
    async def get_job_statistics(self) -> Dict[str, Any]:
        """Get overall job processing statistics"""
        pass

    @abstractmethod
    async def cleanup_completed_jobs(self, days_to_keep: int = 30) -> int:
        """Clean up old completed jobs, return number of deleted records"""
        pass


class IDataProcessingMetricsRepository(ABC):
    """Repository Interface für Data Processing Metrics"""

    @abstractmethod
    async def store_metrics(self, metrics: DataProcessingMetrics) -> bool:
        """Store processing metrics"""
        pass

    @abstractmethod
    async def get_metrics_by_symbol(
        self, 
        symbol: str, 
        start_date: datetime,
        end_date: datetime
    ) -> List[DataProcessingMetrics]:
        """Get metrics for symbol within date range"""
        pass

    @abstractmethod
    async def get_latest_metrics(self, symbol: str) -> Optional[DataProcessingMetrics]:
        """Get most recent metrics for symbol"""
        pass

    @abstractmethod
    async def get_performance_trend(
        self, 
        symbol: str, 
        days: int = 30
    ) -> List[Dict[str, float]]:
        """Get performance trend for symbol over time"""
        pass

    @abstractmethod
    async def get_quality_score_distribution(self) -> Dict[str, int]:
        """Get distribution of quality scores across all predictions"""
        pass

    @abstractmethod
    async def get_system_performance_summary(self) -> Dict[str, float]:
        """Get overall system performance summary"""
        pass

    @abstractmethod
    async def cleanup_old_metrics(self, days_to_keep: int = 365) -> int:
        """Clean up old metrics, return number of deleted records"""
        pass

    @abstractmethod
    async def get_processing_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify processing bottlenecks and performance issues"""
        pass


class IMLModelRepository(ABC):
    """Repository Interface für ML Model Management"""

    @abstractmethod
    async def store_trained_model(
        self, 
        model_type: PredictionModelType,
        symbol: str,
        model_data: bytes,
        metadata: Dict[str, Any]
    ) -> str:
        """Store trained ML model, return model ID"""
        pass

    @abstractmethod
    async def get_trained_model(
        self, 
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get trained model data and metadata"""
        pass

    @abstractmethod
    async def get_model_metadata(
        self, 
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get model metadata without model data"""
        pass

    @abstractmethod
    async def update_model_accuracy(
        self, 
        model_type: PredictionModelType,
        symbol: str,
        accuracy: float
    ) -> bool:
        """Update model accuracy after evaluation"""
        pass

    @abstractmethod
    async def get_model_versions(
        self, 
        model_type: PredictionModelType,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """Get all versions of a model for symbol"""
        pass

    @abstractmethod
    async def cleanup_old_models(self, days_to_keep: int = 90) -> int:
        """Clean up old model versions, return number of deleted records"""
        pass

    @abstractmethod
    async def get_model_usage_statistics(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics for all model types"""
        pass