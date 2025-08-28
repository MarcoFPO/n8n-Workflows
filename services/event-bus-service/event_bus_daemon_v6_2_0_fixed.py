#!/usr/bin/env python3
"""
Event-Bus Service v6.2.0 - Clean Architecture Production Fix
Stable Event-Bus with proper Shared Components integration

KRITISCHE FIXES:
- Shared Components korrekte Integration (config_manager, structured_logging, database_pool)
- Redis Configuration aus ConfigManager
- Clean Architecture Event-Store Integration
- Proper Error Handling und Structured Logging
- Health Checks für Redis und PostgreSQL
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
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add shared to Python path - CLEAN ARCHITECTURE

# Import Shared Components - CLEAN ARCHITECTURE INTEGRATION
from shared.structured_logging import setup_structured_logging
from shared.config_manager import config
from shared.database_pool import db_pool, init_db_pool

class EventMessage(BaseModel):
    """Event Message Schema"""
    event_type: str
    data: Dict[str, Any]
    source: str = "manual"
    correlation_id: Optional[str] = None
    timestamp: Optional[str] = None

class EventBusService:
    """Clean Architecture Event Bus Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service",
            description="Clean Architecture Event-Driven Communication Hub",
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
        self.is_healthy = False
        self.startup_time = datetime.now()
        
        # Setup Routes
        self._setup_routes()
        
        # Setup Event Handlers
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)
    
    def _setup_routes(self):
        """Setup API Routes - Clean Architecture"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-service",
                "version": "6.2.0",
                "architecture": "Clean Architecture",
                "status": "running",
                "port": config.event_bus_service.port,
                "uptime": (datetime.now() - self.startup_time).total_seconds()
            }
        
        @self.app.get("/health")
        async def health():
            """Comprehensive Health Check"""
            redis_status = await self._check_redis_health()
            postgres_status = await self._check_postgres_health()
            
            overall_status = "healthy" if (redis_status and postgres_status) else "degraded"
            
            return {
                "status": overall_status,
                "service": "event-bus-service",
                "version": "6.2.0",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "redis": "healthy" if redis_status else "unhealthy",
                    "postgresql": "healthy" if postgres_status else "unhealthy"
                },
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                "redis_url": config.redis.url,
                "database_url": f"postgresql://{config.database.host}:{config.database.port}/{config.database.database}"
            }
        
        @self.app.post("/events/publish")
        async def publish_event(event: EventMessage, background_tasks: BackgroundTasks):
            """Publish Event to Redis + PostgreSQL Event Store"""
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
                    logger.info("Event published to Redis", event_type=event.event_type, source=event.source)
                
                # Store in PostgreSQL Event Store (Background Task)
                background_tasks.add_task(self._store_event_in_postgres, event)
                
                return {
                    "status": "published",
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "correlation_id": event.correlation_id
                }
                
            except Exception as e:
                logger.error("Event publish failed", error=str(e), event_type=event.event_type)
                raise HTTPException(status_code=500, detail=f"Event publish failed: {str(e)}")
        
        @self.app.get("/events/status")
        async def event_status():
            """Event Bus Status and Statistics"""
            redis_info = {}
            if self.redis_client:
                try:
                    redis_info = await self.redis_client.info()
                except:
                    redis_info = {"status": "connection_failed"}
            
            return {
                "event_bus": {
                    "status": "active",
                    "uptime": (datetime.now() - self.startup_time).total_seconds(),
                    "redis_connected": self.redis_client is not None
                },
                "redis": {
                    "host": config.redis.host,
                    "port": config.redis.port,
                    "db": config.redis.db,
                    "info": redis_info
                },
                "database": {
                    "host": config.database.host,
                    "port": config.database.port,
                    "database": config.database.database,
                    "pool_initialized": db_pool.is_initialized,
                    "pool_stats": db_pool.pool_stats
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
        """Service Startup - Clean Architecture"""
        try:
            global logger
            logger.info("Starting Event-Bus Service v6.2.0...")
            
            # Initialize Redis Connection
            await self._initialize_redis()
            
            # Initialize Database Pool
            await self._initialize_database()
            
            # Mark as healthy
            self.is_healthy = True
            logger.info("Event-Bus Service v6.2.0 started successfully", 
                       redis_connected=self.redis_client is not None,
                       db_pool_initialized=db_pool.is_initialized)
            
        except Exception as e:
            logger.error("Event-Bus Service startup failed", error=str(e))
            raise RuntimeError(f"Service initialization failed: {str(e)}")
    
    async def shutdown(self):
        """Service Shutdown - Clean Architecture"""
        try:
            logger.info("Shutting down Event-Bus Service v6.2.0...")
            
            # Close Redis Connection
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            
            # Close Database Pool
            await db_pool.close()
            logger.info("Database pool closed")
            
            logger.info("Event-Bus Service v6.2.0 shut down successfully")
            
        except Exception as e:
            logger.error("Error during Event-Bus shutdown", error=str(e))
    
    async def _initialize_redis(self):
        """Initialize Redis Connection with Config Manager"""
        try:
            redis_url = config.redis.url
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
            logger.info("Redis connection established", url=redis_url)
            
        except Exception as e:
            logger.error("Redis connection failed", error=str(e), url=config.redis.url)
            self.redis_client = None
            # Continue without Redis - degraded mode
    
    async def _initialize_database(self):
        """Initialize Database Pool with Config Manager"""
        try:
            await init_db_pool()
            
            # Test connection
            health_ok = await db_pool.health_check()
            if health_ok:
                logger.info("Database pool initialized successfully", 
                           host=config.database.host, 
                           database=config.database.database)
            else:
                logger.warning("Database health check failed after initialization")
                
        except Exception as e:
            logger.error("Database pool initialization failed", error=str(e))
            # Continue without database - degraded mode
    
    async def _check_redis_health(self) -> bool:
        """Redis Health Check"""
        try:
            if self.redis_client:
                await self.redis_client.ping()
                return True
            return False
        except:
            return False
    
    async def _check_postgres_health(self) -> bool:
        """PostgreSQL Health Check"""
        try:
            return await db_pool.health_check()
        except:
            return False
    
    async def _store_event_in_postgres(self, event: EventMessage):
        """Store Event in PostgreSQL Event Store - Background Task"""
        try:
            if not db_pool.is_initialized:
                return
                
            event_data = {
                "event_type": event.event_type,
                "source": event.source,
                "data": event.data,
                "correlation_id": event.correlation_id,
                "timestamp": event.timestamp or datetime.now().isoformat()
            }
            
            # Insert into events table (Event Store Pattern)
            await db_pool.execute("""
                INSERT INTO events (event_type, entity_id, correlation_id, event_data, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
            event.event_type,
            event.source, 
            event.correlation_id,
            event_data,
            {"service": "event-bus-service", "version": "6.2.0"},
            datetime.now())
            
            logger.debug("Event stored in PostgreSQL", event_type=event.event_type)
            
        except Exception as e:
            logger.error("Event storage in PostgreSQL failed", error=str(e), event_type=event.event_type)

def main():
    """Main Entry Point"""
    
    # Setup Structured Logging
    global logger
    logger = setup_structured_logging("event-bus-service", config.log_level)
    
    # Create Service Instance
    event_bus_service = EventBusService()
    
    # Uvicorn Configuration
    uvicorn_config = uvicorn.Config(
        app=event_bus_service.app,
        host="0.0.0.0",
        port=config.event_bus_service.port,
        log_level=config.log_level.lower(),
        access_log=True,
        use_colors=False  # Better for systemd/journal
    )
    
    server = uvicorn.Server(uvicorn_config)
    
    logger.info("Event-Bus Service v6.2.0 starting...", 
               host="0.0.0.0", 
               port=config.event_bus_service.port,
               redis_url=config.redis.url,
               database_url=config.database.url)
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Event-Bus Service stopped by user")
    except Exception as e:
        logger.error("Event-Bus Service crashed", error=str(e))
        raise

if __name__ == "__main__":
    main()