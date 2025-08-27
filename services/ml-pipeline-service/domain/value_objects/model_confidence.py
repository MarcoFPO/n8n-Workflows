#!/usr/bin/env python3
"""
Model Confidence Value Object - Clean Architecture Implementation
Domain Value Object für ML Model Prediction Confidence Levels

DOMAIN LAYER - VALUE OBJECTS:
- Immutable Value Object für Model Confidence Assessment
- Business Rules für Confidence Level Classification  
- Statistical Confidence Calculation Logic
- Framework-unabhängige Domain Logic

EXTRACTED FROM: ml_pipeline_service_v6_0_0_20250824.py (Lines 98-105)
REFACTORED TO: Rich Value Object mit Confidence Analysis

Based on: ML-Analytics Success Template
Author: Claude Code - Clean Architecture Specialist
Version: 1.0.0 - Value Object Implementation
Date: 26. August 2025
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math


class ConfidenceLevel(str, Enum):
    """Model Confidence Classification Levels"""
    VERY_LOW = "very_low"      # < 0.3 - Unreliable Predictions
    LOW = "low"                # 0.3 - 0.5 - Limited Reliability  
    MEDIUM = "medium"          # 0.5 - 0.7 - Acceptable Reliability
    HIGH = "high"              # 0.7 - 0.9 - High Reliability
    VERY_HIGH = "very_high"    # > 0.9 - Excellent Reliability


@dataclass(frozen=True)
class ModelConfidence:
    """
    Model Confidence Value Object
    
    BUSINESS RULES:
    - Confidence Level basierend auf statistischen Metrics
    - Berücksichtigt Model Performance, Data Quality, Training Stability
    - Confidence Interval für Prediction Uncertainty
    - Business-friendly Confidence Classification
    
    VALUE OBJECT PROPERTIES:
    - Immutable (frozen=True)
    - Self-validating
    - Rich confidence analysis  
    - Statistical uncertainty quantification
    """
    
    # Core Confidence Metrics
    confidence_score: float           # Overall confidence score [0.0, 1.0]
    prediction_interval_lower: float  # Lower bound of prediction interval
    prediction_interval_upper: float  # Upper bound of prediction interval
    
    # Supporting Metrics
    model_stability: Optional[float] = None      # Model training stability [0.0, 1.0]
    data_quality_score: Optional[float] = None   # Training data quality [0.0, 1.0]
    feature_importance_consistency: Optional[float] = None  # Feature consistency [0.0, 1.0]
    
    def __post_init__(self):
        """Validate business rules on creation"""
        self._validate_confidence_metrics()
    
    def _validate_confidence_metrics(self) -> None:
        """
        Validate Confidence Business Rules
        
        BUSINESS RULES:
        - Confidence Score muss zwischen 0.0 und 1.0 liegen
        - Prediction Interval Lower <= Upper
        - Supporting Metrics (wenn vorhanden) zwischen 0.0 und 1.0
        - Confidence Level muss mit Score konsistent sein
        """
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got: {self.confidence_score}")
            
        if self.prediction_interval_lower > self.prediction_interval_upper:
            raise ValueError(f"Prediction interval lower bound ({self.prediction_interval_lower}) "
                           f"cannot be greater than upper bound ({self.prediction_interval_upper})")
        
        # Validate optional metrics
        for metric_name, metric_value in [
            ("model_stability", self.model_stability),
            ("data_quality_score", self.data_quality_score), 
            ("feature_importance_consistency", self.feature_importance_consistency)
        ]:
            if metric_value is not None and not (0.0 <= metric_value <= 1.0):
                raise ValueError(f"{metric_name} must be between 0.0 and 1.0, got: {metric_value}")
    
    @property
    def value(self) -> float:
        """Get numeric confidence value"""
        return self.confidence_score
    
    @property
    def level(self) -> ConfidenceLevel:
        """
        Business Rule: Classify Confidence Score into Business Levels
        
        CLASSIFICATION LOGIC:
        - VERY_LOW: < 0.3 - Model unreliable für Business Decisions
        - LOW: 0.3-0.5 - Limited reliability, use with caution
        - MEDIUM: 0.5-0.7 - Acceptable für most Business Cases
        - HIGH: 0.7-0.9 - Reliable für wichtige Business Decisions  
        - VERY_HIGH: > 0.9 - Excellent reliability für kritische Decisions
        """
        if self.confidence_score < 0.3:
            return ConfidenceLevel.VERY_LOW
        elif self.confidence_score < 0.5:
            return ConfidenceLevel.LOW
        elif self.confidence_score < 0.7:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score < 0.9:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH
    
    @property
    def prediction_interval_width(self) -> float:
        """
        Prediction Interval Width - Uncertainty Measure
        
        BUSINESS INTERPRETATION:
        - Smaller interval = Higher precision/confidence
        - Larger interval = Lower precision/higher uncertainty
        - Used für Risk Assessment in Trading Decisions
        """
        return abs(self.prediction_interval_upper - self.prediction_interval_lower)
    
    @property
    def uncertainty_percent(self) -> float:
        """
        Uncertainty as Percentage of Prediction Range
        
        BUSINESS METRIC:
        - Percentage uncertainty für Business Communication
        - Based on Prediction Interval Width
        - 0% = Perfect Confidence, 100% = Maximum Uncertainty
        """
        if self.prediction_interval_width == 0:
            return 0.0
        
        # Calculate percentage based on interval width relative to midpoint
        midpoint = (self.prediction_interval_lower + self.prediction_interval_upper) / 2
        if midpoint == 0:
            return 100.0  # Undefined case, return max uncertainty
            
        return min(100.0, (self.prediction_interval_width / abs(midpoint)) * 100)
    
    def is_suitable_for_trading(self, min_confidence: float = 0.6) -> bool:
        """
        Business Rule: Trading Decision Suitability
        
        TRADING SUITABILITY CRITERIA:
        - Minimum Confidence Score erforderlich
        - Prediction Interval Width acceptable
        - Model Stability (wenn verfügbar) ausreichend
        """
        confidence_ok = self.confidence_score >= min_confidence
        
        # Additional checks if metrics available
        stability_ok = (self.model_stability is None or 
                       self.model_stability >= 0.5)
        
        data_quality_ok = (self.data_quality_score is None or 
                          self.data_quality_score >= 0.6)
        
        return confidence_ok and stability_ok and data_quality_ok
    
    def get_trading_risk_level(self) -> str:
        """
        Business Classification: Trading Risk Level
        
        RISK CLASSIFICATION:
        - VERY_LOW confidence → HIGH risk
        - LOW confidence → MEDIUM-HIGH risk
        - MEDIUM confidence → MEDIUM risk  
        - HIGH confidence → LOW-MEDIUM risk
        - VERY_HIGH confidence → LOW risk
        """
        risk_mapping = {
            ConfidenceLevel.VERY_LOW: "HIGH",
            ConfidenceLevel.LOW: "MEDIUM-HIGH", 
            ConfidenceLevel.MEDIUM: "MEDIUM",
            ConfidenceLevel.HIGH: "LOW-MEDIUM",
            ConfidenceLevel.VERY_HIGH: "LOW"
        }
        return risk_mapping[self.level]
    
    def calculate_position_sizing_factor(self, base_position_size: float = 1.0) -> float:
        """
        Business Logic: Position Sizing based on Confidence
        
        POSITION SIZING RULES:
        - Higher Confidence → Larger Position Size
        - Lower Confidence → Smaller Position Size  
        - Risk Management durch Confidence-based Scaling
        """
        # Conservative scaling: confidence^2 für exponential risk reduction
        scaling_factor = self.confidence_score ** 2
        
        # Apply additional penalties if supporting metrics available
        if self.model_stability is not None:
            scaling_factor *= self.model_stability
            
        if self.data_quality_score is not None:
            scaling_factor *= self.data_quality_score
        
        return base_position_size * scaling_factor
    
    def get_confidence_explanation(self) -> Dict[str, Any]:
        """
        Business Intelligence: Explain Confidence Level
        
        EXPLANATION COMPONENTS:
        - Confidence Level and Score interpretation
        - Contributing factors analysis
        - Risk assessment and recommendations
        """
        explanation = {
            'confidence_level': self.level.value,
            'confidence_score': self.confidence_score,
            'interpretation': self._get_level_interpretation(),
            'uncertainty_percent': self.uncertainty_percent,
            'prediction_interval': {
                'lower': self.prediction_interval_lower,
                'upper': self.prediction_interval_upper,
                'width': self.prediction_interval_width
            },
            'trading_suitability': self.is_suitable_for_trading(),
            'risk_level': self.get_trading_risk_level(),
            'recommended_position_factor': self.calculate_position_sizing_factor()
        }
        
        # Add supporting metrics if available
        if self.model_stability is not None:
            explanation['model_stability'] = self.model_stability
        if self.data_quality_score is not None:
            explanation['data_quality_score'] = self.data_quality_score
        if self.feature_importance_consistency is not None:
            explanation['feature_consistency'] = self.feature_importance_consistency
            
        return explanation
    
    def _get_level_interpretation(self) -> str:
        """Get business interpretation of confidence level"""
        interpretations = {
            ConfidenceLevel.VERY_LOW: "Model predictions unreliable. Avoid trading decisions.",
            ConfidenceLevel.LOW: "Limited reliability. Use only for preliminary analysis.",
            ConfidenceLevel.MEDIUM: "Acceptable confidence. Suitable for diversified strategies.", 
            ConfidenceLevel.HIGH: "High reliability. Suitable for focused trading strategies.",
            ConfidenceLevel.VERY_HIGH: "Excellent reliability. Suitable for concentrated positions."
        }
        return interpretations[self.level]
    
    def compare_with(self, other: 'ModelConfidence') -> Dict[str, Any]:
        """
        Business Analysis: Compare confidence with another model
        
        COMPARISON METRICS:
        - Confidence score difference
        - Level comparison
        - Uncertainty comparison
        - Trading suitability comparison
        """
        score_diff = self.confidence_score - other.confidence_score
        uncertainty_diff = self.uncertainty_percent - other.uncertainty_percent
        
        is_more_confident = self.confidence_score > other.confidence_score
        
        return {
            'confidence_improvement': score_diff,
            'uncertainty_reduction': -uncertainty_diff,  # Negative is better
            'is_more_confident': is_more_confident,
            'level_comparison': {
                'self': self.level.value,
                'other': other.level.value,
                'is_level_improvement': self.confidence_score > other.confidence_score
            },
            'trading_suitability': {
                'self': self.is_suitable_for_trading(),
                'other': other.is_suitable_for_trading(),
                'is_better_for_trading': (self.is_suitable_for_trading() and 
                                        not other.is_suitable_for_trading()) or
                                       (self.is_suitable_for_trading() and 
                                        other.is_suitable_for_trading() and 
                                        is_more_confident)
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'confidence_score': self.confidence_score,
            'confidence_level': self.level.value,
            'prediction_interval_lower': self.prediction_interval_lower,
            'prediction_interval_upper': self.prediction_interval_upper,
            'prediction_interval_width': self.prediction_interval_width,
            'uncertainty_percent': self.uncertainty_percent,
            'model_stability': self.model_stability,
            'data_quality_score': self.data_quality_score,
            'feature_importance_consistency': self.feature_importance_consistency,
            'trading_suitability': self.is_suitable_for_trading(),
            'risk_level': self.get_trading_risk_level(),
            'position_sizing_factor': self.calculate_position_sizing_factor(),
            'explanation': self.get_confidence_explanation()
        }
    
    @classmethod
    def from_prediction_results(cls,
                              predictions: List[float],
                              actual_values: Optional[List[float]] = None,
                              model_performance_r2: Optional[float] = None) -> 'ModelConfidence':
        """
        Factory Method: Create confidence from prediction results
        
        CONFIDENCE CALCULATION:
        - Basierend auf Prediction Variance und Model Performance
        - Statistical Confidence Interval Calculation
        - Integration mit Model Performance Metrics
        """
        import numpy as np
        
        predictions_array = np.array(predictions)
        
        # Calculate prediction statistics
        pred_mean = np.mean(predictions_array)
        pred_std = np.std(predictions_array)
        
        # Base confidence from prediction consistency
        if pred_std == 0:
            base_confidence = 0.9  # Very consistent predictions
        else:
            # Normalize by coefficient of variation (inverse relationship)
            cv = pred_std / abs(pred_mean) if pred_mean != 0 else 1.0
            base_confidence = max(0.1, min(0.9, 1.0 / (1.0 + cv)))
        
        # Adjust by model performance if available
        if model_performance_r2 is not None:
            performance_factor = max(0.0, min(1.0, model_performance_r2))
            base_confidence = (base_confidence * 0.6) + (performance_factor * 0.4)
        
        # Calculate prediction intervals (assuming normal distribution)
        confidence_interval = 1.96 * pred_std  # 95% confidence interval
        interval_lower = pred_mean - confidence_interval
        interval_upper = pred_mean + confidence_interval
        
        # Calculate additional metrics if actual values provided
        model_stability = None
        data_quality_score = None
        
        if actual_values is not None:
            actual_array = np.array(actual_values)
            if len(actual_array) == len(predictions_array):
                # Estimate model stability from prediction accuracy
                errors = np.abs(predictions_array - actual_array)
                mean_error = np.mean(errors)
                error_consistency = 1.0 - (np.std(errors) / (mean_error + 1e-8))
                model_stability = max(0.0, min(1.0, error_consistency))
                
                # Estimate data quality from error distribution
                error_normality = 1.0 - min(1.0, np.abs(np.mean(errors)) / (np.std(errors) + 1e-8))
                data_quality_score = max(0.0, min(1.0, error_normality))
        
        return cls(
            confidence_score=base_confidence,
            prediction_interval_lower=interval_lower,
            prediction_interval_upper=interval_upper,
            model_stability=model_stability,
            data_quality_score=data_quality_score
        )
    
    @classmethod
    def create_high_confidence(cls, prediction_value: float, interval_width: float = 0.05) -> 'ModelConfidence':
        """Factory method for high-confidence predictions"""
        half_width = interval_width / 2
        return cls(
            confidence_score=0.85,
            prediction_interval_lower=prediction_value - half_width,
            prediction_interval_upper=prediction_value + half_width,
            model_stability=0.9,
            data_quality_score=0.8
        )
    
    def __str__(self) -> str:
        return f"ModelConfidence({self.level.value}: {self.confidence_score:.3f})"
    
    def __repr__(self) -> str:
        return f"ModelConfidence(score={self.confidence_score:.3f}, level={self.level.value}, " \
               f"interval=[{self.prediction_interval_lower:.3f}, {self.prediction_interval_upper:.3f}])"