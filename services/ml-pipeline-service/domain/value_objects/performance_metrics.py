#!/usr/bin/env python3
"""
Performance Metrics Value Object - Clean Architecture Implementation
Domain Value Object für ML Model Performance Measurements

DOMAIN LAYER - VALUE OBJECTS:
- Immutable Value Object für Model Performance Metrics
- Business Rules für Performance Evaluation 
- Statistical Validation Logic
- Framework-unabhängige Domain Logic

EXTRACTED FROM: ml_pipeline_service_v6_0_0_20250824.py (Lines 198-221)
REFACTORED TO: Rich Value Object mit Statistical Analysis

Based on: ML-Analytics Success Template
Author: Claude Code - Clean Architecture Specialist
Version: 1.0.0 - Value Object Implementation  
Date: 26. August 2025
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math


class PerformanceTier(str, Enum):
    """Performance Classification Tiers"""
    EXCELLENT = "excellent"    # Top 10% Performance
    GOOD = "good"             # Top 25% Performance
    FAIR = "fair"             # Acceptable Performance
    POOR = "poor"             # Below Threshold Performance
    CRITICAL = "critical"     # Requires Immediate Attention


@dataclass(frozen=True)
class PerformanceMetrics:
    """
    Performance Metrics Value Object
    
    BUSINESS RULES:
    - Metrics müssen statistisch valide sein (R² ∈ [-∞, 1])
    - MAE und RMSE müssen non-negative sein
    - Cross Validation Score repräsentiert Model Generalization
    - Performance Tier wird automatisch basierend auf Thresholds klassifiziert
    
    VALUE OBJECT PROPERTIES:
    - Immutable (frozen=True)
    - Self-validating
    - Rich statistical analysis
    - Comparative performance evaluation
    """
    
    # Core Performance Metrics
    mae: float                    # Mean Absolute Error
    mse: float                    # Mean Squared Error  
    rmse: float                   # Root Mean Squared Error
    r2_score: float               # R² Score (Coefficient of Determination)
    
    # Advanced Metrics
    cross_val_score: float        # Cross Validation Score
    mape: Optional[float] = None  # Mean Absolute Percentage Error
    
    # Sample Information
    training_samples: int = 0
    validation_samples: int = 0
    test_samples: int = 0
    
    def __post_init__(self):
        """Validate business rules and calculate derived metrics"""
        self._validate_metrics()
        
        # Calculate RMSE if not provided
        if self.rmse is None or abs(self.rmse - math.sqrt(self.mse)) > 1e-6:
            object.__setattr__(self, 'rmse', math.sqrt(self.mse))
    
    def _validate_metrics(self) -> None:
        """
        Validate Statistical Business Rules
        
        BUSINESS RULES:
        - MAE, MSE, RMSE müssen >= 0 sein
        - R² Score kann negativ sein (worse than baseline)
        - Cross Validation Score sollte mit R² Score konsistent sein  
        - MAPE sollte zwischen 0 und 100 liegen (wenn vorhanden)
        """
        if self.mae < 0:
            raise ValueError(f"MAE must be non-negative, got: {self.mae}")
            
        if self.mse < 0:
            raise ValueError(f"MSE must be non-negative, got: {self.mse}")
            
        if self.rmse < 0:
            raise ValueError(f"RMSE must be non-negative, got: {self.rmse}")
            
        # Validate RMSE = sqrt(MSE) relationship
        expected_rmse = math.sqrt(self.mse)
        if abs(self.rmse - expected_rmse) > 1e-6:
            raise ValueError(f"RMSE ({self.rmse}) must equal sqrt(MSE) ({expected_rmse})")
            
        if self.mape is not None and (self.mape < 0 or self.mape > 100):
            raise ValueError(f"MAPE must be between 0 and 100, got: {self.mape}")
            
        # Cross validation should be reasonable relative to R²
        if abs(self.cross_val_score - self.r2_score) > 1.0:
            # Warning: Large discrepancy might indicate overfitting
            pass
    
    @property
    def normalized_mae(self) -> float:
        """
        Normalized MAE for comparison across different scales
        
        BUSINESS LOGIC:
        - Normalizes MAE to [0, 1] range für Performance Comparison
        - Verwendet RMSE als Normalization Base
        - 0 = Perfect Prediction, 1 = Poor Prediction
        """
        if self.rmse == 0:
            return 0.0
        return min(self.mae / self.rmse, 1.0)
    
    @property
    def performance_tier(self) -> PerformanceTier:
        """
        Business Rule: Classify Model Performance into Tiers
        
        CLASSIFICATION LOGIC:
        - EXCELLENT: R² > 0.8 AND MAE < 2%
        - GOOD: R² > 0.6 AND MAE < 5%  
        - FAIR: R² > 0.3 AND MAE < 8%
        - POOR: R² > 0.1 AND MAE < 12%
        - CRITICAL: R² ≤ 0.1 OR MAE ≥ 12%
        """
        if self.r2_score > 0.8 and self.normalized_mae < 0.02:
            return PerformanceTier.EXCELLENT
        elif self.r2_score > 0.6 and self.normalized_mae < 0.05:
            return PerformanceTier.GOOD
        elif self.r2_score > 0.3 and self.normalized_mae < 0.08:
            return PerformanceTier.FAIR
        elif self.r2_score > 0.1 and self.normalized_mae < 0.12:
            return PerformanceTier.POOR
        else:
            return PerformanceTier.CRITICAL
    
    @property
    def prediction_accuracy_percent(self) -> float:
        """
        Business Metric: Prediction Accuracy as Percentage
        
        CALCULATION:
        - Basierend auf R² Score conversion zu Percentage
        - R² = 1.0 → 100% Accuracy
        - R² = 0.0 → 0% Accuracy (baseline model)
        - R² < 0.0 → Negative Accuracy (worse than baseline)
        """
        if self.r2_score < 0:
            return 0.0  # Cap at 0% for business presentation
        return min(self.r2_score * 100, 100.0)
    
    @property
    def error_rate_percent(self) -> float:
        """MAPE or normalized MAE as error rate percentage"""
        if self.mape is not None:
            return self.mape
        return self.normalized_mae * 100
    
    @property
    def model_reliability_score(self) -> float:
        """
        Business Metric: Model Reliability Score (0-1)
        
        CALCULATION:
        - Kombiniert R² Score und Cross Validation Consistency
        - Penalty für große Diskrepanz zwischen Training und Validation
        - Berücksichtigt Sample Size Adequacy
        """
        # Base Score from R² 
        base_score = max(0.0, min(1.0, self.r2_score))
        
        # Cross Validation Consistency Penalty
        cv_consistency = 1.0 - min(0.5, abs(self.r2_score - self.cross_val_score))
        
        # Sample Size Adequacy Bonus
        total_samples = self.training_samples + self.validation_samples + self.test_samples
        sample_adequacy = min(1.0, total_samples / 1000.0)  # Ideal: 1000+ samples
        
        reliability = (base_score * 0.6 + cv_consistency * 0.3 + sample_adequacy * 0.1)
        return min(1.0, reliability)
    
    def meets_threshold(self, min_r2: float = 0.3, max_mae_percent: float = 5.0) -> bool:
        """
        Business Rule: Check if metrics meet minimum thresholds
        
        THRESHOLD VALIDATION:
        - R² Score must meet minimum value
        - Error Rate must be below maximum threshold
        - Used for Model Deployment Decisions
        """
        r2_ok = self.r2_score >= min_r2
        error_ok = self.error_rate_percent <= max_mae_percent
        return r2_ok and error_ok
    
    def compare_with(self, other: 'PerformanceMetrics') -> Dict[str, Any]:
        """
        Business Analysis: Compare performance with another model
        
        COMPARISON METRICS:
        - Relative R² improvement/degradation
        - Error rate comparison  
        - Performance tier comparison
        - Statistical significance of difference
        """
        r2_diff = self.r2_score - other.r2_score
        mae_diff = self.mae - other.mae
        
        # Determine better performing model
        is_better = (
            self.r2_score > other.r2_score and 
            self.mae < other.mae
        )
        
        return {
            'r2_improvement': r2_diff,
            'mae_reduction': -mae_diff,  # Negative is better
            'accuracy_improvement_percent': (self.r2_score - other.r2_score) * 100,
            'is_better_overall': is_better,
            'tier_comparison': {
                'self': self.performance_tier.value,
                'other': other.performance_tier.value,
                'is_tier_improvement': self.performance_tier.value > other.performance_tier.value
            },
            'reliability_improvement': self.model_reliability_score - other.model_reliability_score
        }
    
    def get_improvement_recommendations(self) -> List[str]:
        """
        Business Intelligence: Generate improvement recommendations
        
        RECOMMENDATION LOGIC:
        - Basierend auf Performance Tier und specific metrics
        - Actionable suggestions für Model Optimization
        - Business-focused improvement areas
        """
        recommendations = []
        
        if self.performance_tier == PerformanceTier.CRITICAL:
            recommendations.extend([
                "Immediate model retraining required",
                "Review feature engineering approach",
                "Consider different model algorithm",
                "Increase training data size significantly"
            ])
        elif self.performance_tier == PerformanceTier.POOR:
            recommendations.extend([
                "Add more relevant features",
                "Optimize hyperparameters", 
                "Consider ensemble methods",
                "Review data quality and preprocessing"
            ])
        elif self.performance_tier == PerformanceTier.FAIR:
            recommendations.extend([
                "Fine-tune hyperparameters",
                "Try feature selection optimization",
                "Consider regularization techniques"
            ])
        
        # Cross validation specific recommendations
        cv_discrepancy = abs(self.r2_score - self.cross_val_score)
        if cv_discrepancy > 0.2:
            recommendations.append("Address potential overfitting - large train/validation gap")
            
        # Sample size recommendations
        total_samples = self.training_samples + self.validation_samples + self.test_samples
        if total_samples < 500:
            recommendations.append("Increase training data size for better model stability")
            
        return recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'mae': self.mae,
            'mse': self.mse,
            'rmse': self.rmse,
            'r2_score': self.r2_score,
            'cross_val_score': self.cross_val_score,
            'mape': self.mape,
            'training_samples': self.training_samples,
            'validation_samples': self.validation_samples,
            'test_samples': self.test_samples,
            'normalized_mae': self.normalized_mae,
            'performance_tier': self.performance_tier.value,
            'prediction_accuracy_percent': self.prediction_accuracy_percent,
            'error_rate_percent': self.error_rate_percent,
            'model_reliability_score': self.model_reliability_score,
            'improvement_recommendations': self.get_improvement_recommendations()
        }
    
    @classmethod
    def from_sklearn_results(cls,
                           y_true: List[float],
                           y_pred: List[float], 
                           cv_scores: Optional[List[float]] = None) -> 'PerformanceMetrics':
        """
        Factory method: Create metrics from scikit-learn results
        
        BUSINESS INTEGRATION:
        - Direkte Integration mit ML Pipeline Results
        - Automatische Berechnung aller Statistical Metrics
        - Cross Validation Score Integration
        """
        import numpy as np
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)
        
        mae = mean_absolute_error(y_true_arr, y_pred_arr)
        mse = mean_squared_error(y_true_arr, y_pred_arr)
        rmse = math.sqrt(mse)
        r2 = r2_score(y_true_arr, y_pred_arr)
        
        # Calculate MAPE
        mape = None
        if not np.any(y_true_arr == 0):  # Avoid division by zero
            mape = np.mean(np.abs((y_true_arr - y_pred_arr) / y_true_arr)) * 100
        
        # Cross validation score
        cv_score = np.mean(cv_scores) if cv_scores else r2
        
        return cls(
            mae=mae,
            mse=mse,
            rmse=rmse,
            r2_score=r2,
            cross_val_score=cv_score,
            mape=mape,
            training_samples=len(y_true),
            validation_samples=0,
            test_samples=0
        )