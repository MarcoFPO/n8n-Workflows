#!/usr/bin/env python3
"""
Prediction Horizon Value Object - Clean Architecture Implementation  
Domain Value Object für ML Prediction Time Horizons

DOMAIN LAYER - VALUE OBJECTS:
- Immutable Value Object für Prediction Horizons
- Business Rules für Multi-Horizon Prediction System
- Validation Logic für Horizon-specific Behavior
- Framework-unabhängige Domain Logic

EXTRACTED FROM: ml_pipeline_service_v6_0_0_20250824.py (Lines 73-78)
REFACTORED TO: Rich Value Object mit Business Logic

Based on: ML-Analytics Success Template
Author: Claude Code - Clean Architecture Specialist  
Version: 1.0.0 - Value Object Implementation
Date: 26. August 2025
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from datetime import timedelta


class HorizonType(str, Enum):
    """Supported Prediction Horizon Types"""
    ONE_WEEK = "1W"
    ONE_MONTH = "1M" 
    THREE_MONTHS = "3M"
    TWELVE_MONTHS = "12M"


@dataclass(frozen=True)
class PredictionHorizon:
    """
    Prediction Horizon Value Object
    
    BUSINESS RULES:
    - Horizon definiert Prediction Window für ML Models
    - Jeder Horizon hat spezifische Feature Engineering Rules
    - Training Data Requirements variieren nach Horizon
    - Validation Period ist Horizon-abhängig
    
    VALUE OBJECT PROPERTIES:
    - Immutable (frozen=True)
    - Self-validating  
    - Rich business behavior
    - Equality based on value
    """
    
    horizon_type: HorizonType
    
    def __post_init__(self):
        """Validate business rules on creation"""
        if not isinstance(self.horizon_type, HorizonType):
            raise ValueError(f"Invalid horizon type: {self.horizon_type}")
    
    @property
    def value(self) -> str:
        """Get horizon string value"""
        return self.horizon_type.value
    
    @property  
    def prediction_window_days(self) -> int:
        """
        Business Rule: Prediction Window in Days
        
        BUSINESS LOGIC:
        - 1W: 7 Tage Forward Prediction
        - 1M: 30 Tage Forward Prediction  
        - 3M: 90 Tage Forward Prediction
        - 12M: 365 Tage Forward Prediction
        """
        horizon_days = {
            HorizonType.ONE_WEEK: 7,
            HorizonType.ONE_MONTH: 30,
            HorizonType.THREE_MONTHS: 90, 
            HorizonType.TWELVE_MONTHS: 365
        }
        return horizon_days[self.horizon_type]
    
    @property
    def minimum_training_samples(self) -> int:
        """
        Business Rule: Minimum Training Data Requirements
        
        BUSINESS LOGIC:
        - Längere Horizonte benötigen mehr Trainingsdaten
        - Minimum Sample Size für statistische Relevanz
        - Basierend auf Time Series Analysis Best Practices
        """
        min_samples = {
            HorizonType.ONE_WEEK: 100,      # 2-3 Monate historische Daten
            HorizonType.ONE_MONTH: 200,     # 6-8 Monate historische Daten
            HorizonType.THREE_MONTHS: 400,  # 1-2 Jahre historische Daten
            HorizonType.TWELVE_MONTHS: 800  # 2-3 Jahre historische Daten
        }
        return min_samples[self.horizon_type]
    
    @property
    def validation_period_days(self) -> int:
        """
        Business Rule: Validation Period für Model Testing
        
        BUSINESS LOGIC:  
        - Validation Period = 20% der Prediction Window
        - Minimum 7 Tage für statistische Relevanz
        - Maximum 60 Tage für praktische Anwendung
        """
        validation_days = max(7, min(60, int(self.prediction_window_days * 0.2)))
        return validation_days
    
    @property
    def feature_engineering_rules(self) -> Dict[str, Any]:
        """
        Business Rule: Horizon-spezifische Feature Engineering Rules
        
        BUSINESS LOGIC:
        - Moving Averages Window Size basierend auf Horizon
        - Technical Indicators Period angepasst an Prediction Window
        - Volatility Measures für entsprechende Zeiträume
        """
        base_window = self.prediction_window_days
        
        return {
            'moving_average_windows': [
                int(base_window * 0.1),   # Short-term MA
                int(base_window * 0.3),   # Medium-term MA
                int(base_window * 0.6)    # Long-term MA
            ],
            'rsi_period': min(14, max(7, int(base_window * 0.2))),
            'bollinger_period': min(20, max(10, int(base_window * 0.3))),
            'macd_fast': min(12, max(5, int(base_window * 0.15))),
            'macd_slow': min(26, max(12, int(base_window * 0.35))),
            'volatility_window': min(30, max(10, int(base_window * 0.4))),
            'momentum_periods': [
                int(base_window * 0.1),
                int(base_window * 0.2),
                int(base_window * 0.3)
            ]
        }
    
    @property
    def model_performance_thresholds(self) -> Dict[str, float]:
        """
        Business Rule: Performance Thresholds nach Horizon
        
        BUSINESS LOGIC:
        - Längere Horizonte haben niedrigere Genauigkeitserwartungen
        - Threshold Values basierend auf Financial Industry Standards
        - Risk-adjusted Performance Expectations
        """
        thresholds = {
            HorizonType.ONE_WEEK: {
                'min_r2_score': 0.6,      # Hohe Genauigkeit für kurze Horizonte
                'max_mae_percent': 2.0,    # Maximum 2% Fehler
                'min_confidence': 0.8      # Hohe Konfidenz erforderlich
            },
            HorizonType.ONE_MONTH: {
                'min_r2_score': 0.4,      # Moderate Genauigkeit  
                'max_mae_percent': 3.5,    # Maximum 3.5% Fehler
                'min_confidence': 0.7      # Moderate Konfidenz
            },
            HorizonType.THREE_MONTHS: {
                'min_r2_score': 0.3,      # Reduzierte Genauigkeit
                'max_mae_percent': 5.0,    # Maximum 5% Fehler
                'min_confidence': 0.6      # Niedrigere Konfidenz
            },
            HorizonType.TWELVE_MONTHS: {
                'min_r2_score': 0.2,      # Minimale Genauigkeit
                'max_mae_percent': 8.0,    # Maximum 8% Fehler  
                'min_confidence': 0.5      # Basis Konfidenz
            }
        }
        return thresholds[self.horizon_type]
    
    def get_training_data_lookback_days(self) -> int:
        """
        Business Rule: Historical Data Lookback Period
        
        BUSINESS LOGIC:
        - Lookback Period = 5x Prediction Window (minimum)
        - Maximum 2 Jahre für praktische Anwendung
        - Berücksichtigt Market Regime Changes
        """
        lookback_multiplier = 5
        max_lookback = 730  # 2 Jahre Maximum
        
        calculated_lookback = self.prediction_window_days * lookback_multiplier
        return min(calculated_lookback, max_lookback)
    
    def validate_training_data_size(self, sample_count: int) -> bool:
        """Validate if training data meets minimum requirements"""
        return sample_count >= self.minimum_training_samples
    
    def calculate_retraining_frequency_days(self) -> int:
        """
        Business Rule: Model Retraining Frequency
        
        BUSINESS LOGIC:
        - Kürzere Horizonte brauchen häufigeres Retraining
        - Market Volatility erfordert Model Updates
        - Balance zwischen Accuracy und Computational Cost
        """
        retraining_frequency = {
            HorizonType.ONE_WEEK: 7,       # Wöchentlich
            HorizonType.ONE_MONTH: 14,     # Alle 2 Wochen
            HorizonType.THREE_MONTHS: 30,  # Monatlich
            HorizonType.TWELVE_MONTHS: 90  # Quartalsweise
        }
        return retraining_frequency[self.horizon_type]
    
    def get_compatible_model_types(self) -> List[str]:
        """
        Business Rule: Compatible ML Model Types pro Horizon
        
        BUSINESS LOGIC:
        - Kurze Horizonte: High-frequency Models (Random Forest, XGBoost)
        - Lange Horizonte: Trend-following Models (Linear Regression, LSTM)  
        - Ensemble Models für alle Horizonte geeignet
        """
        compatibility = {
            HorizonType.ONE_WEEK: [
                "random_forest", "xgboost", "gradient_boosting", "ensemble"
            ],
            HorizonType.ONE_MONTH: [
                "random_forest", "xgboost", "lstm", "ensemble", "ridge_regression"
            ],
            HorizonType.THREE_MONTHS: [
                "lstm", "linear_regression", "ridge_regression", "ensemble"
            ],
            HorizonType.TWELVE_MONTHS: [
                "linear_regression", "ridge_regression", "lstm", "ensemble"
            ]
        }
        return compatibility[self.horizon_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'horizon_type': self.horizon_type.value,
            'prediction_window_days': self.prediction_window_days,
            'minimum_training_samples': self.minimum_training_samples,
            'validation_period_days': self.validation_period_days,
            'feature_engineering_rules': self.feature_engineering_rules,
            'performance_thresholds': self.model_performance_thresholds,
            'training_lookback_days': self.get_training_data_lookback_days(),
            'retraining_frequency_days': self.calculate_retraining_frequency_days(),
            'compatible_model_types': self.get_compatible_model_types()
        }
    
    @classmethod
    def from_string(cls, horizon_str: str) -> 'PredictionHorizon':
        """Factory method to create horizon from string"""
        try:
            horizon_type = HorizonType(horizon_str.upper())
            return cls(horizon_type=horizon_type)
        except ValueError:
            raise ValueError(f"Invalid horizon string: {horizon_str}. "
                           f"Valid options: {[h.value for h in HorizonType]}")
    
    @classmethod
    def get_all_horizons(cls) -> List['PredictionHorizon']:
        """Factory method to get all supported horizons"""
        return [cls(horizon_type=ht) for ht in HorizonType]
    
    def __str__(self) -> str:
        return f"PredictionHorizon({self.value})"
    
    def __repr__(self) -> str:
        return f"PredictionHorizon(horizon_type={self.horizon_type}, " \
               f"window_days={self.prediction_window_days})"