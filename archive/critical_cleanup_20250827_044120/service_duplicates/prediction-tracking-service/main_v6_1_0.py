#!/usr/bin/env python3
"""
Prediction Tracking Service - FastAPI Application v6.1.0
Clean Architecture Implementation mit PostgreSQL Migration

CLEAN ARCHITECTURE v6.1.0 LAYERS:
✅ Domain Layer: Business Logic, Entities, Value Objects, Repository Interfaces
✅ Application Layer: Use Cases, Service Interfaces, Business Rules Orchestration  
✅ Infrastructure Layer: PostgreSQL Database Manager, External APIs, Event Publishing
✅ Presentation Layer: FastAPI Controllers, Request/Response Models, HTTP Handling

MIGRATION v6.0.0 → v6.1.0:
- SQLite Repository zu PostgreSQL Repository Migration
- Central Database Manager Integration (database_connection_manager_v1_0_0_20250825)
- Connection Pool Management für Performance
- Schema Auto-Initialization

ARCHITECTURE COMPLIANCE v6.1.0:
✅ SOLID Principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
✅ Dependency Injection: Centralized Container mit PostgreSQL Database Manager
✅ Event-Driven Pattern: Domain Events, Event Publishing, Event-Bus Integration
✅ Repository Pattern: Data Access Abstraction mit PostgreSQL Implementation
✅ Use Case Pattern: Single-purpose Application Logic Orchestration

FEATURES v6.1.0:
- Prediction Storage and Retrieval (PostgreSQL)
- Performance Analysis and Comparison
- Automated Prediction Evaluation
- Comprehensive Health Checks mit Database Manager Status
- FastAPI REST API mit OpenAPI Documentation
- Background Tasks für Long-running Operations
- Event Publishing für System Integration
- Connection Pool Health Monitoring

Code-Qualität: HÖCHSTE PRIORITÄT - Architecture Refactoring Specialist
Autor: Claude Code - Clean Architecture Implementation
Datum: 25. August 2025
Version: 6.1.0 (PostgreSQL Migration)
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add shared modules to path for Error Framework
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from error_handling_framework_v1_0_0_20250825 import (
    create_exception_handlers,
    setup_error_logging,
    global_error_handler
)

# Configure structured logging with Error Framework
setup_error_logging(
    service_name="prediction-tracking-service",
    log_file_path='/tmp/prediction_tracking_service.log'
)

logger = logging.getLogger(__name__)

# Import Clean Architecture Components
from infrastructure.container_v6_1_0 import PredictionTrackingDIContainer
from presentation.models.prediction_models import (
    StorePredictionRequestDTO,
    StorePredictionResponseDTO,
    GetPerformanceRequestDTO,
    GetPerformanceResponseDTO,
    GetStatisticsResponseDTO,
    EvaluatePredictionsRequestDTO,
    EvaluatePredictionsResponseDTO,
    HealthCheckResponseDTO
)


# Global container instance
container = PredictionTrackingDIContainer()


async def initialize_service() -> bool:
    """
    Initialize service with database manager and schema
    
    Returns:
        True if service initialized successfully
    """
    try:
        logger.info("Initializing Prediction Tracking Service v6.1.0...")
        
        # Initialize container with database manager
        success = await container.initialize()
        if not success:
            logger.error("Failed to initialize service container")
            return False
        
        # Verify database connection
        db_manager = container.get_database_manager()
        health = await db_manager.health_check()
        if not health.get('healthy', False):
            logger.error(f"Database manager unhealthy: {health}")
            return False
            
        logger.info("Prediction Tracking Service v6.1.0 initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return False


async def shutdown_service():
    """Graceful service shutdown"""
    try:
        logger.info("Shutting down Prediction Tracking Service...")
        
        # Shutdown container and cleanup resources
        await container.shutdown()
        
        logger.info("Prediction Tracking Service shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during service shutdown: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    # Startup
    logger.info("Starting up Prediction Tracking Service v6.1.0...")
    
    success = await initialize_service()
    if not success:
        logger.error("Failed to initialize service - startup aborted")
        sys.exit(1)
    
    logger.info("Prediction Tracking Service v6.1.0 startup completed")
    
    yield
    
    # Shutdown
    await shutdown_service()


# FastAPI application with Clean Architecture
app = FastAPI(
    title="Prediction Tracking Service",
    description="Clean Architecture Implementation v6.1.0 - PostgreSQL Migration with Error Framework",
    version="6.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    exception_handlers=create_exception_handlers()
)

# CORS middleware for development/private usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Private environment - broad CORS allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
def get_container() -> PredictionTrackingDIContainer:
    """Get container instance for dependency injection"""
    return container


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthCheckResponseDTO, 
         summary="Health Check", description="Service health status")
async def health_check(container: PredictionTrackingDIContainer = Depends(get_container)):
    """
    Health check endpoint
    
    Returns comprehensive service health including:
    - Container status
    - Database manager status
    - Repository health
    - Component status
    """
    try:
        health_status = await container.health_check()
        
        # Determine overall health
        components_healthy = all(
            comp.get('status') in ['healthy', 'disabled'] 
            for comp in health_status.get('components', {}).values()
        )
        
        overall_status = 'healthy' if components_healthy else 'degraded'
        
        return HealthCheckResponseDTO(
            status=overall_status,
            service="prediction-tracking-service",
            version="6.1.0",
            database="PostgreSQL",
            timestamp=datetime.utcnow().isoformat(),
            components=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponseDTO(
            status="unhealthy",
            service="prediction-tracking-service", 
            version="6.1.0",
            database="PostgreSQL",
            timestamp=datetime.utcnow().isoformat(),
            error=str(e)
        )


@app.get("/api/v1/status", 
         summary="Service Status", description="Detailed service status")
async def get_service_status(container: PredictionTrackingDIContainer = Depends(get_container)):
    """
    Get detailed service status
    
    Returns:
        Comprehensive service status information
    """
    try:
        health_status = await container.health_check()
        container_status = container.get_health_status()
        
        return JSONResponse({
            "service": "prediction-tracking-service",
            "version": "6.1.0",
            "architecture": "Clean Architecture",
            "database": "PostgreSQL",
            "migration": "v6.0.0 → v6.1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "container": container_status,
            "health": health_status,
            "endpoints": {
                "predictions": "/api/v1/predictions",
                "performance": "/api/v1/performance", 
                "statistics": "/api/v1/statistics",
                "evaluation": "/api/v1/evaluation",
                "health": "/health",
                "docs": "/docs"
            }
        })
        
    except Exception as e:
        logger.error(f"Status endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================

@app.post("/api/v1/predictions/store", response_model=StorePredictionResponseDTO,
          summary="Store Prediction", description="Store a new prediction")
async def store_prediction(
    request: StorePredictionRequestDTO,
    background_tasks: BackgroundTasks,
    container: PredictionTrackingDIContainer = Depends(get_container)
):
    """
    Store a new prediction
    
    Args:
        request: Prediction data to store
        background_tasks: FastAPI background tasks
        
    Returns:
        StorePredictionResponseDTO with operation result
    """
    try:
        controller = container.get_controller()
        
        # Execute use case through controller
        result = await controller.store_prediction(request, background_tasks)
        
        if result.get("success", False):
            return StorePredictionResponseDTO(
                success=True,
                prediction_id=result["prediction_id"],
                message="Prediction stored successfully"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=result.get("error", "Failed to store prediction")
            )
            
    except Exception as e:
        logger.error(f"Store prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Store prediction failed: {str(e)}")


@app.post("/api/v1/performance/compare", response_model=GetPerformanceResponseDTO,
          summary="Performance Comparison", description="Get performance comparison")
async def get_performance_comparison(
    request: GetPerformanceRequestDTO,
    container: PredictionTrackingDIContainer = Depends(get_container)
):
    """
    Get performance comparison analysis
    
    Args:
        request: Performance comparison parameters
        
    Returns:
        GetPerformanceResponseDTO with analysis results
    """
    try:
        controller = container.get_controller()
        
        # Execute use case through controller
        result = await controller.get_performance_comparison(request)
        
        return GetPerformanceResponseDTO(
            success=True,
            data=result,
            message="Performance comparison completed"
        )
        
    except Exception as e:
        logger.error(f"Performance comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Performance comparison failed: {str(e)}")


@app.get("/api/v1/statistics", response_model=GetStatisticsResponseDTO,
         summary="Get Statistics", description="Get prediction statistics")
async def get_statistics(container: PredictionTrackingDIContainer = Depends(get_container)):
    """
    Get prediction statistics
    
    Returns:
        GetStatisticsResponseDTO with statistics
    """
    try:
        controller = container.get_controller()
        
        # Execute use case through controller
        result = await controller.get_statistics()
        
        return GetStatisticsResponseDTO(
            success=True,
            statistics=result,
            message="Statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get statistics failed: {str(e)}")


@app.post("/api/v1/evaluation/evaluate", response_model=EvaluatePredictionsResponseDTO,
          summary="Evaluate Predictions", description="Evaluate prediction accuracy")
async def evaluate_predictions(
    request: EvaluatePredictionsRequestDTO,
    background_tasks: BackgroundTasks,
    container: PredictionTrackingDIContainer = Depends(get_container)
):
    """
    Evaluate prediction accuracy
    
    Args:
        request: Evaluation parameters
        background_tasks: FastAPI background tasks
        
    Returns:
        EvaluatePredictionsResponseDTO with evaluation results
    """
    try:
        controller = container.get_controller()
        
        # Execute use case through controller
        result = await controller.evaluate_predictions(request, background_tasks)
        
        return EvaluatePredictionsResponseDTO(
            success=True,
            evaluated_count=result.get("evaluated_count", 0),
            message="Predictions evaluated successfully"
        )
        
    except Exception as e:
        logger.error(f"Evaluate predictions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evaluate predictions failed: {str(e)}")


# =============================================================================
# DEVELOPMENT ENDPOINTS
# =============================================================================

@app.get("/api/v1/dev/database-status",
         summary="Database Status", description="Database manager status")
async def get_database_status(container: PredictionTrackingDIContainer = Depends(get_container)):
    """Get database manager status for development/debugging"""
    try:
        db_manager = container.get_database_manager()
        health = await db_manager.health_check()
        
        return JSONResponse({
            "database_manager": {
                "type": "centralized_postgresql",
                "version": "v1.0.0",
                "health": health,
                "connection_pool": health.get("connection_pool", {}),
                "configuration": health.get("configuration", {})
            },
            "repository": {
                "type": "PostgreSQL",
                "migration": "SQLite → PostgreSQL",
                "schema_initialized": True
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database status failed: {str(e)}")


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum} - initiating graceful shutdown...")
    # FastAPI lifespan will handle the actual cleanup


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    
    logger.info("Starting Prediction Tracking Service v6.1.0...")
    
    # Run FastAPI application
    uvicorn.run(
        "main_v6_1_0:app",
        host="0.0.0.0",
        port=8020,
        reload=False,  # Production mode
        access_log=True,
        log_level="info"
    )