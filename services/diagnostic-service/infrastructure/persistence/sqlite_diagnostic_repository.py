#!/usr/bin/env python3
"""
Diagnostic Service - SQLite Repository Implementation
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER

SQLite persistence für diagnostic data
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import sqlite3
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from ...domain.entities.diagnostic_event import (
    CapturedEvent, DiagnosticTest, SystemHealthSnapshot,
    ModuleCommunicationTest, TestResultStatus, SystemHealthStatus
)
from ...domain.repositories.diagnostic_repository import (
    IDiagnosticEventRepository, IDiagnosticTestRepository,
    ISystemHealthRepository, IModuleCommunicationRepository
)


logger = logging.getLogger(__name__)


class SQLiteDiagnosticEventRepository(IDiagnosticEventRepository):
    """
    SQLite implementation für diagnostic events
    INFRASTRUCTURE LAYER: Database persistence
    """
    
    def __init__(self, db_path: str = "diagnostic_events.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._operation_count = 0
        self._error_count = 0
        self._last_cleanup = None
        
    async def initialize(self):
        """Initialize database schema"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Create captured_events table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS captured_events (
                            capture_id TEXT PRIMARY KEY,
                            event_type TEXT NOT NULL,
                            source TEXT NOT NULL,
                            stream_id TEXT,
                            event_data TEXT NOT NULL,
                            captured_at TIMESTAMP NOT NULL,
                            correlation_id TEXT,
                            processing_time_ms REAL,
                            error_detected BOOLEAN DEFAULT 0,
                            error_indicators TEXT,
                            metadata TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    
                    # Create indices for better query performance
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_events_captured_at 
                        ON captured_events(captured_at DESC)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_events_source 
                        ON captured_events(source)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_events_type 
                        ON captured_events(event_type)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_events_error 
                        ON captured_events(error_detected, captured_at DESC)
                    ''')
                    
                    conn.commit()
                    
            logger.info("Diagnostic events repository initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize diagnostic events repository: {e}")
            self._error_count += 1
            return False
    
    async def save_event(self, event: CapturedEvent) -> bool:
        """Save captured event to database"""
        try:
            async with self._lock:
                self._operation_count += 1
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO captured_events (
                            capture_id, event_type, source, stream_id, event_data,
                            captured_at, correlation_id, processing_time_ms,
                            error_detected, error_indicators, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.capture_id,
                        event.event_type,
                        event.source,
                        event.stream_id,
                        json.dumps(event.event_data),
                        event.captured_at.isoformat(),
                        event.correlation_id,
                        event.processing_time_ms,
                        event.error_detected,
                        json.dumps(event.error_indicators),
                        json.dumps(event.metadata)
                    ))
                    
                    conn.commit()
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to save captured event: {e}")
            self._error_count += 1
            return False
    
    async def get_events(
        self, 
        limit: int = 100, 
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[CapturedEvent]:
        """Get captured events with filtering"""
        try:
            async with self._lock:
                self._operation_count += 1
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Build query with filters
                    where_conditions = []
                    params = []
                    
                    if filter_criteria:
                        if 'event_type' in filter_criteria:
                            where_conditions.append("event_type = ?")
                            params.append(filter_criteria['event_type'])
                        
                        if 'source' in filter_criteria:
                            where_conditions.append("source = ?")
                            params.append(filter_criteria['source'])
                        
                        if 'error_only' in filter_criteria and filter_criteria['error_only']:
                            where_conditions.append("error_detected = 1")
                        
                        if 'max_age_seconds' in filter_criteria:
                            cutoff_time = (datetime.now() - 
                                         timedelta(seconds=filter_criteria['max_age_seconds']))
                            where_conditions.append("captured_at >= ?")
                            params.append(cutoff_time.isoformat())
                    
                    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                    
                    query = f'''
                        SELECT * FROM captured_events 
                        WHERE {where_clause}
                        ORDER BY captured_at DESC 
                        LIMIT ?
                    '''
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to domain entities
                    events = []
                    for row in rows:
                        event = self._row_to_captured_event(row)
                        if event:
                            events.append(event)
                    
                    return events
                    
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            self._error_count += 1
            return []
    
    async def get_event_by_id(self, capture_id: str) -> Optional[CapturedEvent]:
        """Get event by capture ID"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM captured_events WHERE capture_id = ?",
                        (capture_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_captured_event(row)
                    
        except Exception as e:
            logger.error(f"Failed to get event by ID: {e}")
            self._error_count += 1
            
        return None
    
    async def get_events_by_source(self, source: str, limit: int = 100) -> List[CapturedEvent]:
        """Get events from specific source"""
        return await self.get_events(limit, {'source': source})
    
    async def get_events_by_type(self, event_type: str, limit: int = 100) -> List[CapturedEvent]:
        """Get events of specific type"""
        return await self.get_events(limit, {'event_type': event_type})
    
    async def get_error_events(self, limit: int = 50) -> List[CapturedEvent]:
        """Get error events only"""
        return await self.get_events(limit, {'error_only': True})
    
    async def cleanup_old_events(self, older_than_days: int = 7) -> int:
        """Clean up old events"""
        try:
            async with self._lock:
                cutoff_date = datetime.now() - timedelta(days=older_than_days)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Count events to be removed
                    cursor.execute(
                        "SELECT COUNT(*) FROM captured_events WHERE captured_at < ?",
                        (cutoff_date.isoformat(),)
                    )
                    count_to_remove = cursor.fetchone()[0]
                    
                    # Remove old events
                    cursor.execute(
                        "DELETE FROM captured_events WHERE captured_at < ?",
                        (cutoff_date.isoformat(),)
                    )
                    
                    conn.commit()
                    self._last_cleanup = datetime.now()
                    
                    logger.info(f"Cleaned up {count_to_remove} old events")
                    return count_to_remove
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            self._error_count += 1
            return 0
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Get event statistics summary"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Total events
                    cursor.execute("SELECT COUNT(*) FROM captured_events")
                    total_events = cursor.fetchone()[0]
                    
                    # Error events
                    cursor.execute("SELECT COUNT(*) FROM captured_events WHERE error_detected = 1")
                    error_events = cursor.fetchone()[0]
                    
                    # Event type distribution
                    cursor.execute('''
                        SELECT event_type, COUNT(*) 
                        FROM captured_events 
                        GROUP BY event_type 
                        ORDER BY COUNT(*) DESC
                    ''')
                    event_types = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # Source distribution
                    cursor.execute('''
                        SELECT source, COUNT(*) 
                        FROM captured_events 
                        GROUP BY source 
                        ORDER BY COUNT(*) DESC
                    ''')
                    source_counts = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # Recent activity (last hour)
                    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                    cursor.execute(
                        "SELECT COUNT(*) FROM captured_events WHERE captured_at >= ?",
                        (hour_ago,)
                    )
                    recent_events = cursor.fetchone()[0]
                    
                    return {
                        'total_events': total_events,
                        'error_events': error_events,
                        'error_rate_percent': (error_events / total_events * 100) if total_events > 0 else 0,
                        'event_type_counts': event_types,
                        'source_counts': source_counts,
                        'recent_events_last_hour': recent_events,
                        'repository_operations': self._operation_count,
                        'repository_errors': self._error_count,
                        'last_cleanup': self._last_cleanup.isoformat() if self._last_cleanup else None
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get event statistics: {e}")
            self._error_count += 1
            return {}
    
    def _row_to_captured_event(self, row) -> Optional[CapturedEvent]:
        """Convert database row to CapturedEvent entity"""
        try:
            return CapturedEvent(
                capture_id=row[0],
                event_type=row[1],
                source=row[2],
                stream_id=row[3],
                event_data=json.loads(row[4]) if row[4] else {},
                captured_at=datetime.fromisoformat(row[5]),
                correlation_id=row[6],
                processing_time_ms=row[7],
                error_detected=bool(row[8]),
                error_indicators=json.loads(row[9]) if row[9] else [],
                metadata=json.loads(row[10]) if row[10] else {}
            )
        except Exception as e:
            logger.warning(f"Failed to convert row to CapturedEvent: {e}")
            return None


class SQLiteDiagnosticTestRepository(IDiagnosticTestRepository):
    """
    SQLite implementation für diagnostic tests
    INFRASTRUCTURE LAYER: Test persistence
    """
    
    def __init__(self, db_path: str = "diagnostic_tests.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._operation_count = 0
    
    async def initialize(self):
        """Initialize test database schema"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS diagnostic_tests (
                            test_id TEXT PRIMARY KEY,
                            test_name TEXT NOT NULL,
                            test_type TEXT NOT NULL,
                            target_module TEXT,
                            test_data TEXT NOT NULL,
                            created_at TIMESTAMP NOT NULL,
                            executed_at TIMESTAMP,
                            completed_at TIMESTAMP,
                            status TEXT NOT NULL,
                            result_data TEXT,
                            error_message TEXT,
                            execution_time_ms REAL,
                            retry_count INTEGER DEFAULT 0,
                            max_retries INTEGER DEFAULT 3
                        )
                    ''')
                    
                    # Indices
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_tests_created_at 
                        ON diagnostic_tests(created_at DESC)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_tests_status 
                        ON diagnostic_tests(status)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_tests_module 
                        ON diagnostic_tests(target_module)
                    ''')
                    
                    conn.commit()
                    
            logger.info("Diagnostic tests repository initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize diagnostic tests repository: {e}")
            return False
    
    async def save_test(self, test: DiagnosticTest) -> bool:
        """Save diagnostic test"""
        try:
            async with self._lock:
                self._operation_count += 1
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO diagnostic_tests (
                            test_id, test_name, test_type, target_module, test_data,
                            created_at, executed_at, completed_at, status, result_data,
                            error_message, execution_time_ms, retry_count, max_retries
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        test.test_id,
                        test.test_name,
                        test.test_type,
                        test.target_module,
                        json.dumps(test.test_data),
                        test.created_at.isoformat(),
                        test.executed_at.isoformat() if test.executed_at else None,
                        test.completed_at.isoformat() if test.completed_at else None,
                        test.status.value,
                        json.dumps(test.result_data),
                        test.error_message,
                        test.execution_time_ms,
                        test.retry_count,
                        test.max_retries
                    ))
                    
                    conn.commit()
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to save diagnostic test: {e}")
            return False
    
    async def update_test_status(
        self, 
        test_id: str, 
        status: TestResultStatus,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update test execution status"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Update test status and completion time
                    update_fields = ['status = ?', 'completed_at = ?']
                    params = [status.value, datetime.now().isoformat()]
                    
                    if result_data:
                        update_fields.append('result_data = ?')
                        params.append(json.dumps(result_data))
                    
                    if error_message:
                        update_fields.append('error_message = ?')
                        params.append(error_message)
                    
                    params.append(test_id)  # WHERE clause parameter
                    
                    query = f'''
                        UPDATE diagnostic_tests 
                        SET {', '.join(update_fields)}
                        WHERE test_id = ?
                    '''
                    
                    cursor.execute(query, params)
                    conn.commit()
                    
                    return cursor.rowcount > 0
                    
        except Exception as e:
            logger.error(f"Failed to update test status: {e}")
            return False
    
    async def get_test_by_id(self, test_id: str) -> Optional[DiagnosticTest]:
        """Get test by ID"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM diagnostic_tests WHERE test_id = ?",
                        (test_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_diagnostic_test(row)
                    
        except Exception as e:
            logger.error(f"Failed to get test by ID: {e}")
            
        return None
    
    async def get_tests(
        self, 
        limit: int = 100, 
        status_filter: Optional[TestResultStatus] = None
    ) -> List[DiagnosticTest]:
        """Get diagnostic tests with optional status filtering"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if status_filter:
                        cursor.execute('''
                            SELECT * FROM diagnostic_tests 
                            WHERE status = ?
                            ORDER BY created_at DESC 
                            LIMIT ?
                        ''', (status_filter.value, limit))
                    else:
                        cursor.execute('''
                            SELECT * FROM diagnostic_tests 
                            ORDER BY created_at DESC 
                            LIMIT ?
                        ''', (limit,))
                    
                    rows = cursor.fetchall()
                    
                    tests = []
                    for row in rows:
                        test = self._row_to_diagnostic_test(row)
                        if test:
                            tests.append(test)
                    
                    return tests
                    
        except Exception as e:
            logger.error(f"Failed to get tests: {e}")
            return []
    
    async def get_tests_by_module(self, target_module: str) -> List[DiagnosticTest]:
        """Get tests for specific module"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM diagnostic_tests 
                        WHERE target_module = ?
                        ORDER BY created_at DESC
                    ''', (target_module,))
                    
                    rows = cursor.fetchall()
                    
                    tests = []
                    for row in rows:
                        test = self._row_to_diagnostic_test(row)
                        if test:
                            tests.append(test)
                    
                    return tests
                    
        except Exception as e:
            logger.error(f"Failed to get tests by module: {e}")
            return []
    
    async def get_pending_tests(self) -> List[DiagnosticTest]:
        """Get all pending tests"""
        return await self.get_tests(1000, TestResultStatus.PENDING)
    
    async def cleanup_completed_tests(self, older_than_hours: int = 24) -> int:
        """Clean up old completed tests"""
        try:
            async with self._lock:
                cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Count tests to be removed
                    cursor.execute('''
                        SELECT COUNT(*) FROM diagnostic_tests 
                        WHERE completed_at IS NOT NULL AND completed_at < ?
                    ''', (cutoff_time.isoformat(),))
                    count_to_remove = cursor.fetchone()[0]
                    
                    # Remove old completed tests
                    cursor.execute('''
                        DELETE FROM diagnostic_tests 
                        WHERE completed_at IS NOT NULL AND completed_at < ?
                    ''', (cutoff_time.isoformat(),))
                    
                    conn.commit()
                    
                    logger.info(f"Cleaned up {count_to_remove} old completed tests")
                    return count_to_remove
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old tests: {e}")
            return 0
    
    def _row_to_diagnostic_test(self, row) -> Optional[DiagnosticTest]:
        """Convert database row to DiagnosticTest entity"""
        try:
            return DiagnosticTest(
                test_id=row[0],
                test_name=row[1],
                test_type=row[2],
                target_module=row[3],
                test_data=json.loads(row[4]) if row[4] else {},
                created_at=datetime.fromisoformat(row[5]),
                executed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                status=TestResultStatus(row[8]),
                result_data=json.loads(row[9]) if row[9] else {},
                error_message=row[10],
                execution_time_ms=row[11],
                retry_count=row[12],
                max_retries=row[13]
            )
        except Exception as e:
            logger.warning(f"Failed to convert row to DiagnosticTest: {e}")
            return None


class SQLiteSystemHealthRepository(ISystemHealthRepository):
    """
    SQLite implementation für system health snapshots
    INFRASTRUCTURE LAYER: Health snapshot persistence
    """
    
    def __init__(self, db_path: str = "diagnostic_health.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize health database schema"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS health_snapshots (
                            snapshot_id TEXT PRIMARY KEY,
                            timestamp TIMESTAMP NOT NULL,
                            overall_status TEXT NOT NULL,
                            health_score REAL NOT NULL,
                            total_events_monitored INTEGER NOT NULL,
                            error_event_count INTEGER NOT NULL,
                            active_sources TEXT NOT NULL,
                            event_type_distribution TEXT NOT NULL,
                            performance_metrics TEXT NOT NULL,
                            alerts TEXT NOT NULL,
                            recommendations TEXT NOT NULL
                        )
                    ''')
                    
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_health_timestamp 
                        ON health_snapshots(timestamp DESC)
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_health_status 
                        ON health_snapshots(overall_status)
                    ''')
                    
                    conn.commit()
                    
            logger.info("System health repository initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize health repository: {e}")
            return False
    
    async def save_health_snapshot(self, snapshot: SystemHealthSnapshot) -> bool:
        """Save system health snapshot"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO health_snapshots (
                            snapshot_id, timestamp, overall_status, health_score,
                            total_events_monitored, error_event_count, active_sources,
                            event_type_distribution, performance_metrics, alerts, recommendations
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        snapshot.snapshot_id,
                        snapshot.timestamp.isoformat(),
                        snapshot.overall_status.value,
                        snapshot.health_score,
                        snapshot.total_events_monitored,
                        snapshot.error_event_count,
                        json.dumps(snapshot.active_sources),
                        json.dumps(snapshot.event_type_distribution),
                        json.dumps(snapshot.performance_metrics),
                        json.dumps(snapshot.alerts),
                        json.dumps(snapshot.recommendations)
                    ))
                    
                    conn.commit()
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to save health snapshot: {e}")
            return False
    
    async def get_latest_snapshot(self) -> Optional[SystemHealthSnapshot]:
        """Get most recent health snapshot"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM health_snapshots 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    ''')
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_health_snapshot(row)
                    
        except Exception as e:
            logger.error(f"Failed to get latest health snapshot: {e}")
            
        return None
    
    async def get_snapshots(
        self, 
        limit: int = 100,
        from_time: Optional[datetime] = None
    ) -> List[SystemHealthSnapshot]:
        """Get health snapshots with time filtering"""
        try:
            async with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if from_time:
                        cursor.execute('''
                            SELECT * FROM health_snapshots 
                            WHERE timestamp >= ?
                            ORDER BY timestamp DESC 
                            LIMIT ?
                        ''', (from_time.isoformat(), limit))
                    else:
                        cursor.execute('''
                            SELECT * FROM health_snapshots 
                            ORDER BY timestamp DESC 
                            LIMIT ?
                        ''', (limit,))
                    
                    rows = cursor.fetchall()
                    
                    snapshots = []
                    for row in rows:
                        snapshot = self._row_to_health_snapshot(row)
                        if snapshot:
                            snapshots.append(snapshot)
                    
                    return snapshots
                    
        except Exception as e:
            logger.error(f"Failed to get health snapshots: {e}")
            return []
    
    async def get_health_trend(self, hours: int = 24) -> List[SystemHealthSnapshot]:
        """Get health trend over specified hours"""
        from_time = datetime.now() - timedelta(hours=hours)
        return await self.get_snapshots(1000, from_time)
    
    async def cleanup_old_snapshots(self, older_than_days: int = 30) -> int:
        """Clean up old health snapshots"""
        try:
            async with self._lock:
                cutoff_date = datetime.now() - timedelta(days=older_than_days)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Count snapshots to be removed
                    cursor.execute(
                        "SELECT COUNT(*) FROM health_snapshots WHERE timestamp < ?",
                        (cutoff_date.isoformat(),)
                    )
                    count_to_remove = cursor.fetchone()[0]
                    
                    # Remove old snapshots
                    cursor.execute(
                        "DELETE FROM health_snapshots WHERE timestamp < ?",
                        (cutoff_date.isoformat(),)
                    )
                    
                    conn.commit()
                    
                    logger.info(f"Cleaned up {count_to_remove} old health snapshots")
                    return count_to_remove
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old health snapshots: {e}")
            return 0
    
    def _row_to_health_snapshot(self, row) -> Optional[SystemHealthSnapshot]:
        """Convert database row to SystemHealthSnapshot entity"""
        try:
            return SystemHealthSnapshot(
                snapshot_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                overall_status=SystemHealthStatus(row[2]),
                health_score=row[3],
                total_events_monitored=row[4],
                error_event_count=row[5],
                active_sources=json.loads(row[6]),
                event_type_distribution=json.loads(row[7]),
                performance_metrics=json.loads(row[8]),
                alerts=json.loads(row[9]),
                recommendations=json.loads(row[10])
            )
        except Exception as e:
            logger.warning(f"Failed to convert row to SystemHealthSnapshot: {e}")
            return None