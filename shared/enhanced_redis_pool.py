#!/usr/bin/env python3
"""
Enhanced Redis Connection Pool - Performance Optimized
Batch Operations, Selective TTL, Memory Management

Performance-Ziele:
- Redis Memory: <500MB  
- Event-Processing: <50ms
- Batch Operations für Multiple Events
- Intelligente TTL-Verwaltung
"""

import redis.asyncio as redis
import asyncio
import time
import json
import hashlib
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Enhanced Redis Pool Konfiguration"""
    host: str = "10.1.1.174"
    port: int = 6379
    db: int = 0
    max_connections: int = 20
    retry_on_timeout: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
    # Performance-Optimierungen
    enable_batch_operations: bool = True
    batch_size: int = 100
    enable_selective_ttl: bool = True
    default_ttl: int = 3600  # 1 Stunde statt 30 Tage
    high_priority_ttl: int = 86400  # 24 Stunden
    low_priority_ttl: int = 1800  # 30 Minuten
    
    # Memory Management
    max_memory_usage: str = "400mb"
    memory_policy: str = "allkeys-lru"
    enable_compression: bool = True
    
    # Performance Monitoring
    enable_performance_tracking: bool = True
    slow_operation_threshold: float = 0.1  # 100ms


@dataclass
class RedisOperationStats:
    """Redis Operation Performance Stats"""
    operation_type: str
    execution_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    last_executed: float = field(default_factory=time.time)
    
    def update(self, execution_time: float):
        self.execution_count += 1
        self.total_time += execution_time
        self.avg_time = self.total_time / self.execution_count
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.last_executed = time.time()


class EnhancedRedisPool:
    """Performance-optimierte Redis Connection Pool"""
    
    _instance: Optional['EnhancedRedisPool'] = None
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'EnhancedRedisPool':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        # Performance-Tracking
        self._operation_stats: Dict[str, RedisOperationStats] = defaultdict(lambda: RedisOperationStats("unknown"))
        self._batch_operations: List[Tuple[str, List, Dict]] = []
        self._pending_batches = 0
        
        # Metrics
        self._total_operations = 0
        self._batch_operations_count = 0
        self._cache_compressions = 0
        self._slow_operations = 0
        self._failed_operations = 0
        
        # Configuration
        self._config: Optional[RedisConfig] = None
        self._initialized = True
    
    async def initialize(self, redis_config: Optional[RedisConfig] = None):
        """Initialisiert den Enhanced Redis Pool"""
        async with self._lock:
            if self._client is None:
                if redis_config is None:
                    redis_config = RedisConfig()
                
                self._config = redis_config
                
                try:
                    # Connection Pool erstellen
                    self._pool = redis.ConnectionPool(
                        host=redis_config.host,
                        port=redis_config.port,
                        db=redis_config.db,
                        max_connections=redis_config.max_connections,
                        retry_on_timeout=redis_config.retry_on_timeout,
                        socket_timeout=redis_config.socket_timeout,
                        socket_connect_timeout=redis_config.socket_connect_timeout,
                        decode_responses=True
                    )
                    
                    # Redis Client erstellen
                    self._client = redis.Redis(connection_pool=self._pool)
                    
                    # Memory-Management konfigurieren
                    await self._configure_memory_management()
                    
                    # Performance-Monitoring starten
                    if redis_config.enable_performance_tracking:
                        asyncio.create_task(self._performance_monitor_task())
                    
                    logger.info(
                        f"Enhanced Redis pool initialized: {redis_config.max_connections} max connections, "
                        f"Batch Operations: {'enabled' if redis_config.enable_batch_operations else 'disabled'}, "
                        f"Selective TTL: {'enabled' if redis_config.enable_selective_ttl else 'disabled'}"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to initialize enhanced Redis pool: {e}")
                    raise
    
    async def close(self):
        """Schließt den Redis Pool"""
        async with self._lock:
            if self._client:
                await self._client.close()
                self._client = None
                self._pool = None
                logger.info("Enhanced Redis pool closed")
    
    @property
    def is_initialized(self) -> bool:
        """Gibt zurück ob der Pool initialisiert ist"""
        return self._client is not None
    
    async def _ensure_initialized(self):
        """Stellt sicher, dass der Pool initialisiert ist"""
        if not self.is_initialized:
            await self.initialize()
    
    # Enhanced Event Operations mit Performance-Optimierungen
    
    async def store_event_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Speichert mehrere Events in einer Batch-Operation"""
        await self._ensure_initialized()
        start_time = time.time()
        
        try:
            pipe = self._client.pipeline()
            
            for event in events:
                event_id = event.get('id')
                event_type = event.get('type', 'unknown')
                source = event.get('source', 'unknown')
                
                # TTL-Kategorie bestimmen
                ttl = self._get_event_ttl(event_type, event)
                
                # Event-Daten komprimieren wenn aktiviert
                event_data = self._compress_data(event) if self._config.enable_compression else json.dumps(event)
                
                # Event speichern
                pipe.hset(f"event:{event_id}", "data", event_data)
                pipe.expire(f"event:{event_id}", ttl)
                
                # Indizierung
                pipe.sadd(f"events_by_type:{event_type}", event_id)
                pipe.sadd(f"events_by_source:{source}", event_id)
                
                # Typ-Sets auch mit TTL versehen
                pipe.expire(f"events_by_type:{event_type}", ttl)
                pipe.expire(f"events_by_source:{source}", ttl)
            
            # Batch ausführen
            await pipe.execute()
            
            execution_time = time.time() - start_time
            self._update_operation_stats("store_event_batch", execution_time)
            self._batch_operations_count += 1
            
            logger.debug(f"Stored {len(events)} events in batch: {execution_time:.4f}s")
            return True
            
        except Exception as e:
            self._failed_operations += 1
            logger.error(f"Batch event storage failed: {e}")
            return False
    
    async def query_events_optimized(self, event_types: List[str] = None, 
                                   sources: List[str] = None, 
                                   limit: int = 100) -> List[Dict[str, Any]]:
        """Optimierte Event-Query mit SCAN-Limits"""
        await self._ensure_initialized()
        start_time = time.time()
        
        try:
            event_ids = set()
            
            # Filter nach Event-Types mit SCAN-Limit
            if event_types:
                for event_type in event_types:
                    type_key = f"events_by_type:{event_type}"
                    if await self._client.exists(type_key):
                        # SCAN mit Limit statt SMEMBERS für große Sets
                        async for event_id in self._client.sscan_iter(type_key, count=min(limit, 50)):
                            event_ids.add(event_id)
                            if len(event_ids) >= limit:
                                break
            
            # Filter nach Sources
            if sources:
                source_events = set()
                for source in sources:
                    src_key = f"events_by_source:{source}"
                    if await self._client.exists(src_key):
                        async for event_id in self._client.sscan_iter(src_key, count=min(limit, 50)):
                            source_events.add(event_id)
                            if len(source_events) >= limit:
                                break
                
                if event_ids:
                    event_ids = event_ids.intersection(source_events)
                else:
                    event_ids = source_events
            
            # Fallback: Alle Events mit SCAN
            if not event_types and not sources:
                async for key in self._client.scan_iter(match="event:*", count=min(limit, 50)):
                    event_id = key.replace('event:', '')
                    event_ids.add(event_id)
                    if len(event_ids) >= limit:
                        break
            
            # Events in Batches laden
            events = await self._load_events_batch(list(event_ids)[:limit])
            
            execution_time = time.time() - start_time
            self._update_operation_stats("query_events_optimized", execution_time)
            
            logger.debug(f"Query returned {len(events)} events in {execution_time:.4f}s")
            return events
            
        except Exception as e:
            self._failed_operations += 1
            logger.error(f"Optimized event query failed: {e}")
            return []
    
    async def _load_events_batch(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """Lädt Events in Batch-Operation"""
        if not event_ids:
            return []
        
        pipe = self._client.pipeline()
        for event_id in event_ids:
            pipe.hget(f"event:{event_id}", "data")
        
        results = await pipe.execute()
        events = []
        
        for result in results:
            if result:
                try:
                    # Dekomprimierung wenn aktiviert
                    if self._config.enable_compression:
                        event_data = self._decompress_data(result)
                    else:
                        event_data = json.loads(result)
                    events.append(event_data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"Failed to parse event data: {e}")
        
        return events
    
    async def cleanup_expired_events(self) -> int:
        """Bereinigt abgelaufene Events basierend auf TTL"""
        await self._ensure_initialized()
        start_time = time.time()
        
        try:
            cleanup_count = 0
            
            # Scanne Events und prüfe TTL
            async for key in self._client.scan_iter(match="event:*", count=100):
                ttl = await self._client.ttl(key)
                if ttl == -1:  # Kein TTL gesetzt
                    await self._client.expire(key, self._config.default_ttl)
                elif ttl == -2:  # Key existiert nicht mehr
                    cleanup_count += 1
            
            execution_time = time.time() - start_time
            self._update_operation_stats("cleanup_expired_events", execution_time)
            
            logger.debug(f"Cleaned up {cleanup_count} expired events in {execution_time:.4f}s")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Event cleanup failed: {e}")
            return 0
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Holt Redis Memory-Usage Statistiken"""
        await self._ensure_initialized()
        
        try:
            info = await self._client.info("memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "memory_usage_percentage": (info.get("used_memory", 0) / (500 * 1024 * 1024)) * 100  # Gegen 500MB Limit
            }
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {}
    
    # Performance Helper Methods
    
    def _get_event_ttl(self, event_type: str, event: Dict[str, Any]) -> int:
        """Bestimmt TTL basierend auf Event-Typ und Priorität"""
        if not self._config.enable_selective_ttl:
            return self._config.default_ttl
        
        # High-Priority Events (längere TTL)
        high_priority_types = ["prediction", "market_data", "portfolio_update"]
        if event_type in high_priority_types:
            return self._config.high_priority_ttl
        
        # Low-Priority Events (kürzere TTL)
        low_priority_types = ["debug", "trace", "heartbeat"]
        if event_type in low_priority_types:
            return self._config.low_priority_ttl
        
        return self._config.default_ttl
    
    def _compress_data(self, data: Dict[str, Any]) -> str:
        """Komprimiert Event-Daten für Speichereffizienz"""
        try:
            import gzip
            import base64
            json_str = json.dumps(data)
            compressed = gzip.compress(json_str.encode())
            self._cache_compressions += 1
            return base64.b64encode(compressed).decode()
        except Exception:
            # Fallback zu unkomprimiert
            return json.dumps(data)
    
    def _decompress_data(self, compressed_data: str) -> Dict[str, Any]:
        """Dekomprimiert Event-Daten"""
        try:
            import gzip
            import base64
            compressed = base64.b64decode(compressed_data.encode())
            json_str = gzip.decompress(compressed).decode()
            return json.loads(json_str)
        except Exception:
            # Fallback zu normaler JSON-Dekodierung
            return json.loads(compressed_data)
    
    def _update_operation_stats(self, operation_type: str, execution_time: float):
        """Aktualisiert Operation-Statistiken"""
        if not self._config.enable_performance_tracking:
            return
        
        self._operation_stats[operation_type].update(execution_time)
        self._total_operations += 1
        
        if execution_time > self._config.slow_operation_threshold:
            self._slow_operations += 1
            logger.warning(f"Slow Redis operation: {operation_type} took {execution_time:.4f}s")
    
    async def _configure_memory_management(self):
        """Konfiguriert Redis Memory-Management"""
        try:
            await self._client.config_set("maxmemory", self._config.max_memory_usage)
            await self._client.config_set("maxmemory-policy", self._config.memory_policy)
            logger.info(f"Redis memory management configured: {self._config.max_memory_usage}, policy: {self._config.memory_policy}")
        except Exception as e:
            logger.warning(f"Failed to configure Redis memory management: {e}")
    
    async def _performance_monitor_task(self):
        """Hintergrundtask für Performance-Monitoring"""
        while self._client:
            try:
                await asyncio.sleep(300)  # Alle 5 Minuten
                
                # Memory-Usage prüfen
                memory_info = await self.get_memory_usage()
                if memory_info.get("memory_usage_percentage", 0) > 80:
                    logger.warning(f"High Redis memory usage: {memory_info.get('memory_usage_percentage', 0):.1f}%")
                
                # Performance-Stats loggen
                if self._total_operations > 0:
                    logger.debug(f"Redis Performance: {self._total_operations} total operations, "
                               f"{self._slow_operations} slow operations, "
                               f"{self._batch_operations_count} batch operations")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Erstellt detaillierten Performance-Report"""
        memory_info = await self.get_memory_usage()
        
        return {
            "redis_performance": {
                "total_operations": self._total_operations,
                "batch_operations": self._batch_operations_count,
                "slow_operations": self._slow_operations,
                "failed_operations": self._failed_operations,
                "cache_compressions": self._cache_compressions,
                "slow_operation_rate": (self._slow_operations / max(1, self._total_operations)) * 100
            },
            "memory_usage": memory_info,
            "top_operations": [{
                "operation": op_type,
                "execution_count": stats.execution_count,
                "avg_time": f"{stats.avg_time:.4f}s",
                "max_time": f"{stats.max_time:.4f}s"
            } for op_type, stats in sorted(
                self._operation_stats.items(),
                key=lambda x: x[1].avg_time,
                reverse=True
            )[:5]],
            "configuration": {
                "max_connections": self._config.max_connections if self._config else "N/A",
                "batch_operations_enabled": self._config.enable_batch_operations if self._config else False,
                "selective_ttl_enabled": self._config.enable_selective_ttl if self._config else False,
                "compression_enabled": self._config.enable_compression if self._config else False,
                "default_ttl": f"{self._config.default_ttl}s" if self._config else "N/A"
            }
        }


# Global Enhanced Singleton Instance
enhanced_redis_pool = EnhancedRedisPool()


# Convenience Functions
async def init_enhanced_redis_pool(redis_config: Optional[RedisConfig] = None):
    """Initialisiert den Enhanced Redis Pool"""
    await enhanced_redis_pool.initialize(redis_config)


async def close_enhanced_redis_pool():
    """Schließt den Enhanced Redis Pool"""
    await enhanced_redis_pool.close()


# Context Manager
@asynccontextmanager
async def get_enhanced_redis_client():
    """Enhanced Context Manager für Redis-Operationen"""
    await enhanced_redis_pool._ensure_initialized()
    yield enhanced_redis_pool._client


# Performance Decorator für Redis-Operationen
def track_redis_performance(func):
    """Decorator für Redis Performance-Tracking"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"Redis operation executed in {execution_time:.4f}s: {func.__name__}")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"Redis operation failed after {execution_time:.4f}s: {func.__name__} - {e}")
            raise
    return wrapper