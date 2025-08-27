#!/usr/bin/env python3
"""
ML Analytics Service v6.1.1 - Standardized API Clean Architecture FastAPI Application
Machine Learning Analytics with PostgreSQL Database Integration and API Standards

PRESENTATION LAYER - FASTAPI APPLICATION:
- Standardized RESTful API endpoints with consistent patterns
- PostgreSQL database integration via Database Manager
- Async request handling and dependency injection
- Comprehensive error handling via Error Framework
- API Standards compliance and OpenAPI documentation

CLEAN ARCHITECTURE LAYERS:
- Presentation: FastAPI routes with standard API patterns
- Application: Use cases orchestration
- Domain: Business logic and entities
- Infrastructure: Database and external services

API STANDARDS:
- Consistent URL structure: /api/v1/resource
- Standard request/response models with metadata
- Unified error handling and status codes
- OpenAPI/Swagger documentation compliance
- Pagination, filtering, and sorting support

DATABASE FEATURES:
- PostgreSQL with connection pooling
- ACID transactions and consistency
- Advanced indexing and query optimization
- Centralized connection management

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.1 - API Standards Integration
"""

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add shared modules to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from error_handling_framework_v1_0_0_20250825 import (
    create_exception_handlers,
    setup_error_logging,
    global_error_handler
)
from api_standards_framework_v1_0_0_20250825 import (
    APIStandards,
    APIDocumentationStandards,
    apply_api_standards_to_app,
    StandardItemResponse,
    StandardListResponse,
    StandardMetadata,
    StandardHealthResponse,
    PaginationRequest
)
from service_api_patterns_v1_0_0_20250825 import (
    ServiceAPIPatternFactory,
    MLTrainingRequest,
    MLPredictionRequest,
    MLBatchPredictionRequest,
    MLEvaluationRequest
)

# Add infrastructure container to path
from infrastructure.container_v6_1_0 import get_container, initialize_container, shutdown_container

# Import DTOs from presentation layer
from presentation.dtos.ml_response_dtos import (
    MLModelResponse,
    PredictionResponse,
    BatchPredictionResponse,
    RiskMetricsResponse,
    ModelEvaluationResponse,
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
    start_time = time.time()
    try:
        logger.info("Starting ML Analytics Service v6.1.1 (PostgreSQL + API Standards)...")
        
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
        
        # Store startup time for metrics
        app.state.startup_time = start_time
        
        logger.info("ML Analytics Service v6.1.1 started successfully (PostgreSQL + API Standards)")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start ML Analytics Service: {str(e)}")
        raise
    finally:
        logger.info("Shutting down ML Analytics Service v6.1.1...")
        await shutdown_container()
        logger.info("ML Analytics Service v6.1.1 shutdown complete")


# =============================================================================
# FASTAPI APPLICATION INITIALIZATION
# =============================================================================

# API Standards Configuration
api_standards = APIStandards(
    version_strategy="url_path",
    current_version="v1",
    base_path="/api",
    default_page_size=20,
    max_page_size=100
)

app = FastAPI(
    title="ML Analytics Service API",
    description="Machine Learning Analytics Service with PostgreSQL Integration and API Standards - Clean Architecture v6.1.1",
    version="6.1.1",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    exception_handlers=create_exception_handlers(),
    openapi_tags=APIDocumentationStandards.get_tag_metadata([
        "ml-training", "ml-predictions", "risk-analysis", "model-management"
    ])
)

# Apply API standards to the application
apply_api_standards_to_app(
    app,
    service_name="ml-analytics-service",
    version="6.1.1",
    description="Advanced ML Analytics with PostgreSQL and standardized API patterns"
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

def get_processing_time(start_time: float = None) -> float:
    """Calculate processing time in milliseconds"""
    if start_time is None:
        return None
    return round((time.time() - start_time) * 1000, 2)


# =============================================================================
# STANDARD HEALTH AND STATUS ENDPOINTS
# =============================================================================

@app.get("/health", response_model=StandardHealthResponse, tags=["Health"])
async def health_check():
    """
    Comprehensive health check including PostgreSQL Database Manager status
    
    Returns:
        Health status of all service components including database connections
    """
    try:
        container = get_container()
        health_status = await container.get_health_status()
        
        return StandardHealthResponse(
            status="healthy" if container.is_initialized() else "unhealthy",
            version="6.1.1",
            timestamp=health_status.get("container", {}).get("initialization_time"),
            database=health_status.get("database_manager"),
            dependencies=health_status.get("ml_services"),
            metrics=health_status.get("event_publisher")
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/api/v1/status", response_model=StandardItemResponse, tags=["Status"])
async def service_status(controller = Depends(get_ml_controller)):
    """
    Get ML Analytics service statistics and PostgreSQL database metrics
    
    Returns:
        Service statistics including model counts, prediction metrics, and database status
    """
    start_time = time.time()
    try:
        stats = await controller.get_service_statistics()
        
        # Add uptime calculation
        uptime_seconds = time.time() - app.state.startup_time
        stats["uptime_seconds"] = uptime_seconds
        
        return StandardItemResponse(
            data=stats,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )


# =============================================================================
# ML TRAINING ENDPOINTS (Standardized API Pattern)
# =============================================================================

@app.post("/api/v1/models/train", response_model=StandardItemResponse, tags=["ML Training"])
async def train_model(
    request: MLTrainingRequest,
    background_tasks: BackgroundTasks,
    controller = Depends(get_ml_controller)
):
    """
    Train new ML model with specified parameters
    
    Trains and stores model in PostgreSQL database with full metadata tracking.
    Uses background tasks for long-running training operations.
    """
    start_time = time.time()
    try:
        # Convert standardized request to controller format
        result = await controller.train_model(
            symbol=request.symbol,
            model_type=request.model_type,
            features=request.features,
            target=request.target,
            hyperparameters=request.hyperparameters,
            training_data_start=request.training_data_start,
            training_data_end=request.training_data_end
        )
        
        return StandardItemResponse(
            data=result,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model training failed: {str(e)}"
        )

@app.post("/api/v1/models/{model_id}/evaluate", response_model=StandardItemResponse, tags=["ML Training"])
async def evaluate_model(
    model_id: str,
    request: MLEvaluationRequest,
    controller = Depends(get_ml_controller)
):
    """
    Evaluate trained ML model performance
    
    Evaluates model against test data and stores results in PostgreSQL.
    """
    start_time = time.time()
    try:
        result = await controller.evaluate_model(
            model_id=model_id,
            test_data_start=request.test_data_start,
            test_data_end=request.test_data_end,
            metrics=request.metrics
        )
        
        return StandardItemResponse(
            data=result,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model evaluation failed: {str(e)}"
        )

@app.post("/api/v1/models/retrain", response_model=StandardItemResponse, tags=["ML Training"])
async def retrain_outdated_models(
    background_tasks: BackgroundTasks,
    controller = Depends(get_ml_controller)
):
    """
    Retrain all outdated models based on configured thresholds
    
    Identifies and retrains models requiring updates based on performance metrics.
    """
    start_time = time.time()
    try:
        results = await controller.retrain_outdated_models()
        
        return StandardItemResponse(
            data={"retrained_models": results, "count": len(results)},
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model retraining failed: {str(e)}"
        )


# =============================================================================
# ML PREDICTION ENDPOINTS (Standardized API Pattern)
# =============================================================================

@app.post("/api/v1/predictions/generate", response_model=StandardItemResponse, tags=["ML Predictions"])
async def generate_prediction(
    request: MLPredictionRequest,
    controller = Depends(get_ml_controller)
):
    """
    Generate ML prediction for specified symbol and timeframe
    
    Uses best available model to generate predictions stored in PostgreSQL.
    """
    start_time = time.time()
    try:
        result = await controller.generate_prediction(
            symbol=request.symbol,
            model_type=request.model_type,
            prediction_horizon=request.prediction_horizon,
            features=request.features,
            confidence_threshold=request.confidence_threshold
        )
        
        return StandardItemResponse(
            data=result,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Prediction generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction generation failed: {str(e)}"
        )

@app.post("/api/v1/predictions/batch", response_model=StandardItemResponse, tags=["ML Predictions"])
async def batch_predictions(
    request: MLBatchPredictionRequest,
    controller = Depends(get_ml_controller)
):
    """
    Generate batch predictions for multiple symbols
    
    Efficiently processes multiple symbols using optimized PostgreSQL queries.
    """
    start_time = time.time()
    try:
        result = await controller.generate_batch_predictions(
            symbols=request.symbols,
            model_type=request.model_type,
            prediction_horizon=request.prediction_horizon,
            features=request.features
        )
        
        return StandardItemResponse(
            data=result,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )

@app.get("/api/v1/predictions/{symbol}/history", response_model=StandardListResponse, tags=["ML Predictions"])
async def get_prediction_history(
    symbol: str,
    pagination: PaginationRequest = Depends(),
    controller = Depends(get_ml_controller)
):
    """
    Get historical predictions for symbol from PostgreSQL database
    
    Returns paginated prediction history with full metadata.
    """
    start_time = time.time()
    try:
        results = await controller.get_prediction_history(
            symbol=symbol,
            page=pagination.page,
            size=pagination.size
        )
        
        return StandardListResponse(
            data=results.get("predictions", []),
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            ),
            pagination=results.get("pagination")
        )
    except Exception as e:
        logger.error(f"Prediction history retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction history retrieval failed: {str(e)}"
        )


# =============================================================================
# MODEL MANAGEMENT ENDPOINTS (Standardized API Pattern)
# =============================================================================

@app.get("/api/v1/models", response_model=StandardListResponse, tags=["Model Management"])
async def list_models(
    pagination: PaginationRequest = Depends(),
    controller = Depends(get_ml_controller)
):
    """
    List all available ML models from PostgreSQL database
    
    Returns comprehensive model metadata including performance metrics.
    """
    start_time = time.time()
    try:
        results = await controller.list_models(
            page=pagination.page,
            size=pagination.size
        )
        
        return StandardListResponse(
            data=results.get("models", []),
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            ),
            pagination=results.get("pagination")
        )
    except Exception as e:
        logger.error(f"Model listing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model listing failed: {str(e)}"
        )

@app.get("/api/v1/models/{model_id}", response_model=StandardItemResponse, tags=["Model Management"])
async def get_model(model_id: str, controller = Depends(get_ml_controller)):
    """
    Get specific ML model details from PostgreSQL
    
    Returns full model metadata and performance history.
    """
    start_time = time.time()
    try:
        result = await controller.get_model(model_id=model_id)
        
        return StandardItemResponse(
            data=result,
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
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

@app.delete("/api/v1/models/{model_id}", response_model=StandardItemResponse, tags=["Model Management"])
async def delete_model(model_id: str, controller = Depends(get_ml_controller)):
    """
    Delete ML model from PostgreSQL database
    
    Removes model and all associated metadata while preserving prediction history.
    """
    start_time = time.time()
    try:
        await controller.delete_model(model_id=model_id)
        
        return StandardItemResponse(
            data={"message": f"Model {model_id} deleted successfully", "model_id": model_id},
            metadata=StandardMetadata(
                service="ml-analytics-service",
                version="6.1.1",
                processing_time_ms=get_processing_time(start_time)
            )
        )
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
    logger.info("Starting ML Analytics Service v6.1.1 with PostgreSQL and API Standards...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8016,
        log_level="info",
        reload=False
    )