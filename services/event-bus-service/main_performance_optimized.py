"""
Event-Bus Service Performance Optimized v2.0.0
Performance-optimierter Event-Hub mit Enhanced Pools

Performance-Verbesserungen:
- Enhanced Redis Pool mit Batch-Operations
- Selective TTL Management  
- Memory-optimierte Event-Verarbeitung
- Async Connection Pooling
- Query-Caching und Prepared Statements
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import redis.asyncio as aioredis
import aio_pika
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import Management - CLEAN ARCHITECTURE
from shared.standard_import_manager_v1_0_0_20250824 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()

# Enhanced Performance Pools
from shared.enhanced_database_pool import (
    enhanced_db_pool, 
    init_enhanced_db_pool, 
    PoolConfig,
    track_query_performance
)
from shared.enhanced_redis_pool import (
    enhanced_redis_pool, 
    init_enhanced_redis_pool, 
    RedisConfig,
    track_redis_performance
)

# Clean imports
from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType, Event

# Configure performance-aware logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [event-bus-optimized] [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("event-bus-optimized")

# Pydantic Models mit Performance-Optimierungen
class OptimizedEventMessage(BaseModel):
    event_type: str
    stream_id: Optional[str] = None
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: Optional[str] = Field(default="normal", description="Event priority: low, normal, high")

class EventStoreQuery(BaseModel):
    event_types: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    limit: int = Field(default=50, le=1000, description="Max 1000 events für Performance")
    offset: int = Field(default=0, ge=0)

class BatchEventMessage(BaseModel):
    events: List[OptimizedEventMessage] = Field(..., max_items=100, description="Max 100 events per batch")


class EnhancedEventBusService(BackendBaseModule):
    """Performance-optimierter Event-Bus Service"""
    
    def __init__(self):
        super().__init__()
        self.service_name = "event-bus-service-optimized"
        self.app = FastAPI(
            title="Enhanced Event-Bus Service",
            version="2.0.0",
            description="Performance-optimized Event Hub with Batch Operations"
        )
        
        # Performance-Enhanced Clients
        self.redis_client = None
        self.db_pool = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        
        # Performance Metrics
        self.processed_events = 0
        self.batch_operations = 0
        self.cache_hits = 0
        self.start_time = datetime.now()
        
        # Batch Processing
        self.event_batch_queue = []
        self.batch_size = 50
        self.batch_timeout = 1.0  # 1 Sekunde
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Performance-optimierte Middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Für private Entwicklungsumgebung
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """API-Routes mit Performance-Fokus"""
        
        @self.app.post("/events", 
                      summary="Store Single Event",
                      description="Store single event with automatic batching")
        async def store_event(event: OptimizedEventMessage):
            return await self._store_single_event(event)
        
        @self.app.post("/events/batch",
                      summary="Store Event Batch", 
                      description="Store up to 100 events in single operation")
        async def store_event_batch(batch: BatchEventMessage):
            return await self._store_event_batch(batch.events)
        
        @self.app.post("/events/query",
                      summary="Query Events Optimized",
                      description="Query events with performance optimizations")
        async def query_events(query: EventStoreQuery):
            return await self._query_events_optimized(query)
        
        @self.app.get("/events/{event_id}",
                     summary="Get Single Event",
                     description="Get event by ID with caching")
        async def get_event(event_id: str):
            return await self._get_event_cached(event_id)
        
        @self.app.get("/health/performance",
                     summary="Performance Health Check",
                     description="Detailed performance metrics and health status")
        async def performance_health():
            return await self._get_performance_health()
        
        @self.app.post("/admin/cleanup",
                      summary="Cleanup Expired Events",
                      description="Trigger cleanup of expired events")
        async def cleanup_expired():
            return await self._cleanup_expired_events()
        
        @self.app.get("/metrics/performance",
                     summary="Performance Report", 
                     description="Comprehensive performance analysis")
        async def get_performance_metrics():
            return await self._get_performance_report()
    
    async def initialize(self):
        """Enhanced Initialization mit Performance Pools"""
        try:
            # Enhanced Database Pool initialisieren
            db_config = PoolConfig(
                min_connections=5,
                max_connections=20,
                enable_query_cache=True,
                enable_prepared_statements=True,
                max_query_time=10  # 10s für Event-Queries
            )
            await init_enhanced_db_pool(db_config)
            logger.info("Enhanced database pool initialized")
            
            # Enhanced Redis Pool initialisieren
            redis_config = RedisConfig(
                host=os.getenv("REDIS_HOST", "10.1.1.174"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                max_connections=20,
                enable_batch_operations=True,
                enable_selective_ttl=True,
                default_ttl=3600,  # 1 Stunde statt 30 Tage
                high_priority_ttl=86400,  # 24h für wichtige Events
                low_priority_ttl=1800,  # 30min für unwichtige Events
                enable_compression=True
            )
            await init_enhanced_redis_pool(redis_config)
            logger.info("Enhanced Redis pool initialized")
            
            # RabbitMQ Connection (optional für Pub/Sub)
            await self._setup_rabbitmq()
            
            # Batch Processing Task starten
            asyncio.create_task(self._batch_processing_task())
            
            logger.info("Enhanced Event-Bus Service fully initialized")
            
        except Exception as e:
            logger.error(f"Enhanced initialization failed: {e}")
            raise
    
    @track_redis_performance
    async def _store_single_event(self, event: OptimizedEventMessage) -> Dict[str, Any]:
        """Speichert einzelnes Event mit Auto-Batching"""
        try:
            event_id = str(uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            event_data = {
                "id": event_id,
                "type": event.event_type,
                "source": event.source,
                "data": event.data,
                "timestamp": timestamp,
                "correlation_id": event.correlation_id,
                "metadata": event.metadata or {},
                "priority": event.priority
            }
            
            # Event zur Batch-Queue hinzufügen
            self.event_batch_queue.append(event_data)
            
            # Sofortige Batch-Verarbeitung wenn Batch voll
            if len(self.event_batch_queue) >= self.batch_size:
                await self._process_event_batch()
            
            self.processed_events += 1
            
            return {
                "status": "queued",
                "event_id": event_id,
                "timestamp": timestamp,
                "batch_position": len(self.event_batch_queue)
            }
            
        except Exception as e:
            logger.error(f"Single event storage failed: {e}")
            raise HTTPException(status_code=500, detail=f"Event storage failed: {str(e)}")
    
    @track_redis_performance  
    async def _store_event_batch(self, events: List[OptimizedEventMessage]) -> Dict[str, Any]:
        """Speichert Event-Batch direkt"""
        try:
            if len(events) > 100:
                raise HTTPException(status_code=400, detail="Maximum 100 events per batch")
            
            event_batch = []
            event_ids = []
            
            for event in events:
                event_id = str(uuid4())
                timestamp = datetime.utcnow().isoformat()
                event_ids.append(event_id)
                
                event_data = {
                    "id": event_id,
                    "type": event.event_type,
                    "source": event.source,
                    "data": event.data,
                    "timestamp": timestamp,
                    "correlation_id": event.correlation_id,
                    "metadata": event.metadata or {},
                    "priority": event.priority
                }
                event_batch.append(event_data)
            
            # Direkte Batch-Verarbeitung
            success = await enhanced_redis_pool.store_event_batch(event_batch)
            
            if not success:
                raise HTTPException(status_code=500, detail="Batch storage failed")
            
            self.processed_events += len(events)
            self.batch_operations += 1
            
            return {
                "status": "stored",
                "event_count": len(events),
                "event_ids": event_ids,
                "batch_id": str(uuid4())
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Batch event storage failed: {e}")
            raise HTTPException(status_code=500, detail=f"Batch storage failed: {str(e)}")
    
    @track_redis_performance
    async def _query_events_optimized(self, query: EventStoreQuery) -> Dict[str, Any]:
        """Optimierte Event-Query mit SCAN-Limits"""
        try:
            start_time = datetime.now()
            
            events = await enhanced_redis_pool.query_events_optimized(
                event_types=query.event_types,
                sources=query.sources,
                limit=query.limit
            )
            
            # Offset-basierte Pagination (in-memory)
            if query.offset > 0:
                events = events[query.offset:]
            
            query_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "events": events,
                "total_count": len(events),
                "query_time_ms": int(query_time * 1000),
                "cache_info": "optimized_scan_query",
                "performance": {
                    "scan_limited": True,
                    "batch_loaded": True,
                    "compressed": enhanced_redis_pool._config.enable_compression if enhanced_redis_pool._config else False
                }
            }
            
        except Exception as e:
            logger.error(f"Optimized event query failed: {e}")
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    @track_redis_performance
    async def _get_event_cached(self, event_id: str) -> Dict[str, Any]:
        """Holt einzelnes Event mit Caching"""
        try:
            await enhanced_redis_pool._ensure_initialized()
            
            # Event-Daten laden
            event_data = await enhanced_redis_pool._client.hget(f"event:{event_id}", "data")
            
            if not event_data:
                raise HTTPException(status_code=404, detail="Event not found")
            
            # Dekomprimierung falls aktiviert
            if enhanced_redis_pool._config.enable_compression:
                event = enhanced_redis_pool._decompress_data(event_data)
            else:
                event = json.loads(event_data)
            
            self.cache_hits += 1
            
            return {
                "event": event,
                "cache_hit": True,
                "compression_enabled": enhanced_redis_pool._config.enable_compression
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get event failed: {e}")
            raise HTTPException(status_code=500, detail=f"Get event failed: {str(e)}")
    
    async def _cleanup_expired_events(self) -> Dict[str, Any]:
        """Bereinigung abgelaufener Events"""
        try:
            cleanup_count = await enhanced_redis_pool.cleanup_expired_events()
            
            return {
                "status": "completed",
                "cleaned_events": cleanup_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Event cleanup failed: {e}")
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    
    async def _get_performance_health(self) -> Dict[str, Any]:
        """Performance Health Check"""
        try:
            # Redis Memory Info
            redis_memory = await enhanced_redis_pool.get_memory_usage()
            
            # Database Pool Stats
            db_stats = enhanced_db_pool.pool_stats if enhanced_db_pool.is_initialized else {}
            
            # Service Metrics
            uptime = (datetime.now() - self.start_time).total_seconds()
            events_per_second = self.processed_events / max(1, uptime)
            
            return {
                "status": "healthy",
                "service_metrics": {
                    "uptime_seconds": int(uptime),
                    "processed_events": self.processed_events,
                    "events_per_second": round(events_per_second, 2),
                    "batch_operations": self.batch_operations,
                    "cache_hits": self.cache_hits,
                    "batch_queue_size": len(self.event_batch_queue)
                },
                "redis_performance": {
                    "memory_usage": redis_memory.get("used_memory_human", "Unknown"),
                    "memory_percentage": round(redis_memory.get("memory_usage_percentage", 0), 2),
                    "pool_initialized": enhanced_redis_pool.is_initialized
                },
                "database_performance": db_stats,
                "health_checks": {
                    "redis_healthy": enhanced_redis_pool.is_initialized,
                    "database_healthy": enhanced_db_pool.is_initialized,
                    "memory_ok": redis_memory.get("memory_usage_percentage", 0) < 90,
                    "event_processing_ok": events_per_second > 0 if self.processed_events > 0 else True
                }
            }
            
        except Exception as e:
            logger.error(f"Performance health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_performance_report(self) -> Dict[str, Any]:
        """Comprehensive Performance Report"""
        try:
            # Redis Performance Report
            redis_report = await enhanced_redis_pool.get_performance_report()
            
            # Database Performance Report
            db_report = await enhanced_db_pool.get_performance_report() if enhanced_db_pool.is_initialized else {}
            
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            return {
                "service_performance": {
                    "service_name": self.service_name,
                    "version": "2.0.0",
                    "uptime_seconds": int(uptime),
                    "processed_events": self.processed_events,
                    "events_per_second": round(self.processed_events / max(1, uptime), 2),
                    "batch_operations": self.batch_operations,
                    "batch_efficiency": round((self.batch_operations * self.batch_size) / max(1, self.processed_events) * 100, 2)
                },
                "redis_performance": redis_report,
                "database_performance": db_report,
                "recommendations": self._get_performance_recommendations(redis_report, db_report),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Performance report failed: {e}")
            raise HTTPException(status_code=500, detail=f"Performance report failed: {str(e)}")
    
    def _get_performance_recommendations(self, redis_report: Dict, db_report: Dict) -> List[str]:
        """Generiert Performance-Empfehlungen"""
        recommendations = []
        
        # Redis Recommendations
        if redis_report.get("memory_usage", {}).get("memory_usage_percentage", 0) > 80:
            recommendations.append("Redis memory usage high - consider increasing memory limit or reducing TTL")
        
        slow_op_rate = redis_report.get("redis_performance", {}).get("slow_operation_rate", 0)
        if slow_op_rate > 10:
            recommendations.append(f"Redis slow operation rate high ({slow_op_rate:.1f}%) - review query patterns")
        
        # Database Recommendations
        if db_report.get("query_performance", {}).get("cache_efficiency", {}).get("hit_ratio", 0) < 50:
            recommendations.append("Database cache hit ratio low - consider increasing cache size")
        
        error_rate = db_report.get("query_performance", {}).get("error_rate", 0)
        if error_rate > 5:
            recommendations.append(f"Database error rate high ({error_rate:.1f}%) - review connection stability")
        
        # Service Recommendations
        uptime = (datetime.now() - self.start_time).total_seconds()
        if self.processed_events / max(1, uptime) < 10:
            recommendations.append("Low event throughput - consider batch size optimization")
        
        if len(recommendations) == 0:
            recommendations.append("Performance metrics look good - no immediate optimizations needed")
        
        return recommendations
    
    async def _process_event_batch(self):
        """Verarbeitet Events in Batches"""
        if not self.event_batch_queue:
            return
        
        try:
            batch_to_process = self.event_batch_queue.copy()
            self.event_batch_queue.clear()
            
            success = await enhanced_redis_pool.store_event_batch(batch_to_process)
            
            if success:
                self.batch_operations += 1
                logger.debug(f"Processed event batch of {len(batch_to_process)} events")
            else:
                logger.error("Event batch processing failed")
                # Events zurück in Queue (mit Limit)
                self.event_batch_queue.extend(batch_to_process[:50])
                
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
    
    async def _batch_processing_task(self):
        """Hintergrund-Task für Batch-Verarbeitung"""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                
                if self.event_batch_queue:
                    await self._process_event_batch()
                    
            except asyncio.CancelledError:
                # Final batch processing before shutdown
                if self.event_batch_queue:
                    await self._process_event_batch()
                break
            except Exception as e:
                logger.error(f"Batch processing task error: {e}")
    
    async def _setup_rabbitmq(self):
        """Optional RabbitMQ Setup für Pub/Sub"""
        try:
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@10.1.1.174:5672/")
            self.rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            logger.info("RabbitMQ connection established")
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed: {e} - continuing without pub/sub")
    
    async def shutdown(self):
        """Enhanced Shutdown mit Performance-Cleanup"""
        try:
            # Final batch processing
            if self.event_batch_queue:
                await self._process_event_batch()
            
            # Close RabbitMQ
            if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
                await self.rabbitmq_connection.close()
            
            # Performance Report vor Shutdown
            final_report = await self._get_performance_report()
            logger.info(f"Final Performance Report: {json.dumps(final_report, indent=2)}")
            
            logger.info("Enhanced Event-Bus Service shutdown completed")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


# FastAPI Lifecycle Events
service = EnhancedEventBusService()
app = service.app

@app.on_event("startup")
async def startup_event():
    await service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await service.shutdown()

if __name__ == "__main__":
    # Performance-optimierte Konfiguration
    uvicorn.run(
        "main_performance_optimized:app",
        host="0.0.0.0",
        port=8006,
        workers=1,  # Single worker für Connection-Pool-Sharing
        loop="asyncio",
        log_level="info",
        access_log=True
    )