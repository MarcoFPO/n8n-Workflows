#!/usr/bin/env python3
"""
Centralized Database Connection Pool - Clean Architecture
Singleton Pattern für einheitliche PostgreSQL Connections

Alle Services sollen diese zentralisierte Connection Pool Implementierung
verwenden anstatt separate Database-Connections zu erstellen.
"""

import asyncpg
import asyncio
import os
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
from .config_manager import config

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Database Pool Konfiguration"""
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: int = 60
    server_settings: Dict[str, str] = None
    
    def __post_init__(self):
        if self.server_settings is None:
            self.server_settings = {
                'application_name': 'aktienanalyse_pool',
                'timezone': 'UTC'
            }


class DatabasePool:
    """Singleton Database Connection Pool für alle Services"""
    
    _instance: Optional['DatabasePool'] = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'DatabasePool':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, pool_config: Optional[PoolConfig] = None):
        """Initialisiert den Connection Pool (Thread-Safe)"""
        async with self._lock:
            if self._pool is None:
                if pool_config is None:
                    pool_config = PoolConfig()
                
                try:
                    self._pool = await asyncpg.create_pool(
                        host=config.database.host,
                        port=config.database.port,
                        database=config.database.database,
                        user=config.database.user,
                        password=config.database.password,
                        min_size=pool_config.min_connections,
                        max_size=pool_config.max_connections,
                        command_timeout=pool_config.command_timeout,
                        server_settings=pool_config.server_settings
                    )
                    logger.info(
                        f"Database pool initialized: {pool_config.min_connections}-{pool_config.max_connections} connections"
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize database pool: {e}")
                    raise
    
    async def close(self):
        """Schließt den Connection Pool"""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
                logger.info("Database pool closed")
    
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
    
    async def execute(self, query: str, *args) -> str:
        """Führt eine SQL-Query aus und gibt Ergebnis zurück"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Führt eine SELECT-Query aus und gibt Rows zurück"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Führt eine SELECT-Query aus und gibt eine Row zurück"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Führt eine SELECT-Query aus und gibt einen Wert zurück"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    @asynccontextmanager
    async def transaction(self):
        """Context Manager für Database-Transaktionen"""
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn
    
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
        """Gibt Pool-Statistiken zurück"""
        if not self._pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "initialized",
            "size": self._pool.get_size(),
            "min_size": self._pool._min_size,
            "max_size": self._pool._max_size,
            "free_connections": self._pool.get_size() - self._pool.get_free_count(),
            "free_count": self._pool.get_free_count()
        }


# Global Singleton Instance
db_pool = DatabasePool()


# Convenience Functions für häufige Operationen
async def init_db_pool(pool_config: Optional[PoolConfig] = None):
    """Initialisiert den globalen Database Pool"""
    await db_pool.initialize(pool_config)


async def close_db_pool():
    """Schließt den globalen Database Pool"""
    await db_pool.close()


# Context Manager für einfache Nutzung
@asynccontextmanager
async def get_db_connection():
    """Convenience Context Manager für Database-Connections"""
    async with db_pool.acquire() as conn:
        yield conn


# Decorator für automatische Pool-Initialisierung
def ensure_db_pool(func):
    """Decorator der sicherstellt, dass der DB-Pool initialisiert ist"""
    async def wrapper(*args, **kwargs):
        if not db_pool.is_initialized:
            await init_db_pool()
        return await func(*args, **kwargs)
    return wrapper