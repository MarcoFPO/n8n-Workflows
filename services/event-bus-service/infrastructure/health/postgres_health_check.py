"""
PostgreSQL Health Check Implementation
Clean Architecture - Infrastructure Layer
"""

import asyncio
import asyncpg
from typing import Dict, Any, Optional
from datetime import datetime


class PostgreSQLHealthCheck:
    """Health Check für PostgreSQL Event Store"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection: Optional[asyncpg.Connection] = None
        
    async def initialize(self):
        """Initialize PostgreSQL connection"""
        try:
            self._connection = await asyncpg.connect(self.connection_string)
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            
    async def check_health(self) -> Dict[str, Any]:
        """Check PostgreSQL health status"""
        try:
            if not self._connection:
                await self.initialize()
                
            # Test query
            result = await self._connection.fetchval("SELECT 1")
            
            # Get event store size
            event_count = await self._connection.fetchval(
                "SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL '1 day'"
            )
            
            # Get database size
            db_size = await self._connection.fetchval(
                "SELECT pg_database_size(current_database()) / 1024 / 1024"
            )
            
            return {
                "connected": True,
                "responsive": result == 1,
                "event_count_24h": event_count or 0,
                "database_size_mb": db_size or 0,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "connected": False,
                "responsive": False,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
            
    async def cleanup(self):
        """Close PostgreSQL connection"""
        if self._connection:
            await self._connection.close()