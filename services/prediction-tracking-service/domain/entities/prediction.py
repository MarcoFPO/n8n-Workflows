#!/usr/bin/env python3
"""
Prediction Tracking Service - Domain Entities
Clean Architecture Domain Layer

CLEAN ARCHITECTURE - DOMAIN LAYER:
- Core business entities with domain logic
- Immutable objects with validation
- Business rules and invariants

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from enum import Enum


logger = logging.getLogger(__name__)


class TimeframeType(Enum):
    """
    Prediction timeframe enumeration
    
    DOMAIN VALUE OBJECT: Standard timeframe definitions
    """
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PredictionStatus(Enum):
    """
    Prediction status enumeration
    
    DOMAIN VALUE OBJECT: Prediction lifecycle status
    """
    PENDING = "pending"
    ACTIVE = "active"
    EVALUATED = "evaluated"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Prediction:
    """
    Prediction Domain Entity
    
    DOMAIN ENTITY: Core business logic for prediction tracking
    IMMUTABLE: Frozen dataclass ensures immutability
    RICH DOMAIN MODEL: Contains business logic and invariants
    """
    
    prediction_id: Optional[str] = None
    symbol: str = ""
    timeframe: str = ""
    predicted_return: Decimal = Decimal("0.0")
    predicted_date: datetime = field(default_factory=datetime.now)
    actual_return: Optional[Decimal] = None
    evaluation_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    source: str = "prediction_tracking_service"
    
    def __post_init__(self):
        """
        Post-initialization validation
        
        Raises:
            ValueError: If validation fails
        """
        # Validate symbol
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        # Validate timeframe
        valid_timeframes = [tf.value for tf in TimeframeType]
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe: {self.timeframe}. Must be one of: {valid_timeframes}")
        
        # Validate predicted return range (realistic bounds)
        if abs(self.predicted_return) > Decimal("1000.0"):  # ±1000% seems reasonable max
            raise ValueError(f"Predicted return out of bounds: {self.predicted_return}%")
    
    def get_status(self) -> PredictionStatus:
        """
        Get current prediction status
        
        Returns:
            PredictionStatus based on current state
        """
        if self.evaluation_date is not None:
            return PredictionStatus.EVALUATED
        
        # Check if prediction is expired (past predicted date + buffer)
        days_buffer = self._get_timeframe_buffer_days()
        if datetime.now() > self.predicted_date.replace(day=self.predicted_date.day + days_buffer):
            return PredictionStatus.EXPIRED
        
        if datetime.now() >= self.predicted_date:
            return PredictionStatus.ACTIVE
        
        return PredictionStatus.PENDING
    
    def is_evaluated(self) -> bool:
        """
        Check if prediction has been evaluated
        
        Returns:
            True if prediction has actual return data
        """
        return self.actual_return is not None and self.evaluation_date is not None
    
    def is_accurate(self, tolerance_percentage: float = 5.0) -> Optional[bool]:
        """
        Check if prediction is accurate within tolerance
        
        Args:
            tolerance_percentage: Accuracy tolerance in percentage points
            
        Returns:
            True if accurate, False if not, None if not evaluated
        """
        if not self.is_evaluated():
            return None
        
        difference = abs(self.predicted_return - self.actual_return)
        return difference <= Decimal(str(tolerance_percentage))
    
    def get_accuracy_difference(self) -> Optional[Decimal]:
        """
        Get difference between predicted and actual return
        
        Returns:
            Difference (actual - predicted) or None if not evaluated
        """
        if not self.is_evaluated():
            return None
        
        return self.actual_return - self.predicted_return
    
    def get_accuracy_percentage(self) -> Optional[Decimal]:
        """
        Get accuracy as percentage (how close predicted was to actual)
        
        Returns:
            Accuracy percentage or None if not evaluated
        """
        if not self.is_evaluated() or self.actual_return == 0:
            return None
        
        # Calculate relative accuracy: 100% - |error%|
        error_percentage = abs((self.predicted_return - self.actual_return) / self.actual_return * 100)
        accuracy = max(Decimal("0"), Decimal("100") - error_percentage)
        return round(accuracy, 2)
    
    def is_positive_performance(self) -> bool:
        """
        Check if predicted return is positive
        
        Returns:
            True if predicted return is positive
        """
        return self.predicted_return > Decimal("0")
    
    def get_timeframe_type(self) -> TimeframeType:
        """
        Get timeframe as enum
        
        Returns:
            TimeframeType enum
        """
        try:
            return TimeframeType(self.timeframe)
        except ValueError:
            return TimeframeType.DAILY  # Default fallback
    
    def _get_timeframe_buffer_days(self) -> int:
        """
        Get buffer days for timeframe expiration
        
        Returns:
            Buffer days based on timeframe
        """
        timeframe_type = self.get_timeframe_type()
        buffer_map = {
            TimeframeType.DAILY: 1,
            TimeframeType.WEEKLY: 7,
            TimeframeType.MONTHLY: 30,
            TimeframeType.QUARTERLY: 90,
            TimeframeType.YEARLY: 365
        }
        return buffer_map.get(timeframe_type, 7)  # Default 7 days
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert prediction to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            'prediction_id': self.prediction_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'predicted_return': float(self.predicted_return),
            'predicted_date': self.predicted_date.isoformat(),
            'actual_return': float(self.actual_return) if self.actual_return else None,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
            'created_at': self.created_at.isoformat(),
            'source': self.source,
            'status': self.get_status().value,
            'is_evaluated': self.is_evaluated(),
            'is_positive_performance': self.is_positive_performance(),
            'accuracy_difference': float(self.get_accuracy_difference()) if self.get_accuracy_difference() else None,
            'accuracy_percentage': float(self.get_accuracy_percentage()) if self.get_accuracy_percentage() else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prediction':
        """
        Create Prediction from dictionary
        
        Args:
            data: Dictionary with prediction data
            
        Returns:
            Prediction instance
        """
        return cls(
            prediction_id=data.get('prediction_id'),
            symbol=data.get('symbol', ''),
            timeframe=data.get('timeframe', ''),
            predicted_return=Decimal(str(data.get('predicted_return', 0.0))),
            predicted_date=datetime.fromisoformat(data['predicted_date']) if data.get('predicted_date') else datetime.now(),
            actual_return=Decimal(str(data['actual_return'])) if data.get('actual_return') is not None else None,
            evaluation_date=datetime.fromisoformat(data['evaluation_date']) if data.get('evaluation_date') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            source=data.get('source', 'prediction_tracking_service')
        )
    
    def __str__(self) -> str:
        """String representation"""
        status = self.get_status().value
        return f"Prediction({self.symbol}, {self.timeframe}, {self.predicted_return}%, {status})"


@dataclass(frozen=True)
class PredictionRequest:
    """
    Prediction Request Value Object
    
    DOMAIN VALUE OBJECT: Validation for prediction creation requests
    """
    
    symbol: str
    timeframe: str
    predicted_return: Decimal
    requested_at: datetime = field(default_factory=datetime.now)
    source: str = "prediction_tracking_service"
    
    def __post_init__(self):
        """Validate request"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol is required")
        
        valid_timeframes = [tf.value for tf in TimeframeType]
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe: {self.timeframe}")
    
    def is_request_valid(self, max_age_minutes: int = 5) -> bool:
        """
        Check if request is still valid
        
        Args:
            max_age_minutes: Maximum age of request in minutes
            
        Returns:
            True if request is valid
        """
        age = datetime.now() - self.requested_at
        return age.total_seconds() <= max_age_minutes * 60
    
    def to_prediction(self) -> Prediction:
        """
        Convert request to prediction entity
        
        Returns:
            Prediction entity
        """
        return Prediction(
            symbol=self.symbol.upper().strip(),
            timeframe=self.timeframe,
            predicted_return=self.predicted_return,
            predicted_date=datetime.now(),
            source=self.source
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'predicted_return': float(self.predicted_return),
            'requested_at': self.requested_at.isoformat(),
            'source': self.source
        }


@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Performance Metrics Value Object
    
    DOMAIN VALUE OBJECT: Aggregated performance statistics
    """
    
    timeframe: str
    total_predictions: int = 0
    evaluated_predictions: int = 0
    accurate_predictions: int = 0
    accuracy_rate: Decimal = Decimal("0.0")
    average_predicted_return: Decimal = Decimal("0.0")
    average_actual_return: Decimal = Decimal("0.0")
    average_error: Decimal = Decimal("0.0")
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def get_evaluation_rate(self) -> Decimal:
        """
        Get percentage of predictions that have been evaluated
        
        Returns:
            Evaluation rate as percentage
        """
        if self.total_predictions == 0:
            return Decimal("0.0")
        
        return round(Decimal(self.evaluated_predictions) / Decimal(self.total_predictions) * 100, 2)
    
    def is_performing_well(self, threshold: float = 60.0) -> bool:
        """
        Check if performance is above threshold
        
        Args:
            threshold: Minimum accuracy rate threshold
            
        Returns:
            True if performing above threshold
        """
        return self.accuracy_rate >= Decimal(str(threshold))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timeframe': self.timeframe,
            'total_predictions': self.total_predictions,
            'evaluated_predictions': self.evaluated_predictions,
            'accurate_predictions': self.accurate_predictions,
            'accuracy_rate': float(self.accuracy_rate),
            'evaluation_rate': float(self.get_evaluation_rate()),
            'average_predicted_return': float(self.average_predicted_return),
            'average_actual_return': float(self.average_actual_return),
            'average_error': float(self.average_error),
            'is_performing_well': self.is_performing_well(),
            'calculated_at': self.calculated_at.isoformat()
        }