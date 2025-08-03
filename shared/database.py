"""
Database utilities for Aktienanalyse-Ökosystem
Provides connection pool management and database utilities
"""

import os
import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import structlog
from security import ParameterizedQuery

logger = structlog.get_logger(__name__)


class DatabaseConfig:
    """Database configuration from environment"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.host = os.getenv("DATABASE_HOST", "localhost")
        self.port = int(os.getenv("DATABASE_PORT", "5432"))
        self.database = os.getenv("DATABASE_NAME", "aktienanalyse_events")
        self.user = os.getenv("DATABASE_USER", "aktienanalyse_user")
        self.password = os.getenv("DATABASE_PASSWORD")
        
        # Connection pool settings
        self.min_size = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
        self.max_size = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
        self.command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        self.server_settings = {
            "application_name": "aktienanalyse_service",
            "timezone": "UTC"
        }
    
    def get_connection_url(self) -> str:
        """Get properly formatted connection URL"""
        if self.database_url:
            return self.database_url
            
        if not self.password:
            raise ValueError("DATABASE_PASSWORD environment variable is required")
            
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DatabaseManager:
    """Centralized database connection management"""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.pool: Optional[asyncpg.Pool] = None
        self.query_builder = ParameterizedQuery()
        
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            connection_url = self.config.get_connection_url()
            
            self.pool = await asyncpg.create_pool(
                connection_url,
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                command_timeout=self.config.command_timeout,
                server_settings=self.config.server_settings
            )
            
            logger.info("Database connection pool initialized", 
                       min_size=self.config.min_size, 
                       max_size=self.config.max_size)
                       
        except Exception as e:
            logger.error("Failed to initialize database pool", error=str(e))
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
            
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error("Database connection error", error=str(e))
                raise
    
    async def execute_query(self, query: str, *args) -> str:
        """Execute parameterized query"""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(query, *args)
                logger.debug("Query executed successfully", query=query[:100])
                return result
            except Exception as e:
                logger.error("Query execution failed", 
                           query=query[:100], 
                           error=str(e))
                raise
    
    async def fetch_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch results from parameterized query"""
        async with self.get_connection() as conn:
            try:
                rows = await conn.fetch(query, *args)
                result = [dict(row) for row in rows]
                logger.debug("Query fetched successfully", 
                           query=query[:100], 
                           row_count=len(result))
                return result
            except Exception as e:
                logger.error("Query fetch failed", 
                           query=query[:100], 
                           error=str(e))
                raise
    
    async def fetch_one_query(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch single result from parameterized query"""
        async with self.get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *args)
                result = dict(row) if row else None
                logger.debug("Query fetchone successful", 
                           query=query[:100], 
                           found=result is not None)
                return result
            except Exception as e:
                logger.error("Query fetchone failed", 
                           query=query[:100], 
                           error=str(e))
                raise


class EventStore:
    """Event store operations using parameterized queries"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def store_event(self, stream_id: str, event_type: str, event_version: int,
                         aggregate_id: str, aggregate_type: str, 
                         event_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> str:
        """Store event with parameterized query"""
        import json
        
        query = self.db.query_builder.build_insert_events_query()
        metadata = metadata or {}
        
        try:
            result = await self.db.execute_query(
                query,
                stream_id,
                event_type, 
                event_version,
                aggregate_id,
                aggregate_type,
                json.dumps(event_data),
                json.dumps(metadata)
            )
            
            logger.info("Event stored successfully", 
                       stream_id=stream_id,
                       event_type=event_type,
                       aggregate_id=aggregate_id)
            return result
            
        except Exception as e:
            logger.error("Failed to store event", 
                        stream_id=stream_id,
                        event_type=event_type,
                        error=str(e))
            raise
    
    async def get_events(self, aggregate_id: str, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events with parameterized query"""
        query = self.db.query_builder.build_select_events_query()
        
        try:
            events = await self.db.fetch_query(
                query,
                aggregate_id,
                event_type or "%",
                limit
            )
            
            # Parse JSON fields
            for event in events:
                if event.get('event_data'):
                    event['event_data'] = json.loads(event['event_data'])
                if event.get('metadata'):
                    event['metadata'] = json.loads(event['metadata'])
            
            logger.debug("Events retrieved", 
                        aggregate_id=aggregate_id,
                        count=len(events))
            return events
            
        except Exception as e:
            logger.error("Failed to get events", 
                        aggregate_id=aggregate_id,
                        error=str(e))
            raise


class StockAnalysisRepository:
    """Repository for stock analysis data"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def update_analysis(self, symbol: str, score: float, 
                            recommendation: str, confidence: float) -> str:
        """Update stock analysis with parameterized query"""
        query = self.db.query_builder.build_update_analysis_query()
        
        try:
            result = await self.db.execute_query(
                query,
                score,
                recommendation,
                confidence,
                symbol
            )
            
            logger.info("Stock analysis updated", 
                       symbol=symbol,
                       score=score,
                       recommendation=recommendation)
            return result
            
        except Exception as e:
            logger.error("Failed to update analysis", 
                        symbol=symbol,
                        error=str(e))
            raise
    
    async def get_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock analysis for symbol"""
        query = """
        SELECT symbol, score, recommendation, confidence, updated_at
        FROM stock_analysis 
        WHERE symbol = $1
        """
        
        try:
            result = await self.db.fetch_one_query(query, symbol)
            logger.debug("Stock analysis retrieved", 
                        symbol=symbol,
                        found=result is not None)
            return result
            
        except Exception as e:
            logger.error("Failed to get analysis", 
                        symbol=symbol,
                        error=str(e))
            raise


class HealthChecker:
    """Database health check utilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def check_connection(self) -> Dict[str, Any]:
        """Check database connection health"""
        try:
            # Simple query to test connection
            result = await self.db.fetch_one_query("SELECT 1 as health_check, NOW() as timestamp")
            
            if result:
                return {
                    "status": "healthy",
                    "timestamp": result["timestamp"],
                    "pool_size": self.db.pool.get_size() if self.db.pool else 0,
                    "pool_free": self.db.pool.get_idle_size() if self.db.pool else 0
                }
            else:
                return {"status": "unhealthy", "error": "No response from database"}
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_tables(self) -> Dict[str, Any]:
        """Check if required tables exist"""
        tables_to_check = ["events", "stock_analysis", "system_metrics"]
        
        try:
            query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = ANY($1)
            """
            
            existing_tables = await self.db.fetch_query(query, tables_to_check)
            existing_names = [row["table_name"] for row in existing_tables]
            
            missing_tables = [table for table in tables_to_check if table not in existing_names]
            
            return {
                "status": "healthy" if not missing_tables else "warning",
                "existing_tables": existing_names,
                "missing_tables": missing_tables
            }
            
        except Exception as e:
            logger.error("Table check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}


# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
async def get_db_connection():
    """Get database connection (backward compatibility)"""
    async with db_manager.get_connection() as conn:
        yield conn

async def initialize_database():
    """Initialize global database manager"""
    await db_manager.initialize()

async def close_database():
    """Close global database manager"""
    await db_manager.close()