#!/usr/bin/env python3
"""
ML Analytics Service v6.1.0 - PostgreSQL Clean Architecture FastAPI Application
Machine Learning Analytics with PostgreSQL Database Integration

PRESENTATION LAYER - FASTAPI APPLICATION:
- RESTful API endpoints for ML analytics
- PostgreSQL database integration via Database Manager
- Async request handling and dependency injection
- Comprehensive error handling and validation
- Health monitoring and service status

CLEAN ARCHITECTURE LAYERS:
- Presentation: FastAPI routes and HTTP handling
- Application: Use cases orchestration
- Domain: Business logic and entities
- Infrastructure: Database and external services

DATABASE FEATURES:
- PostgreSQL with connection pooling
- ACID transactions and consistency
- Advanced indexing and query optimization
- Centralized connection management

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add shared modules to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from error_handling_framework_v1_0_0_20250825 import (
    create_exception_handlers,
    setup_error_logging,
    global_error_handler
)

# Add infrastructure container to path
from infrastructure.container_v6_1_0 import get_container, initialize_container, shutdown_container

# Import DTOs from presentation layer
from presentation.dtos.ml_request_dtos import (
    TrainModelRequest,
    PredictionRequest,
    BatchPredictionRequest,
    RiskAnalysisRequest,
    ModelEvaluationRequest
)
from presentation.dtos.ml_response_dtos import (
    MLModelResponse,
    PredictionResponse,
    BatchPredictionResponse,
    RiskMetricsResponse,
    ModelEvaluationResponse,
    HealthStatusResponse,
    MLAnalyticsStatsResponse
)

# Import domain exceptions
from domain.exceptions.ml_exceptions import (
    MLModelNotFoundError,
    MLTrainingError,
    MLPredictionError,
    MLValidationError
)


# Configure structured logging with Error Framework
setup_error_logging(
    service_name="ml-analytics-service",
    log_file_path='/opt/aktienanalyse-ökosystem/logs/ml-analytics-service.log'
)

logger = logging.getLogger(__name__)


# =============================================================================
# APPLICATION LIFECYCLE MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI application lifespan manager for PostgreSQL initialization
    
    Handles startup and shutdown of all services including Database Manager.
    """
    try:
        logger.info("Starting ML Analytics Service v6.1.0 (PostgreSQL)...")
        
        # Load configuration for PostgreSQL
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "aktienanalyse",
                "user": "aktienanalyse_user",
                "password": "",  # Will be loaded from environment
                "min_connections": 5,
                "max_connections": 20,
                "connection_timeout": 30,
                "command_timeout": 60
            },
            "ml_services": {
                "model_storage_path": "/opt/aktienanalyse-ökosystem/models/ml-analytics",
                "use_mock_providers": True,
                "enable_gpu_acceleration": False,
                "max_concurrent_trainings": 3,
                "feature_cache_size": 1000,
                "prediction_cache_ttl_minutes": 15
            },
            "events": {
                "enabled": True,
                "event_bus_url": "http://10.1.1.174:8014",
                "batch_size": 10,
                "flush_interval_seconds": 5,
                "max_retry_attempts": 3
            }
        }
        
        # Initialize container with PostgreSQL
        success = await initialize_container(config)
        if not success:
            raise RuntimeError("Failed to initialize ML Analytics Service container")
        
        logger.info("ML Analytics Service v6.1.0 started successfully (PostgreSQL)")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start ML Analytics Service: {str(e)}")
        raise
    finally:
        logger.info("Shutting down ML Analytics Service v6.1.0...")
        await shutdown_container()
        logger.info("ML Analytics Service v6.1.0 shutdown complete")


# =============================================================================
# FASTAPI APPLICATION INITIALIZATION
# =============================================================================

app = FastAPI(
    title="ML Analytics Service",
    description="Machine Learning Analytics Service with PostgreSQL Integration - Clean Architecture v6.1.0",
    version="6.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    exception_handlers=create_exception_handlers()
)

# Add CORS middleware for private development environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private development - permissive CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_ml_controller():
    """Dependency injection for ML Analytics Controller"""
    container = get_container()
    if not container.is_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML Analytics Service not initialized"
        )
    return container.get_controller()


# =============================================================================
# ERROR HANDLERS - Managed by Shared Error Framework
# =============================================================================
# Error handling is now managed by the shared error framework
# All ML exceptions inherit from BaseServiceError and are handled automatically


# =============================================================================
# HEALTH AND STATUS ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthStatusResponse, tags=["Health"])
async def health_check():
    """
    Comprehensive health check including PostgreSQL Database Manager status
    
    Returns:
        Health status of all service components including database connections
    """
    try:
        container = get_container()
        health_status = await container.get_health_status()
        
        return HealthStatusResponse(
            status="healthy" if container.is_initialized() else "unhealthy",
            version="6.1.0",
            database_type="PostgreSQL",
            components=health_status,
            timestamp=health_status.get("container", {}).get("initialization_time")
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/status", response_model=MLAnalyticsStatsResponse, tags=["Status"])
async def service_status(controller = Depends(get_ml_controller)):
    """
    Get ML Analytics service statistics and PostgreSQL database metrics
    
    Returns:
        Service statistics including model counts, prediction metrics, and database status
    """
    try:
        stats = await controller.get_service_statistics()
        return MLAnalyticsStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )


# =============================================================================
# ML MODEL TRAINING ENDPOINTS
# =============================================================================

@app.post("/models/train", response_model=MLModelResponse, tags=["ML Training"])
async def train_model(
    request: TrainModelRequest,
    controller = Depends(get_ml_controller)
):
    """
    Train new ML model with specified parameters
    
    Trains and stores model in PostgreSQL database with full metadata tracking.
    """
    try:
        result = await controller.train_model(
            symbol=request.symbol,
            model_type=request.model_type,
            features=request.features,
            target=request.target,
            hyperparameters=request.hyperparameters,
            training_data_start=request.training_data_start,
            training_data_end=request.training_data_end
        )
        return MLModelResponse(**result)
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )

@app.post("/models/{model_id}/evaluate", response_model=ModelEvaluationResponse, tags=["ML Training"])
async def evaluate_model(
    model_id: str,
    request: ModelEvaluationRequest,
    controller = Depends(get_ml_controller)
):
    """
    Evaluate trained ML model performance
    
    Evaluates model against test data and stores results in PostgreSQL.
    """
    try:
        result = await controller.evaluate_model(
            model_id=model_id,
            test_data_start=request.test_data_start,
            test_data_end=request.test_data_end,
            metrics=request.metrics
        )
        return ModelEvaluationResponse(**result)
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model evaluation failed: {str(e)}"
        )

@app.post("/models/retrain", response_model=List[MLModelResponse], tags=["ML Training"])
async def retrain_outdated_models(controller = Depends(get_ml_controller)):
    """
    Retrain all outdated models based on configured thresholds
    
    Identifies and retrains models requiring updates based on performance metrics.
    """
    try:
        results = await controller.retrain_outdated_models()
        return [MLModelResponse(**result) for result in results]
    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining failed: {str(e)}"
        )


# =============================================================================
# ML PREDICTION ENDPOINTS
# =============================================================================

@app.post("/predictions/generate", response_model=PredictionResponse, tags=["ML Predictions"])
async def generate_prediction(
    request: PredictionRequest,
    controller = Depends(get_ml_controller)
):
    """
    Generate ML prediction for specified symbol and timeframe
    
    Uses best available model to generate predictions stored in PostgreSQL.
    """
    try:
        result = await controller.generate_prediction(
            symbol=request.symbol,
            model_type=request.model_type,
            prediction_horizon=request.prediction_horizon,
            features=request.features,
            confidence_threshold=request.confidence_threshold
        )
        return PredictionResponse(**result)
    except Exception as e:
        logger.error(f"Prediction generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction generation failed: {str(e)}"
        )

@app.post("/predictions/batch", response_model=BatchPredictionResponse, tags=["ML Predictions"])
async def batch_predictions(
    request: BatchPredictionRequest,
    controller = Depends(get_ml_controller)
):
    """
    Generate batch predictions for multiple symbols
    
    Efficiently processes multiple symbols using optimized PostgreSQL queries.
    """
    try:
        result = await controller.generate_batch_predictions(
            symbols=request.symbols,
            model_type=request.model_type,
            prediction_horizon=request.prediction_horizon,
            features=request.features
        )
        return BatchPredictionResponse(**result)
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )

@app.get("/predictions/{symbol}/history", response_model=List[PredictionResponse], tags=["ML Predictions"])
async def get_prediction_history(
    symbol: str,
    limit: int = 100,
    controller = Depends(get_ml_controller)
):
    """
    Get historical predictions for symbol from PostgreSQL database
    
    Returns paginated prediction history with full metadata.
    """
    try:
        results = await controller.get_prediction_history(
            symbol=symbol,
            limit=limit
        )
        return [PredictionResponse(**result) for result in results]
    except Exception as e:
        logger.error(f"Prediction history retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction history retrieval failed: {str(e)}"
        )


# =============================================================================
# RISK ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/risk/analyze", response_model=RiskMetricsResponse, tags=["Risk Analysis"])
async def analyze_risk(
    request: RiskAnalysisRequest,
    controller = Depends(get_ml_controller)
):
    """
    Calculate comprehensive risk metrics for portfolio
    
    Advanced risk analysis using multiple ML models and PostgreSQL storage.
    """
    try:
        result = await controller.calculate_risk_metrics(
            symbols=request.symbols,
            positions=request.positions,
            risk_models=request.risk_models,
            time_horizon=request.time_horizon,
            confidence_level=request.confidence_level
        )
        return RiskMetricsResponse(**result)
    except Exception as e:
        logger.error(f"Risk analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk analysis failed: {str(e)}"
        )


# =============================================================================
# MODEL MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/models", response_model=List[MLModelResponse], tags=["Model Management"])
async def list_models(controller = Depends(get_ml_controller)):
    """
    List all available ML models from PostgreSQL database
    
    Returns comprehensive model metadata including performance metrics.
    """
    try:
        results = await controller.list_models()
        return [MLModelResponse(**result) for result in results]
    except Exception as e:
        logger.error(f"Model listing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model listing failed: {str(e)}"
        )

@app.get("/models/{model_id}", response_model=MLModelResponse, tags=["Model Management"])
async def get_model(model_id: str, controller = Depends(get_ml_controller)):
    """
    Get specific ML model details from PostgreSQL
    
    Returns full model metadata and performance history.
    """
    try:
        result = await controller.get_model(model_id=model_id)
        return MLModelResponse(**result)
    except MLModelNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )
    except Exception as e:
        logger.error(f"Model retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retrieval failed: {str(e)}"
        )

@app.delete("/models/{model_id}", tags=["Model Management"])
async def delete_model(model_id: str, controller = Depends(get_ml_controller)):
    """
    Delete ML model from PostgreSQL database
    
    Removes model and all associated metadata while preserving prediction history.
    """
    try:
        await controller.delete_model(model_id=model_id)
        return {"message": f"Model {model_id} deleted successfully"}
    except MLModelNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )
    except Exception as e:
        logger.error(f"Model deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model deletion failed: {str(e)}"
        )


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting ML Analytics Service v6.1.0 with PostgreSQL...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8016,
        log_level="info",
        reload=False
    )