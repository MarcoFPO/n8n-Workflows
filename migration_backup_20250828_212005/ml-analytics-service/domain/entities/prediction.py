#!/usr/bin/env python3
"""
Prediction Domain Entity

Autor: Claude Code - Domain-Driven Design Specialist
Datum: 26. August 2025
Clean Architecture v6.0.0 - Domain Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4


class PredictionStatus(Enum):
    """Prediction Status - Domain Value Object"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class RecommendationStrength(Enum):
    """Investment Recommendation Strength - Domain Value Object"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class ConfidenceLevel(Enum):
    """Prediction Confidence Level - Domain Value Object"""
    VERY_LOW = "very_low"      # 0-20%
    LOW = "low"                # 21-40%
    MEDIUM = "medium"          # 41-60%
    HIGH = "high"              # 61-80%
    VERY_HIGH = "very_high"    # 81-100%


@dataclass(frozen=True)
class PredictionMetrics:
    """Prediction Quality Metrics Value Object"""
    confidence_score: float  # 0.0 - 1.0
    accuracy_score: Optional[float] = None  # Historical accuracy
    volatility_estimate: Optional[float] = None
    risk_score: Optional[float] = None  # 0.0 - 1.0
    
    def __post_init__(self):
        """Domain validation rules"""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        
        if self.accuracy_score is not None and not 0.0 <= self.accuracy_score <= 1.0:
            raise ValueError("Accuracy score must be between 0.0 and 1.0")
        
        if self.risk_score is not None and not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("Risk score must be between 0.0 and 1.0")
    
    def get_confidence_level(self) -> ConfidenceLevel:
        """Business Rule: Convert confidence score to level"""
        if self.confidence_score <= 0.2:
            return ConfidenceLevel.VERY_LOW
        elif self.confidence_score <= 0.4:
            return ConfidenceLevel.LOW
        elif self.confidence_score <= 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score <= 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH
    
    def is_reliable(self) -> bool:
        """Business Rule: Check if prediction is reliable enough for trading"""
        return self.confidence_score >= 0.6  # High or Very High confidence


@dataclass(frozen=True)
class PredictionTarget:
    """Prediction Target Value Object"""
    symbol: str
    horizon: 'PredictionHorizon'  # Forward reference
    target_date: datetime
    
    def __post_init__(self):
        """Domain validation rules"""
        if not self.symbol or len(self.symbol.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        
        if self.target_date <= datetime.utcnow():
            raise ValueError("Target date must be in the future")


@dataclass
class PredictionResult:
    """Prediction Result Domain Entity"""
    prediction_id: UUID = field(default_factory=uuid4)
    target: PredictionTarget = None
    engine_type: 'MLEngineType' = None  # Forward reference
    predicted_price: float = None
    current_price: Optional[float] = None
    price_change: Optional[float] = None  # Absolute change
    price_change_percent: Optional[float] = None  # Percentage change
    metrics: Optional[PredictionMetrics] = None
    status: PredictionStatus = PredictionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    additional_features: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_price_changes(self) -> None:
        """Domain Action: Calculate price changes from current to predicted"""
        if self.current_price is not None and self.predicted_price is not None:
            self.price_change = self.predicted_price - self.current_price
            self.price_change_percent = (self.price_change / self.current_price) * 100
    
    def get_recommendation_strength(self) -> RecommendationStrength:
        """Business Rule: Calculate investment recommendation strength"""
        if self.price_change_percent is None:
            return RecommendationStrength.NEUTRAL
        
        # Business rules for recommendation strength
        if self.price_change_percent >= 10.0:
            return RecommendationStrength.STRONG_BUY
        elif self.price_change_percent >= 3.0:
            return RecommendationStrength.BUY
        elif self.price_change_percent <= -10.0:
            return RecommendationStrength.STRONG_SELL
        elif self.price_change_percent <= -3.0:
            return RecommendationStrength.SELL
        else:
            return RecommendationStrength.NEUTRAL
    
    def is_actionable(self) -> bool:
        """Business Rule: Check if prediction is actionable for trading"""
        return (
            self.status == PredictionStatus.COMPLETED and
            self.metrics is not None and
            self.metrics.is_reliable() and
            abs(self.price_change_percent or 0) >= 2.0  # At least 2% price movement
        )
    
    def mark_as_completed(self, predicted_price: float, metrics: PredictionMetrics) -> None:
        """Domain Action: Mark prediction as completed"""
        self.predicted_price = predicted_price
        self.metrics = metrics
        self.status = PredictionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.calculate_price_changes()
    
    def mark_as_failed(self, error_message: str) -> None:
        """Domain Action: Mark prediction as failed"""
        self.status = PredictionStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
    
    def is_expired(self, expiry_hours: int = 24) -> bool:
        """Business Rule: Check if prediction is expired"""
        if self.status != PredictionStatus.COMPLETED:
            return False
        
        hours_since_completion = (datetime.utcnow() - (self.completed_at or self.created_at)).total_seconds() / 3600
        return hours_since_completion > expiry_hours


@dataclass
class EnsemblePrediction:
    """Ensemble Prediction Domain Entity"""
    ensemble_id: UUID = field(default_factory=uuid4)
    target: PredictionTarget = None
    individual_predictions: List[PredictionResult] = field(default_factory=list)
    ensemble_prediction: Optional[PredictionResult] = None
    weights: Dict['MLEngineType', float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_prediction(self, prediction: PredictionResult, weight: float = 1.0) -> None:
        """Domain Action: Add individual prediction to ensemble"""
        if prediction.status != PredictionStatus.COMPLETED:
            raise ValueError("Can only add completed predictions to ensemble")
        
        if weight < 0 or weight > 1:
            raise ValueError("Weight must be between 0 and 1")
        
        self.individual_predictions.append(prediction)
        self.weights[prediction.engine_type] = weight
    
    def calculate_ensemble_prediction(self) -> PredictionResult:
        """Business Rule: Calculate weighted ensemble prediction"""
        if not self.individual_predictions:
            raise ValueError("Cannot calculate ensemble with no predictions")
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        normalized_weights = {k: v/total_weight for k, v in self.weights.items()}
        
        # Calculate weighted average prediction
        weighted_price = sum(
            pred.predicted_price * normalized_weights[pred.engine_type]
            for pred in self.individual_predictions
        )
        
        # Calculate ensemble confidence (average weighted by individual confidence)
        weighted_confidence = sum(
            pred.metrics.confidence_score * normalized_weights[pred.engine_type]
            for pred in self.individual_predictions
            if pred.metrics is not None
        )
        
        # Create ensemble prediction result
        ensemble_metrics = PredictionMetrics(confidence_score=weighted_confidence)
        
        self.ensemble_prediction = PredictionResult(
            target=self.target,
            engine_type=None,  # Ensemble has no single engine type
            predicted_price=weighted_price,
            current_price=self.individual_predictions[0].current_price,
            metrics=ensemble_metrics,
            status=PredictionStatus.COMPLETED,
            additional_features={
                "ensemble_type": "weighted_average",
                "individual_count": len(self.individual_predictions),
                "weights": dict(normalized_weights)
            }
        )
        
        self.ensemble_prediction.calculate_price_changes()
        return self.ensemble_prediction
    
    def get_prediction_consensus(self) -> RecommendationStrength:
        """Business Rule: Get consensus recommendation from all predictions"""
        if not self.individual_predictions:
            return RecommendationStrength.NEUTRAL
        
        recommendations = [pred.get_recommendation_strength() for pred in self.individual_predictions]
        
        # Simple majority vote
        recommendation_counts = {}
        for rec in recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Return most frequent recommendation
        return max(recommendation_counts.items(), key=lambda x: x[1])[0]