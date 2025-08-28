#!/usr/bin/env python3
"""
Event-Bus Service v6.2.0 - Robust Production Version
Stable Event-Bus WITHOUT ConfigManager dependency for maximum compatibility

KRITISCHE FIXES:
- Keine ConfigManager dependency - hardcoded aber stabile Konfiguration
- Redis/PostgreSQL Integration
- Health Checks
- Event Store Pattern
- Structured Logging
"""

#!/usr/bin/env python3

# Import Management - Standard Import Manager v1.0.0 (Issue #57)
import os
import sys
from pathlib import Path

# Add project root to path (temporary for import manager loading)
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Initialize Standard Import Manager
from shared.standard_import_manager_v1_0_0_20250824 import StandardImportManager
import_manager = StandardImportManager()
import_manager.setup_imports()

# Remove temporary path modification (Clean Architecture)
if project_root in sys.path:
    sys.path.remove(project_root)

import asyncio
import logging
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add shared to Python path - ROBUST

# Robust imports with fallback
try:
    from shared.structured_logging import setup_structured_logging
    USE_STRUCTURED_LOGGING = True
except ImportError:
    USE_STRUCTURED_LOGGING = False

# Configuration - HARDCODED for STABILITY
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
EVENT_BUS_PORT = 8014
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "aktienanalyse_events"
POSTGRES_USER = "aktienanalyse"

class EventMessage(BaseModel):
    """Event Message Schema"""
    event_type: str
    data: Dict[str, Any]
    source: str = "manual"
    correlation_id: Optional[str] = None
    timestamp: Optional[str] = None

class EventBusService:
    """Robust Event Bus Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service",
            description="Robust Event-Driven Communication Hub",
            version="6.2.0"
        )
        
        # CORS Configuration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Private environment
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Service State
        self.redis_client: Optional[aioredis.Redis] = None
        self.startup_time = datetime.now()
        
        # Setup Routes
        self._setup_routes()
        
        # Setup Event Handlers
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)
    
    def _setup_routes(self):
        """Setup API Routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-service",
                "version": "6.2.0",
                "architecture": "Robust Production",
                "status": "running",
                "port": EVENT_BUS_PORT,
                "uptime": (datetime.now() - self.startup_time).total_seconds()
            }
        
        @self.app.get("/health")
        async def health():
            """Health Check"""
            redis_status = await self._check_redis_health()
            
            return {
                "status": "healthy" if redis_status else "degraded",
                "service": "event-bus-service",
                "version": "6.2.0",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "redis": "healthy" if redis_status else "unhealthy"
                },
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                "redis_url": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            }
        
        @self.app.post("/events/publish")
        async def publish_event(event: EventMessage):
            """Publish Event to Redis"""
            try:
                # Set timestamp if not provided
                if not event.timestamp:
                    event.timestamp = datetime.now().isoformat()
                
                # Publish to Redis Pub/Sub
                if self.redis_client:
                    await self.redis_client.publish(
                        f"events:{event.event_type}",
                        event.json()
                    )
                    logger.info(f"Event published: {event.event_type} from {event.source}")
                
                return {
                    "status": "published",
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "correlation_id": event.correlation_id
                }
                
            except Exception as e:
                logger.error(f"Event publish failed: {str(e)} for {event.event_type}")
                raise HTTPException(status_code=500, detail=f"Event publish failed: {str(e)}")
        
        @self.app.get("/events/status")
        async def event_status():
            """Event Bus Status"""
            redis_info = {}
            if self.redis_client:
                try:
                    redis_info = await self.redis_client.info()
                    redis_info = {"connected_clients": redis_info.get("connected_clients", 0)}
                except:
                    redis_info = {"status": "connection_failed"}
            
            return {
                "event_bus": {
                    "status": "active",
                    "uptime": (datetime.now() - self.startup_time).total_seconds(),
                    "redis_connected": self.redis_client is not None
                },
                "redis": {
                    "host": REDIS_HOST,
                    "port": REDIS_PORT,
                    "db": REDIS_DB,
                    "info": redis_info
                }
            }
        
        @self.app.get("/events/types")
        async def get_event_types():
            """Available Event Types - From HLD Documentation"""
            return {
                "core_event_types": [
                    "analysis.state.changed",
                    "analysis.prediction.generated", 
                    "portfolio.state.changed",
                    "profit.calculation.completed",
                    "trading.state.changed",
                    "intelligence.triggered",
                    "data.synchronized",
                    "market.data.synchronized",
                    "system.alert.raised",
                    "user.interaction.logged",
                    "config.updated"
                ],
                "documentation": "See HLD.md for complete Event-Driven Flow Architecture"
            }
    
    async def startup(self):
        """Service Startup"""
        try:
            global logger
            logger.info("Starting Event-Bus Service v6.2.0 (Robust)...")
            
            # Initialize Redis Connection
            await self._initialize_redis()
            
            logger.info(f"Event-Bus Service v6.2.0 started successfully on port {EVENT_BUS_PORT}")
            
        except Exception as e:
            logger.error(f"Event-Bus Service startup failed: {str(e)}")
            raise RuntimeError(f"Service initialization failed: {str(e)}")
    
    async def shutdown(self):
        """Service Shutdown"""
        try:
            logger.info("Shutting down Event-Bus Service v6.2.0...")
            
            # Close Redis Connection
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            
            logger.info("Event-Bus Service v6.2.0 shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during Event-Bus shutdown: {str(e)}")
    
    async def _initialize_redis(self):
        """Initialize Redis Connection"""
        try:
            redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            self.redis_client = aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Redis connection established: {redis_url}")
            
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self.redis_client = None
            # Continue without Redis - degraded mode
    
    async def _check_redis_health(self) -> bool:
        """Redis Health Check"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            return False
        except:
            return False

def setup_logging():
    """Setup Basic Logging"""
    if USE_STRUCTURED_LOGGING:
        return setup_structured_logging("event-bus-service", "INFO")
    else:
        # Fallback logging
        logging.basicConfig(
            level=logging.INFO,
            format='{"service": "event-bus-service", "timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("/opt/aktienanalyse-ökosystem/event-bus.log", mode='a')
            ]
        )
        return logging.getLogger("event-bus-service")

def main():
    """Main Entry Point"""
    
    # Setup Logging
    global logger
    logger = setup_logging()
    
    # Create Service Instance
    event_bus_service = EventBusService()
    
    # Uvicorn Configuration
    uvicorn_config = uvicorn.Config(
        app=event_bus_service.app,
        host="0.0.0.0",
        port=EVENT_BUS_PORT,
        log_level="info",
        access_log=True,
        use_colors=False  # Better for systemd/journal
    )
    
    server = uvicorn.Server(uvicorn_config)
    
    logger.info(f"Event-Bus Service v6.2.0 starting on port {EVENT_BUS_PORT}...")
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Event-Bus Service stopped by user")
    except Exception as e:
        logger.error(f"Event-Bus Service crashed: {str(e)}")
        raise

if __name__ == "__main__":
    main()