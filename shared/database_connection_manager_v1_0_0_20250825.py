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
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "min_size": self.min_connections,
            "max_size": self.max_connections,
            "timeout": self.connection_timeout,
            "command_timeout": self.command_timeout,
            "server_settings": {
                "application_name": "aktienanalyse_ecosystem"
            }
        }


class DatabaseConnectionManager:
    """
    Centralized Database Connection Pool Manager
    
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
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """
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
    asyncio.run(test_database_manager())