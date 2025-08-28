#!/usr/bin/env python3
"""
Prediction Use Cases

Autor: Claude Code - Clean Architecture Use Case Designer
Datum: 26. August 2025  
Clean Architecture v6.0.0 - Application Layer
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

import sys
from pathlib import Path

# Add service root to path for imports
service_root = str(Path(__file__).parent.parent.parent)
if service_root not in sys.path:
    sys.path.append(service_root)

from application.interfaces.ml_prediction_service import IMLPredictionService
from application.interfaces.event_publisher import IEventPublisher, MLDomainEvents
from domain.entities.prediction import PredictionResult, PredictionTarget, EnsemblePrediction
from domain.entities.ml_engine import MLEngineType, PredictionHorizon
from domain.services.prediction_domain_service import PredictionDomainService
from domain.exceptions.ml_exceptions import MLInputValidationError, MLModelNotReadyError, MLPredictionError


class GenerateSinglePredictionUseCase:
    """Use Case: Generate Single ML Prediction"""
    
    def __init__(self,
                 prediction_service: IMLPredictionService,
                 domain_service: PredictionDomainService,
                 event_publisher: IEventPublisher):
        self._prediction_service = prediction_service
        self._domain_service = domain_service
        self._event_publisher = event_publisher
    
    async def execute(self, request: 'GeneratePredictionRequest') -> 'GeneratePredictionResponse':
        """Execute single prediction generation"""
        
        # 1. Create prediction target from request
        target = PredictionTarget(
            symbol=request.symbol.upper().strip(),
            horizon=request.horizon,
            target_date=self._calculate_target_date(request.horizon)
        )
        
        # 2. Validate prediction request using domain service
        validation_errors = self._domain_service.validate_prediction_request(
            target, request.engine_type
        )
        
        if validation_errors:
            raise MLInputValidationError(f"Validation failed: {', '.join(validation_errors)}")
        
        # 3. Generate prediction using ML service
        try:
            prediction_result = await self._prediction_service.generate_single_prediction(
                target, request.engine_type
            )
            
            # 4. Calculate recommendation strength using domain service
            recommendation_data = {
                'price_change_percent': prediction_result.price_change_percent or 0.0,
                'confidence_score': prediction_result.metrics.confidence_score if prediction_result.metrics else 0.0,
                'volatility_estimate': prediction_result.metrics.volatility_estimate if prediction_result.metrics else 0.0
            }
            
            recommendation = self._domain_service.calculate_recommendation_strength(recommendation_data)
            
            # 5. Publish prediction generated event
            event = MLDomainEvents.prediction_generated(
                prediction_id=str(prediction_result.prediction_id),
                symbol=target.symbol,
                model_id="",  # Will be filled by infrastructure
                model_type=request.engine_type.value,
                predicted_price=prediction_result.predicted_price,
                confidence_score=prediction_result.metrics.confidence_score if prediction_result.metrics else 0.0,
                prediction_horizon=request.horizon.value,
                high_confidence=prediction_result.metrics.confidence_score >= 0.8 if prediction_result.metrics else False
            )
            await self._event_publisher.publish(event)
            
            # 6. Return structured response
            return GeneratePredictionResponse(
                prediction_id=prediction_result.prediction_id,
                symbol=target.symbol,
                predicted_price=prediction_result.predicted_price,
                current_price=prediction_result.current_price,
                price_change_percent=prediction_result.price_change_percent,
                recommendation=recommendation,
                confidence_level=prediction_result.metrics.get_confidence_level().value if prediction_result.metrics else "low",
                target_date=target.target_date,
                engine_used=request.engine_type.value,
                is_actionable=prediction_result.is_actionable()
            )
            
        except Exception as e:
            # Publish prediction failed event
            await self._event_publisher.publish_event({
                "event_type": "PredictionFailed",
                "symbol": target.symbol,
                "engine_type": request.engine_type.value,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            raise MLModelNotReadyError(f"Failed to generate prediction: {str(e)}")
    
    def _calculate_target_date(self, horizon: PredictionHorizon) -> datetime:
        """Calculate target date based on prediction horizon"""
        now = datetime.utcnow()
        
        if horizon == PredictionHorizon.INTRADAY:
            return now + timedelta(hours=4)  # 4 hours ahead
        elif horizon == PredictionHorizon.SHORT_TERM:
            return now + timedelta(days=7)   # 1 week
        elif horizon == PredictionHorizon.MEDIUM_TERM:
            return now + timedelta(days=30)  # 1 month
        elif horizon == PredictionHorizon.LONG_TERM:
            return now + timedelta(days=90)  # 3 months
        elif horizon == PredictionHorizon.EXTENDED:
            return now + timedelta(days=365) # 1 year
        else:
            return now + timedelta(days=7)   # Default to 1 week


class GenerateEnsemblePredictionUseCase:
    """Use Case: Generate Ensemble ML Prediction"""
    
    def __init__(self,
                 prediction_service: IMLPredictionService,
                 domain_service: PredictionDomainService,
                 event_publisher: IEventPublisher):
        self._prediction_service = prediction_service
        self._domain_service = domain_service
        self._event_publisher = event_publisher
    
    async def execute(self, request: 'GenerateEnsemblePredictionRequest') -> 'GenerateEnsemblePredictionResponse':
        """Execute ensemble prediction generation"""
        
        # 1. Create prediction target
        target = PredictionTarget(
            symbol=request.symbol.upper().strip(),
            horizon=request.horizon,
            target_date=self._calculate_target_date(request.horizon)
        )
        
        # 2. Validate each engine can handle the request
        for engine_type in request.engine_types:
            validation_errors = self._domain_service.validate_prediction_request(target, engine_type)
            if validation_errors:
                raise PredictionValidationError(
                    f"Engine {engine_type.value} validation failed: {', '.join(validation_errors)}"
                )
        
        # 3. Generate ensemble prediction
        try:
            ensemble_prediction = await self._prediction_service.generate_ensemble_prediction(
                target, request.engine_types
            )
            
            # 4. Calculate ensemble recommendation
            if ensemble_prediction.ensemble_prediction:
                recommendation_data = {
                    'price_change_percent': ensemble_prediction.ensemble_prediction.price_change_percent or 0.0,
                    'confidence_score': ensemble_prediction.ensemble_prediction.metrics.confidence_score if ensemble_prediction.ensemble_prediction.metrics else 0.0,
                    'volatility_estimate': ensemble_prediction.ensemble_prediction.metrics.volatility_estimate if ensemble_prediction.ensemble_prediction.metrics else 0.0
                }
                recommendation = self._domain_service.calculate_recommendation_strength(recommendation_data)
                consensus = ensemble_prediction.get_prediction_consensus().value
            else:
                recommendation = "NEUTRAL"
                consensus = "NEUTRAL"
            
            # 5. Publish ensemble prediction event
            await self._event_publisher.publish_event({
                "event_type": "EnsemblePredictionGenerated",
                "ensemble_id": str(ensemble_prediction.ensemble_id),
                "symbol": target.symbol,
                "engines_used": [engine.value for engine in request.engine_types],
                "individual_predictions": len(ensemble_prediction.individual_predictions),
                "recommendation": recommendation,
                "consensus": consensus,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 6. Return ensemble response
            return GenerateEnsemblePredictionResponse(
                ensemble_id=ensemble_prediction.ensemble_id,
                symbol=target.symbol,
                ensemble_prediction=ensemble_prediction.ensemble_prediction,
                individual_predictions=ensemble_prediction.individual_predictions,
                consensus_recommendation=consensus,
                weights=ensemble_prediction.weights,
                confidence_level=ensemble_prediction.ensemble_prediction.metrics.get_confidence_level().value if ensemble_prediction.ensemble_prediction and ensemble_prediction.ensemble_prediction.metrics else "low"
            )
            
        except Exception as e:
            await self._event_publisher.publish_event({
                "event_type": "EnsemblePredictionFailed",
                "symbol": target.symbol,
                "engines": [engine.value for engine in request.engine_types],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            raise MLEngineNotAvailableError(f"Failed to generate ensemble prediction: {str(e)}")
    
    def _calculate_target_date(self, horizon: PredictionHorizon) -> datetime:
        """Calculate target date based on prediction horizon"""
        now = datetime.utcnow()
        
        if horizon == PredictionHorizon.INTRADAY:
            return now + timedelta(hours=4)
        elif horizon == PredictionHorizon.SHORT_TERM:
            return now + timedelta(days=7)
        elif horizon == PredictionHorizon.MEDIUM_TERM:
            return now + timedelta(days=30)
        elif horizon == PredictionHorizon.LONG_TERM:
            return now + timedelta(days=90)
        elif horizon == PredictionHorizon.EXTENDED:
            return now + timedelta(days=365)
        else:
            return now + timedelta(days=7)


class BatchPredictionUseCase:
    """Use Case: Generate Batch Predictions"""
    
    def __init__(self,
                 prediction_service: IMLPredictionService,
                 domain_service: PredictionDomainService,
                 event_publisher: IEventPublisher):
        self._prediction_service = prediction_service
        self._domain_service = domain_service
        self._event_publisher = event_publisher
    
    async def execute(self, request: 'BatchPredictionRequest') -> 'BatchPredictionResponse':
        """Execute batch prediction generation"""
        
        # 1. Validate symbols
        valid_symbols = []
        for symbol in request.symbols:
            if self._domain_service._is_valid_symbol(symbol):
                valid_symbols.append(symbol.upper().strip())
        
        if not valid_symbols:
            raise PredictionValidationError("No valid symbols provided")
        
        # 2. Generate batch predictions
        try:
            prediction_results = await self._prediction_service.batch_predict(
                valid_symbols, request.horizon, request.engine_types
            )
            
            # 3. Process results and calculate recommendations
            processed_results = []
            for result in prediction_results:
                if result.status.value == "completed":
                    recommendation_data = {
                        'price_change_percent': result.price_change_percent or 0.0,
                        'confidence_score': result.metrics.confidence_score if result.metrics else 0.0,
                        'volatility_estimate': result.metrics.volatility_estimate if result.metrics else 0.0
                    }
                    recommendation = self._domain_service.calculate_recommendation_strength(recommendation_data)
                    
                    processed_results.append({
                        'symbol': result.target.symbol,
                        'predicted_price': result.predicted_price,
                        'price_change_percent': result.price_change_percent,
                        'recommendation': recommendation,
                        'confidence': result.metrics.confidence_score if result.metrics else 0.0,
                        'is_actionable': result.is_actionable()
                    })
            
            # 4. Publish batch prediction event
            await self._event_publisher.publish_event({
                "event_type": "BatchPredictionCompleted",
                "symbols_requested": len(request.symbols),
                "predictions_generated": len(processed_results),
                "engines_used": [engine.value for engine in request.engine_types],
                "horizon": request.horizon.value,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 5. Return batch response
            return BatchPredictionResponse(
                total_requested=len(request.symbols),
                predictions_generated=len(processed_results),
                predictions=processed_results,
                horizon=request.horizon,
                engines_used=[engine.value for engine in request.engine_types]
            )
            
        except Exception as e:
            await self._event_publisher.publish_event({
                "event_type": "BatchPredictionFailed",
                "symbols": request.symbols,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            raise MLEngineNotAvailableError(f"Failed to generate batch predictions: {str(e)}")


# Request/Response DTOs for Use Cases
from dataclasses import dataclass

@dataclass
class GeneratePredictionRequest:
    symbol: str
    engine_type: MLEngineType
    horizon: PredictionHorizon

@dataclass  
class GeneratePredictionResponse:
    prediction_id: UUID
    symbol: str
    predicted_price: float
    current_price: Optional[float]
    price_change_percent: Optional[float]
    recommendation: str
    confidence_level: str
    target_date: datetime
    engine_used: str
    is_actionable: bool

@dataclass
class GenerateEnsemblePredictionRequest:
    symbol: str
    engine_types: List[MLEngineType]
    horizon: PredictionHorizon

@dataclass
class GenerateEnsemblePredictionResponse:
    ensemble_id: UUID
    symbol: str
    ensemble_prediction: Optional[PredictionResult]
    individual_predictions: List[PredictionResult]
    consensus_recommendation: str
    weights: Dict[MLEngineType, float]
    confidence_level: str

@dataclass
class BatchPredictionRequest:
    symbols: List[str]
    engine_types: List[MLEngineType]
    horizon: PredictionHorizon

@dataclass
class BatchPredictionResponse:
    total_requested: int
    predictions_generated: int
    predictions: List[Dict[str, Any]]
    horizon: PredictionHorizon
    engines_used: List[str]