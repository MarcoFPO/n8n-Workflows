#!/usr/bin/env python3
"""
Database Connection Manager v1.0.0 - Centralized Database Connection Pool
Clean Architecture Implementation für Aktienanalyse-Ökosystem

CENTRALIZED CONNECTION MANAGEMENT:
- Single Database Connection Pool für alle Services
- Environment-based Configuration mit Fallbacks
- Health Monitoring und Connection Validation
- Automatic Retry Logic und Error Handling
- Resource Management und Graceful Shutdown

Code-Qualität: HÖCHSTE PRIORITÄT - Architecture Refactoring
Autor: Claude Code - Database Architecture Specialist
Datum: 25. August 2025
Version: 1.0.0 (Initial Centralized Implementation)
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
import asyncpg
import json

logger = logging.getLogger(__name__)


class DatabaseConfiguration:
    """
    Centralized Database Configuration
    
    SINGLE RESPONSIBILITY: Configuration Management
    Environment-aware Configuration mit Production Deployment
    """
    
    def __init__(self):
        # Production deployment auf 10.1.1.174
        self.host = os.getenv("POSTGRES_HOST", "10.1.1.174")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "aktienanalyse_events")
        self.user = os.getenv("POSTGRES_USER", "aktienanalyse")
        
        # SECURITY: Environment-based Password
        self.password = os.getenv("POSTGRES_PASSWORD")
        if not self.password:
            raise ValueError("POSTGRES_PASSWORD environment variable must be set for security!")
        
<<<<<<< HEAD
        # Connection Pool Settings - Production optimized
        self.min_pool_size = int(os.getenv("DB_POOL_MIN_SIZE", "5"))
        self.max_pool_size = int(os.getenv("DB_POOL_MAX_SIZE", "25"))
        self.command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        self.query_timeout = int(os.getenv("DB_QUERY_TIMEOUT", "30"))
        
        # Connection Settings
        self.server_settings = {
            "application_name": "aktienanalyse_ecosystem",
            "timezone": "UTC",
            "statement_timeout": "30s",
            "idle_in_transaction_session_timeout": "60s"
        }
        
        # Retry Settings
        self.max_retries = int(os.getenv("DB_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("DB_RETRY_DELAY", "1.0"))
        
    def get_connection_url(self) -> str:
        """Get properly formatted PostgreSQL connection URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get connection kwargs for asyncpg"""
=======
        # Connection Pool Configuration
        self.min_connections = int(os.getenv("POSTGRES_MIN_CONNECTIONS", "2"))
        self.max_connections = int(os.getenv("POSTGRES_MAX_CONNECTIONS", "10"))
        self.connection_timeout = float(os.getenv("POSTGRES_TIMEOUT", "30.0"))
        
        # Advanced Settings
        self.command_timeout = float(os.getenv("POSTGRES_COMMAND_TIMEOUT", "60.0"))
        self.retry_attempts = int(os.getenv("POSTGRES_RETRY_ATTEMPTS", "3"))
        self.retry_delay = float(os.getenv("POSTGRES_RETRY_DELAY", "1.0"))
        
    def get_connection_string(self) -> str:
        """Secure Connection String für asyncpg"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def get_pool_config(self) -> Dict[str, Any]:
        """Pool Configuration für asyncpg.create_pool"""
>>>>>>> 9c9fee7d29d51b982d5ae7fef40e6d0c8940cb15
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
<<<<<<< HEAD
            "server_settings": self.server_settings,
            "command_timeout": self.command_timeout
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Configuration als Dictionary (ohne sensible Daten)"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "min_pool_size": self.min_pool_size,
            "max_pool_size": self.max_pool_size,
            "command_timeout": self.command_timeout,
            "query_timeout": self.query_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay
=======
            "min_size": self.min_connections,
            "max_size": self.max_connections,
            "timeout": self.connection_timeout,
            "command_timeout": self.command_timeout,
            "server_settings": {
                "application_name": "aktienanalyse_ecosystem"
            }
>>>>>>> 9c9fee7d29d51b982d5ae7fef40e6d0c8940cb15
        }


class DatabaseConnectionManager:
    """
    Centralized Database Connection Pool Manager
    
<<<<<<< HEAD
    CLEAN ARCHITECTURE PRINCIPLES:
    - Single Responsibility: Database Connection Management
    - Open/Closed: Extensible für neue Connection Types
    - Dependency Inversion: Interface-based Dependencies
    
    Ersetzt alle 29 separaten Connection Pool Implementierungen
    """
    
    _instance: Optional['DatabaseConnectionManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls, config: Optional[DatabaseConfiguration] = None):
        """Singleton Pattern für globale Connection Pool Verwaltung"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[DatabaseConfiguration] = None):
        if self._initialized:
            return
            
        self.config = config or DatabaseConfiguration()
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized_flag = False
        self._connection_stats = {
            "total_connections": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "retries_performed": 0,
            "last_health_check": None
        }
        
        logger.info("Database Connection Manager initialized with config:")
        logger.info(self.config.to_dict())
    
    async def initialize(self) -> None:
        """
        Initialize centralized connection pool
        
        THREAD-SAFE: Uses asyncio.Lock für concurrent initialization
        """
        async with self._lock:
            if self._initialized_flag:
                logger.info("Database Connection Manager already initialized")
                return
            
            try:
                logger.info("🗄️ Initializing centralized database connection pool")
                
                # Create connection pool with production settings
                self.pool = await asyncpg.create_pool(
                    **self.config.get_connection_kwargs(),
                    min_size=self.config.min_pool_size,
                    max_size=self.config.max_pool_size
                )
                
                # Test connection
                async with self.pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")
                    if result != 1:
                        raise Exception("Database connection test failed")
                
                self._initialized_flag = True
                self._connection_stats["total_connections"] = self.config.max_pool_size
                
                logger.info("✅ Centralized database connection pool initialized successfully")
                logger.info(f"Pool size: {self.config.min_pool_size}-{self.config.max_pool_size} connections")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize database connection pool: {e}")
                if self.pool:
                    await self.pool.close()
                    self.pool = None
                raise
    
    async def close(self) -> None:
        """
        Close centralized connection pool
        
        Graceful shutdown für alle aktiven Connections
        """
        async with self._lock:
            if self.pool and self._initialized_flag:
                try:
                    logger.info("🗄️ Closing centralized database connection pool")
                    await self.pool.close()
                    logger.info("✅ Database connection pool closed")
                except Exception as e:
                    logger.error(f"❌ Error closing database pool: {e}")
                finally:
                    self.pool = None
                    self._initialized_flag = False
=======
    SINGLE RESPONSIBILITY: Database Connection Management
    - Pool Lifecycle Management (Create/Acquire/Release/Close)
    - Health Monitoring und Validation
    - Error Handling und Recovery
    - Performance Metrics Collection
    """
    
    def __init__(self):
        self.config = DatabaseConfiguration()
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()
        self._health_check_interval = 30.0  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_healthy = False
        self._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "last_health_check": None
        }
        
    async def initialize(self) -> None:
        """
        Initialize Connection Pool
        
        DEFENSIVE PROGRAMMING: Comprehensive Error Handling
        """
        async with self._lock:
            if self.pool is not None:
                logger.warning("Connection pool already initialized")
                return
                
            try:
                logger.info(f"Initializing PostgreSQL connection pool to {self.config.host}:{self.config.port}")
                
                pool_config = self.config.get_pool_config()
                self.pool = await asyncpg.create_pool(**pool_config)
                
                # Initial Health Check
                await self._perform_health_check()
                
                # Start Background Health Monitoring
                self._health_check_task = asyncio.create_task(self._health_monitor_loop())
                
                logger.info("Database connection pool initialized successfully")
                self._is_healthy = True
                
            except Exception as e:
                logger.error(f"Failed to initialize database connection pool: {e}")
                self._is_healthy = False
                raise
                
    async def close(self) -> None:
        """
        Graceful Shutdown
        
        RESOURCE MANAGEMENT: Clean Connection Closure
        """
        async with self._lock:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                    
            if self.pool:
                logger.info("Closing database connection pool")
                await self.pool.close()
                self.pool = None
                self._is_healthy = False
                logger.info("Database connection pool closed")
>>>>>>> 9c9fee7d29d51b982d5ae7fef40e6d0c8940cb15
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """
<<<<<<< HEAD
        Get database connection from centralized pool
        
        RESOURCE MANAGEMENT: Automatic connection return to pool
        ERROR HANDLING: Comprehensive error handling und logging
        """
        if not self._initialized_flag or not self.pool:
            raise RuntimeError("Database Connection Manager not initialized - call initialize() first")
        
        connection = None
        try:
            # Acquire connection from pool
            connection = await self.pool.acquire()
            yield connection
            
        except Exception as e:
            self._connection_stats["failed_queries"] += 1
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            # Always return connection to pool
            if connection:
                try:
                    await self.pool.release(connection)
                except Exception as e:
                    logger.error(f"Error releasing connection to pool: {e}")
    
    async def execute_query(self, query: str, *args, retry_count: Optional[int] = None) -> str:
        """
        Execute parameterized query mit automatic retry
        
        RETRY LOGIC: Automatic retry bei temporären Fehlern
        SECURITY: Parameterized queries gegen SQL Injection
        """
        retry_count = retry_count or self.config.max_retries
        
        for attempt in range(retry_count + 1):
            try:
                async with self.get_connection() as conn:
                    result = await asyncio.wait_for(
                        conn.execute(query, *args),
                        timeout=self.config.query_timeout
                    )
                    
                    self._connection_stats["successful_queries"] += 1
                    logger.debug(f"Query executed successfully: {query[:100]}...")
                    return result
                    
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError, asyncio.TimeoutError) as e:
                if attempt < retry_count:
                    self._connection_stats["retries_performed"] += 1
                    logger.warning(f"Query failed (attempt {attempt + 1}/{retry_count + 1}): {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    self._connection_stats["failed_queries"] += 1
                    logger.error(f"Query failed after {retry_count + 1} attempts: {e}")
                    raise
            except Exception as e:
                self._connection_stats["failed_queries"] += 1
                logger.error(f"Query execution error: {e}")
                raise
    
    async def fetch_query(self, query: str, *args, retry_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch results from parameterized query mit automatic retry
        
        RETURN FORMAT: List of dictionaries für easy consumption
        """
        retry_count = retry_count or self.config.max_retries
        
        for attempt in range(retry_count + 1):
            try:
                async with self.get_connection() as conn:
                    rows = await asyncio.wait_for(
                        conn.fetch(query, *args),
                        timeout=self.config.query_timeout
                    )
                    
                    result = [dict(row) for row in rows]
                    self._connection_stats["successful_queries"] += 1
                    logger.debug(f"Query fetched {len(result)} rows: {query[:100]}...")
                    return result
                    
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError, asyncio.TimeoutError) as e:
                if attempt < retry_count:
                    self._connection_stats["retries_performed"] += 1
                    logger.warning(f"Fetch failed (attempt {attempt + 1}/{retry_count + 1}): {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    self._connection_stats["failed_queries"] += 1
                    logger.error(f"Fetch failed after {retry_count + 1} attempts: {e}")
                    raise
            except Exception as e:
                self._connection_stats["failed_queries"] += 1
                logger.error(f"Fetch execution error: {e}")
                raise
    
    async def fetch_one_query(self, query: str, *args, retry_count: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch single result from parameterized query mit automatic retry
        
        RETURN FORMAT: Dictionary oder None
        """
        retry_count = retry_count or self.config.max_retries
        
        for attempt in range(retry_count + 1):
            try:
                async with self.get_connection() as conn:
                    row = await asyncio.wait_for(
                        conn.fetchrow(query, *args),
                        timeout=self.config.query_timeout
                    )
                    
                    result = dict(row) if row else None
                    self._connection_stats["successful_queries"] += 1
                    logger.debug(f"Query fetchone successful: {query[:100]}...")
                    return result
                    
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError, asyncio.TimeoutError) as e:
                if attempt < retry_count:
                    self._connection_stats["retries_performed"] += 1
                    logger.warning(f"Fetchone failed (attempt {attempt + 1}/{retry_count + 1}): {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    self._connection_stats["failed_queries"] += 1
                    logger.error(f"Fetchone failed after {retry_count + 1} attempts: {e}")
                    raise
            except Exception as e:
                self._connection_stats["failed_queries"] += 1
                logger.error(f"Fetchone execution error: {e}")
                raise
    
    async def execute_transaction(self, queries: List[tuple], retry_count: Optional[int] = None) -> List[Any]:
        """
        Execute multiple queries in a transaction
        
        ACID COMPLIANCE: All queries succeed oder all fail
        PARAMETER FORMAT: [(query, args), (query, args), ...]
        """
        retry_count = retry_count or self.config.max_retries
        
        for attempt in range(retry_count + 1):
            try:
                async with self.get_connection() as conn:
                    async with conn.transaction():
                        results = []
                        for query, args in queries:
                            result = await conn.execute(query, *args)
                            results.append(result)
                        
                        self._connection_stats["successful_queries"] += len(queries)
                        logger.debug(f"Transaction executed with {len(queries)} queries")
                        return results
                        
            except (asyncpg.ConnectionDoesNotExistError, asyncpg.InterfaceError, asyncio.TimeoutError) as e:
                if attempt < retry_count:
                    self._connection_stats["retries_performed"] += 1
                    logger.warning(f"Transaction failed (attempt {attempt + 1}/{retry_count + 1}): {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                else:
                    self._connection_stats["failed_queries"] += len(queries)
                    logger.error(f"Transaction failed after {retry_count + 1} attempts: {e}")
                    raise
            except Exception as e:
                self._connection_stats["failed_queries"] += len(queries)
                logger.error(f"Transaction execution error: {e}")
                raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive database health check
        
        CONNECTION POOL STATUS: Active/Idle connections
        PERFORMANCE METRICS: Query success/failure rates
        """
        try:
            self._connection_stats["last_health_check"] = datetime.now().isoformat()
            
            if not self._initialized_flag or not self.pool:
                return {
                    "status": "unhealthy",
                    "error": "Database Connection Manager not initialized",
                    "stats": self._connection_stats
                }
            
            # Test connection
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                
                # Get pool statistics
                pool_stats = {
                    "size": self.pool.get_size(),
                    "idle": self.pool.get_idle_size(),
                    "min_size": self.config.min_pool_size,
                    "max_size": self.config.max_pool_size
                }
                
                # Calculate success rate
                total_queries = self._connection_stats["successful_queries"] + self._connection_stats["failed_queries"]
                success_rate = (self._connection_stats["successful_queries"] / total_queries * 100) if total_queries > 0 else 100
                
                return {
                    "status": "healthy",
                    "connection_test": "passed",
                    "pool_stats": pool_stats,
                    "performance_stats": {
                        **self._connection_stats,
                        "success_rate_percent": round(success_rate, 2)
                    },
                    "configuration": self.config.to_dict()
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self._connection_stats
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self._connection_stats.copy()
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._initialized_flag and self.pool is not None


# Global Database Connection Manager Instance
_db_manager: Optional[DatabaseConnectionManager] = None


def get_database_manager() -> DatabaseConnectionManager:
    """
    Get global database manager instance
    
    SINGLETON ACCESS: Thread-safe singleton pattern
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
    return _db_manager


async def initialize_database_manager(config: Optional[DatabaseConfiguration] = None) -> None:
    """Initialize global database manager"""
    manager = get_database_manager()
    if config:
        manager.config = config
    await manager.initialize()


async def close_database_manager() -> None:
    """Close global database manager"""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None


# Convenience Functions für Easy Migration
async def get_db_connection():
    """
    Get database connection (backward compatibility)
    
    MIGRATION SUPPORT: Drop-in replacement für alte Connection-Implementierungen
    """
    manager = get_database_manager()
    async with manager.get_connection() as conn:
        yield conn


async def execute_db_query(query: str, *args) -> str:
    """Execute database query (convenience function)"""
    manager = get_database_manager()
    return await manager.execute_query(query, *args)


async def fetch_db_query(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch database query results (convenience function)"""
    manager = get_database_manager()
    return await manager.fetch_query(query, *args)


async def fetch_db_one_query(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch single database query result (convenience function)"""
    manager = get_database_manager()
    return await manager.fetch_one_query(query, *args)


# Context Manager für Easy Service Integration
@asynccontextmanager
async def database_manager_context(config: Optional[DatabaseConfiguration] = None):
    """
    Context Manager für Database Manager Lifecycle
    
    RESOURCE MANAGEMENT: Automatic initialization and cleanup
    """
    manager = get_database_manager()
    if config:
        manager.config = config
    
    await manager.initialize()
    try:
        yield manager
    finally:
        await manager.close()


if __name__ == "__main__":
    # Test Database Connection Manager
    import asyncio
    
    async def test_database_manager():
        """Test Database Connection Manager functionality"""
        print("🧪 Testing Database Connection Manager")
        
        try:
            # Initialize
            config = DatabaseConfiguration()
            manager = get_database_manager()
            await manager.initialize()
            
            # Test query
            result = await manager.fetch_one_query("SELECT 1 as test, NOW() as timestamp")
            print(f"✅ Test query result: {result}")
            
            # Health check
            health = await manager.health_check()
            print(f"✅ Health check: {health['status']}")
            
            # Stats
            stats = manager.get_stats()
            print(f"✅ Stats: {stats}")
            
            print("✅ Database Connection Manager test successful")
            
        except Exception as e:
            print(f"❌ Database Connection Manager test failed: {e}")
        finally:
            await manager.close()
    
    # Run test
=======
        Context Manager für Database Connections
        
        AUTOMATIC RESOURCE MANAGEMENT: Connection Acquire/Release
        """
        if not self.pool:
            raise RuntimeError("Database connection pool not initialized")
            
        connection = None
        try:
            connection = await self.pool.acquire()
            self._connection_stats["total_connections"] += 1
            self._connection_stats["active_connections"] += 1
            
            yield connection
            
        except Exception as e:
            self._connection_stats["failed_connections"] += 1
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                await self.pool.release(connection)
                self._connection_stats["active_connections"] -= 1
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Execute Query mit Retry Logic
        
        RESILIENCE PATTERN: Automatic Retry mit Exponential Backoff
        """
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.get_connection() as connection:
                    result = await connection.fetch(query, *args)
                    return [dict(record) for record in result]
                    
            except Exception as e:
                logger.warning(f"Query execution failed (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                
                if attempt == self.config.retry_attempts - 1:
                    raise
                    
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                
    async def execute_command(self, command: str, *args) -> str:
        """
        Execute Command (INSERT/UPDATE/DELETE) mit Retry Logic
        """
        for attempt in range(self.config.retry_attempts):
            try:
                async with self.get_connection() as connection:
                    result = await connection.execute(command, *args)
                    return result
                    
            except Exception as e:
                logger.warning(f"Command execution failed (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                
                if attempt == self.config.retry_attempts - 1:
                    raise
                    
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
    
    async def _perform_health_check(self) -> None:
        """
        Perform Database Health Check
        """
        try:
            async with self.get_connection() as connection:
                await connection.fetch("SELECT 1 as health_check")
                self._is_healthy = True
                self._connection_stats["last_health_check"] = datetime.utcnow().isoformat()
                logger.debug("Database health check: OK")
                
        except Exception as e:
            self._is_healthy = False
            logger.error(f"Database health check failed: {e}")
            
    async def _health_monitor_loop(self) -> None:
        """
        Background Health Monitoring Loop
        """
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                
    def is_healthy(self) -> bool:
        """Check if Database Connection Pool is healthy"""
        return self._is_healthy and self.pool is not None
        
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get Connection Pool Statistics"""
        stats = self._connection_stats.copy()
        if self.pool:
            stats.update({
                "pool_size": self.pool.get_size(),
                "pool_min_size": self.pool.get_min_size(),
                "pool_max_size": self.pool.get_max_size(),
                "pool_idle_size": self.pool.get_idle_size()
            })
        return stats


# SINGLETON PATTERN: Global Database Manager Instance
_database_manager: Optional[DatabaseConnectionManager] = None


async def get_database_manager() -> DatabaseConnectionManager:
    """
    Get Global Database Manager Instance
    
    SINGLETON PATTERN: Ensure Single Connection Pool
    """
    global _database_manager
    
    if _database_manager is None:
        _database_manager = DatabaseConnectionManager()
        await _database_manager.initialize()
        
    return _database_manager


async def close_database_manager() -> None:
    """
    Close Global Database Manager
    
    CLEANUP: For Application Shutdown
    """
    global _database_manager
    
    if _database_manager:
        await _database_manager.close()
        _database_manager = None


# CONVENIENCE FUNCTIONS für Direct Usage
async def execute_query(query: str, *args) -> List[Dict[str, Any]]:
    """Execute Query using Global Database Manager"""
    manager = await get_database_manager()
    return await manager.execute_query(query, *args)


async def execute_command(command: str, *args) -> str:
    """Execute Command using Global Database Manager"""
    manager = await get_database_manager()
    return await manager.execute_command(command, *args)


async def get_connection():
    """Get Database Connection using Global Database Manager"""
    manager = await get_database_manager()
    return manager.get_connection()


def is_database_healthy() -> bool:
    """Check if Global Database Manager is healthy"""
    global _database_manager
    return _database_manager.is_healthy() if _database_manager else False


if __name__ == "__main__":
    async def test_database_manager():
        """Test Database Manager Functionality"""
        try:
            # Initialize
            manager = await get_database_manager()
            print(f"Database Manager initialized: {manager.is_healthy()}")
            
            # Test Query
            result = await execute_query("SELECT NOW() as current_time")
            print(f"Test query result: {result}")
            
            # Connection Stats
            stats = manager.get_connection_stats()
            print(f"Connection stats: {json.dumps(stats, indent=2)}")
            
        except Exception as e:
            print(f"Test failed: {e}")
        finally:
            await close_database_manager()
    
    # Run Test
>>>>>>> 9c9fee7d29d51b982d5ae7fef40e6d0c8940cb15
    asyncio.run(test_database_manager())