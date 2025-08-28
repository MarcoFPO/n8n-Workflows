#!/usr/bin/env python3
"""
ML Analytics Domain Entities - Clean Architecture v6.0.0
Core Business Logic for Machine Learning Operations

DOMAIN LAYER - BUSINESS ENTITIES:
- MLModel: Immutable ML model entity with business rules
- MLPrediction: Stock prediction entity with validation
- MLTrainingJob: Training job lifecycle management
- MLPerformanceMetrics: Model evaluation and business rules
- MLRiskMetrics: Risk assessment business logic

SOLID PRINCIPLES IMPLEMENTED:
- Single Responsibility: Each entity has one business concern
- Open/Closed: Extensible through composition
- Liskov Substitution: All entities follow same contract
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: No infrastructure dependencies

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import json


# =============================================================================
# ENUMS AND VALUE OBJECTS
# =============================================================================

class MLModelType(Enum):
    """Enumeration of supported ML model types"""
    LSTM_BASIC = "lstm_basic"
    LSTM_MULTI_HORIZON = "lstm_multi_horizon"
    XGBOOST_SENTIMENT = "xgboost_sentiment"
    XGBOOST_FUNDAMENTAL = "xgboost_fundamental"
    LIGHTGBM_META = "lightgbm_meta"
    ENSEMBLE_MULTI_HORIZON = "ensemble_multi_horizon"
    RISK_MANAGEMENT = "risk_management"
    ESG_ANALYTICS = "esg_analytics"
    MARKET_INTELLIGENCE = "market_intelligence"
    QUANTUM_ENHANCED = "quantum_enhanced"
    PORTFOLIO_OPTIMIZER = "portfolio_optimizer"
    CORRELATION_ENGINE = "correlation_engine"
    MICROSTRUCTURE_ENGINE = "microstructure_engine"
    OPTIONS_PRICING = "options_pricing"
    DERIVATIVES_ENGINE = "derivatives_engine"
    STREAMING_ANALYTICS = "streaming_analytics"


class MLJobStatus(Enum):
    """Training job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MLPredictionHorizon(Enum):
    """Prediction horizon enumeration"""
    INTRADAY = "intraday"  # 1 hour
    SHORT_TERM = "short_term"  # 1-7 days
    MEDIUM_TERM = "medium_term"  # 1-4 weeks  
    LONG_TERM = "long_term"  # 1-12 months
    MULTI_HORIZON = "multi_horizon"  # Multiple horizons


class ModelPerformanceCategory(Enum):
    """Model performance classification"""
    EXCELLENT = "excellent"  # >90% accuracy
    GOOD = "good"  # 80-90% accuracy
    AVERAGE = "average"  # 70-80% accuracy
    POOR = "poor"  # <70% accuracy


@dataclass(frozen=True)
class ModelConfiguration:
    """Value object for ML model configuration"""
    model_type: MLModelType
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_set: List[str] = field(default_factory=list)
    training_window_days: int = 252  # 1 year default
    prediction_horizon: MLPredictionHorizon = MLPredictionHorizon.SHORT_TERM
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if self.training_window_days <= 0:
            raise ValueError("Training window must be positive")
        if not self.feature_set:
            raise ValueError("Feature set cannot be empty")


# =============================================================================
# CORE DOMAIN ENTITIES
# =============================================================================

@dataclass(frozen=True)
class MLModel:
    """
    ML Model Domain Entity
    
    Represents a trained machine learning model with business rules
    and performance tracking capabilities.
    
    Business Rules:
    - Models must have unique identifiers
    - Performance metrics must be tracked
    - Version management is mandatory
    - Models can be active or deprecated
    """
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_type: MLModelType = MLModelType.LSTM_BASIC
    version: str = "1.0.0"
    configuration: ModelConfiguration = field(default_factory=lambda: ModelConfiguration(MLModelType.LSTM_BASIC))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_trained_at: Optional[datetime] = None
    is_active: bool = True
    model_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_outdated(self, max_age_days: int = 30) -> bool:
        """
        Business rule: Check if model needs retraining
        
        Args:
            max_age_days: Maximum allowed model age
            
        Returns:
            True if model is outdated
        """
        if not self.last_trained_at:
            return True
            
        age_days = (datetime.now(timezone.utc) - self.last_trained_at).days
        return age_days > max_age_days
    
    def can_make_predictions(self) -> bool:
        """
        Business rule: Check if model is ready for predictions
        
        Returns:
            True if model can make predictions
        """
        return (
            self.is_active and
            self.last_trained_at is not None and
            not self.is_outdated()
        )
    
    def get_model_age_days(self) -> int:
        """Get model age in days"""
        if not self.last_trained_at:
            return 0
        return (datetime.now(timezone.utc) - self.last_trained_at).days
    
    def supports_horizon(self, horizon: MLPredictionHorizon) -> bool:
        """Check if model supports specific prediction horizon"""
        model_horizon = self.configuration.prediction_horizon
        
        # Multi-horizon models support all horizons
        if model_horizon == MLPredictionHorizon.MULTI_HORIZON:
            return True
            
        # Specific horizon support
        return model_horizon == horizon


@dataclass(frozen=True)
class MLPrediction:
    """
    ML Prediction Domain Entity
    
    Represents a stock price prediction with confidence metrics
    and validation rules.
    
    Business Rules:
    - Predictions must have confidence scores
    - Predicted prices must be positive
    - Predictions expire after horizon period
    - High confidence predictions are prioritized
    """
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    symbol: str = ""
    predicted_price: Decimal = Decimal('0')
    confidence_score: float = 0.0
    prediction_horizon: MLPredictionHorizon = MLPredictionHorizon.SHORT_TERM
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    features_used: List[str] = field(default_factory=list)
    prediction_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate prediction parameters"""
        if self.predicted_price <= 0:
            raise ValueError("Predicted price must be positive")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.model_id:
            raise ValueError("Model ID cannot be empty")
    
    def is_high_confidence(self) -> bool:
        """
        Business rule: Classify prediction confidence
        
        Returns:
            True if prediction has high confidence (>0.8)
        """
        return self.confidence_score > 0.8
    
    def is_expired(self) -> bool:
        """
        Business rule: Check if prediction is expired
        
        Returns:
            True if prediction is beyond its horizon
        """
        now = datetime.now(timezone.utc)
        age_hours = (now - self.created_at).total_seconds() / 3600
        
        horizon_limits = {
            MLPredictionHorizon.INTRADAY: 24,  # 1 day
            MLPredictionHorizon.SHORT_TERM: 168,  # 7 days
            MLPredictionHorizon.MEDIUM_TERM: 720,  # 30 days
            MLPredictionHorizon.LONG_TERM: 8760,  # 365 days
            MLPredictionHorizon.MULTI_HORIZON: 168  # Default to short term
        }
        
        limit_hours = horizon_limits.get(self.prediction_horizon, 168)
        return age_hours > limit_hours
    
    def get_prediction_age_hours(self) -> float:
        """Get prediction age in hours"""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600
    
    def calculate_confidence_category(self) -> str:
        """Categorize prediction confidence"""
        if self.confidence_score >= 0.9:
            return "very_high"
        elif self.confidence_score >= 0.8:
            return "high"
        elif self.confidence_score >= 0.6:
            return "medium"
        elif self.confidence_score >= 0.4:
            return "low"
        else:
            return "very_low"


@dataclass(frozen=True)
class MLTrainingJob:
    """
    ML Training Job Domain Entity
    
    Represents a model training job with lifecycle management
    and progress tracking.
    
    Business Rules:
    - Jobs must have unique identifiers
    - Progress must be between 0 and 100
    - Failed jobs can be retried
    - Completed jobs produce trained models
    """
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    model_type: MLModelType = MLModelType.LSTM_BASIC
    status: MLJobStatus = MLJobStatus.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    training_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate training job parameters"""
        if not 0 <= self.progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
        if not self.model_id:
            raise ValueError("Model ID cannot be empty")
    
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status == MLJobStatus.RUNNING
    
    def is_completed(self) -> bool:
        """Check if job is completed successfully"""
        return self.status == MLJobStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if job has failed"""
        return self.status == MLJobStatus.FAILED
    
    def can_be_retried(self) -> bool:
        """
        Business rule: Check if failed job can be retried
        
        Returns:
            True if job can be retried
        """
        return self.is_failed() and self.error_message is not None
    
    def get_duration_minutes(self) -> Optional[float]:
        """Get job duration in minutes"""
        if not self.started_at:
            return None
            
        end_time = self.completed_at or datetime.now(timezone.utc)
        duration_seconds = (end_time - self.started_at).total_seconds()
        return duration_seconds / 60
    
    def estimate_completion_time(self) -> Optional[datetime]:
        """Estimate job completion time based on progress"""
        if not self.started_at or self.progress <= 0:
            return None
            
        elapsed = datetime.now(timezone.utc) - self.started_at
        total_estimated = elapsed * (100 / self.progress)
        return self.started_at + total_estimated


@dataclass(frozen=True)
class MLPerformanceMetrics:
    """
    ML Performance Metrics Domain Entity
    
    Represents model performance evaluation with business rules
    for performance classification and comparison.
    
    Business Rules:
    - Performance metrics must be realistic (0-1 range)
    - Models with poor performance should be retrained
    - Performance trends must be tracked
    - Metrics must be comparable across models
    """
    metrics_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    mse: float = float('inf')
    mae: float = float('inf')
    r2_score: float = 0.0
    sharpe_ratio: float = 0.0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_period_days: int = 30
    sample_size: int = 0
    performance_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate performance metrics"""
        for metric in [self.accuracy, self.precision, self.recall, self.f1_score]:
            if not 0 <= metric <= 1:
                raise ValueError(f"Metric {metric} must be between 0 and 1")
        
        if self.sample_size < 0:
            raise ValueError("Sample size must be non-negative")
        if not self.model_id:
            raise ValueError("Model ID cannot be empty")
    
    def get_performance_category(self) -> ModelPerformanceCategory:
        """
        Business rule: Classify model performance
        
        Returns:
            Performance category based on accuracy
        """
        if self.accuracy >= 0.9:
            return ModelPerformanceCategory.EXCELLENT
        elif self.accuracy >= 0.8:
            return ModelPerformanceCategory.GOOD
        elif self.accuracy >= 0.7:
            return ModelPerformanceCategory.AVERAGE
        else:
            return ModelPerformanceCategory.POOR
    
    def needs_retraining(self) -> bool:
        """
        Business rule: Check if model needs retraining
        
        Returns:
            True if performance is below acceptable threshold
        """
        return (
            self.accuracy < 0.7 or
            self.f1_score < 0.6 or
            self.r2_score < 0.5
        )
    
    def is_better_than(self, other: 'MLPerformanceMetrics') -> bool:
        """
        Business rule: Compare performance with another model
        
        Args:
            other: Other performance metrics to compare
            
        Returns:
            True if this model performs better
        """
        # Weighted performance score
        our_score = (
            0.4 * self.accuracy +
            0.2 * self.f1_score +
            0.2 * self.r2_score +
            0.1 * self.precision +
            0.1 * self.recall
        )
        
        their_score = (
            0.4 * other.accuracy +
            0.2 * other.f1_score +
            0.2 * other.r2_score +
            0.1 * other.precision +
            0.1 * other.recall
        )
        
        return our_score > their_score
    
    def get_composite_score(self) -> float:
        """Calculate composite performance score (0-1)"""
        return (
            0.4 * self.accuracy +
            0.2 * self.f1_score +
            0.2 * max(0, self.r2_score) +
            0.1 * self.precision +
            0.1 * self.recall
        )


@dataclass(frozen=True)
class MLRiskMetrics:
    """
    ML Risk Metrics Domain Entity
    
    Represents risk assessment metrics with business rules
    for risk management and position sizing.
    
    Business Rules:
    - Risk metrics must be calculated for all predictions
    - High risk predictions require additional validation
    - Risk levels determine position sizing
    - Risk metrics must be updated regularly
    """
    risk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    prediction_id: str = ""
    symbol: str = ""
    var_95: Decimal = Decimal('0')  # Value at Risk 95%
    var_99: Decimal = Decimal('0')  # Value at Risk 99%
    expected_shortfall: Decimal = Decimal('0')
    volatility: float = 0.0
    beta: float = 1.0
    max_drawdown: Decimal = Decimal('0')
    risk_score: float = 0.0  # 0-10 scale
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    calculation_period_days: int = 252  # 1 year
    risk_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate risk metrics"""
        if not 0 <= self.risk_score <= 10:
            raise ValueError("Risk score must be between 0 and 10")
        if self.volatility < 0:
            raise ValueError("Volatility must be non-negative")
        if not self.prediction_id:
            raise ValueError("Prediction ID cannot be empty")
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
    
    def is_high_risk(self) -> bool:
        """
        Business rule: Check if prediction has high risk
        
        Returns:
            True if risk score indicates high risk (>7)
        """
        return self.risk_score > 7.0
    
    def get_risk_category(self) -> str:
        """Categorize risk level"""
        if self.risk_score <= 3:
            return "low"
        elif self.risk_score <= 6:
            return "medium"
        elif self.risk_score <= 8:
            return "high"
        else:
            return "very_high"
    
    def calculate_position_sizing_factor(self) -> float:
        """
        Business rule: Calculate position sizing based on risk
        
        Returns:
            Position sizing factor (0.1 to 1.0)
        """
        # Higher risk = smaller position
        if self.is_high_risk():
            return max(0.1, 1.0 - (self.risk_score / 10))
        else:
            return min(1.0, 0.5 + (0.5 * (10 - self.risk_score) / 10))
    
    def requires_additional_validation(self) -> bool:
        """
        Business rule: Check if high-risk predictions need validation
        
        Returns:
            True if additional validation is required
        """
        return (
            self.is_high_risk() or
            self.volatility > 0.5 or
            abs(self.beta) > 2.0
        )
    
    def is_within_risk_tolerance(self, max_var_pct: float = 5.0) -> bool:
        """Check if risk is within acceptable tolerance"""
        var_pct = float(self.var_95) * 100
        return var_pct <= max_var_pct