#!/usr/bin/env python3
"""
ML Prediction Use Cases - Clean Architecture v6.0.0
Business Logic Orchestration for Machine Learning Prediction Operations

APPLICATION LAYER - USE CASES:
- GeneratePredictionUseCase: Orchestrates ML prediction generation
- GetPredictionHistoryUseCase: Manages prediction retrieval and filtering
- CalculateRiskMetricsUseCase: Handles risk assessment for predictions
- BatchPredictionUseCase: Manages bulk prediction operations

CLEAN ARCHITECTURE PRINCIPLES:
- Pure business logic without infrastructure dependencies
- Single Responsibility per Use Case
- Dependency Inversion through interfaces
- Domain-driven validation and rules

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal

from ..interfaces.ml_service_provider import IMLPredictor, IRiskCalculator
from ..interfaces.event_publisher import IEventPublisher
from ...domain.entities.ml_entities import (
    MLModel,
    MLPrediction,
    MLRiskMetrics,
    MLModelType,
    MLPredictionHorizon,
    ModelConfiguration
)
from ...domain.repositories.ml_repository import IMLAnalyticsRepository


logger = logging.getLogger(__name__)


# =============================================================================
# USE CASE REQUEST/RESPONSE MODELS
# =============================================================================

@dataclass
class GeneratePredictionRequest:
    """Request model for generating ML predictions"""
    symbol: str
    model_type: MLModelType
    prediction_horizon: MLPredictionHorizon = MLPredictionHorizon.SHORT_TERM
    include_risk_metrics: bool = True
    use_ensemble: bool = False
    confidence_threshold: float = 0.0


@dataclass
class GeneratePredictionResponse:
    """Response model for prediction generation"""
    success: bool
    prediction: Optional[MLPrediction] = None
    risk_metrics: Optional[MLRiskMetrics] = None
    model_info: Optional[Dict[str, Any]] = None
    warnings: List[str] = None
    message: str = ""


@dataclass
class BatchPredictionRequest:
    """Request model for batch predictions"""
    symbols: List[str]
    model_types: List[MLModelType] = None
    prediction_horizon: MLPredictionHorizon = MLPredictionHorizon.SHORT_TERM
    include_risk_metrics: bool = True
    max_concurrent_predictions: int = 5
    min_confidence_threshold: float = 0.5


@dataclass
class BatchPredictionResponse:
    """Response model for batch predictions"""
    success: bool
    predictions: List[MLPrediction] = None
    risk_metrics: List[MLRiskMetrics] = None
    failed_symbols: List[str] = None
    processing_time_seconds: float = 0.0
    message: str = ""


@dataclass
class PredictionHistoryRequest:
    """Request model for prediction history"""
    symbol: Optional[str] = None
    model_id: Optional[str] = None
    model_type: Optional[MLModelType] = None
    prediction_horizon: Optional[MLPredictionHorizon] = None
    min_confidence: float = 0.0
    days_back: int = 30
    limit: int = 100


@dataclass
class PredictionHistoryResponse:
    """Response model for prediction history"""
    success: bool
    predictions: List[MLPrediction] = None
    total_count: int = 0
    average_confidence: float = 0.0
    accuracy_metrics: Optional[Dict[str, float]] = None
    message: str = ""


@dataclass
class RiskAssessmentRequest:
    """Request model for risk assessment"""
    prediction_id: Optional[str] = None
    symbol: Optional[str] = None
    portfolio_symbols: Optional[List[str]] = None
    portfolio_weights: Optional[List[float]] = None
    risk_horizon_days: int = 252
    confidence_level: float = 0.95


@dataclass
class RiskAssessmentResponse:
    """Response model for risk assessment"""
    success: bool
    risk_metrics: Optional[MLRiskMetrics] = None
    portfolio_var: Optional[Dict[str, Decimal]] = None
    risk_recommendations: List[str] = None
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    message: str = ""


# =============================================================================
# ML PREDICTION USE CASES
# =============================================================================

class GeneratePredictionUseCase:
    """
    Use Case for Generating ML Predictions
    
    Orchestrates the complete prediction generation workflow including
    model selection, prediction execution, risk assessment, and result validation.
    
    Business Rules:
    - Only active, non-outdated models can generate predictions
    - Predictions below confidence threshold are flagged
    - Risk metrics must be calculated for all predictions
    - Ensemble predictions combine multiple model outputs
    """
    
    def __init__(self, 
                 repository: IMLAnalyticsRepository,
                 predictor: IMLPredictor,
                 risk_calculator: IRiskCalculator,
                 event_publisher: IEventPublisher):
        self.repository = repository
        self.predictor = predictor
        self.risk_calculator = risk_calculator
        self.event_publisher = event_publisher
    
    async def execute(self, request: GeneratePredictionRequest) -> GeneratePredictionResponse:
        """
        Execute prediction generation workflow
        
        Args:
            request: Prediction generation request
            
        Returns:
            Prediction response with model output and risk metrics
        """
        try:
            logger.info(f"Generating prediction for {request.symbol} using {request.model_type.value}")
            
            # Find suitable model
            model = await self._find_suitable_model(request.model_type, request.prediction_horizon)
            if not model:
                return GeneratePredictionResponse(
                    success=False,
                    message=f"No suitable {request.model_type.value} model found for {request.prediction_horizon.value}"
                )
            
            # Validate model can make predictions
            if not model.can_make_predictions():
                return GeneratePredictionResponse(
                    success=False,
                    message=f"Model {model.model_id} is not ready for predictions",
                    warnings=["Model may need retraining"]
                )
            
            # Generate prediction
            if request.use_ensemble:
                prediction = await self._generate_ensemble_prediction(
                    request.symbol, request.prediction_horizon, request.model_type
                )
            else:
                prediction = await self.predictor.generate_prediction(
                    model_id=model.model_id,
                    symbol=request.symbol,
                    prediction_horizon=request.prediction_horizon
                )
            
            if not prediction:
                return GeneratePredictionResponse(
                    success=False,
                    message="Prediction generation failed"
                )
            
            # Validate confidence threshold
            warnings = []
            if prediction.confidence_score < request.confidence_threshold:
                warnings.append(f"Prediction confidence ({prediction.confidence_score:.2f}) below threshold ({request.confidence_threshold:.2f})")
            
            # Save prediction
            prediction_saved = await self.repository.predictions.save(prediction)
            if not prediction_saved:
                logger.warning("Failed to save prediction")
            
            # Calculate risk metrics if requested
            risk_metrics = None
            if request.include_risk_metrics:
                risk_metrics = await self.risk_calculator.calculate_risk_metrics(
                    prediction_id=prediction.prediction_id,
                    symbol=request.symbol,
                    predicted_price=prediction.predicted_price
                )
                
                if risk_metrics:
                    await self.repository.risk.save(risk_metrics)
                    
                    # Add risk warnings
                    if risk_metrics.is_high_risk():
                        warnings.append(f"High risk prediction (risk score: {risk_metrics.risk_score:.1f})")
            
            # Publish prediction generated event
            await self.event_publisher.publish({
                "event_type": "PredictionGenerated",
                "prediction_id": prediction.prediction_id,
                "symbol": request.symbol,
                "model_id": model.model_id,
                "model_type": request.model_type.value,
                "predicted_price": float(prediction.predicted_price),
                "confidence_score": prediction.confidence_score,
                "prediction_horizon": request.prediction_horizon.value,
                "high_confidence": prediction.is_high_confidence(),
                "high_risk": risk_metrics.is_high_risk() if risk_metrics else False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return GeneratePredictionResponse(
                success=True,
                prediction=prediction,
                risk_metrics=risk_metrics,
                model_info={
                    "model_id": model.model_id,
                    "model_type": model.model_type.value,
                    "model_age_days": model.get_model_age_days(),
                    "is_outdated": model.is_outdated()
                },
                warnings=warnings,
                message="Prediction generated successfully"
            )
            
        except Exception as e:
            logger.error(f"Error generating prediction: {str(e)}")
            return GeneratePredictionResponse(
                success=False,
                message="Internal error during prediction generation"
            )
    
    async def _find_suitable_model(self, 
                                 model_type: MLModelType, 
                                 horizon: MLPredictionHorizon) -> Optional[MLModel]:
        """Find suitable model for prediction generation"""
        try:
            models = await self.repository.models.get_by_type(model_type)
            active_models = [model for model in models if model.is_active]
            
            # Find models supporting the horizon
            suitable_models = [
                model for model in active_models 
                if model.supports_horizon(horizon) and model.can_make_predictions()
            ]
            
            if not suitable_models:
                return None
            
            # Return newest suitable model
            return max(suitable_models, key=lambda m: m.last_trained_at or m.created_at)
            
        except Exception as e:
            logger.error(f"Error finding suitable model: {str(e)}")
            return None
    
    async def _generate_ensemble_prediction(self, 
                                          symbol: str, 
                                          horizon: MLPredictionHorizon,
                                          primary_model_type: MLModelType) -> Optional[MLPrediction]:
        """Generate ensemble prediction using multiple models"""
        try:
            # Get all active models that support the horizon
            all_models = await self.repository.models.get_active_models()
            suitable_models = [
                model for model in all_models 
                if model.supports_horizon(horizon) and model.can_make_predictions()
            ]
            
            if len(suitable_models) < 2:
                # Fall back to single model prediction
                primary_model = await self._find_suitable_model(primary_model_type, horizon)
                if primary_model:
                    return await self.predictor.generate_prediction(
                        model_id=primary_model.model_id,
                        symbol=symbol,
                        prediction_horizon=horizon
                    )
                return None
            
            # Generate predictions from multiple models
            predictions = []
            for model in suitable_models[:5]:  # Limit to 5 models for performance
                try:
                    prediction = await self.predictor.generate_prediction(
                        model_id=model.model_id,
                        symbol=symbol,
                        prediction_horizon=horizon
                    )
                    if prediction:
                        predictions.append((model, prediction))
                except Exception as e:
                    logger.warning(f"Model {model.model_id} prediction failed: {str(e)}")
            
            if not predictions:
                return None
            
            # Combine predictions using weighted average
            return self._combine_predictions(predictions, symbol, horizon)
            
        except Exception as e:
            logger.error(f"Error generating ensemble prediction: {str(e)}")
            return None
    
    def _combine_predictions(self, 
                           model_predictions: List[tuple], 
                           symbol: str, 
                           horizon: MLPredictionHorizon) -> MLPrediction:
        """Combine multiple model predictions into ensemble prediction"""
        total_weight = 0.0
        weighted_price = Decimal('0')
        weighted_confidence = 0.0
        features_used = []
        
        for model, prediction in model_predictions:
            # Weight based on model performance and confidence
            weight = prediction.confidence_score
            
            # Get latest performance metrics for additional weighting
            # (This would require async call, simplifying for now)
            
            total_weight += weight
            weighted_price += prediction.predicted_price * Decimal(str(weight))
            weighted_confidence += prediction.confidence_score * weight
            features_used.extend(prediction.features_used)
        
        if total_weight == 0:
            total_weight = 1.0
        
        # Create ensemble prediction
        ensemble_prediction = MLPrediction(
            model_id="ensemble",  # Special ID for ensemble predictions
            symbol=symbol,
            predicted_price=weighted_price / Decimal(str(total_weight)),
            confidence_score=weighted_confidence / total_weight,
            prediction_horizon=horizon,
            features_used=list(set(features_used)),  # Remove duplicates
            prediction_metadata={
                "ensemble_size": len(model_predictions),
                "component_models": [model.model_id for model, _ in model_predictions],
                "weighting_method": "confidence_weighted"
            }
        )
        
        return ensemble_prediction


class BatchPredictionUseCase:
    """
    Use Case for Batch Prediction Generation
    
    Orchestrates bulk prediction generation across multiple symbols
    with concurrent processing and error handling.
    """
    
    def __init__(self, 
                 generate_prediction_use_case: GeneratePredictionUseCase):
        self.generate_prediction_use_case = generate_prediction_use_case
    
    async def execute(self, request: BatchPredictionRequest) -> BatchPredictionResponse:
        """
        Execute batch prediction generation workflow
        
        Args:
            request: Batch prediction request
            
        Returns:
            Batch prediction response with all results
        """
        try:
            start_time = datetime.now()
            logger.info(f"Starting batch predictions for {len(request.symbols)} symbols")
            
            # Default model types if not specified
            model_types = request.model_types or [MLModelType.LSTM_BASIC]
            
            # Create semaphore for concurrent processing
            semaphore = asyncio.Semaphore(request.max_concurrent_predictions)
            
            predictions = []
            risk_metrics = []
            failed_symbols = []
            
            async def process_symbol_model(symbol: str, model_type: MLModelType):
                async with semaphore:
                    try:
                        prediction_request = GeneratePredictionRequest(
                            symbol=symbol,
                            model_type=model_type,
                            prediction_horizon=request.prediction_horizon,
                            include_risk_metrics=request.include_risk_metrics,
                            confidence_threshold=request.min_confidence_threshold
                        )
                        
                        response = await self.generate_prediction_use_case.execute(prediction_request)
                        
                        if response.success:
                            if response.prediction:
                                predictions.append(response.prediction)
                            if response.risk_metrics:
                                risk_metrics.append(response.risk_metrics)
                        else:
                            failed_symbols.append(f"{symbol}:{model_type.value}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {symbol}:{model_type.value}: {str(e)}")
                        failed_symbols.append(f"{symbol}:{model_type.value}")
            
            # Create tasks for all symbol-model combinations
            tasks = [
                process_symbol_model(symbol, model_type)
                for symbol in request.symbols
                for model_type in model_types
            ]
            
            # Execute all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return BatchPredictionResponse(
                success=len(predictions) > 0,
                predictions=predictions,
                risk_metrics=risk_metrics,
                failed_symbols=failed_symbols,
                processing_time_seconds=processing_time,
                message=f"Generated {len(predictions)} predictions, {len(failed_symbols)} failures"
            )
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {str(e)}")
            return BatchPredictionResponse(
                success=False,
                message="Internal error during batch prediction"
            )


class GetPredictionHistoryUseCase:
    """
    Use Case for Retrieving Prediction History
    
    Orchestrates prediction history retrieval with filtering,
    statistics calculation, and accuracy analysis.
    """
    
    def __init__(self, repository: IMLAnalyticsRepository):
        self.repository = repository
    
    async def execute(self, request: PredictionHistoryRequest) -> PredictionHistoryResponse:
        """
        Execute prediction history retrieval workflow
        
        Args:
            request: Prediction history request
            
        Returns:
            Prediction history response with filtered results and statistics
        """
        try:
            logger.info("Retrieving prediction history")
            
            predictions = []
            
            # Filter by different criteria
            if request.symbol:
                predictions = await self.repository.predictions.get_by_symbol(
                    request.symbol, request.limit
                )
            elif request.model_id:
                predictions = await self.repository.predictions.get_by_model(
                    request.model_id, request.limit
                )
            elif request.prediction_horizon:
                predictions = await self.repository.predictions.get_predictions_by_horizon(
                    request.prediction_horizon, request.limit
                )
            else:
                # Get recent predictions
                hours_back = request.days_back * 24
                predictions = await self.repository.predictions.get_recent_predictions(
                    hours_back, request.limit
                )
            
            # Apply additional filters
            if request.model_type:
                # Filter by model type (requires model lookup)
                filtered_predictions = []
                for prediction in predictions:
                    if prediction.model_id == "ensemble":
                        # For ensemble predictions, check metadata
                        continue
                    
                    model = await self.repository.models.get_by_id(prediction.model_id)
                    if model and model.model_type == request.model_type:
                        filtered_predictions.append(prediction)
                predictions = filtered_predictions
            
            if request.min_confidence > 0:
                predictions = [
                    p for p in predictions 
                    if p.confidence_score >= request.min_confidence
                ]
            
            # Calculate statistics
            total_count = len(predictions)
            average_confidence = 0.0
            if predictions:
                average_confidence = sum(p.confidence_score for p in predictions) / len(predictions)
            
            # Calculate accuracy metrics (simplified)
            accuracy_metrics = await self._calculate_accuracy_metrics(predictions)
            
            return PredictionHistoryResponse(
                success=True,
                predictions=predictions,
                total_count=total_count,
                average_confidence=average_confidence,
                accuracy_metrics=accuracy_metrics,
                message=f"Retrieved {total_count} predictions"
            )
            
        except Exception as e:
            logger.error(f"Error retrieving prediction history: {str(e)}")
            return PredictionHistoryResponse(
                success=False,
                message="Internal error retrieving prediction history"
            )
    
    async def _calculate_accuracy_metrics(self, 
                                        predictions: List[MLPrediction]) -> Dict[str, float]:
        """Calculate accuracy metrics for predictions (simplified implementation)"""
        try:
            if not predictions:
                return {}
            
            # Group by confidence ranges
            high_confidence = [p for p in predictions if p.is_high_confidence()]
            medium_confidence = [p for p in predictions if 0.5 <= p.confidence_score < 0.8]
            low_confidence = [p for p in predictions if p.confidence_score < 0.5]
            
            return {
                "total_predictions": len(predictions),
                "high_confidence_count": len(high_confidence),
                "medium_confidence_count": len(medium_confidence),
                "low_confidence_count": len(low_confidence),
                "high_confidence_ratio": len(high_confidence) / len(predictions),
                "expired_predictions": len([p for p in predictions if p.is_expired()])
            }
            
        except Exception:
            return {}


class CalculateRiskMetricsUseCase:
    """
    Use Case for Risk Metrics Calculation
    
    Orchestrates comprehensive risk assessment including VaR calculation,
    portfolio risk analysis, and correlation matrix generation.
    """
    
    def __init__(self, 
                 repository: IMLAnalyticsRepository,
                 risk_calculator: IRiskCalculator,
                 event_publisher: IEventPublisher):
        self.repository = repository
        self.risk_calculator = risk_calculator
        self.event_publisher = event_publisher
    
    async def execute(self, request: RiskAssessmentRequest) -> RiskAssessmentResponse:
        """
        Execute risk assessment workflow
        
        Args:
            request: Risk assessment request
            
        Returns:
            Risk assessment response with metrics and recommendations
        """
        try:
            logger.info("Calculating risk metrics")
            
            risk_metrics = None
            portfolio_var = None
            correlation_matrix = None
            
            # Single prediction risk assessment
            if request.prediction_id:
                prediction = await self.repository.predictions.get_by_id(request.prediction_id)
                if not prediction:
                    return RiskAssessmentResponse(
                        success=False,
                        message=f"Prediction {request.prediction_id} not found"
                    )
                
                risk_metrics = await self.risk_calculator.calculate_risk_metrics(
                    prediction_id=request.prediction_id,
                    symbol=prediction.symbol,
                    predicted_price=prediction.predicted_price,
                    calculation_period_days=request.risk_horizon_days
                )
            
            # Single symbol risk assessment
            elif request.symbol:
                # Get latest prediction for symbol
                predictions = await self.repository.predictions.get_by_symbol(request.symbol, 1)
                if predictions:
                    prediction = predictions[0]
                    risk_metrics = await self.risk_calculator.calculate_risk_metrics(
                        prediction_id=prediction.prediction_id,
                        symbol=request.symbol,
                        predicted_price=prediction.predicted_price,
                        calculation_period_days=request.risk_horizon_days
                    )
            
            # Portfolio risk assessment
            elif request.portfolio_symbols and request.portfolio_weights:
                if len(request.portfolio_symbols) != len(request.portfolio_weights):
                    return RiskAssessmentResponse(
                        success=False,
                        message="Portfolio symbols and weights must have same length"
                    )
                
                # Calculate portfolio VaR
                portfolio_var = await self.repository.risk.calculate_portfolio_var(
                    request.portfolio_symbols, request.portfolio_weights
                )
                
                # Get correlation matrix
                correlation_matrix = await self.repository.risk.get_correlation_matrix(
                    request.portfolio_symbols
                )
            
            else:
                return RiskAssessmentResponse(
                    success=False,
                    message="Must specify prediction_id, symbol, or portfolio for risk assessment"
                )
            
            # Save risk metrics if calculated
            if risk_metrics:
                await self.repository.risk.save(risk_metrics)
            
            # Generate risk recommendations
            recommendations = self._generate_risk_recommendations(
                risk_metrics, portfolio_var, correlation_matrix
            )
            
            # Publish risk assessment event
            if risk_metrics:
                await self.event_publisher.publish({
                    "event_type": "RiskAssessmentCompleted",
                    "prediction_id": request.prediction_id,
                    "symbol": request.symbol,
                    "risk_score": risk_metrics.risk_score,
                    "risk_category": risk_metrics.get_risk_category(),
                    "high_risk": risk_metrics.is_high_risk(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            return RiskAssessmentResponse(
                success=True,
                risk_metrics=risk_metrics,
                portfolio_var=portfolio_var,
                risk_recommendations=recommendations,
                correlation_matrix=correlation_matrix,
                message="Risk assessment completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return RiskAssessmentResponse(
                success=False,
                message="Internal error during risk assessment"
            )
    
    def _generate_risk_recommendations(self, 
                                     risk_metrics: Optional[MLRiskMetrics],
                                     portfolio_var: Optional[Dict[str, Decimal]],
                                     correlation_matrix: Optional[Dict[str, Dict[str, float]]]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if risk_metrics:
            if risk_metrics.is_high_risk():
                recommendations.append("High risk detected - consider reducing position size")
                recommendations.append(f"Recommended position sizing factor: {risk_metrics.calculate_position_sizing_factor():.2f}")
            
            if risk_metrics.requires_additional_validation():
                recommendations.append("Additional validation required due to elevated risk metrics")
            
            if not risk_metrics.is_within_risk_tolerance():
                recommendations.append("Risk exceeds tolerance levels - consider alternative strategies")
        
        if portfolio_var:
            var_95 = portfolio_var.get('var_95', Decimal('0'))
            if var_95 > Decimal('0.05'):  # 5% VaR threshold
                recommendations.append("Portfolio VaR exceeds 5% - consider diversification")
        
        if correlation_matrix:
            # Check for high correlations
            high_corr_pairs = []
            symbols = list(correlation_matrix.keys())
            for i, symbol1 in enumerate(symbols):
                for symbol2 in symbols[i+1:]:
                    corr = correlation_matrix.get(symbol1, {}).get(symbol2, 0)
                    if abs(corr) > 0.8:
                        high_corr_pairs.append(f"{symbol1}-{symbol2}: {corr:.2f}")
            
            if high_corr_pairs:
                recommendations.append(f"High correlations detected: {', '.join(high_corr_pairs[:3])}")
                recommendations.append("Consider reducing concentration in correlated assets")
        
        return recommendations