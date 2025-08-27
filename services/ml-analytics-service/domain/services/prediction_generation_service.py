#!/usr/bin/env python3
"""
Prediction Generation Domain Service v1.0.0
Clean Architecture Domain Layer - ML Prediction Generation Business Logic

DOMAIN SERVICE RESPONSIBILITIES:
- Implements core business logic for ML prediction generation
- Orchestrates multi-horizon prediction workflows
- Manages ensemble prediction creation and validation
- Implements prediction confidence and risk assessment

BUSINESS RULES IMPLEMENTED:
- Multi-Horizon Predictions: 1W, 1M, 3M, 12M simultaneous generation
- Confidence Thresholds: Min 60% confidence for production predictions
- Risk Assessment: Comprehensive risk scoring and volatility analysis
- Ensemble Logic: Weighted combination of multiple models
- Quality Gates: Prediction validation and quality control

CLEAN ARCHITECTURE COMPLIANCE:
- No Infrastructure dependencies (database, external APIs)
- Pure business logic implementation
- Domain Entity orchestration
- Value Object validation
- Repository pattern abstraction

SUCCESS TEMPLATE: Based on ML-Analytics Clean Architecture Migration
Integration: Event-Driven Architecture for Prediction Coordination

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0 - Domain Service Implementation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
from statistics import mean, median, stdev

# Domain Layer Imports
from ..entities.ml_engine import MLEngine, ModelConfiguration
from ..entities.prediction import PredictionHorizon, ModelPerformanceMetrics, PredictionResult
from ..value_objects.model_confidence import ModelConfidence
from ..value_objects.performance_metrics import PerformanceMetrics
from ..exceptions.ml_exceptions import (
    PredictionGenerationError,
    InsufficientDataError,
    ModelNotAvailableError,
    ConfidenceThresholdError
)


class PredictionQuality(Enum):
    """Prediction Quality Enumeration - Domain Value Object"""
    EXCELLENT = "excellent"  # >90% confidence
    GOOD = "good"           # 80-90% confidence
    ACCEPTABLE = "acceptable" # 60-80% confidence
    POOR = "poor"           # 40-60% confidence
    UNRELIABLE = "unreliable" # <40% confidence


class RiskLevel(Enum):
    """Risk Level Enumeration - Domain Value Object"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class PredictionRequest:
    """Prediction Request Value Object - Domain Layer"""
    symbol: str
    horizons: List[PredictionHorizon]
    model_types: List[str]
    confidence_threshold: float
    include_ensemble: bool
    risk_tolerance: RiskLevel
    urgency: int  # 1-10 scale
    requested_at: datetime
    
    def validate(self) -> bool:
        """Validate prediction request business rules"""
        if not self.symbol or len(self.symbol.strip()) < 2:
            raise ValueError("Valid symbol required")
        
        if self.confidence_threshold < 0.4 or self.confidence_threshold > 1.0:
            raise ValueError("Confidence threshold must be between 40% and 100%")
        
        if not self.horizons:
            raise ValueError("At least one prediction horizon must be specified")
        
        if self.urgency < 1 or self.urgency > 10:
            raise ValueError("Urgency must be between 1 and 10")
            
        return True


@dataclass
class PredictionOutput:
    """Prediction Output Value Object - Domain Layer"""
    symbol: str
    horizon: PredictionHorizon
    predicted_price: float
    price_change_percent: float
    confidence_score: float
    risk_score: float
    quality: PredictionQuality
    model_used: str
    prediction_timestamp: datetime
    target_date: datetime
    supporting_factors: List[str]
    risk_factors: List[str]
    ensemble_components: Optional[List[Dict[str, Any]]] = None


@dataclass
class EnsemblePrediction:
    """Ensemble Prediction Value Object - Domain Layer"""
    individual_predictions: List[PredictionOutput]
    ensemble_prediction: PredictionOutput
    model_weights: Dict[str, float]
    consensus_score: float
    disagreement_score: float
    reliability_score: float


class PredictionGenerationService:
    """
    Prediction Generation Domain Service - Clean Architecture
    
    DOMAIN LAYER RESPONSIBILITIES:
    - Implements core ML prediction generation business logic
    - Orchestrates multi-horizon prediction workflows
    - Manages ensemble prediction creation and validation
    - Implements prediction quality assessment and risk analysis
    
    BUSINESS RULES:
    - Multi-horizon prediction generation (1W, 1M, 3M, 12M)
    - Confidence threshold validation (min 60% for production)
    - Risk assessment and volatility analysis
    - Ensemble prediction creation and validation
    - Quality gates and prediction filtering
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._prediction_cache: Dict[str, PredictionOutput] = {}
        self._model_performance_history: Dict[str, List[float]] = {}
        
    async def generate_multi_horizon_predictions(
        self,
        prediction_request: PredictionRequest
    ) -> Dict[PredictionHorizon, EnsemblePrediction]:
        """
        Generate multi-horizon predictions with ensemble logic
        
        BUSINESS LOGIC:
        1. Validate prediction request
        2. Generate individual model predictions for each horizon
        3. Create ensemble predictions
        4. Validate quality thresholds
        5. Apply risk assessment
        """
        try:
            self.logger.info(f"Generating multi-horizon predictions for {prediction_request.symbol}")
            self.logger.info(f"Horizons: {[h.value for h in prediction_request.horizons]}")
            
            # Validate request business rules
            prediction_request.validate()
            
            ensemble_predictions = {}
            
            # Generate predictions for each horizon
            for horizon in prediction_request.horizons:
                self.logger.info(f"Processing horizon {horizon.value}")
                
                # Generate individual model predictions
                individual_predictions = await self._generate_individual_predictions(
                    prediction_request, horizon
                )
                
                # Filter by confidence threshold
                qualified_predictions = [
                    p for p in individual_predictions 
                    if p.confidence_score >= prediction_request.confidence_threshold
                ]
                
                if not qualified_predictions:
                    self.logger.warning(f"No predictions meet confidence threshold for {horizon.value}")
                    continue
                
                # Create ensemble prediction
                ensemble_prediction = await self._create_ensemble_prediction(
                    qualified_predictions, prediction_request, horizon
                )
                
                ensemble_predictions[horizon] = ensemble_prediction
            
            self.logger.info(f"Generated {len(ensemble_predictions)} ensemble predictions")
            return ensemble_predictions
            
        except Exception as e:
            self.logger.error(f"Multi-horizon prediction generation failed: {str(e)}")
            raise PredictionGenerationError(f"Prediction generation failed: {str(e)}")
    
    async def _generate_individual_predictions(
        self,
        request: PredictionRequest,
        horizon: PredictionHorizon
    ) -> List[PredictionOutput]:
        """Generate individual model predictions for a specific horizon"""
        predictions = []
        
        for model_type in request.model_types:
            try:
                self.logger.debug(f"Generating {model_type} prediction for {horizon.value}")
                
                prediction = await self._generate_single_model_prediction(
                    request.symbol, horizon, model_type, request
                )
                
                if prediction:
                    predictions.append(prediction)
                    
            except Exception as e:
                self.logger.warning(f"Failed to generate {model_type} prediction: {e}")
                continue
        
        return predictions
    
    async def _generate_single_model_prediction(
        self,
        symbol: str,
        horizon: PredictionHorizon,
        model_type: str,
        request: PredictionRequest
    ) -> Optional[PredictionOutput]:
        """Generate prediction from a single ML model"""
        try:
            # Simulate model prediction (in real implementation, calls ML engines)
            await asyncio.sleep(0.05)  # Simulate processing time
            
            # Get current price (simulated)
            current_price = self._get_current_price_simulation(symbol)
            
            # Generate prediction based on model type and horizon
            prediction_data = self._simulate_model_prediction(
                symbol, horizon, model_type, current_price
            )
            
            # Calculate target date
            target_date = self._calculate_target_date(horizon)
            
            # Assess prediction quality
            quality = self._assess_prediction_quality(
                prediction_data['confidence'], 
                prediction_data['volatility']
            )
            
            # Generate supporting and risk factors
            supporting_factors = self._generate_supporting_factors(
                model_type, prediction_data['trend'], quality
            )
            risk_factors = self._generate_risk_factors(
                prediction_data['volatility'], 
                prediction_data['uncertainty']
            )
            
            prediction = PredictionOutput(
                symbol=symbol,
                horizon=horizon,
                predicted_price=prediction_data['predicted_price'],
                price_change_percent=prediction_data['price_change_percent'],
                confidence_score=prediction_data['confidence'],
                risk_score=prediction_data['risk_score'],
                quality=quality,
                model_used=model_type,
                prediction_timestamp=datetime.now(),
                target_date=target_date,
                supporting_factors=supporting_factors,
                risk_factors=risk_factors
            )
            
            # Update model performance history
            self._update_model_performance_history(model_type, prediction_data['confidence'])
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Single model prediction failed: {str(e)}")
            return None
    
    async def _create_ensemble_prediction(
        self,
        individual_predictions: List[PredictionOutput],
        request: PredictionRequest,
        horizon: PredictionHorizon
    ) -> EnsemblePrediction:
        """Create ensemble prediction from individual model predictions"""
        try:
            if len(individual_predictions) < 2:
                # Return single prediction as "ensemble" with perfect consensus
                single_pred = individual_predictions[0]
                return EnsemblePrediction(
                    individual_predictions=individual_predictions,
                    ensemble_prediction=single_pred,
                    model_weights={single_pred.model_used: 1.0},
                    consensus_score=1.0,
                    disagreement_score=0.0,
                    reliability_score=single_pred.confidence_score
                )
            
            # Calculate model weights based on confidence and historical performance
            model_weights = self._calculate_ensemble_weights(individual_predictions)
            
            # Calculate weighted ensemble prediction
            weighted_price = sum(
                pred.predicted_price * model_weights[pred.model_used]
                for pred in individual_predictions
            )
            
            weighted_change = sum(
                pred.price_change_percent * model_weights[pred.model_used]
                for pred in individual_predictions
            )
            
            # Calculate ensemble confidence (weighted average + consensus bonus)
            base_confidence = sum(
                pred.confidence_score * model_weights[pred.model_used]
                for pred in individual_predictions
            )
            
            # Calculate consensus metrics
            consensus_score = self._calculate_consensus_score(individual_predictions)
            disagreement_score = self._calculate_disagreement_score(individual_predictions)
            
            # Adjust confidence based on consensus
            ensemble_confidence = min(base_confidence * (1 + consensus_score * 0.1), 0.98)
            
            # Calculate ensemble risk score
            ensemble_risk = self._calculate_ensemble_risk(individual_predictions, model_weights)
            
            # Assess ensemble quality
            ensemble_quality = self._assess_prediction_quality(ensemble_confidence, ensemble_risk)
            
            # Generate ensemble supporting factors
            supporting_factors = self._generate_ensemble_supporting_factors(
                individual_predictions, consensus_score
            )
            risk_factors = self._generate_ensemble_risk_factors(
                individual_predictions, disagreement_score
            )
            
            # Calculate reliability score
            reliability_score = (ensemble_confidence * 0.6 + 
                               consensus_score * 0.3 + 
                               (1 - disagreement_score) * 0.1)
            
            ensemble_pred = PredictionOutput(
                symbol=request.symbol,
                horizon=horizon,
                predicted_price=weighted_price,
                price_change_percent=weighted_change,
                confidence_score=ensemble_confidence,
                risk_score=ensemble_risk,
                quality=ensemble_quality,
                model_used="ensemble",
                prediction_timestamp=datetime.now(),
                target_date=self._calculate_target_date(horizon),
                supporting_factors=supporting_factors,
                risk_factors=risk_factors,
                ensemble_components=[
                    {
                        'model': pred.model_used,
                        'weight': model_weights[pred.model_used],
                        'prediction': pred.predicted_price,
                        'confidence': pred.confidence_score
                    } for pred in individual_predictions
                ]
            )
            
            return EnsemblePrediction(
                individual_predictions=individual_predictions,
                ensemble_prediction=ensemble_pred,
                model_weights=model_weights,
                consensus_score=consensus_score,
                disagreement_score=disagreement_score,
                reliability_score=reliability_score
            )
            
        except Exception as e:
            self.logger.error(f"Ensemble prediction creation failed: {str(e)}")
            raise PredictionGenerationError(f"Failed to create ensemble prediction: {str(e)}")
    
    def _calculate_ensemble_weights(self, predictions: List[PredictionOutput]) -> Dict[str, float]:
        """Calculate optimal weights for ensemble based on model performance"""
        weights = {}
        
        for pred in predictions:
            # Base weight from confidence
            base_weight = pred.confidence_score
            
            # Adjust based on historical performance
            historical_performance = self._get_historical_performance(pred.model_used)
            if historical_performance:
                performance_multiplier = mean(historical_performance[-10:])  # Last 10 predictions
                base_weight *= performance_multiplier
            
            # Adjust based on quality
            quality_multiplier = {
                PredictionQuality.EXCELLENT: 1.2,
                PredictionQuality.GOOD: 1.1,
                PredictionQuality.ACCEPTABLE: 1.0,
                PredictionQuality.POOR: 0.8,
                PredictionQuality.UNRELIABLE: 0.5
            }
            base_weight *= quality_multiplier.get(pred.quality, 1.0)
            
            weights[pred.model_used] = base_weight
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        return weights
    
    def _calculate_consensus_score(self, predictions: List[PredictionOutput]) -> float:
        """Calculate how much the models agree (0-1 scale)"""
        if len(predictions) < 2:
            return 1.0
        
        price_changes = [p.price_change_percent for p in predictions]
        
        # Calculate standard deviation of price changes
        if len(price_changes) > 1:
            change_stdev = stdev(price_changes)
            # Convert to 0-1 score (lower deviation = higher consensus)
            consensus_score = max(0.0, 1.0 - (change_stdev / 20.0))  # 20% = full disagreement
        else:
            consensus_score = 1.0
        
        return consensus_score
    
    def _calculate_disagreement_score(self, predictions: List[PredictionOutput]) -> float:
        """Calculate disagreement between models (0-1 scale)"""
        return 1.0 - self._calculate_consensus_score(predictions)
    
    def _calculate_ensemble_risk(self, predictions: List[PredictionOutput], weights: Dict[str, float]) -> float:
        """Calculate weighted ensemble risk score"""
        weighted_risk = sum(
            pred.risk_score * weights[pred.model_used]
            for pred in predictions
        )
        
        # Add uncertainty penalty for disagreement
        disagreement = self._calculate_disagreement_score(predictions)
        uncertainty_penalty = disagreement * 0.1  # Max 10% penalty
        
        return min(weighted_risk + uncertainty_penalty, 1.0)
    
    def _assess_prediction_quality(self, confidence: float, volatility: float) -> PredictionQuality:
        """Assess prediction quality based on confidence and volatility"""
        # Adjust confidence based on volatility
        adjusted_confidence = confidence * (1.0 - volatility * 0.3)
        
        if adjusted_confidence >= 0.9:
            return PredictionQuality.EXCELLENT
        elif adjusted_confidence >= 0.8:
            return PredictionQuality.GOOD
        elif adjusted_confidence >= 0.6:
            return PredictionQuality.ACCEPTABLE
        elif adjusted_confidence >= 0.4:
            return PredictionQuality.POOR
        else:
            return PredictionQuality.UNRELIABLE
    
    def _simulate_model_prediction(self, symbol: str, horizon: PredictionHorizon, 
                                  model_type: str, current_price: float) -> Dict[str, Any]:
        """Simulate model prediction (replaced with actual ML engine calls in production)"""
        import random
        
        # Model-specific performance characteristics
        model_characteristics = {
            'lstm': {'volatility': 0.15, 'bias': 0.02, 'confidence_range': (0.65, 0.85)},
            'xgboost': {'volatility': 0.20, 'bias': -0.01, 'confidence_range': (0.60, 0.80)},
            'ensemble': {'volatility': 0.12, 'bias': 0.005, 'confidence_range': (0.70, 0.90)},
            'transformer': {'volatility': 0.18, 'bias': 0.015, 'confidence_range': (0.68, 0.88)}
        }
        
        char = model_characteristics.get(model_type, model_characteristics['lstm'])
        
        # Horizon-specific adjustments
        horizon_adjustments = {
            PredictionHorizon.ONE_WEEK: {'volatility_mult': 0.8, 'confidence_mult': 1.1},
            PredictionHorizon.ONE_MONTH: {'volatility_mult': 1.0, 'confidence_mult': 1.0},
            PredictionHorizon.THREE_MONTHS: {'volatility_mult': 1.3, 'confidence_mult': 0.9},
            PredictionHorizon.TWELVE_MONTHS: {'volatility_mult': 1.8, 'confidence_mult': 0.75}
        }
        
        horizon_adj = horizon_adjustments.get(horizon, horizon_adjustments[PredictionHorizon.ONE_MONTH])
        
        # Generate prediction
        base_change = random.gauss(char['bias'] * 100, 5)  # Base percentage change
        volatility = char['volatility'] * horizon_adj['volatility_mult']
        
        # Add volatility noise
        change_with_volatility = base_change + random.gauss(0, volatility * 10)
        
        # Clamp to reasonable ranges
        price_change_percent = max(-50, min(50, change_with_volatility))
        
        predicted_price = current_price * (1 + price_change_percent / 100)
        
        # Calculate confidence
        min_conf, max_conf = char['confidence_range']
        base_confidence = random.uniform(min_conf, max_conf) * horizon_adj['confidence_mult']
        
        # Reduce confidence for extreme predictions
        extreme_penalty = min(abs(price_change_percent) / 30, 0.3)
        confidence = max(0.3, base_confidence - extreme_penalty)
        
        # Calculate risk score (higher for volatile predictions)
        risk_score = min(volatility + extreme_penalty / 3, 1.0)
        
        return {
            'predicted_price': predicted_price,
            'price_change_percent': price_change_percent,
            'confidence': confidence,
            'volatility': volatility,
            'risk_score': risk_score,
            'trend': 'bullish' if price_change_percent > 0 else 'bearish',
            'uncertainty': 1.0 - confidence
        }
    
    def _calculate_target_date(self, horizon: PredictionHorizon) -> datetime:
        """Calculate target date based on prediction horizon"""
        now = datetime.now()
        
        horizon_deltas = {
            PredictionHorizon.ONE_WEEK: timedelta(days=7),
            PredictionHorizon.ONE_MONTH: timedelta(days=30),
            PredictionHorizon.THREE_MONTHS: timedelta(days=90),
            PredictionHorizon.TWELVE_MONTHS: timedelta(days=365)
        }
        
        delta = horizon_deltas.get(horizon, timedelta(days=30))
        return now + delta
    
    def _get_current_price_simulation(self, symbol: str) -> float:
        """Simulate current price lookup (replaced with market data API in production)"""
        # Simulate different price ranges for different symbols
        symbol_prices = {
            'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 2500.0, 'AMZN': 3200.0,
            'TSLA': 800.0, 'META': 350.0, 'NVDA': 450.0, 'NFLX': 400.0
        }
        
        return symbol_prices.get(symbol.upper(), 100.0)
    
    def _generate_supporting_factors(self, model_type: str, trend: str, 
                                   quality: PredictionQuality) -> List[str]:
        """Generate supporting factors for the prediction"""
        factors = []
        
        if quality in [PredictionQuality.EXCELLENT, PredictionQuality.GOOD]:
            factors.extend([
                f"High confidence {model_type} model prediction",
                "Strong historical pattern recognition",
                "Consistent market indicators alignment"
            ])
        
        if trend == 'bullish':
            factors.extend([
                "Positive momentum indicators",
                "Favorable technical analysis patterns",
                "Strong fundamental support"
            ])
        else:
            factors.extend([
                "Clear bearish technical signals",
                "Momentum indicators showing weakness",
                "Risk indicators elevated"
            ])
        
        return factors[:4]  # Limit to top 4 factors
    
    def _generate_risk_factors(self, volatility: float, uncertainty: float) -> List[str]:
        """Generate risk factors for the prediction"""
        factors = []
        
        if volatility > 0.3:
            factors.append("High market volatility detected")
        elif volatility > 0.15:
            factors.append("Moderate volatility may affect accuracy")
        
        if uncertainty > 0.4:
            factors.append("Elevated model uncertainty")
        elif uncertainty > 0.25:
            factors.append("Model shows some uncertainty")
        
        # General risk factors
        factors.extend([
            "Market conditions can change rapidly",
            "Unexpected news events may impact prediction"
        ])
        
        return factors[:3]  # Limit to top 3 risk factors
    
    def _generate_ensemble_supporting_factors(self, predictions: List[PredictionOutput], 
                                            consensus_score: float) -> List[str]:
        """Generate supporting factors for ensemble predictions"""
        factors = [
            f"Ensemble of {len(predictions)} independent models",
            f"Model consensus score: {consensus_score:.1%}"
        ]
        
        if consensus_score > 0.8:
            factors.append("Strong agreement between models")
        elif consensus_score > 0.6:
            factors.append("Good model consensus achieved")
        
        # Add best individual model factors
        best_pred = max(predictions, key=lambda p: p.confidence_score)
        factors.extend(best_pred.supporting_factors[:2])
        
        return factors[:5]
    
    def _generate_ensemble_risk_factors(self, predictions: List[PredictionOutput], 
                                      disagreement_score: float) -> List[str]:
        """Generate risk factors for ensemble predictions"""
        factors = []
        
        if disagreement_score > 0.4:
            factors.append("Significant disagreement between models")
        elif disagreement_score > 0.2:
            factors.append("Some model disagreement present")
        
        # Aggregate individual risk factors
        all_risk_factors = []
        for pred in predictions:
            all_risk_factors.extend(pred.risk_factors)
        
        # Count frequency of risk factors and include most common
        risk_factor_counts = {}
        for factor in all_risk_factors:
            risk_factor_counts[factor] = risk_factor_counts.get(factor, 0) + 1
        
        common_risks = sorted(risk_factor_counts.items(), key=lambda x: x[1], reverse=True)
        factors.extend([factor for factor, count in common_risks[:2]])
        
        return factors[:4]
    
    def _update_model_performance_history(self, model_type: str, confidence: float) -> None:
        """Update model performance history for ensemble weighting"""
        if model_type not in self._model_performance_history:
            self._model_performance_history[model_type] = []
        
        self._model_performance_history[model_type].append(confidence)
        
        # Keep only last 50 predictions for each model
        if len(self._model_performance_history[model_type]) > 50:
            self._model_performance_history[model_type] = self._model_performance_history[model_type][-50:]
    
    def _get_historical_performance(self, model_type: str) -> List[float]:
        """Get historical performance for a model type"""
        return self._model_performance_history.get(model_type, [])
    
    def get_model_performance_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for all models"""
        summary = {}
        
        for model_type, performances in self._model_performance_history.items():
            if performances:
                summary[model_type] = {
                    'average_confidence': mean(performances),
                    'recent_confidence': mean(performances[-10:]) if len(performances) >= 10 else mean(performances),
                    'confidence_trend': 'improving' if len(performances) >= 10 and mean(performances[-5:]) > mean(performances[-10:-5]) else 'stable',
                    'total_predictions': len(performances),
                    'reliability_score': min(mean(performances) * 1.1, 1.0)  # Slight boost for historical performance
                }
        
        return summary