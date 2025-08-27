#!/usr/bin/env python3
"""
Prediction Domain Service

Autor: Claude Code - Domain-Driven Design Specialist
Datum: 26. August 2025
Clean Architecture v6.0.0 - Domain Layer
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from ..entities.prediction import (
    PredictionResult, EnsemblePrediction, PredictionMetrics,
    RecommendationStrength, ConfidenceLevel, PredictionTarget
)
from ..entities.ml_engine import MLEngineType, PredictionHorizon


class PredictionDomainService:
    """Domain Service für Prediction Business Logic"""
    
    def calculate_recommendation_strength(self, predictions: Dict[str, Any]) -> str:
        """
        Berechnet Empfehlungsstärke basierend auf ML-Predictions
        
        Extrahiert aus main.py Zeile 394-398
        Erweitert mit sophistizierten Business Rules
        """
        if not predictions:
            return RecommendationStrength.NEUTRAL.value
        
        # Extract price change information
        price_change_percent = predictions.get('price_change_percent', 0.0)
        confidence_score = predictions.get('confidence_score', 0.0)
        volatility = predictions.get('volatility_estimate', 0.0)
        
        # Business Rule: Adjust recommendation based on confidence
        confidence_multiplier = self._get_confidence_multiplier(confidence_score)
        adjusted_change = price_change_percent * confidence_multiplier
        
        # Business Rule: Consider volatility in recommendation strength
        volatility_penalty = self._calculate_volatility_penalty(volatility)
        final_change = adjusted_change - volatility_penalty
        
        # Business Rules for recommendation strength
        if final_change >= 15.0:
            return RecommendationStrength.STRONG_BUY.value
        elif final_change >= 5.0:
            return RecommendationStrength.BUY.value
        elif final_change <= -15.0:
            return RecommendationStrength.STRONG_SELL.value
        elif final_change <= -5.0:
            return RecommendationStrength.SELL.value
        else:
            return RecommendationStrength.NEUTRAL.value
    
    def _get_confidence_multiplier(self, confidence_score: float) -> float:
        """Business Rule: Calculate confidence multiplier for recommendation"""
        if confidence_score >= 0.8:
            return 1.2  # Boost high confidence predictions
        elif confidence_score >= 0.6:
            return 1.0  # Normal confidence
        elif confidence_score >= 0.4:
            return 0.7  # Reduce medium confidence
        else:
            return 0.3  # Heavily reduce low confidence
    
    def _calculate_volatility_penalty(self, volatility: float) -> float:
        """Business Rule: Calculate volatility penalty for recommendation"""
        if volatility <= 0.1:  # Low volatility
            return 0.0
        elif volatility <= 0.2:  # Medium volatility
            return 1.0
        else:  # High volatility
            return 3.0
    
    def validate_prediction_request(self, target: PredictionTarget, engine_type: MLEngineType) -> List[str]:
        """
        Business Rule: Validate prediction request
        
        Returns list of validation errors (empty if valid)
        """
        errors = []
        
        # Validate symbol format
        if not self._is_valid_symbol(target.symbol):
            errors.append(f"Invalid symbol format: {target.symbol}")
        
        # Validate horizon compatibility with engine
        if not self._is_horizon_compatible(target.horizon, engine_type):
            errors.append(f"Engine {engine_type.value} does not support horizon {target.horizon.value}")
        
        # Validate target date
        if not self._is_valid_target_date(target.target_date, target.horizon):
            errors.append(f"Invalid target date for horizon {target.horizon.value}")
        
        return errors
    
    def _is_valid_symbol(self, symbol: str) -> bool:
        """Business Rule: Validate stock symbol format"""
        if not symbol or len(symbol.strip()) == 0:
            return False
        
        # Basic symbol validation (2-5 characters, alphanumeric)
        clean_symbol = symbol.strip().upper()
        return (2 <= len(clean_symbol) <= 5 and 
                clean_symbol.isalnum() and 
                clean_symbol.isascii())
    
    def _is_horizon_compatible(self, horizon: PredictionHorizon, engine_type: MLEngineType) -> bool:
        """Business Rule: Check if engine supports prediction horizon"""
        # Define engine-horizon compatibility matrix
        compatibility_matrix = {
            MLEngineType.SIMPLE_LSTM: [
                PredictionHorizon.SHORT_TERM, 
                PredictionHorizon.MEDIUM_TERM
            ],
            MLEngineType.MULTI_HORIZON_LSTM: [
                PredictionHorizon.INTRADAY,
                PredictionHorizon.SHORT_TERM,
                PredictionHorizon.MEDIUM_TERM,
                PredictionHorizon.LONG_TERM,
                PredictionHorizon.EXTENDED
            ],
            MLEngineType.SENTIMENT_XGBOOST: [
                PredictionHorizon.INTRADAY,
                PredictionHorizon.SHORT_TERM
            ],
            MLEngineType.FUNDAMENTAL_XGBOOST: [
                PredictionHorizon.MEDIUM_TERM,
                PredictionHorizon.LONG_TERM,
                PredictionHorizon.EXTENDED
            ]
        }
        
        supported_horizons = compatibility_matrix.get(engine_type, [])
        return horizon in supported_horizons
    
    def _is_valid_target_date(self, target_date: datetime, horizon: PredictionHorizon) -> bool:
        """Business Rule: Validate target date matches horizon"""
        now = datetime.utcnow()
        time_diff = target_date - now
        
        # Define expected time ranges for each horizon
        horizon_ranges = {
            PredictionHorizon.INTRADAY: (timedelta(hours=0.5), timedelta(hours=24)),
            PredictionHorizon.SHORT_TERM: (timedelta(days=1), timedelta(days=14)),
            PredictionHorizon.MEDIUM_TERM: (timedelta(days=7), timedelta(days=45)),
            PredictionHorizon.LONG_TERM: (timedelta(days=30), timedelta(days=120)),
            PredictionHorizon.EXTENDED: (timedelta(days=90), timedelta(days=400))
        }
        
        min_time, max_time = horizon_ranges.get(horizon, (timedelta(0), timedelta(days=365)))
        return min_time <= time_diff <= max_time
    
    def calculate_ensemble_weights(self, predictions: List[PredictionResult]) -> Dict[MLEngineType, float]:
        """
        Business Rule: Calculate optimal weights for ensemble prediction
        
        Weights based on historical accuracy and confidence
        """
        if not predictions:
            return {}
        
        weights = {}
        
        for prediction in predictions:
            if prediction.engine_type is None or prediction.metrics is None:
                continue
            
            # Base weight from confidence
            base_weight = prediction.metrics.confidence_score
            
            # Adjust based on historical accuracy if available
            if prediction.metrics.accuracy_score is not None:
                accuracy_multiplier = prediction.metrics.accuracy_score
                base_weight *= accuracy_multiplier
            
            # Penalize high risk predictions
            if prediction.metrics.risk_score is not None:
                risk_penalty = 1.0 - (prediction.metrics.risk_score * 0.3)
                base_weight *= max(risk_penalty, 0.1)  # Minimum 10% weight
            
            weights[prediction.engine_type] = base_weight
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        return weights
    
    def should_trigger_retraining(self, prediction_results: List[PredictionResult], 
                                 accuracy_threshold: float = 0.7) -> bool:
        """
        Business Rule: Determine if model should be retrained
        
        Based on recent prediction accuracy degradation
        """
        if len(prediction_results) < 5:  # Need minimum sample size
            return False
        
        # Calculate recent accuracy
        recent_predictions = sorted(prediction_results, key=lambda p: p.created_at, reverse=True)[:10]
        accurate_predictions = sum(
            1 for p in recent_predictions 
            if p.metrics and p.metrics.accuracy_score and p.metrics.accuracy_score >= accuracy_threshold
        )
        
        recent_accuracy = accurate_predictions / len(recent_predictions)
        
        # Trigger retraining if accuracy falls below threshold
        return recent_accuracy < accuracy_threshold
    
    def calculate_prediction_urgency(self, target: PredictionTarget) -> int:
        """
        Business Rule: Calculate prediction request urgency (1-10)
        
        Based on time to target and horizon type
        """
        now = datetime.utcnow()
        time_to_target = target.target_date - now
        
        # Base urgency by horizon
        horizon_urgency = {
            PredictionHorizon.INTRADAY: 10,    # Highest urgency
            PredictionHorizon.SHORT_TERM: 7,
            PredictionHorizon.MEDIUM_TERM: 5,
            PredictionHorizon.LONG_TERM: 3,
            PredictionHorizon.EXTENDED: 1      # Lowest urgency
        }
        
        base_urgency = horizon_urgency.get(target.horizon, 5)
        
        # Adjust based on time remaining
        hours_remaining = time_to_target.total_seconds() / 3600
        
        if hours_remaining < 1:
            urgency_multiplier = 2.0
        elif hours_remaining < 24:
            urgency_multiplier = 1.5
        elif hours_remaining < 168:  # 1 week
            urgency_multiplier = 1.2
        else:
            urgency_multiplier = 1.0
        
        final_urgency = int(base_urgency * urgency_multiplier)
        return min(max(final_urgency, 1), 10)  # Clamp to 1-10 range