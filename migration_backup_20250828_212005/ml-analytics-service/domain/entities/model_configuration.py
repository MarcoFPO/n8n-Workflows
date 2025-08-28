#!/usr/bin/env python3
"""
Model Configuration Domain Entity

Autor: Claude Code - Domain-Driven Design Specialist
Datum: 26. August 2025
Clean Architecture v6.0.0 - Domain Layer
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class ModelVersion(Enum):
    """Model Version Schema - Domain Value Object"""
    V1_0_0 = "v1.0.0"
    V1_1_0 = "v1.1.0"
    V2_0_0 = "v2.0.0"
    LATEST = "latest"


class TrainingStatus(Enum):
    """Model Training Status - Domain Value Object"""
    NOT_TRAINED = "not_trained"
    TRAINING = "training"
    TRAINED = "trained"
    FAILED = "failed"
    OUTDATED = "outdated"


class ModelQuality(Enum):
    """Model Quality Rating - Domain Value Object"""
    POOR = "poor"          # < 60% accuracy
    FAIR = "fair"          # 60-70% accuracy
    GOOD = "good"          # 70-80% accuracy
    EXCELLENT = "excellent" # 80-90% accuracy
    OUTSTANDING = "outstanding" # > 90% accuracy


@dataclass(frozen=True)
class HyperParameters:
    """Hyperparameter Configuration Value Object"""
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    dropout_rate: float = 0.2
    hidden_layers: List[int] = field(default_factory=lambda: [64, 32])
    optimizer: str = "adam"
    loss_function: str = "mse"
    regularization_l1: float = 0.0
    regularization_l2: float = 0.0
    early_stopping_patience: int = 10
    
    def __post_init__(self):
        """Domain validation rules"""
        if self.learning_rate <= 0 or self.learning_rate > 1:
            raise ValueError("Learning rate must be between 0 and 1")
        
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        
        if self.epochs <= 0:
            raise ValueError("Epochs must be positive")
        
        if not 0 <= self.dropout_rate <= 1:
            raise ValueError("Dropout rate must be between 0 and 1")
        
        if not self.hidden_layers or any(layer <= 0 for layer in self.hidden_layers):
            raise ValueError("Hidden layers must contain positive integers")


@dataclass(frozen=True)
class FeatureConfiguration:
    """Feature Engineering Configuration Value Object"""
    feature_set: List[str]
    lookback_period: int = 30  # Days
    technical_indicators: List[str] = field(default_factory=lambda: ['sma', 'ema', 'rsi', 'macd'])
    include_sentiment: bool = False
    include_fundamental: bool = False
    include_market_data: bool = True
    scaling_method: str = "minmax"  # minmax, standard, robust
    feature_selection_threshold: float = 0.01
    
    def __post_init__(self):
        """Domain validation rules"""
        if not self.feature_set:
            raise ValueError("Feature set cannot be empty")
        
        if self.lookback_period <= 0:
            raise ValueError("Lookback period must be positive")
        
        if self.scaling_method not in ['minmax', 'standard', 'robust']:
            raise ValueError("Invalid scaling method")
        
        if not 0 <= self.feature_selection_threshold <= 1:
            raise ValueError("Feature selection threshold must be between 0 and 1")


@dataclass
class ModelPerformanceMetrics:
    """Model Performance Tracking Entity"""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    mae: Optional[float] = None  # Mean Absolute Error
    rmse: Optional[float] = None  # Root Mean Square Error
    mape: Optional[float] = None  # Mean Absolute Percentage Error
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def get_quality_rating(self) -> ModelQuality:
        """Business Rule: Calculate model quality based on accuracy"""
        if self.accuracy is None:
            return ModelQuality.POOR
        
        if self.accuracy >= 0.9:
            return ModelQuality.OUTSTANDING
        elif self.accuracy >= 0.8:
            return ModelQuality.EXCELLENT
        elif self.accuracy >= 0.7:
            return ModelQuality.GOOD
        elif self.accuracy >= 0.6:
            return ModelQuality.FAIR
        else:
            return ModelQuality.POOR
    
    def is_performing_well(self) -> bool:
        """Business Rule: Check if model meets performance standards"""
        return (
            self.accuracy is not None and self.accuracy >= 0.7 and
            self.sharpe_ratio is not None and self.sharpe_ratio >= 1.0
        )
    
    def needs_improvement(self) -> bool:
        """Business Rule: Check if model needs performance improvement"""
        return (
            self.accuracy is not None and self.accuracy < 0.6 or
            self.sharpe_ratio is not None and self.sharpe_ratio < 0.5 or
            self.win_rate is not None and self.win_rate < 0.5
        )


@dataclass
class ModelConfiguration:
    """Model Configuration Domain Entity - Rich Domain Model"""
    configuration_id: UUID = field(default_factory=uuid4)
    model_type: 'MLEngineType' = None  # Forward reference
    version: ModelVersion = ModelVersion.V1_0_0
    hyperparameters: HyperParameters = field(default_factory=HyperParameters)
    feature_config: FeatureConfiguration = None
    training_window_days: int = 252  # 1 year
    prediction_horizons: List['PredictionHorizon'] = field(default_factory=list)  # Forward reference
    performance_metrics: Optional[ModelPerformanceMetrics] = None
    training_status: TrainingStatus = TrainingStatus.NOT_TRAINED
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_trained: Optional[datetime] = None
    model_file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_outdated(self, max_age_days: int = 30) -> bool:
        """Business Rule: Check if model needs retraining due to age"""
        if self.last_trained is None:
            return True
        
        age = datetime.utcnow() - self.last_trained
        return age > timedelta(days=max_age_days)
    
    def can_make_predictions(self) -> bool:
        """Business Rule: Check if model is ready for predictions"""
        return (
            self.training_status == TrainingStatus.TRAINED and
            self.model_file_path is not None and
            not self.is_outdated()
        )
    
    def supports_horizon(self, horizon: 'PredictionHorizon') -> bool:
        """Business Rule: Check if model supports given prediction horizon"""
        return horizon in self.prediction_horizons
    
    def get_training_priority(self) -> int:
        """Business Rule: Calculate training priority (1-10, higher = more urgent)"""
        priority = 5  # Base priority
        
        # Increase priority if model is not trained
        if self.training_status == TrainingStatus.NOT_TRAINED:
            priority += 3
        
        # Increase priority if model failed
        if self.training_status == TrainingStatus.FAILED:
            priority += 4
        
        # Increase priority if model is outdated
        if self.is_outdated():
            priority += 2
        
        # Increase priority if performance is poor
        if (self.performance_metrics and 
            self.performance_metrics.needs_improvement()):
            priority += 2
        
        return min(priority, 10)  # Cap at 10
    
    def mark_training_started(self) -> None:
        """Domain Action: Mark model training as started"""
        self.training_status = TrainingStatus.TRAINING
        self.metadata['training_started_at'] = datetime.utcnow().isoformat()
    
    def mark_training_completed(self, model_file_path: str, 
                              performance_metrics: ModelPerformanceMetrics) -> None:
        """Domain Action: Mark model training as completed"""
        self.training_status = TrainingStatus.TRAINED
        self.last_trained = datetime.utcnow()
        self.model_file_path = model_file_path
        self.performance_metrics = performance_metrics
        self.metadata['training_completed_at'] = datetime.utcnow().isoformat()
    
    def mark_training_failed(self, error_message: str) -> None:
        """Domain Action: Mark model training as failed"""
        self.training_status = TrainingStatus.FAILED
        self.metadata['training_failed_at'] = datetime.utcnow().isoformat()
        self.metadata['error_message'] = error_message
    
    def update_performance_metrics(self, metrics: ModelPerformanceMetrics) -> None:
        """Domain Action: Update model performance metrics"""
        self.performance_metrics = metrics
        
        # Mark as outdated if performance degraded significantly
        if metrics.needs_improvement() and self.training_status == TrainingStatus.TRAINED:
            self.training_status = TrainingStatus.OUTDATED
    
    def create_version_snapshot(self) -> 'ModelConfiguration':
        """Domain Action: Create new version of configuration"""
        # Parse current version and increment
        version_parts = self.version.value.replace('v', '').split('.')
        major, minor, patch = map(int, version_parts)
        
        # Increment minor version
        new_version = f"v{major}.{minor + 1}.{patch}"
        
        # Create new configuration with incremented version
        new_config = ModelConfiguration(
            model_type=self.model_type,
            version=ModelVersion(new_version) if new_version in [v.value for v in ModelVersion] else ModelVersion.LATEST,
            hyperparameters=self.hyperparameters,
            feature_config=self.feature_config,
            training_window_days=self.training_window_days,
            prediction_horizons=self.prediction_horizons.copy(),
            metadata=self.metadata.copy()
        )
        
        return new_config