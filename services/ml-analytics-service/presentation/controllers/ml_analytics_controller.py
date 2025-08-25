#!/usr/bin/env python3
"""
ML Analytics Controller - Clean Architecture v6.0.0
HTTP Request/Response Handler for Machine Learning Operations

PRESENTATION LAYER - CONTROLLER:
- FastAPI endpoint coordination for ML operations
- Request/Response transformation and validation
- HTTP-specific error handling and status codes
- Async operation management for ML workflows

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Only HTTP request coordination
- Dependency Inversion: Uses application layer interfaces
- No business logic in presentation layer
- Proper separation of concerns

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

# Application Layer Imports
from ...application.use_cases.ml_training_use_cases import (
    TrainModelUseCase,
    EvaluateModelUseCase,
    RetrainOutdatedModelsUseCase,
    TrainModelRequest,
    TrainModelResponse,
    ModelEvaluationRequest,
    ModelEvaluationResponse,
    RetrainModelsRequest,
    RetrainModelsResponse
)
from ...application.use_cases.ml_prediction_use_cases import (
    GeneratePredictionUseCase,
    BatchPredictionUseCase,
    GetPredictionHistoryUseCase,
    CalculateRiskMetricsUseCase,
    GeneratePredictionRequest,
    GeneratePredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionHistoryRequest,
    PredictionHistoryResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse
)

# Domain Layer Imports
from ...domain.entities.ml_entities import MLModelType, MLPredictionHorizon, ModelConfiguration

# Presentation Layer Models
from ..models.ml_models import *


logger = logging.getLogger(__name__)


# =============================================================================
# ML ANALYTICS CONTROLLER
# =============================================================================

class MLAnalyticsController:
    """
    ML Analytics Controller
    
    Coordinates HTTP requests for machine learning operations including
    model training, prediction generation, evaluation, and risk assessment.
    
    SOLID Principles:
    - Single Responsibility: Only HTTP request coordination
    - Open/Closed: Extensible for new ML endpoints
    - Dependency Inversion: Uses application layer use cases
    """
    
    def __init__(self,
                 train_model_use_case: TrainModelUseCase,
                 evaluate_model_use_case: EvaluateModelUseCase,
                 retrain_models_use_case: RetrainOutdatedModelsUseCase,
                 generate_prediction_use_case: GeneratePredictionUseCase,
                 batch_prediction_use_case: BatchPredictionUseCase,
                 get_prediction_history_use_case: GetPredictionHistoryUseCase,
                 calculate_risk_metrics_use_case: CalculateRiskMetricsUseCase):
        
        # Training Use Cases
        self.train_model_use_case = train_model_use_case
        self.evaluate_model_use_case = evaluate_model_use_case
        self.retrain_models_use_case = retrain_models_use_case
        
        # Prediction Use Cases
        self.generate_prediction_use_case = generate_prediction_use_case
        self.batch_prediction_use_case = batch_prediction_use_case
        self.get_prediction_history_use_case = get_prediction_history_use_case
        self.calculate_risk_metrics_use_case = calculate_risk_metrics_use_case
        
        logger.info("ML Analytics Controller initialized")
    
    # =============================================================================
    # MODEL TRAINING ENDPOINTS
    # =============================================================================
    
    async def train_model(self, request: TrainModelRequestDTO, background_tasks: BackgroundTasks) -> JSONResponse:
        """
        Train ML model endpoint
        
        Args:
            request: Training request DTO
            background_tasks: FastAPI background tasks
            
        Returns:
            JSON response with training job details
        """
        try:
            logger.info(f"Training model request: {request.model_type} for {request.symbol}")
            
            # Convert DTO to domain request
            configuration = ModelConfiguration(
                model_type=MLModelType(request.model_type),
                hyperparameters=request.hyperparameters or {},
                feature_set=request.feature_set or [],
                training_window_days=request.training_window_days,
                prediction_horizon=MLPredictionHorizon(request.prediction_horizon)
            )
            
            domain_request = TrainModelRequest(
                model_type=MLModelType(request.model_type),
                configuration=configuration,
                symbol=request.symbol,
                force_retrain=request.force_retrain,
                background_training=request.background_training
            )
            
            # Execute use case
            response = await self.train_model_use_case.execute(domain_request)
            
            # Convert to HTTP response
            if response.success:
                return JSONResponse(
                    status_code=201 if request.background_training else 200,
                    content={
                        "success": True,
                        "data": {
                            "job_id": response.job_id,
                            "model_id": response.model_id,
                            "estimated_completion_minutes": response.estimated_completion_minutes,
                            "background_training": request.background_training
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "details": response.error_details,
                            "code": "TRAINING_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except ValueError as e:
            logger.error(f"Validation error in train_model: {str(e)}")
            raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in train_model endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def evaluate_model(self, request: ModelEvaluationRequestDTO) -> JSONResponse:
        """
        Evaluate model performance endpoint
        
        Args:
            request: Model evaluation request DTO
            
        Returns:
            JSON response with evaluation results
        """
        try:
            logger.info(f"Evaluating model: {request.model_id}")
            
            # Convert DTO to domain request
            domain_request = ModelEvaluationRequest(
                model_id=request.model_id,
                evaluation_period_days=request.evaluation_period_days,
                include_risk_metrics=request.include_risk_metrics,
                comparison_models=request.comparison_models
            )
            
            # Execute use case
            response = await self.evaluate_model_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "data": {
                            "model_id": request.model_id,
                            "performance_metrics": {
                                "accuracy": response.performance_metrics.accuracy,
                                "precision": response.performance_metrics.precision,
                                "recall": response.performance_metrics.recall,
                                "f1_score": response.performance_metrics.f1_score,
                                "r2_score": response.performance_metrics.r2_score
                            } if response.performance_metrics else None,
                            "performance_category": response.performance_category.value if response.performance_category else None,
                            "needs_retraining": response.performance_metrics.needs_retraining() if response.performance_metrics else None,
                            "comparison_results": response.comparison_results,
                            "recommendations": response.recommendations
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=404 if "not found" in response.message.lower() else 400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "EVALUATION_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in evaluate_model endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def retrain_outdated_models(self, request: RetrainModelsRequestDTO, background_tasks: BackgroundTasks) -> JSONResponse:
        """
        Retrain outdated models endpoint
        
        Args:
            request: Batch retraining request DTO
            background_tasks: FastAPI background tasks
            
        Returns:
            JSON response with retraining job details
        """
        try:
            logger.info("Starting batch model retraining")
            
            # Convert DTO to domain request
            model_types = None
            if request.model_types:
                model_types = [MLModelType(mt) for mt in request.model_types]
            
            domain_request = RetrainModelsRequest(
                max_age_days=request.max_age_days,
                model_types=model_types,
                force_retrain_poor_performers=request.force_retrain_poor_performers,
                max_concurrent_jobs=request.max_concurrent_jobs
            )
            
            # Execute use case
            response = await self.retrain_models_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=202,  # Accepted for background processing
                    content={
                        "success": True,
                        "data": {
                            "jobs_started": response.jobs_started or [],
                            "models_evaluated": response.models_evaluated,
                            "estimated_total_time_minutes": response.estimated_total_time_minutes
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "RETRAINING_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in retrain_outdated_models endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # =============================================================================
    # PREDICTION ENDPOINTS
    # =============================================================================
    
    async def generate_prediction(self, request: GeneratePredictionRequestDTO) -> JSONResponse:
        """
        Generate ML prediction endpoint
        
        Args:
            request: Prediction generation request DTO
            
        Returns:
            JSON response with prediction and risk metrics
        """
        try:
            logger.info(f"Generating prediction for {request.symbol} using {request.model_type}")
            
            # Convert DTO to domain request
            domain_request = GeneratePredictionRequest(
                symbol=request.symbol,
                model_type=MLModelType(request.model_type),
                prediction_horizon=MLPredictionHorizon(request.prediction_horizon),
                include_risk_metrics=request.include_risk_metrics,
                use_ensemble=request.use_ensemble,
                confidence_threshold=request.confidence_threshold
            )
            
            # Execute use case
            response = await self.generate_prediction_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "data": {
                            "prediction": {
                                "prediction_id": response.prediction.prediction_id,
                                "symbol": response.prediction.symbol,
                                "predicted_price": float(response.prediction.predicted_price),
                                "confidence_score": response.prediction.confidence_score,
                                "prediction_horizon": response.prediction.prediction_horizon.value,
                                "high_confidence": response.prediction.is_high_confidence(),
                                "created_at": response.prediction.created_at.isoformat(),
                                "features_used": response.prediction.features_used
                            } if response.prediction else None,
                            "risk_metrics": {
                                "risk_score": response.risk_metrics.risk_score,
                                "risk_category": response.risk_metrics.get_risk_category(),
                                "var_95": float(response.risk_metrics.var_95),
                                "volatility": response.risk_metrics.volatility,
                                "position_sizing_factor": response.risk_metrics.calculate_position_sizing_factor()
                            } if response.risk_metrics else None,
                            "model_info": response.model_info,
                            "warnings": response.warnings or []
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=404 if "not found" in response.message.lower() else 400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "PREDICTION_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in generate_prediction endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def batch_predict(self, request: BatchPredictionRequestDTO) -> JSONResponse:
        """
        Batch prediction generation endpoint
        
        Args:
            request: Batch prediction request DTO
            
        Returns:
            JSON response with batch prediction results
        """
        try:
            logger.info(f"Generating batch predictions for {len(request.symbols)} symbols")
            
            # Convert DTO to domain request
            model_types = None
            if request.model_types:
                model_types = [MLModelType(mt) for mt in request.model_types]
            
            domain_request = BatchPredictionRequest(
                symbols=request.symbols,
                model_types=model_types,
                prediction_horizon=MLPredictionHorizon(request.prediction_horizon),
                include_risk_metrics=request.include_risk_metrics,
                max_concurrent_predictions=request.max_concurrent_predictions,
                min_confidence_threshold=request.min_confidence_threshold
            )
            
            # Execute use case
            response = await self.batch_prediction_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "data": {
                            "predictions": [
                                {
                                    "prediction_id": pred.prediction_id,
                                    "symbol": pred.symbol,
                                    "predicted_price": float(pred.predicted_price),
                                    "confidence_score": pred.confidence_score,
                                    "prediction_horizon": pred.prediction_horizon.value,
                                    "high_confidence": pred.is_high_confidence()
                                }
                                for pred in (response.predictions or [])
                            ],
                            "risk_metrics": [
                                {
                                    "symbol": risk.symbol,
                                    "risk_score": risk.risk_score,
                                    "risk_category": risk.get_risk_category()
                                }
                                for risk in (response.risk_metrics or [])
                            ],
                            "failed_symbols": response.failed_symbols or [],
                            "processing_time_seconds": response.processing_time_seconds
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "BATCH_PREDICTION_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in batch_predict endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_prediction_history(self, request: PredictionHistoryRequestDTO) -> JSONResponse:
        """
        Get prediction history endpoint
        
        Args:
            request: Prediction history request DTO
            
        Returns:
            JSON response with prediction history and statistics
        """
        try:
            logger.info("Retrieving prediction history")
            
            # Convert DTO to domain request
            model_type = MLModelType(request.model_type) if request.model_type else None
            prediction_horizon = MLPredictionHorizon(request.prediction_horizon) if request.prediction_horizon else None
            
            domain_request = PredictionHistoryRequest(
                symbol=request.symbol,
                model_id=request.model_id,
                model_type=model_type,
                prediction_horizon=prediction_horizon,
                min_confidence=request.min_confidence,
                days_back=request.days_back,
                limit=request.limit
            )
            
            # Execute use case
            response = await self.get_prediction_history_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "data": {
                            "predictions": [
                                {
                                    "prediction_id": pred.prediction_id,
                                    "model_id": pred.model_id,
                                    "symbol": pred.symbol,
                                    "predicted_price": float(pred.predicted_price),
                                    "confidence_score": pred.confidence_score,
                                    "prediction_horizon": pred.prediction_horizon.value,
                                    "created_at": pred.created_at.isoformat(),
                                    "is_expired": pred.is_expired()
                                }
                                for pred in (response.predictions or [])
                            ],
                            "total_count": response.total_count,
                            "average_confidence": response.average_confidence,
                            "accuracy_metrics": response.accuracy_metrics
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "HISTORY_RETRIEVAL_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in get_prediction_history endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # =============================================================================
    # RISK ASSESSMENT ENDPOINTS
    # =============================================================================
    
    async def calculate_risk_metrics(self, request: RiskAssessmentRequestDTO) -> JSONResponse:
        """
        Calculate risk metrics endpoint
        
        Args:
            request: Risk assessment request DTO
            
        Returns:
            JSON response with risk metrics and recommendations
        """
        try:
            logger.info("Calculating risk metrics")
            
            # Convert DTO to domain request
            domain_request = RiskAssessmentRequest(
                prediction_id=request.prediction_id,
                symbol=request.symbol,
                portfolio_symbols=request.portfolio_symbols,
                portfolio_weights=request.portfolio_weights,
                risk_horizon_days=request.risk_horizon_days,
                confidence_level=request.confidence_level
            )
            
            # Execute use case
            response = await self.calculate_risk_metrics_use_case.execute(domain_request)
            
            if response.success:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "data": {
                            "risk_metrics": {
                                "risk_score": response.risk_metrics.risk_score,
                                "risk_category": response.risk_metrics.get_risk_category(),
                                "var_95": float(response.risk_metrics.var_95),
                                "var_99": float(response.risk_metrics.var_99),
                                "expected_shortfall": float(response.risk_metrics.expected_shortfall),
                                "volatility": response.risk_metrics.volatility,
                                "beta": response.risk_metrics.beta,
                                "position_sizing_factor": response.risk_metrics.calculate_position_sizing_factor(),
                                "requires_validation": response.risk_metrics.requires_additional_validation()
                            } if response.risk_metrics else None,
                            "portfolio_var": {
                                key: float(value) for key, value in response.portfolio_var.items()
                            } if response.portfolio_var else None,
                            "correlation_matrix": response.correlation_matrix,
                            "risk_recommendations": response.risk_recommendations or []
                        },
                        "message": response.message,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "message": response.message,
                            "code": "RISK_CALCULATION_FAILED"
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in calculate_risk_metrics endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # =============================================================================
    # HEALTH AND STATUS ENDPOINTS
    # =============================================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Controller health check
        
        Returns:
            Dictionary with controller health status
        """
        return {
            "status": "healthy",
            "controller": "MLAnalyticsController",
            "version": "6.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "use_cases_initialized": {
                "train_model": self.train_model_use_case is not None,
                "evaluate_model": self.evaluate_model_use_case is not None,
                "retrain_models": self.retrain_models_use_case is not None,
                "generate_prediction": self.generate_prediction_use_case is not None,
                "batch_prediction": self.batch_prediction_use_case is not None,
                "prediction_history": self.get_prediction_history_use_case is not None,
                "risk_metrics": self.calculate_risk_metrics_use_case is not None
            }
        }