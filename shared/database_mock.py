"""
Mock Database Implementation for Testing
Provides the same interface as database.py but without PostgreSQL dependencies
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MockDatabaseManager:
    """Mock database manager for testing without PostgreSQL"""
    
    def __init__(self):
        self.is_initialized = False
        self.host = "mock-localhost"
        self.port = 5432
        self.database = "mock-database"
        self.user = "mock-user"
        self.password = "mock-password"
        self.pool = None
        
    async def initialize(self):
        """Initialize mock database connection"""
        logger.info("Initializing mock database connection")
        self.is_initialized = True
        logger.info("Mock database pool created successfully")
    
    async def close(self):
        """Close mock database connection"""
        if self.is_initialized:
            logger.info("Closing mock database connection")
            self.is_initialized = False
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire mock database connection"""
        if not self.is_initialized:
            raise RuntimeError("Mock database not initialized")
        
        # Return a mock connection
        yield MockConnection()


class MockConnection:
    """Mock database connection"""
    
    async def execute(self, query: str, *args):
        """Execute mock query"""
        logger.debug(f"Mock execute: {query[:50]}... with args: {args}")
        return "MOCK-EXECUTE"
    
    async def fetch(self, query: str, *args):
        """Fetch mock records"""
        logger.debug(f"Mock fetch: {query[:50]}... with args: {args}")
        return []
    
    async def fetchrow(self, query: str, *args):
        """Fetch mock single record"""
        logger.debug(f"Mock fetchrow: {query[:50]}... with args: {args}")
        return None


class MockEventStore:
    """Mock event store for testing"""
    
    def __init__(self, db_manager: MockDatabaseManager):
        self.db_manager = db_manager
        self.events = []  # In-memory storage
    
    async def create_event(self, stream_id: str, event_type: str, event_version: int,
                          aggregate_id: str, aggregate_type: str, event_data: Dict[str, Any],
                          metadata: Dict[str, Any] = None) -> str:
        """Create mock event"""
        event_id = f"mock-event-{len(self.events)}"
        event = {
            "event_id": event_id,
            "stream_id": stream_id,
            "event_type": event_type,
            "event_version": event_version,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "event_data": event_data,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        self.events.append(event)
        logger.info(f"Mock event created: {event_id}")
        return event_id
    
    async def get_events(self, aggregate_id: str, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get mock events"""
        filtered_events = [e for e in self.events if e["aggregate_id"] == aggregate_id]
        if event_type:
            filtered_events = [e for e in filtered_events if e["event_type"] == event_type]
        return filtered_events[:limit]


class MockStockAnalysisRepository:
    """Mock stock analysis repository"""
    
    def __init__(self, db_manager: MockDatabaseManager):
        self.db_manager = db_manager
        self.analyses = {}  # In-memory storage
    
    async def save_analysis(self, symbol: str, score: float, recommendation: str, 
                           confidence: float, analysis_data: Dict[str, Any]) -> str:
        """Save mock analysis"""
        analysis_id = f"mock-analysis-{symbol}-{int(datetime.utcnow().timestamp())}"
        analysis = {
            "analysis_id": analysis_id,
            "symbol": symbol,
            "score": score,
            "recommendation": recommendation,
            "confidence": confidence,
            "analysis_data": analysis_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        self.analyses[symbol] = analysis
        logger.info(f"Mock analysis saved: {analysis_id}")
        return analysis_id
    
    async def get_latest_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get mock latest analysis"""
        return self.analyses.get(symbol)
    
    async def get_analyses_by_score(self, min_score: float = 0.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Get mock analyses by score"""
        analyses = list(self.analyses.values())
        filtered = [a for a in analyses if a["score"] >= min_score]
        return sorted(filtered, key=lambda x: x["score"], reverse=True)[:limit]


class MockHealthChecker:
    """Mock health checker"""
    
    def __init__(self, db_manager: MockDatabaseManager):
        self.db_manager = db_manager
    
    async def check_database(self) -> Dict[str, Any]:
        """Check mock database health"""
        return {
            "status": "healthy",
            "response_time_ms": 1.0,
            "connection_pool": {
                "total_connections": 10,
                "active_connections": 2,
                "idle_connections": 8
            },
            "last_check": datetime.utcnow().isoformat(),
            "version": "Mock-PostgreSQL-15",
            "uptime_seconds": 3600
        }
    
    async def check_connection(self) -> bool:
        """Check mock connection"""
        return self.db_manager.is_initialized
    
    async def get_database_size(self) -> Dict[str, Any]:
        """Get mock database size"""
        return {
            "total_size_mb": 100.0,
            "table_count": 5,
            "index_count": 10
        }


# Alias the mock classes to match the original interface
DatabaseManager = MockDatabaseManager
EventStore = MockEventStore
StockAnalysisRepository = MockStockAnalysisRepository
HealthChecker = MockHealthChecker