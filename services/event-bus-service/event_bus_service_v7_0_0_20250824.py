#!/usr/bin/env python3
"""
Event-Bus Service v7.0.0 - Clean Architecture Implementation
Zentraler Event-Hub für aktienanalyse-ökosystem mit Redis Pub/Sub

CLEAN ARCHITECTURE LAYERS:
✅ Domain Layer: Event Entities, Event Store, Domain Services
✅ Application Layer: Event Publishing, Event Subscription Use Cases
✅ Infrastructure Layer: Redis Integration, PostgreSQL Event Store
✅ Presentation Layer: FastAPI Controllers, Event APIs

KRITISCHES HERZSTÜCK: Event-Driven Architecture für alle 11 Services
Port: 8014 (VERPFLICHTEND für Event-Driven Pattern)

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Specialist
Autor: Claude Code - Event-Bus Service Implementation  
Datum: 24. August 2025
Version: 7.0.0 (Clean Architecture Compliant)
"""

import asyncio
import json
import logging
import signal
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Clean Architecture Imports
from container import EventBusContainer, EventBusConfiguration
from presentation.controllers import EventController, EventStoreController
from presentation.models import (
    EventMessage,
    EventPublishRequest,
    EventSubscribeRequest,
    EventQueryRequest,
    EventQueryResponse,
    HealthCheckResponse,
    ServiceMetricsResponse
)

# Global Container Instance
container: EventBusContainer = None


def setup_logging(log_level: str = "INFO"):
    """
    Centralized Logging Configuration
    
    CLEAN ARCHITECTURE: Infrastructure Concern
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='{"service": "event-bus-service", "version": "7.0.0", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s", "module": "%(name)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/event-bus-service-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


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
        logger.info("🚀 Starting Event-Bus Service v7.0.0 - Clean Architecture")
        logger.info("📐 Architecture: Domain -> Application -> Infrastructure -> Presentation")
        logger.info("🎯 KRITISCHES HERZSTÜCK: Port 8014 für Event-Driven Pattern")
        
        # Initialize Configuration
        config = EventBusConfiguration()
        logger.info(f"⚙️ Configuration loaded: {config.to_dict()}")
        
        # Initialize Dependency Container
        container = EventBusContainer(config)
        await container.initialize()
        
        # Store in app state for access in routes
        app.state.container = container
        app.state.config = config
        app.state.startup_time = datetime.now()
        
        logger.info("✅ Event-Bus Service v7.0.0 initialized successfully")
        logger.info("🎯 Clean Architecture Layers: ✅ Domain | ✅ Application | ✅ Infrastructure | ✅ Presentation")
        logger.info(f"🌐 Event-Bus available at http://{config.service_host}:{config.service_port}")
        logger.info("📡 Redis Pub/Sub Event-Driven Pattern AKTIV")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Event-Bus Service: {e}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down Event-Bus Service v7.0.0")
    if container:
        await container.cleanup()
    logger.info("✅ Event-Bus shutdown completed")


# FastAPI App Creation mit Clean Architecture Setup
config = EventBusConfiguration()
setup_logging(config.log_level)

app = FastAPI(
    title="Event-Bus Service v7.0",
    description="Event-Driven Trading Intelligence System - Central Event Hub",
    version="7.0.0",
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

def get_container() -> EventBusContainer:
    """Dependency Injection Helper für Container Access"""
    if not hasattr(app.state, 'container') or not app.state.container:
        raise HTTPException(status_code=503, detail="Event-Bus container not initialized")
    return app.state.container


def get_event_controller(container: EventBusContainer = Depends(get_container)) -> EventController:
    """Dependency Injection Helper für Event Controller Access"""
    if not container.is_initialized() or not container.event_controller:
        raise HTTPException(status_code=503, detail="Event Controller not initialized")
    return container.event_controller


def get_event_store_controller(container: EventBusContainer = Depends(get_container)) -> EventStoreController:
    """Dependency Injection Helper für Event Store Controller Access"""
    if not container.is_initialized() or not container.event_store_controller:
        raise HTTPException(status_code=503, detail="Event Store Controller not initialized")
    return container.event_store_controller


# =============================================================================
# CLEAN ARCHITECTURE API ENDPOINTS - EVENT PUBLISHING
# =============================================================================

@app.post(
    "/api/v1/events/publish",
    summary="Publish Event to Redis Event-Bus",
    description="Publiziert Event über Redis Pub/Sub an alle abonnierten Services - HERZSTÜCK des Event-Driven Patterns"
)
async def publish_event(
    request: EventPublishRequest,
    controller: EventController = Depends(get_event_controller)
):
    """
    Event Publishing Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller (Presentation) -> Use Case (Application) -> Redis Publisher (Infrastructure) -> Domain Event
    """
    try:
        logger.info(f"📡 Event publish request: {request.event_type}")
        result = await controller.publish_event(request)
        return result
    except Exception as e:
        logger.error(f"❌ Event publishing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/events/subscribe",
    summary="Subscribe to Event Types",
    description="Abonniert Event-Types für Service - ermöglicht Event-Driven Communication zwischen Services"
)
async def subscribe_to_events(
    request: EventSubscribeRequest,
    controller: EventController = Depends(get_event_controller)
):
    """
    Event Subscription Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller -> Use Case -> Redis Subscriber -> Event Handler Registration
    """
    try:
        logger.info(f"📥 Event subscription request: service={request.service_name}, events={request.event_types}")
        result = await controller.subscribe_to_events(request)
        return result
    except Exception as e:
        logger.error(f"❌ Event subscription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CLEAN ARCHITECTURE API ENDPOINTS - EVENT STORE
# =============================================================================

@app.post(
    "/api/v1/events/query",
    response_model=EventQueryResponse,
    summary="Query Events from Event Store",
    description="PostgreSQL Event Store Abfrage - Single Source of Truth für alle Events im System"
)
async def query_events(
    request: EventQueryRequest,
    controller: EventStoreController = Depends(get_event_store_controller)
) -> EventQueryResponse:
    """
    Event Store Query Endpoint
    
    CLEAN ARCHITECTURE FLOW:
    Request -> Controller -> Use Case -> Event Repository -> PostgreSQL Event Store -> Domain Events
    """
    try:
        logger.info(f"🔍 Event store query: event_types={request.event_types}, limit={request.limit}")
        return await controller.query_events(request)
    except Exception as e:
        logger.error(f"❌ Event store query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/events/types",
    summary="Get Available Event Types",
    description="Verfügbare Event-Types im System - definiert in Domain Layer"
)
async def get_event_types(
    controller: EventStoreController = Depends(get_event_store_controller)
):
    """
    Event Types Endpoint
    
    CLEAN ARCHITECTURE: Domain Event Type Discovery
    """
    try:
        return await controller.get_available_event_types()
    except Exception as e:
        logger.error(f"❌ Event types query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH CHECK AND MONITORING
# =============================================================================

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Event-Bus Health Check",
    description="Comprehensive Health Check - Redis Pub/Sub, PostgreSQL Event Store, Service Availability"
)
async def health_check(
    controller: EventController = Depends(get_event_controller)
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
            service="event-bus-service",
            version="7.0.0",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@app.get(
    "/api/v1/metrics",
    response_model=ServiceMetricsResponse,
    summary="Event-Bus Service Metrics",
    description="Service Metriken für Monitoring - Event Counts, Redis Status, Performance Metrics"
)
async def get_service_metrics(
    controller: EventController = Depends(get_event_controller)
) -> ServiceMetricsResponse:
    """
    Service Metrics Endpoint
    
    CLEAN ARCHITECTURE: Infrastructure Monitoring
    """
    try:
        return await controller.get_service_metrics()
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EVENT-DRIVEN PATTERN TEST ENDPOINTS
# =============================================================================

@app.post("/api/v1/test/event-flow")
async def test_event_flow(container: EventBusContainer = Depends(get_container)):
    """
    Test Endpoint für Event-Driven Pattern
    
    CLEAN ARCHITECTURE: Event Flow Testing
    Publiziert Test Event über Redis Event-Bus für Service-Integration Tests
    """
    try:
        logger.info("🧪 Testing Event-Driven Pattern Flow")
        
        if not container.event_publisher:
            raise HTTPException(status_code=503, detail="Event publisher not available")
        
        # Test Event publizieren
        test_event = {
            "event_type": "system.test.event_flow", 
            "event_data": {
                "message": "Event-Driven Pattern Flow Test",
                "service": "event-bus-service",
                "version": "7.0.0",
                "test_timestamp": datetime.now().isoformat(),
                "clean_architecture": True,
                "critical_component": "Event-Bus Service Port 8014"
            },
            "source": "event-bus-service",
            "correlation_id": str(uuid.uuid4()),
            "metadata": {
                "test_type": "event_flow",
                "priority": "high"
            }
        }
        
        await container.event_publisher.publish("system.test.event_flow", test_event)
        
        logger.info("✅ Event-Driven Pattern test successful")
        return {
            "success": True,
            "message": "Event published successfully to Redis Event-Bus (Port 8014)",
            "event_type": "system.test.event_flow",
            "timestamp": datetime.now().isoformat(),
            "status": "Event-Bus Service FUNCTIONAL"
        }
        
    except Exception as e:
        logger.error(f"❌ Event flow test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/services/status")
async def get_connected_services(container: EventBusContainer = Depends(get_container)):
    """
    Connected Services Status
    
    CLEAN ARCHITECTURE: Service Registry Information
    Zeigt welche Services mit dem Event-Bus verbunden sind
    """
    try:
        logger.info("📊 Retrieving connected services status")
        
        if not container.event_service_registry:
            raise HTTPException(status_code=503, detail="Service registry not available")
        
        connected_services = await container.event_service_registry.get_connected_services()
        
        return {
            "event_bus_status": "operational",
            "port": 8014,
            "connected_services": connected_services,
            "total_services": len(connected_services),
            "architecture_compliance": "Clean Architecture v7.0",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Connected services query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global Exception Handler mit Clean Architecture Error Response"""
    logger.error(f"❌ Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if config.log_level == "DEBUG" else "An error occurred",
            "service": "event-bus-service", 
            "version": "7.0.0",
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
    logger.info("🛑 Event-Bus Service graceful shutdown initiated")
    
    global container
    if container:
        await container.cleanup()
    
    logger.info("✅ Event-Bus Service graceful shutdown completed")
    sys.exit(0)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main Service Execution
    
    CLEAN ARCHITECTURE: Application Entry Point für Event-Bus Service
    """
    
    logger.info("🚀 Starting Event-Bus Service v7.0.0 - KRITISCHES HERZSTÜCK")
    logger.info("📐 Clean Architecture Implementation:")
    logger.info("   ✅ Domain Layer: Event Entities, Event Store Domain")
    logger.info("   ✅ Application Layer: Event Publishing, Event Subscription Use Cases")  
    logger.info("   ✅ Infrastructure Layer: Redis Pub/Sub, PostgreSQL Event Store")
    logger.info("   ✅ Presentation Layer: FastAPI Controllers, Event APIs")
    logger.info("   ✅ Dependency Injection: Centralized Event-Bus Container")
    logger.info("   ✅ Event-Driven Pattern: ZENTRALE Redis Event-Bus Integration")
    logger.info("🎯 PORT 8014: Ermöglicht Event-Driven Communication für alle 11 Services")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    # Configuration
    config = EventBusConfiguration()
    
    try:
        # Start FastAPI Server
        uvicorn.run(
            "event_bus_service_v7_0_0_20250824:app",
            host=config.service_host,
            port=config.service_port,
            log_level=config.log_level.lower(),
            reload=False,  # Production setting
            workers=1,     # Single worker für Clean Architecture Compliance
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Event-Bus Service interrupted by user")
    except Exception as e:
        logger.error(f"❌ Event-Bus Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()