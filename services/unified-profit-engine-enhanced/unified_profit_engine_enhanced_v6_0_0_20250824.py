#!/usr/bin/env python3
"""
Unified Profit Engine Enhanced v6.0.0 - Clean Architecture Implementation
Event-Driven Trading Intelligence System mit Clean Architecture Principles

CLEAN ARCHITECTURE LAYERS:
✅ Domain Layer: Business Logic, Entities, Value Objects, Domain Events
✅ Application Layer: Use Cases, Service Interfaces, Business Rules Orchestration  
✅ Infrastructure Layer: Database, External APIs, Event Publishing, Data Persistence
✅ Presentation Layer: FastAPI Controllers, Request/Response Models, HTTP Handling

ARCHITECTURE COMPLIANCE:
✅ SOLID Principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
✅ Dependency Injection: Centralized Container mit Interface-based Dependencies
✅ Event-Driven Pattern: Domain Events, Event Publishing, Event-Bus Integration
✅ Repository Pattern: Data Access Abstraction mit PostgreSQL Implementation
✅ Use Case Pattern: Single-purpose Application Logic Orchestration

FEATURES v6.0.0:
- Multi-Horizon Profit Predictions (1W, 1M, 3M, 12M)
- SOLL-IST Performance Tracking mit Accuracy Calculation
- Event-Driven Architecture Integration (Port 8014)
- PostgreSQL Persistence mit Advanced Views
- Yahoo Finance Market Data Integration
- Redis Event Publishing mit Event Store
- FastAPI REST API mit OpenAPI Documentation
- Comprehensive Error Handling und Logging
- Health Checks und Service Metrics

Code-Qualität: HÖCHSTE PRIORITÄT - Architecture Refactoring Specialist
Autor: Claude Code - Clean Architecture Implementation
Datum: 24. August 2025
Version: 6.0.0 (Clean Architecture Refactored)
"""

import asyncio
import logging
import signal
import sys
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Clean Architecture Imports
from container import DependencyContainer, ServiceConfiguration
from presentation.controllers import UnifiedProfitEngineController
from presentation.models import (
    MultiHorizonPredictionRequest,
    MultiHorizonPredictionResponse,
    ISTCalculationRequest,
    ISTCalculationResponse,
    PerformanceAnalysisRequest,
    PerformanceAnalysisResponse,
    HealthCheckResponse,
    ServiceMetricsResponse
)

# Global Container Instance
container: DependencyContainer = None


def setup_logging(log_level: str = "INFO"):
    """
    Centralized Logging Configuration
    
    CLEAN ARCHITECTURE: Infrastructure Concern
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='{"service": "unified-profit-engine-enhanced", "version": "6.0.0", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s", "module": "%(name)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/unified-profit-engine-enhanced-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Application Lifespan Management
    
    CLEAN ARCHITECTURE: Application Infrastructure Setup
    """
    logger = logging.getLogger(__name__)
    global container
    
    # Startup
    try:
        logger.info("🚀 Starting Unified Profit Engine Enhanced v6.0.0 - Clean Architecture")
        logger.info("📐 Architecture: Domain -> Application -> Infrastructure -> Presentation")
        
        # Initialize Configuration
        config = ServiceConfiguration()
        logger.info(f"⚙️ Configuration loaded: {config.to_dict()}")
        
        # Initialize Dependency Container
        container = DependencyContainer(config)
        await container.initialize()
        
        # Store in app state for access in routes
        app.state.container = container
        app.state.config = config
        app.state.startup_time = datetime.now()
        
        logger.info("✅ Unified Profit Engine Enhanced v6.0.0 initialized successfully")
        logger.info("🎯 Clean Architecture Layers: ✅ Domain | ✅ Application | ✅ Infrastructure | ✅ Presentation")
        logger.info(f"🌐 Service available at http://{config.service_host}:{config.service_port}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down Unified Profit Engine Enhanced v6.0.0")
    if container:
        await container.cleanup()
    logger.info("✅ Shutdown completed")


# FastAPI App Creation mit Clean Architecture Setup
config = ServiceConfiguration()
setup_logging(config.log_level)

app = FastAPI(
    title="Unified Profit Engine Enhanced v6.0",
    description="Event-Driven Trading Intelligence System mit Clean Architecture",
    version="6.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware für private Entwicklungsumgebung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für privaten Gebrauch akzeptabel (laut CLAUDE.md)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


# =============================================================================
# DEPENDENCY INJECTION HELPERS
# =============================================================================

def get_container() -> DependencyContainer:
    """Dependency Injection Helper für Container Access"""
    if not hasattr(app.state, 'container') or not app.state.container:
        raise HTTPException(status_code=503, detail="Service container not initialized")
    return app.state.container


def get_controller(container: DependencyContainer = Depends(get_container)) -> UnifiedProfitEngineController:
    """Dependency Injection Helper für Controller Access"""
    if not container.is_initialized() or not container.main_controller:
        raise HTTPException(status_code=503, detail="Service not fully initialized")
    return container.main_controller


# =============================================================================
# CLEAN ARCHITECTURE API ENDPOINTS
# =============================================================================

@app.post(
    "/api/v1/profit-engine/predictions/multi-horizon",
    response_model=MultiHorizonPredictionResponse,
    summary="Generate Multi-Horizon Profit Predictions",
    description="Generiert SOLL-Gewinn Vorhersagen für alle Horizonte (1W, 1M, 3M, 12M) basierend auf ML-Pipeline Integration"
)
async def generate_multi_horizon_predictions(
    request: MultiHorizonPredictionRequest,
    controller: UnifiedProfitEngineController = Depends(get_controller)
) -> MultiHorizonPredictionResponse:
    """
    Multi-Horizon Profit Prediction Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller (Presentation) -> Use Case (Application) -> Repository (Infrastructure) -> Domain Logic
    """
    try:
        logger.info(f"🎯 Multi-horizon prediction request: {len(request.symbols)} symbols")
        return await controller.generate_multi_horizon_predictions(request)
    except Exception as e:
        logger.error(f"❌ Multi-horizon prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/profit-engine/ist/calculate",
    response_model=ISTCalculationResponse,
    summary="Calculate IST Performance",
    description="Berechnet aktuelle IST-Performance für Symbole basierend auf Yahoo Finance Marktdaten"
)
async def calculate_ist_performance(
    request: ISTCalculationRequest,
    controller: UnifiedProfitEngineController = Depends(get_controller)
) -> ISTCalculationResponse:
    """
    IST Performance Calculation Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller -> Use Case -> Market Data Repository -> Yahoo Finance Adapter -> Domain Calculation
    """
    try:
        logger.info(f"📊 IST calculation request: {len(request.symbols)} symbols")
        return await controller.calculate_ist_performance(request)
    except Exception as e:
        logger.error(f"❌ IST calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/profit-engine/performance/analysis",
    response_model=PerformanceAnalysisResponse,
    summary="Get Performance Analysis",
    description="Lädt SOLL-IST Performance-Analyse mit Accuracy-Berechnungen und Best-Performing-Horizon-Identifikation"
)
async def get_performance_analysis(
    request: PerformanceAnalysisRequest,
    controller: UnifiedProfitEngineController = Depends(get_controller)
) -> PerformanceAnalysisResponse:
    """
    Performance Analysis Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller -> Use Case -> SOLL-IST Repository -> PostgreSQL Views -> Calculated Metrics
    """
    try:
        logger.info(f"📈 Performance analysis request: symbol={request.symbol}, horizon={request.horizon}")
        return await controller.get_performance_analysis(request)
    except Exception as e:
        logger.error(f"❌ Performance analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/profit-engine/health",
    response_model=HealthCheckResponse,
    summary="Service Health Check",
    description="Comprehensive Service Health Check inklusive Dependencies (PostgreSQL, Redis, Yahoo Finance)"
)
async def health_check(
    controller: UnifiedProfitEngineController = Depends(get_controller)
) -> HealthCheckResponse:
    """
    Health Check Endpoint
    
    CLEAN ARCHITECTURE: Infrastructure Health Monitoring
    """
    try:
        return await controller.health_check()
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthCheckResponse(
            healthy=False,
            service="unified-profit-engine-enhanced",
            version="6.0.0",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@app.get(
    "/api/v1/profit-engine/metrics", 
    response_model=ServiceMetricsResponse,
    summary="Service Metrics",
    description="Service Metriken für Monitoring (Request Count, Error Rate, Success Rate, Uptime)"
)
async def get_service_metrics(
    controller: UnifiedProfitEngineController = Depends(get_controller)
) -> ServiceMetricsResponse:
    """
    Service Metrics Endpoint
    
    CLEAN ARCHITECTURE: Infrastructure Monitoring und Metrics
    """
    try:
        return await controller.get_service_metrics()
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EVENT-DRIVEN PATTERN TEST ENDPOINT
# =============================================================================

@app.post("/api/v1/profit-engine/test/event-flow")
async def test_event_flow(container: DependencyContainer = Depends(get_container)):
    """
    Test Endpoint für Event-Driven Pattern
    
    CLEAN ARCHITECTURE: Event Flow Testing
    Publiziert Test Event über Redis Event-Bus (Port 8014)
    """
    try:
        logger.info("🧪 Testing Event-Driven Pattern")
        
        if not container.event_publisher:
            raise HTTPException(status_code=503, detail="Event publisher not available")
        
        # Test Event publizieren
        await container.event_publisher.publish(
            "test.event.flow", 
            {
                "message": "Event-Driven Pattern Test",
                "service": "unified-profit-engine-enhanced",
                "version": "6.0.0",
                "test_timestamp": datetime.now().isoformat(),
                "clean_architecture": True
            }
        )
        
        logger.info("✅ Event-Driven Pattern test successful")
        return {
            "success": True,
            "message": "Event published successfully to Redis Event-Bus (Port 8014)",
            "event_type": "test.event.flow",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Event flow test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global Exception Handler mit Clean Architecture Error Response"""
    logger.error(f"❌ Unhandled exception: {exc}")
    logger.error(f"Stack trace: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if config.log_level == "DEBUG" else "An error occurred",
            "service": "unified-profit-engine-enhanced",
            "version": "6.0.0",
            "timestamp": datetime.now().isoformat()
        }
    )


# =============================================================================
# SIGNAL HANDLING
# =============================================================================

def setup_signal_handlers():
    """Setup Signal Handlers für Graceful Shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown")
        asyncio.create_task(shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def shutdown():
    """Graceful Shutdown Procedure"""
    logger.info("🛑 Graceful shutdown initiated")
    
    global container
    if container:
        await container.cleanup()
    
    logger.info("✅ Graceful shutdown completed")
    sys.exit(0)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main Service Execution
    
    CLEAN ARCHITECTURE: Application Entry Point
    """
    
    logger.info("🚀 Starting Unified Profit Engine Enhanced v6.0.0")
    logger.info("📐 Clean Architecture Implementation:")
    logger.info("   ✅ Domain Layer: Business Logic, Entities, Value Objects")
    logger.info("   ✅ Application Layer: Use Cases, Service Interfaces")  
    logger.info("   ✅ Infrastructure Layer: Repositories, External APIs, Event Publishing")
    logger.info("   ✅ Presentation Layer: FastAPI Controllers, Request/Response Models")
    logger.info("   ✅ Dependency Injection: Centralized Container")
    logger.info("   ✅ Event-Driven Pattern: Redis Event-Bus Integration")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Configuration
    config = ServiceConfiguration()
    
    try:
        # Start FastAPI Server
        uvicorn.run(
            "unified_profit_engine_enhanced_v6_0_0_20250824:app",
            host=config.service_host,
            port=config.service_port,
            log_level=config.log_level.lower(),
            reload=False,  # Production setting
            workers=1,     # Single worker für Clean Architecture Compliance
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Service interrupted by user")
    except Exception as e:
        logger.error(f"❌ Service failed to start: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()