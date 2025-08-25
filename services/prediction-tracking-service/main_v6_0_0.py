#!/usr/bin/env python3
"""
Prediction Tracking Service - Clean Architecture v6.0.0 Main Application
FastAPI Service Entry Point

CLEAN ARCHITECTURE - COMPOSITION ROOT:
- Dependency injection container configuration
- FastAPI application setup and routing
- Service lifecycle management

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Clean Architecture Imports
from .infrastructure.container import container
from .presentation.controllers.prediction_controller import PredictionController
from .presentation.models.prediction_models import (
    PredictionListRequest,
    PerformanceComparisonRequest,
    EvaluationRequest,
    StoreResponse,
    PerformanceComparisonResponse,
    StatisticsResponse,
    EvaluationResponse,
    TrendsResponse,
    HealthResponse,
    ErrorResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Manages startup and shutdown procedures
    """
    # Startup
    logger.info("Prediction Tracking Service v6.0.0 starting up...")
    
    # Initialize container with configuration
    container.configure({
        'database_path': 'predictions.db',
        'use_real_provider': True,
        'profit_engine_host': '10.1.1.174',
        'profit_engine_port': 8025,
        'event_publishing_enabled': True,
        'accuracy_threshold': 5.0,
        'provider_timeout': 10
    })
    
    # Pre-populate some test data for development
    controller = container.get_controller()
    
    # Create sample predictions for testing
    test_predictions = [
        {'symbol': 'AAPL', 'timeframe': 'weekly', 'predicted_return': 8.5},
        {'symbol': 'GOOGL', 'timeframe': 'monthly', 'predicted_return': 12.3},
        {'symbol': 'MSFT', 'timeframe': 'weekly', 'predicted_return': 9.8},
    ]
    
    try:
        await controller.store_predictions(test_predictions, source="startup_initialization")
        logger.info("Pre-populated test predictions for development")
    except Exception as e:
        logger.warning(f"Failed to pre-populate test data: {e}")
    
    # Schedule background tasks
    asyncio.create_task(periodic_evaluation_task())
    
    logger.info("Prediction Tracking Service v6.0.0 startup complete")
    
    yield
    
    # Shutdown
    logger.info("Prediction Tracking Service v6.0.0 shutting down...")
    container.reset()
    logger.info("Prediction Tracking Service v6.0.0 shutdown complete")


async def periodic_evaluation_task():
    """
    Background task to periodically evaluate predictions
    """
    while True:
        try:
            # Wait 5 minutes between evaluation runs
            await asyncio.sleep(300)
            
            controller = container.get_controller()
            result = await controller.evaluate_predictions(days_old=1)
            
            if result.get('success') and result.get('evaluated_count', 0) > 0:
                logger.info(f"Background evaluation: {result['evaluated_count']} predictions evaluated")
            
        except Exception as e:
            logger.error(f"Background evaluation task error: {e}")


# Create FastAPI application
app = FastAPI(
    title="Prediction Tracking Service",
    description="Clean Architecture v6.0.0 - Stock Prediction Performance Tracking",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for private development environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private use - relaxed CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_controller() -> PredictionController:
    """
    Dependency injection for controller
    
    Returns:
        PredictionController instance from DI container
    """
    return container.get_controller()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """
    Global exception handler for unhandled errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


# === API ENDPOINTS ===

@app.get("/", response_model=HealthResponse)
async def root():
    """
    Root endpoint with service information
    """
    return {
        "success": True,
        "data": {
            "service": "Prediction Tracking Service",
            "version": "6.0.0",
            "architecture": "Clean Architecture",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "endpoints": [
                "/store-prediction",
                "/performance-comparison/{timeframe}",
                "/statistics",
                "/evaluate-predictions",
                "/trends/{timeframe}",
                "/health",
                "/docs"
            ]
        }
    }


@app.post("/store-prediction", response_model=StoreResponse)
async def store_prediction(
    prediction_data: PredictionListRequest,
    background_tasks: BackgroundTasks,
    controller: PredictionController = Depends(get_controller)
):
    """
    Store predictions for later performance tracking
    
    Args:
        prediction_data: List of predictions to store
        background_tasks: FastAPI background tasks
        controller: Injected controller instance
    
    Returns:
        Storage operation response
    """
    try:
        # Convert Pydantic models to dicts
        predictions = [pred.dict() for pred in prediction_data.predictions]
        
        result = await controller.store_predictions(
            predictions=predictions,
            source="api_endpoint"
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except ValueError as e:
        logger.error(f"Validation error in store_prediction: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in store_prediction endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/performance-comparison/{timeframe}", response_model=PerformanceComparisonResponse)
async def get_performance_comparison(
    timeframe: str,
    days_back: int = 30,
    controller: PredictionController = Depends(get_controller)
):
    """
    Get SOLL-IST performance comparison for timeframe
    
    Args:
        timeframe: Timeframe to analyze (daily, weekly, monthly, quarterly, yearly)
        days_back: How many days back to analyze
        controller: Injected controller instance
    
    Returns:
        Performance comparison response
    """
    try:
        # Validate timeframe
        valid_timeframes = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'all']
        if timeframe.lower() not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        result = await controller.get_performance_comparison(
            timeframe=timeframe.lower(),
            days_back=days_back
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_performance_comparison endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    controller: PredictionController = Depends(get_controller)
):
    """
    Get overall prediction statistics
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Service statistics response
    """
    try:
        result = await controller.get_statistics()
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error in get_statistics endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/evaluate-predictions", response_model=EvaluationResponse)
async def evaluate_predictions(
    evaluation_request: EvaluationRequest = EvaluationRequest(),
    controller: PredictionController = Depends(get_controller)
):
    """
    Evaluate pending predictions with actual returns
    
    Args:
        evaluation_request: Evaluation parameters
        controller: Injected controller instance
    
    Returns:
        Evaluation results response
    """
    try:
        result = await controller.evaluate_predictions(
            days_old=evaluation_request.days_old
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        logger.error(f"Error in evaluate_predictions endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/trends/{timeframe}", response_model=TrendsResponse)
async def get_prediction_trends(
    timeframe: str,
    days_back: int = 30,
    controller: PredictionController = Depends(get_controller)
):
    """
    Get prediction performance trends over time
    
    Args:
        timeframe: Timeframe to analyze
        days_back: How many days back to analyze
        controller: Injected controller instance
    
    Returns:
        Trend analysis response
    """
    try:
        # Validate timeframe
        valid_timeframes = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
        if timeframe.lower() not in valid_timeframes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        result = await controller.get_prediction_trends(
            timeframe=timeframe.lower(),
            days_back=days_back
        )
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_prediction_trends endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthResponse)
async def health_check(
    controller: PredictionController = Depends(get_controller)
):
    """
    Comprehensive service health check
    
    Args:
        controller: Injected controller instance
    
    Returns:
        Health check response
    """
    try:
        # Get controller health
        controller_health = await controller.health_check()
        
        # Get container health
        container_health = await container.health_check()
        
        return {
            "success": True,
            "data": {
                "service": "Prediction Tracking Service",
                "version": "6.0.0",
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "controller": controller_health['data'],
                    "container": container_health
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in health_check endpoint: {e}")
        return {
            "success": False,
            "error": {
                "message": "Health check failed",
                "code": "HEALTH_CHECK_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        }


# === DEVELOPMENT ENDPOINTS ===

@app.get("/dev/container-status")
async def get_container_status():
    """
    Get detailed container status (development only)
    """
    return await container.health_check()


@app.post("/dev/reset-service")
async def reset_service():
    """
    Reset service state (development only)
    """
    try:
        container.reset()
        
        # Re-configure
        container.configure({
            'database_path': 'predictions.db',
            'use_real_provider': True,
            'event_publishing_enabled': True
        })
        
        return {
            "success": True,
            "message": "Prediction Tracking Service reset successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting service: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset service")


@app.get("/dev/events")
async def get_recent_events(limit: int = 20):
    """
    Get recent events for debugging (development only)
    """
    try:
        event_publisher = container.get_event_publisher()
        if event_publisher:
            events = await event_publisher.get_published_events(limit=limit)
            return {
                "success": True,
                "events": events,
                "count": len(events)
            }
        else:
            return {
                "success": False,
                "message": "Event publisher not available"
            }
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get events")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_v6_0_0:app",
        host="0.0.0.0",
        port=8018,
        reload=True,
        log_level="info"
    )