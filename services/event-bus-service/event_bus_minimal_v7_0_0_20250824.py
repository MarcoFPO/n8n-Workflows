#!/usr/bin/env python3
"""
Event-Bus Service v7.0.0 - Minimal Implementation
KRITISCHES HERZSTÜCK für Event-Driven Architecture - Port 8014

Minimale funktionsfähige Version für sofortigen Deployment
Implementiert Redis Pub/Sub Event Publishing für alle 11 Services

Code-Qualität: HÖCHSTE PRIORITÄT
Autor: Claude Code - Event-Bus Critical Implementation
Datum: 24. August 2025
Version: 7.0.0 (Minimal Deployment Ready)
"""

import asyncio
import json
import logging
import signal
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# =============================================================================
# CONFIGURATION
# =============================================================================

class EventBusConfig:
    """Event-Bus Configuration"""
    def __init__(self):
        self.service_name = "event-bus-service"
        self.service_host = "0.0.0.0"
        self.service_port = 8014  # KRITISCHER PORT für Event-Driven Pattern
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 0
        self.log_level = "INFO"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class EventMessage(BaseModel):
    """Event Message Model"""
    event_type: str = Field(..., description="Type of event")
    source: str = Field(..., description="Source service")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata")
    priority: str = Field("normal", description="Event priority")


class EventPublishResponse(BaseModel):
    """Event Publish Response"""
    success: bool
    event_id: str
    message: str
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    """Health Check Response"""
    healthy: bool
    service: str
    version: str
    redis_connected: bool
    port: int
    timestamp: datetime


# =============================================================================
# EVENT BUS SERVICE
# =============================================================================

class EventBusService:
    """
    Minimal Event-Bus Service Implementation
    
    KRITISCHES HERZSTÜCK für Event-Driven Architecture
    """
    
    def __init__(self, config: EventBusConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self.logger = logging.getLogger(__name__)
        self.events_published = 0
        self.start_time = datetime.now()
    
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = aioredis.from_url(
                f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}",
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("✅ Redis connection established")
            
        except Exception as e:
            self.logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def publish_event(self, event: EventMessage) -> str:
        """
        Publish event to Redis
        
        KRITISCH: Event-Driven Pattern Implementation
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            # Generate event ID
            event_id = str(uuid.uuid4())
            correlation_id = event.correlation_id or str(uuid.uuid4())
            
            # Build event message
            event_message = {
                "event_id": event_id,
                "event_type": event.event_type,
                "correlation_id": correlation_id,
                "source": event.source,
                "timestamp": datetime.now().isoformat(),
                "event_data": event.event_data,
                "metadata": event.metadata or {},
                "priority": event.priority
            }
            
            # Serialize event
            event_json = json.dumps(event_message, ensure_ascii=False, default=str)
            
            # Publish to Redis channel
            channel = f"events:{event.event_type}"
            await self.redis_client.publish(channel, event_json)
            
            # Store event with TTL
            event_key = f"event:{event_id}"
            await self.redis_client.setex(event_key, 86400, event_json)  # 24h TTL
            
            self.events_published += 1
            
            self.logger.info(f"📡 Event published: {event.event_type} -> {channel}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"❌ Event publishing failed: {e}")
            raise
    
    async def is_healthy(self) -> bool:
        """Check service health"""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except:
            return False
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.aclose()
        self.logger.info("✅ Event-Bus Service cleaned up")


# =============================================================================
# GLOBAL SERVICE INSTANCE
# =============================================================================

config = EventBusConfig()
event_bus_service: Optional[EventBusService] = None

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='{"service": "event-bus-service", "version": "7.0.0", "level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/event-bus-service-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan management"""
    global event_bus_service
    logger = logging.getLogger(__name__)
    
    # Startup
    try:
        logger.info("🚀 Starting Event-Bus Service v7.0.0 - KRITISCHES HERZSTÜCK")
        logger.info("🎯 Port 8014: Event-Driven Pattern für alle 11 Services")
        
        event_bus_service = EventBusService(config)
        await event_bus_service.initialize()
        
        app.state.event_bus = event_bus_service
        
        logger.info("✅ Event-Bus Service initialized successfully")
        logger.info("📡 Redis Pub/Sub Event-Driven Pattern AKTIV")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Event-Bus Service: {e}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down Event-Bus Service")
    if event_bus_service:
        await event_bus_service.cleanup()
    logger.info("✅ Event-Bus shutdown completed")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

setup_logging(config.log_level)

app = FastAPI(
    title="Event-Bus Service v7.0",
    description="Event-Driven Trading Intelligence System - Central Event Hub",
    version="7.0.0",
    lifespan=lifespan
)

# CORS für private Entwicklungsumgebung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "event-bus-service",
        "version": "7.0.0",
        "status": "KRITISCHES HERZSTÜCK AKTIV",
        "port": 8014,
        "description": "Event-Driven Pattern für aktienanalyse-ökosystem",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health Check Endpoint
    
    KRITISCH: Überprüft ob Event-Bus funktional ist
    """
    try:
        service = app.state.event_bus
        redis_healthy = await service.is_healthy() if service else False
        
        return HealthCheckResponse(
            healthy=redis_healthy,
            service="event-bus-service",
            version="7.0.0",
            redis_connected=redis_healthy,
            port=8014,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return HealthCheckResponse(
            healthy=False,
            service="event-bus-service",
            version="7.0.0",
            redis_connected=False,
            port=8014,
            timestamp=datetime.now()
        )


@app.post("/api/v1/events/publish", response_model=EventPublishResponse)
async def publish_event(event: EventMessage) -> EventPublishResponse:
    """
    Event Publishing Endpoint
    
    KRITISCH: Publiziert Events für Event-Driven Pattern
    """
    try:
        service = app.state.event_bus
        if not service:
            raise HTTPException(status_code=503, detail="Event-Bus service not initialized")
        
        event_id = await service.publish_event(event)
        
        return EventPublishResponse(
            success=True,
            event_id=event_id,
            message=f"Event {event.event_type} published successfully",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"❌ Event publishing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/test/event-flow")
async def test_event_flow():
    """
    Test Event Flow
    
    KRITISCH: Test ob Event-Driven Pattern funktioniert
    """
    try:
        service = app.state.event_bus
        if not service:
            raise HTTPException(status_code=503, detail="Event-Bus service not initialized")
        
        # Test Event erstellen
        test_event = EventMessage(
            event_type="system.test.event_flow",
            source="event-bus-service",
            event_data={
                "message": "Event-Driven Pattern Flow Test",
                "service": "event-bus-service",
                "version": "7.0.0",
                "test_timestamp": datetime.now().isoformat(),
                "critical_component": "Event-Bus Service Port 8014"
            },
            metadata={"test_type": "event_flow", "priority": "high"}
        )
        
        event_id = await service.publish_event(test_event)
        
        return {
            "success": True,
            "message": "Event published successfully to Redis Event-Bus (Port 8014)",
            "event_type": "system.test.event_flow",
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "status": "Event-Bus Service FUNCTIONAL"
        }
        
    except Exception as e:
        logger.error(f"❌ Event flow test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/metrics")
async def get_metrics():
    """Service metrics"""
    try:
        service = app.state.event_bus
        if not service:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        uptime = (datetime.now() - service.start_time).total_seconds()
        
        return {
            "service": "event-bus-service",
            "version": "7.0.0",
            "port": 8014,
            "events_published_total": service.events_published,
            "uptime_seconds": uptime,
            "redis_connected": await service.is_healthy(),
            "status": "KRITISCHES HERZSTÜCK AKTIV",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"❌ Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
            "service": "event-bus-service",
            "version": "7.0.0",
            "timestamp": datetime.now().isoformat()
        }
    )


# =============================================================================
# SIGNAL HANDLING
# =============================================================================

def setup_signal_handlers():
    """Setup signal handlers"""
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating shutdown")
        asyncio.create_task(shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def shutdown():
    """Graceful shutdown"""
    logger.info("🛑 Event-Bus Service graceful shutdown initiated")
    
    global event_bus_service
    if event_bus_service:
        await event_bus_service.cleanup()
    
    logger.info("✅ Event-Bus Service graceful shutdown completed")
    sys.exit(0)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Main entry point
    
    KRITISCH: Startet Event-Bus Service auf Port 8014
    """
    logger.info("🚀 Starting Event-Bus Service v7.0.0 - KRITISCHES HERZSTÜCK")
    logger.info("🎯 PORT 8014: Ermöglicht Event-Driven Communication für alle 11 Services")
    logger.info("📡 Redis Pub/Sub Event-Driven Pattern für aktienanalyse-ökosystem")
    
    setup_signal_handlers()
    
    try:
        uvicorn.run(
            "event_bus_minimal_v7_0_0_20250824:app",
            host=config.service_host,
            port=config.service_port,
            log_level=config.log_level.lower(),
            reload=False,
            workers=1,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Event-Bus Service interrupted by user")
    except Exception as e:
        logger.error(f"❌ Event-Bus Service failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()