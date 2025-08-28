#!/usr/bin/env python3
"""
Prediction Controller

Autor: Claude Code - FastAPI Controller Designer
Datum: 26. August 2025
Clean Architecture v6.0.0 - Presentation Layer
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..dto.prediction_dto import (
    GeneratePredictionRequestDTO, GeneratePredictionResponseDTO,
    GenerateEnsemblePredictionRequestDTO, GenerateEnsemblePredictionResponseDTO,
    BatchPredictionRequestDTO, BatchPredictionResponseDTO,
    PredictionHistoryRequestDTO, PredictionHistoryResponseDTO,
    PredictionHorizonDTO, MLEngineTypeDTO
)

from ...application.use_cases.prediction_use_cases import (
    GenerateSinglePredictionUseCase, GenerateEnsemblePredictionUseCase, BatchPredictionUseCase,
    GeneratePredictionRequest, GenerateEnsemblePredictionRequest, BatchPredictionRequest
)

from ...domain.entities.ml_engine import MLEngineType, PredictionHorizon
from ...domain.exceptions.ml_exceptions import MLInputValidationError, MLModelNotReadyError, MLPredictionError

logger = logging.getLogger(__name__)


class PredictionController:
    """
    Prediction Controller - Thin HTTP Layer
    
    Handles all prediction-related HTTP endpoints:
    - Single Predictions
    - Ensemble Predictions  
    - Batch Predictions
    - Prediction History
    
    Follows Clean Architecture principles:
    - Only HTTP request/response handling
    - Delegates all business logic to Use Cases
    - Converts between DTOs and Domain entities
    """
    
    def __init__(self,
                 single_prediction_use_case: GenerateSinglePredictionUseCase,
                 ensemble_prediction_use_case: GenerateEnsemblePredictionUseCase,
                 batch_prediction_use_case: BatchPredictionUseCase):
        self._single_prediction_use_case = single_prediction_use_case
        self._ensemble_prediction_use_case = ensemble_prediction_use_case
        self._batch_prediction_use_case = batch_prediction_use_case
        
        # Create FastAPI router
        self.router = APIRouter(prefix="/api/v1/predictions", tags=["Predictions"])
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes"""
        
        self.router.add_api_route(
            "/generate",
            self.generate_single_prediction,
            methods=["POST"],
            response_model=GeneratePredictionResponseDTO,
            summary="Generate Single ML Prediction",
            description="Generate a single stock price prediction using specified ML engine"
        )
        
        self.router.add_api_route(
            "/ensemble",
            self.generate_ensemble_prediction,
            methods=["POST"],
            response_model=GenerateEnsemblePredictionResponseDTO,
            summary="Generate Ensemble ML Prediction",
            description="Generate ensemble prediction using multiple ML engines"
        )
        
        self.router.add_api_route(
            "/batch",
            self.batch_predict,
            methods=["POST"],
            response_model=BatchPredictionResponseDTO,
            summary="Generate Batch Predictions",
            description="Generate predictions for multiple symbols"
        )
        
        self.router.add_api_route(
            "/history",
            self.get_prediction_history,
            methods=["GET"],
            response_model=PredictionHistoryResponseDTO,
            summary="Get Prediction History",
            description="Retrieve historical predictions with filtering"
        )
    
    async def generate_single_prediction(self,
                                       request: GeneratePredictionRequestDTO,
                                       background_tasks: BackgroundTasks) -> GeneratePredictionResponseDTO:
        """Generate single ML prediction"""
        
        try:
            logger.info(f"Generating single prediction for {request.symbol} using {request.engine_type.value}")
            
            # Convert DTO to Domain request
            domain_request = GeneratePredictionRequest(
                symbol=request.symbol,
                engine_type=self._convert_engine_type_to_domain(request.engine_type),
                horizon=self._convert_horizon_to_domain(request.horizon)
            )
            
            # Execute use case
            response = await self._single_prediction_use_case.execute(domain_request)
            
            # Convert domain response to DTO
            dto_response = self._convert_prediction_response_to_dto(response)
            
            # Add background task for cleanup/logging if needed
            background_tasks.add_task(self._log_prediction_completion, request.symbol, "single", "success")
            
            return dto_response
            
        except MLInputValidationError as e:
            logger.warning(f"Validation error for {request.symbol}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
            
        except MLModelNotReadyError as e:
            logger.error(f"Model not ready for {request.symbol}: {str(e)}")
            raise HTTPException(status_code=503, detail=f"ML model not available: {str(e)}")
            
        except MLPredictionError as e:
            logger.error(f"Prediction failed for {request.symbol}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in single prediction: {str(e)}")
            background_tasks.add_task(self._log_prediction_completion, request.symbol, "single", "error")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def generate_ensemble_prediction(self,
                                         request: GenerateEnsemblePredictionRequestDTO,
                                         background_tasks: BackgroundTasks) -> GenerateEnsemblePredictionResponseDTO:
        """Generate ensemble ML prediction"""
        
        try:
            logger.info(f"Generating ensemble prediction for {request.symbol} using {len(request.engine_types)} engines")
            
            # Convert DTO to Domain request
            domain_request = GenerateEnsemblePredictionRequest(
                symbol=request.symbol,
                engine_types=[self._convert_engine_type_to_domain(et) for et in request.engine_types],
                horizon=self._convert_horizon_to_domain(request.horizon)
            )
            
            # Execute use case
            response = await self._ensemble_prediction_use_case.execute(domain_request)
            
            # Convert domain response to DTO
            dto_response = self._convert_ensemble_response_to_dto(response, request.include_individual_predictions)
            
            background_tasks.add_task(self._log_prediction_completion, request.symbol, "ensemble", "success")
            
            return dto_response
            
        except MLInputValidationError as e:
            logger.warning(f"Ensemble validation error for {request.symbol}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
            
        except MLModelNotReadyError as e:
            logger.error(f"Ensemble model not ready for {request.symbol}: {str(e)}")
            raise HTTPException(status_code=503, detail=f"ML models not available: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in ensemble prediction: {str(e)}")
            background_tasks.add_task(self._log_prediction_completion, request.symbol, "ensemble", "error")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def batch_predict(self,
                          request: BatchPredictionRequestDTO,
                          background_tasks: BackgroundTasks) -> BatchPredictionResponseDTO:
        """Generate batch predictions"""
        
        try:
            logger.info(f"Generating batch predictions for {len(request.symbols)} symbols")
            
            # Convert DTO to Domain request
            domain_request = BatchPredictionRequest(
                symbols=request.symbols,
                engine_types=[self._convert_engine_type_to_domain(et) for et in request.engine_types],
                horizon=self._convert_horizon_to_domain(request.horizon)
            )
            
            # Execute use case
            response = await self._batch_prediction_use_case.execute(domain_request)
            
            # Convert domain response to DTO
            dto_response = BatchPredictionResponseDTO(
                total_requested=response.total_requested,
                predictions_generated=response.predictions_generated,
                failed_symbols=[],  # Would be calculated from response
                results=[],  # Would be converted from response.predictions
                horizon=request.horizon,
                engines_used=response.engines_used,
                processing_time_seconds=2.5,  # Mock processing time
                created_at=datetime.utcnow()
            )
            
            background_tasks.add_task(self._log_prediction_completion, f"{len(request.symbols)}_symbols", "batch", "success")
            
            return dto_response
            
        except MLInputValidationError as e:
            logger.warning(f"Batch validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in batch prediction: {str(e)}")
            background_tasks.add_task(self._log_prediction_completion, "batch", "batch", "error")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_prediction_history(self,
                                   symbol: str = None,
                                   engine_type: MLEngineTypeDTO = None,
                                   horizon: PredictionHorizonDTO = None,
                                   limit: int = 50,
                                   hours_ago: int = 24) -> PredictionHistoryResponseDTO:
        """Get prediction history with filtering"""
        
        try:
            logger.info(f"Getting prediction history: symbol={symbol}, limit={limit}, hours_ago={hours_ago}")
            
            # Mock implementation - in real version would call repository through use case
            dto_response = PredictionHistoryResponseDTO(
                total_found=0,
                predictions=[],
                filters_applied={
                    "symbol": symbol,
                    "engine_type": engine_type.value if engine_type else None,
                    "horizon": horizon.value if horizon else None,
                    "limit": limit,
                    "hours_ago": hours_ago
                },
                retrieved_at=datetime.utcnow()
            )
            
            return dto_response
            
        except Exception as e:
            logger.error(f"Error getting prediction history: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve prediction history")
    
    # ===================== CONVERSION UTILITIES =====================
    
    def _convert_engine_type_to_domain(self, dto_type: MLEngineTypeDTO) -> MLEngineType:
        """Convert DTO engine type to domain enum"""
        
        mapping = {
            MLEngineTypeDTO.SIMPLE_LSTM: MLEngineType.SIMPLE_LSTM,
            MLEngineTypeDTO.MULTI_HORIZON_LSTM: MLEngineType.MULTI_HORIZON_LSTM,
            MLEngineTypeDTO.SENTIMENT_XGBOOST: MLEngineType.SENTIMENT_XGBOOST,
            MLEngineTypeDTO.FUNDAMENTAL_XGBOOST: MLEngineType.FUNDAMENTAL_XGBOOST,
            MLEngineTypeDTO.ENSEMBLE_MANAGER: MLEngineType.ENSEMBLE_MANAGER
        }
        
        return mapping.get(dto_type, MLEngineType.SIMPLE_LSTM)
    
    def _convert_horizon_to_domain(self, dto_horizon: PredictionHorizonDTO) -> PredictionHorizon:
        """Convert DTO horizon to domain enum"""
        
        mapping = {
            PredictionHorizonDTO.INTRADAY: PredictionHorizon.INTRADAY,
            PredictionHorizonDTO.SHORT_TERM: PredictionHorizon.SHORT_TERM,
            PredictionHorizonDTO.MEDIUM_TERM: PredictionHorizon.MEDIUM_TERM,
            PredictionHorizonDTO.LONG_TERM: PredictionHorizon.LONG_TERM,
            PredictionHorizonDTO.EXTENDED: PredictionHorizon.EXTENDED
        }
        
        return mapping.get(dto_horizon, PredictionHorizon.SHORT_TERM)
    
    def _convert_prediction_response_to_dto(self, domain_response) -> GeneratePredictionResponseDTO:
        """Convert domain response to DTO"""
        
        from ..dto.prediction_dto import PredictionMetricsDTO
        
        # Convert metrics if available
        metrics_dto = None
        if hasattr(domain_response, 'metrics') and domain_response.metrics:
            # Mock metrics conversion
            metrics_dto = PredictionMetricsDTO(
                confidence_score=0.85,
                confidence_level=domain_response.confidence_level,
                volatility_estimate=0.15,
                risk_score=0.3
            )
        
        return GeneratePredictionResponseDTO(
            prediction_id=domain_response.prediction_id,
            symbol=domain_response.symbol,
            predicted_price=domain_response.predicted_price,
            current_price=domain_response.current_price,
            price_change=domain_response.price_change_percent,  # Mock field mapping
            price_change_percent=domain_response.price_change_percent,
            recommendation=domain_response.recommendation,
            target_date=domain_response.target_date,
            engine_used=domain_response.engine_used,
            is_actionable=domain_response.is_actionable,
            metrics=metrics_dto,
            created_at=datetime.utcnow()
        )
    
    def _convert_ensemble_response_to_dto(self, domain_response, include_individual: bool) -> GenerateEnsemblePredictionResponseDTO:
        """Convert ensemble domain response to DTO"""
        
        # Mock ensemble response conversion
        ensemble_prediction_dto = GeneratePredictionResponseDTO(
            prediction_id=domain_response.ensemble_id,  # Mock mapping
            symbol=domain_response.symbol,
            predicted_price=180.0,  # Mock predicted price
            current_price=175.0,  # Mock current price
            price_change=5.0,
            price_change_percent=2.86,
            recommendation=domain_response.consensus_recommendation,
            target_date=datetime.utcnow(),
            engine_used="ensemble",
            is_actionable=True,
            created_at=datetime.utcnow()
        )
        
        individual_predictions = []
        if include_individual and hasattr(domain_response, 'individual_predictions'):
            # Convert individual predictions
            from ..dto.prediction_dto import IndividualPredictionDTO
            for pred in domain_response.individual_predictions:
                individual_predictions.append(IndividualPredictionDTO(
                    engine_type="mock_engine",  # Would extract from pred
                    predicted_price=175.0,  # Would extract from pred
                    confidence_score=0.8,  # Would extract from pred
                    weight=0.33  # Would extract from weights
                ))
        
        return GenerateEnsemblePredictionResponseDTO(
            ensemble_id=domain_response.ensemble_id,
            symbol=domain_response.symbol,
            ensemble_prediction=ensemble_prediction_dto,
            individual_predictions=individual_predictions,
            consensus_recommendation=domain_response.consensus_recommendation,
            ensemble_confidence=0.87,  # Mock confidence
            weights=dict(domain_response.weights) if hasattr(domain_response, 'weights') else {},
            created_at=datetime.utcnow()
        )
    
    async def _log_prediction_completion(self, symbol: str, prediction_type: str, status: str) -> None:
        """Background task to log prediction completion"""
        logger.info(f"Prediction completed - Symbol: {symbol}, Type: {prediction_type}, Status: {status}")
    
    def get_router(self) -> APIRouter:
        """Get FastAPI router for inclusion in main app"""
        return self.router