"""
PostgreSQL Health Check Implementation - Using Connection Pool
Clean Architecture - Infrastructure Layer
Migrated to use centralized database pool
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
from typing import Dict, Any
from datetime import datetime
import logging
import sys
import os

# Add shared to path for imports

from shared.database_pool import db_pool

logger = logging.getLogger(__name__)

class PostgreSQLHealthCheck:
    """Health Check für PostgreSQL Event Store - Using Connection Pool"""
    
    async def check_health(self) -> Dict[str, Any]:
        """Check PostgreSQL health status using connection pool"""
        try:
            # Ensure pool is initialized
            if not db_pool.is_initialized:
                await db_pool.initialize()
            
            # Use pool for health check
            health_ok = await db_pool.health_check()
            
            if health_ok:
                # Get additional metrics using pool
                event_count = await db_pool.fetchval(
                    "SELECT COUNT(*) FROM events WHERE created_at > NOW() - INTERVAL '1 day'"
                )
                
                db_size = await db_pool.fetchval(
                    "SELECT pg_database_size(current_database()) / 1024 / 1024"
                )
                
                # Get pool statistics
                pool_stats = db_pool.pool_stats
                
                return {
                    "connected": True,
                    "responsive": True,
                    "event_count_24h": event_count or 0,
                    "database_size_mb": db_size or 0,
                    "pool_stats": pool_stats,
                    "last_check": datetime.now().isoformat()
                }
            else:
                return {
                    "connected": False,
                    "responsive": False,
                    "error": "Health check query failed",
                    "last_check": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                "connected": False,
                "responsive": False,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def initialize(self):
        """Initialize is now handled by the pool"""
        if not db_pool.is_initialized:
            await db_pool.initialize()
    
    async def cleanup(self):
        """Cleanup is handled by pool - nothing to do here"""
        pass  # Pool manages its own lifecycle