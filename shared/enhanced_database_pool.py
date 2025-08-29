#!/usr/bin/env python3
"""
Enhanced Database Connection Pool - Performance Optimized
Singleton Pattern mit Query-Caching, Prepared Statements und Performance-Monitoring

Performance-Ziele:
- Response Time: ≤100ms für normale Queries
- Connection Pool: Max 20 Connections per Service  
- Intelligent Caching mit LRU-Eviction
- Batch Operations für höheren Durchsatz
"""

import asyncpg
import asyncio
import os
import time
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging
from collections import deque
import weakref

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Enhanced Database Pool Konfiguration"""
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: int = 60
    server_settings: Dict[str, str] = None
    
    # Performance-Optimierungen
    connection_idle_timeout: int = 300  # 5 Minuten
    query_cache_size: int = 1000
    enable_prepared_statements: bool = True
    enable_query_cache: bool = True
    enable_connection_pooling: bool = True
    max_query_time: int = 30  # Sekunden
    
    def __post_init__(self):
        if self.server_settings is None:
            self.server_settings = {
                'application_name': 'aktienanalyse_pool_enhanced',
                'timezone': 'UTC',
                'statement_timeout': f'{self.max_query_time}s',
                'idle_in_transaction_session_timeout': f'{self.connection_idle_timeout}s'
            }


@dataclass
class QueryStats:
    """Query Performance Statistics"""
    query_hash: str
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


class EnhancedDatabasePool:
    """Performance-optimierte Database Connection Pool"""
    
    _instance: Optional['EnhancedDatabasePool'] = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'EnhancedDatabasePool':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        # Performance-Tracking
        self._query_stats: Dict[str, QueryStats] = {}
        self._query_cache: Dict[str, Any] = {}
        self._query_cache_order = deque(maxlen=1000)
        self._prepared_statements: Dict[str, str] = {}
        self._connection_refs: List[weakref.ref] = []
        
        # Metrics
        self._total_queries = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._slow_queries = 0
        self._failed_queries = 0
        
        # Configuration
        self._config: Optional[PoolConfig] = None
        self._initialized = True
    
    async def initialize(self, pool_config: Optional[PoolConfig] = None):
        """Initialisiert den Enhanced Connection Pool (Thread-Safe)"""
        async with self._lock:
            if self._pool is None:
                if pool_config is None:
                    pool_config = PoolConfig()
                
                self._config = pool_config
                
                try:
                    # Lade Configuration dynamisch
                    from .config_manager import config
                    
                    self._pool = await asyncpg.create_pool(
                        host=config.database.host,
                        port=config.database.port,
                        database=config.database.database,
                        user=config.database.user,
                        password=config.database.password,
                        min_size=pool_config.min_connections,
                        max_size=pool_config.max_connections,
                        command_timeout=pool_config.command_timeout,
                        server_settings=pool_config.server_settings,
                        init=self._connection_init
                    )
                    
                    # Performance-Monitoring starten
                    if pool_config.enable_query_cache:
                        asyncio.create_task(self._cache_cleanup_task())
                    
                    logger.info(
                        f"Enhanced database pool initialized: {pool_config.min_connections}-{pool_config.max_connections} connections, "
                        f"Cache: {'enabled' if pool_config.enable_query_cache else 'disabled'}, "
                        f"Prepared Statements: {'enabled' if pool_config.enable_prepared_statements else 'disabled'}"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize enhanced database pool: {e}")
                    raise
    
    async def close(self):
        """Schließt den Connection Pool"""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
                logger.info("Enhanced database pool closed")
    
    @asynccontextmanager
    async def acquire(self):
        """Context Manager für Database-Connections"""
        if self._pool is None:
            await self.initialize()
        
        async with self._pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise
    
    async def execute(self, query: str, *args, use_cache: bool = False) -> str:
        """Führt eine SQL-Query aus mit Performance-Optimierungen"""
        start_time = time.time()
        query_hash = self._get_query_hash(query, args)
        
        try:
            # Cache-Check für SELECT-Queries
            if use_cache and query.strip().upper().startswith('SELECT'):
                cached_result = self._get_cached_result(query_hash)
                if cached_result is not None:
                    self._cache_hits += 1
                    return cached_result
                self._cache_misses += 1
            
            async with self.acquire() as conn:
                # Prepared Statement verwenden wenn möglich
                if self._config and self._config.enable_prepared_statements:
                    result = await self._execute_prepared(conn, query, args)
                else:
                    result = await conn.execute(query, *args)
                
                # Cache-Update
                if use_cache and query.strip().upper().startswith('SELECT'):
                    self._cache_result(query_hash, result)
                
                self._total_queries += 1
                execution_time = time.time() - start_time
                self._update_query_stats(query_hash, execution_time)
                
                return result
                
        except Exception as e:
            self._failed_queries += 1
            execution_time = time.time() - start_time
            if execution_time > (self._config.max_query_time if self._config else 30):
                self._slow_queries += 1
            logger.error(f"Database execute failed: {e}, Query: {query[:100]}...")
            raise
    
    async def fetch(self, query: str, *args, use_cache: bool = True) -> list:
        """Führt eine SELECT-Query aus mit intelligentez Caching"""
        start_time = time.time()
        query_hash = self._get_query_hash(query, args)
        
        try:
            # Cache-Check
            if use_cache:
                cached_result = self._get_cached_result(query_hash)
                if cached_result is not None:
                    self._cache_hits += 1
                    return cached_result
                self._cache_misses += 1
            
            async with self.acquire() as conn:
                # Prepared Statement verwenden
                if self._config and self._config.enable_prepared_statements:
                    result = await self._fetch_prepared(conn, query, args)
                else:
                    result = await conn.fetch(query, *args)
                
                # Cache-Update
                if use_cache:
                    self._cache_result(query_hash, result)
                
                self._total_queries += 1
                execution_time = time.time() - start_time
                self._update_query_stats(query_hash, execution_time)
                
                return result
                
        except Exception as e:
            self._failed_queries += 1
            execution_time = time.time() - start_time
            if execution_time > (self._config.max_query_time if self._config else 30):
                self._slow_queries += 1
            logger.error(f"Database fetch failed: {e}, Query: {query[:100]}...")
            raise
    
    async def fetchrow(self, query: str, *args, use_cache: bool = True) -> Optional[asyncpg.Record]:
        """Führt eine SELECT-Query aus und gibt eine Row zurück"""
        result = await self.fetch(query, *args, use_cache=use_cache)
        return result[0] if result else None
    
    async def fetchval(self, query: str, *args, use_cache: bool = True) -> Any:
        """Führt eine SELECT-Query aus und gibt einen Wert zurück"""
        row = await self.fetchrow(query, *args, use_cache=use_cache)
        return row[0] if row else None
    
    @asynccontextmanager
    async def transaction(self):
        """Context Manager für Database-Transaktionen"""
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn
    
    # Batch Operations für bessere Performance
    async def batch_execute(self, queries: List[Tuple[str, Tuple]]) -> List[str]:
        """Führt mehrere Queries in einer Transaktion aus"""
        start_time = time.time()
        
        try:
            async with self.transaction() as conn:
                results = []
                for query, args in queries:
                    result = await conn.execute(query, *args)
                    results.append(result)
                
                execution_time = time.time() - start_time
                self._total_queries += len(queries)
                logger.debug(f"Batch executed {len(queries)} queries in {execution_time:.4f}s")
                
                return results
                
        except Exception as e:
            self._failed_queries += len(queries)
            logger.error(f"Batch execution failed: {e}")
            raise
    
    async def batch_fetch(self, queries: List[Tuple[str, Tuple]]) -> List[List]:
        """Führt mehrere SELECT-Queries in einer Transaktion aus"""
        start_time = time.time()
        
        try:
            async with self.transaction() as conn:
                results = []
                for query, args in queries:
                    result = await conn.fetch(query, *args)
                    results.append(result)
                
                execution_time = time.time() - start_time
                self._total_queries += len(queries)
                logger.debug(f"Batch fetched {len(queries)} queries in {execution_time:.4f}s")
                
                return results
                
        except Exception as e:
            self._failed_queries += len(queries)
            logger.error(f"Batch fetch failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Überprüft die Database-Connection Health"""
        try:
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @property
    def is_initialized(self) -> bool:
        """Gibt zurück ob der Pool initialisiert ist"""
        return self._pool is not None
    
    @property
    def pool_stats(self) -> Dict[str, Any]:
        """Gibt erweiterte Pool-Statistiken zurück"""
        if not self._pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "pool": {
                "size": self._pool.get_size(),
                "min_size": self._pool._min_size,
                "max_size": self._pool._max_size,
                "free_connections": self._pool.get_free_count(),
                "active_connections": self._pool.get_size() - self._pool.get_free_count()
            },
            "performance": {
                "total_queries": self._total_queries,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_ratio": (self._cache_hits / max(1, self._cache_hits + self._cache_misses)) * 100,
                "slow_queries": self._slow_queries,
                "failed_queries": self._failed_queries,
                "prepared_statements_count": len(self._prepared_statements),
                "cached_queries_count": len(self._query_cache)
            },
            "top_queries": self._get_top_queries(5)
        }
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Erstellt detaillierten Performance-Report"""
        return {
            "pool_stats": self.pool_stats,
            "query_performance": {
                "total_queries": self._total_queries,
                "cache_efficiency": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_ratio": (self._cache_hits / max(1, self._cache_hits + self._cache_misses)) * 100
                },
                "error_rate": (self._failed_queries / max(1, self._total_queries)) * 100,
                "slow_query_rate": (self._slow_queries / max(1, self._total_queries)) * 100
            },
            "top_slow_queries": self._get_top_queries(10),
            "configuration": {
                "min_connections": self._config.min_connections if self._config else "N/A",
                "max_connections": self._config.max_connections if self._config else "N/A",
                "query_cache_enabled": self._config.enable_query_cache if self._config else False,
                "prepared_statements_enabled": self._config.enable_prepared_statements if self._config else False,
                "cache_size": len(self._query_cache),
                "prepared_statements_count": len(self._prepared_statements)
            }
        }
    
    # Performance Helper Methods
    def _get_query_hash(self, query: str, args: Tuple) -> str:
        """Erstellt einen Hash für Query-Caching"""
        query_str = query + str(args)
        return hashlib.md5(query_str.encode()).hexdigest()[:16]
    
    def _get_cached_result(self, query_hash: str) -> Optional[Any]:
        """Holt gecachtes Ergebnis"""
        if not self._config or not self._config.enable_query_cache:
            return None
        return self._query_cache.get(query_hash)
    
    def _cache_result(self, query_hash: str, result: Any):
        """Cached Query-Ergebnis"""
        if not self._config or not self._config.enable_query_cache:
            return
        
        # LRU-Cache-Management
        if len(self._query_cache) >= self._config.query_cache_size:
            oldest_key = self._query_cache_order.popleft()
            self._query_cache.pop(oldest_key, None)
        
        self._query_cache[query_hash] = result
        self._query_cache_order.append(query_hash)
    
    def _update_query_stats(self, query_hash: str, execution_time: float):
        """Aktualisiert Query-Statistiken"""
        if query_hash not in self._query_stats:
            self._query_stats[query_hash] = QueryStats(query_hash)
        self._query_stats[query_hash].update(execution_time)
        
        # Slow Query Detection
        if execution_time > (self._config.max_query_time if self._config else 30):
            self._slow_queries += 1
            logger.warning(f"Slow query detected: {execution_time:.4f}s - Hash: {query_hash}")
    
    def _get_top_queries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Holt die langsamsten Queries"""
        sorted_stats = sorted(
            self._query_stats.values(),
            key=lambda x: x.avg_time,
            reverse=True
        )[:limit]
        
        return [{
            "query_hash": stat.query_hash,
            "execution_count": stat.execution_count,
            "avg_time": f"{stat.avg_time:.4f}s",
            "max_time": f"{stat.max_time:.4f}s",
            "total_time": f"{stat.total_time:.4f}s"
        } for stat in sorted_stats]
    
    async def _connection_init(self, conn):
        """Connection-Initialisierung mit Performance-Settings"""
        if self._config:
            # Set application name for monitoring
            await conn.execute(f"SET application_name = 'aktienanalyse_pool_{os.getpid()}'")
            
            # Performance-Optimierungen für SSD und moderne Hardware
            await conn.execute("SET random_page_cost = 1.1")  # SSD-Optimierung
            await conn.execute("SET effective_cache_size = '1GB'")
            await conn.execute("SET shared_buffers = '256MB'")
    
    async def _execute_prepared(self, conn, query: str, args: Tuple) -> str:
        """Führt Prepared Statement aus"""
        query_hash = self._get_query_hash(query, ())
        
        if query_hash not in self._prepared_statements:
            stmt_name = f"stmt_{query_hash}"
            await conn.execute(f"PREPARE {stmt_name} AS {query}")
            self._prepared_statements[query_hash] = stmt_name
        
        stmt_name = self._prepared_statements[query_hash]
        return await conn.execute(f"EXECUTE {stmt_name}", *args)
    
    async def _fetch_prepared(self, conn, query: str, args: Tuple) -> List:
        """Führt Prepared Statement für SELECT aus"""
        query_hash = self._get_query_hash(query, ())
        
        if query_hash not in self._prepared_statements:
            stmt_name = f"stmt_{query_hash}"
            await conn.execute(f"PREPARE {stmt_name} AS {query}")
            self._prepared_statements[query_hash] = stmt_name
        
        stmt_name = self._prepared_statements[query_hash]
        return await conn.fetch(f"EXECUTE {stmt_name}", *args)
    
    async def _cache_cleanup_task(self):
        """Hintergrundtask für Cache-Cleanup"""
        while self._pool:
            try:
                await asyncio.sleep(300)  # Alle 5 Minuten
                current_time = time.time()
                
                # Entferne alte Cache-Einträge (älter als 1 Stunde)
                keys_to_remove = []
                for query_hash, stats in self._query_stats.items():
                    if current_time - stats.last_executed > 3600:
                        keys_to_remove.append(query_hash)
                
                for key in keys_to_remove:
                    self._query_stats.pop(key, None)
                    self._query_cache.pop(key, None)
                
                if keys_to_remove:
                    logger.debug(f"Cache cleanup: removed {len(keys_to_remove)} old entries")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")


# Global Enhanced Singleton Instance
enhanced_db_pool = EnhancedDatabasePool()


# Convenience Functions für häufige Operationen
async def init_enhanced_db_pool(pool_config: Optional[PoolConfig] = None):
    """Initialisiert den Enhanced Database Pool"""
    await enhanced_db_pool.initialize(pool_config)


async def close_enhanced_db_pool():
    """Schließt den Enhanced Database Pool"""
    await enhanced_db_pool.close()


# Context Manager für einfache Nutzung
@asynccontextmanager
async def get_enhanced_db_connection():
    """Enhanced Context Manager für Database-Connections"""
    async with enhanced_db_pool.acquire() as conn:
        yield conn


# Performance Decorator
def track_query_performance(func):
    """Decorator für automatisches Query-Performance-Tracking"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"Query executed in {execution_time:.4f}s: {func.__name__}")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.warning(f"Query failed after {execution_time:.4f}s: {func.__name__} - {e}")
            raise
    return wrapper


# Enhanced Decorator für Pool-Initialisierung
def ensure_enhanced_db_pool(func):
    """Decorator der sicherstellt, dass der Enhanced DB-Pool initialisiert ist"""
    async def wrapper(*args, **kwargs):
        if not enhanced_db_pool.is_initialized:
            await init_enhanced_db_pool()
        return await func(*args, **kwargs)
    return wrapper