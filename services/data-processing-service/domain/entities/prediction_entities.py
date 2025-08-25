"""
Data Processing Service - Domain Entities
Clean Architecture v6.0.0

Rich Domain Entities für ML-basierte Aktienanalyse und Prediction Pipeline
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid
from decimal import Decimal


class PredictionModelType(Enum):
    """ML Model Types für Stock Prediction"""
    LINEAR_REGRESSION = "linear_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    NEURAL_NETWORK = "neural_network"


class PredictionStatus(Enum):
    """Status der Prediction Pipeline"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DataQuality(Enum):
    """Data Quality Assessment"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


class EnsembleWeightStrategy(Enum):
    """Ensemble Weight Calculation Strategies"""
    EQUAL_WEIGHT = "equal_weight"
    ACCURACY_WEIGHTED = "accuracy_weighted"
    RECENCY_WEIGHTED = "recency_weighted"
    PERFORMANCE_WEIGHTED = "performance_weighted"
    ADAPTIVE = "adaptive"


@dataclass(frozen=True)
class StockData:
    """Value Object für Stock Market Data"""
    symbol: str
    date: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.symbol is None or len(self.symbol.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        if self.open_price <= 0 or self.close_price <= 0:
            raise ValueError("Prices must be positive")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")

    def daily_return(self) -> Decimal:
        """Berechne Daily Return"""
        if self.open_price == 0:
            return Decimal('0')
        return (self.close_price - self.open_price) / self.open_price

    def price_range(self) -> Decimal:
        """Berechne Price Range (High - Low)"""
        return self.high_price - self.low_price


@dataclass(frozen=True)
class ModelPrediction:
    """Einzelne ML Model Prediction"""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: PredictionModelType = PredictionModelType.LINEAR_REGRESSION
    symbol: str = ""
    predicted_price: Decimal = Decimal('0')
    confidence_score: float = 0.0  # 0.0 - 1.0
    prediction_horizon_days: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    model_accuracy: Optional[float] = None
    feature_importance: Optional[Dict[str, float]] = None
    training_data_size: Optional[int] = None
    
    def __post_init__(self):
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        if self.prediction_horizon_days <= 0:
            raise ValueError("Prediction horizon must be positive")
        if self.predicted_price <= 0:
            raise ValueError("Predicted price must be positive")

    def is_high_confidence(self) -> bool:
        """Check if prediction has high confidence (>0.7)"""
        return self.confidence_score > 0.7

    def reliability_score(self) -> float:
        """Combined reliability score based on confidence and accuracy"""
        if self.model_accuracy is None:
            return self.confidence_score
        return (self.confidence_score + self.model_accuracy) / 2.0


@dataclass
class EnsemblePrediction:
    """Ensemble Prediction aus multiple ML Models"""
    ensemble_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    individual_predictions: List[ModelPrediction] = field(default_factory=list)
    ensemble_price: Optional[Decimal] = None
    ensemble_confidence: Optional[float] = None
    weight_strategy: EnsembleWeightStrategy = EnsembleWeightStrategy.EQUAL_WEIGHT
    model_weights: Optional[Dict[str, float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    prediction_horizon_days: int = 1
    data_quality_score: Optional[DataQuality] = None
    
    def add_prediction(self, prediction: ModelPrediction) -> None:
        """Add individual model prediction to ensemble"""
        if prediction.symbol != self.symbol:
            raise ValueError("Prediction symbol must match ensemble symbol")
        if prediction.prediction_horizon_days != self.prediction_horizon_days:
            raise ValueError("Prediction horizon must match ensemble horizon")
        
        self.individual_predictions.append(prediction)
        # Recalculate ensemble metrics
        self._recalculate_ensemble()

    def _recalculate_ensemble(self) -> None:
        """Recalculate ensemble prediction and confidence"""
        if not self.individual_predictions:
            return
            
        # Calculate weighted ensemble price
        total_weight = 0.0
        weighted_sum = Decimal('0')
        confidence_sum = 0.0
        
        for prediction in self.individual_predictions:
            weight = self._get_model_weight(prediction)
            weighted_sum += prediction.predicted_price * Decimal(str(weight))
            confidence_sum += prediction.confidence_score * weight
            total_weight += weight
        
        if total_weight > 0:
            self.ensemble_price = weighted_sum / Decimal(str(total_weight))
            self.ensemble_confidence = confidence_sum / total_weight

    def _get_model_weight(self, prediction: ModelPrediction) -> float:
        """Get weight for specific model based on strategy"""
        if self.weight_strategy == EnsembleWeightStrategy.EQUAL_WEIGHT:
            return 1.0
        elif self.weight_strategy == EnsembleWeightStrategy.ACCURACY_WEIGHTED:
            return prediction.model_accuracy or 0.5
        elif self.weight_strategy == EnsembleWeightStrategy.PERFORMANCE_WEIGHTED:
            return prediction.reliability_score()
        else:
            return 1.0

    def get_model_count(self) -> int:
        """Get number of individual models in ensemble"""
        return len(self.individual_predictions)

    def get_consensus_strength(self) -> float:
        """Calculate consensus strength among predictions"""
        if len(self.individual_predictions) < 2:
            return 1.0
            
        prices = [float(p.predicted_price) for p in self.individual_predictions]
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        # Lower variance = higher consensus
        return 1.0 / (1.0 + variance) if variance > 0 else 1.0


@dataclass
class PredictionJob:
    """Prediction Processing Job"""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    requested_models: List[PredictionModelType] = field(default_factory=list)
    prediction_horizon_days: int = 1
    status: PredictionStatus = PredictionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Processing metadata
    input_data_size: Optional[int] = None
    processing_duration_seconds: Optional[float] = None
    ensemble_prediction: Optional[EnsemblePrediction] = None
    
    def start_processing(self) -> None:
        """Mark job as started"""
        self.status = PredictionStatus.PROCESSING
        self.started_at = datetime.now()

    def complete_successfully(self, ensemble: EnsemblePrediction) -> None:
        """Mark job as completed with results"""
        self.status = PredictionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.ensemble_prediction = ensemble
        
        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.processing_duration_seconds = duration

    def mark_failed(self, error_message: str) -> None:
        """Mark job as failed with error"""
        self.status = PredictionStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message

    def is_expired(self, expiry_hours: int = 24) -> bool:
        """Check if job is expired based on creation time"""
        if self.status in [PredictionStatus.COMPLETED, PredictionStatus.FAILED]:
            return False
            
        expiry_time = self.created_at.replace(
            hour=self.created_at.hour + expiry_hours
        )
        return datetime.now() > expiry_time

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics"""
        return {
            "job_id": self.job_id,
            "symbol": self.symbol,
            "status": self.status.value,
            "requested_models": [m.value for m in self.requested_models],
            "prediction_horizon_days": self.prediction_horizon_days,
            "processing_duration_seconds": self.processing_duration_seconds,
            "input_data_size": self.input_data_size,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }


@dataclass
class DataProcessingMetrics:
    """Metrics für Data Processing Operations"""
    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Data quality metrics
    data_completeness_score: float = 0.0  # 0.0 - 1.0
    data_freshness_hours: float = 0.0
    data_volume_processed: int = 0
    missing_data_points: int = 0
    
    # Processing performance metrics
    total_processing_time_seconds: float = 0.0
    model_training_time_seconds: float = 0.0
    prediction_generation_time_seconds: float = 0.0
    ensemble_calculation_time_seconds: float = 0.0
    
    # Prediction quality metrics
    ensemble_consensus_strength: float = 0.0
    average_model_confidence: float = 0.0
    prediction_variance: float = 0.0
    
    def calculate_overall_quality_score(self) -> float:
        """Calculate overall quality score combining all metrics"""
        quality_factors = [
            self.data_completeness_score,
            min(1.0, (24.0 - self.data_freshness_hours) / 24.0),  # Fresher = better
            self.ensemble_consensus_strength,
            self.average_model_confidence
        ]
        return sum(quality_factors) / len(quality_factors)

    def is_high_quality_prediction(self) -> bool:
        """Check if this represents a high-quality prediction"""
        return (self.calculate_overall_quality_score() > 0.7 and
                self.data_completeness_score > 0.8 and
                self.average_model_confidence > 0.6)

    def get_performance_summary(self) -> Dict[str, float]:
        """Get performance metrics summary"""
        return {
            "total_processing_time": self.total_processing_time_seconds,
            "model_training_time": self.model_training_time_seconds,
            "prediction_time": self.prediction_generation_time_seconds,
            "ensemble_time": self.ensemble_calculation_time_seconds,
            "data_quality_score": self.calculate_overall_quality_score(),
            "prediction_consensus": self.ensemble_consensus_strength
        }