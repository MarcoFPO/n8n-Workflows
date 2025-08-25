#!/usr/bin/env python3
"""
Diagnostic Service - PostgreSQL Repository Implementation
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER - PostgreSQL Migration

PostgreSQL persistence für diagnostic data mit centralized database manager
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0 (PostgreSQL Migration)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Database Manager Import - Direct Path Import
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager

from ...domain.entities.diagnostic_event import (
    CapturedEvent, DiagnosticTest, SystemHealthSnapshot,
    ModuleCommunicationTest, TestResultStatus, SystemHealthStatus
)
from ...domain.repositories.diagnostic_repository import (
    IDiagnosticEventRepository, IDiagnosticTestRepository,
    ISystemHealthRepository, IModuleCommunicationRepository
)


logger = logging.getLogger(__name__)


class PostgreSQLDiagnosticEventRepository(IDiagnosticEventRepository):
    """
    PostgreSQL implementation für diagnostic events
    INFRASTRUCTURE LAYER: Database persistence mit Database Manager
    """
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._error_count = 0
        self._last_cleanup = None
        self._initialized_at = datetime.now(timezone.utc)
        
    async def initialize_schema(self) -> bool:
        """Initialize diagnostic events schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create diagnostic_events table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS diagnostic_events (
                        id SERIAL PRIMARY KEY,
                        event_id VARCHAR(255) UNIQUE NOT NULL,
                        event_type VARCHAR(100) NOT NULL,
                        service_name VARCHAR(100) NOT NULL,
                        message TEXT NOT NULL,
                        level VARCHAR(20) NOT NULL,
                        module_name VARCHAR(100),
                        function_name VARCHAR(100),
                        line_number INTEGER,
                        additional_data JSONB,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        processed BOOLEAN NOT NULL DEFAULT FALSE
                    )
                ''')
                
                # Create indexes
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_events_type 
                    ON diagnostic_events (event_type)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_events_service 
                    ON diagnostic_events (service_name)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_events_created 
                    ON diagnostic_events (created_at)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_events_processed 
                    ON diagnostic_events (processed)
                ''')
                
                logger.info("Diagnostic events schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize diagnostic events schema: {e}")
            return False
    
    async def store_event(self, event: CapturedEvent) -> bool:
        """Store diagnostic event"""
        try:
            async with self.db_manager.get_connection() as connection:
                additional_data_json = json.dumps(event.additional_data) if event.additional_data else None
                
                await connection.execute('''
                    INSERT INTO diagnostic_events (
                        event_id, event_type, service_name, message, level,
                        module_name, function_name, line_number, additional_data,
                        created_at, processed
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (event_id) DO UPDATE SET
                        message = EXCLUDED.message,
                        additional_data = EXCLUDED.additional_data,
                        processed = EXCLUDED.processed
                ''',
                    event.event_id,
                    event.event_type,
                    event.service_name,
                    event.message,
                    event.level,
                    event.module_name,
                    event.function_name,
                    event.line_number,
                    additional_data_json,
                    event.timestamp,
                    event.processed
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to store diagnostic event {event.event_id}: {e}")
            self._error_count += 1
            return False
    
    async def get_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[CapturedEvent]:
        """Get diagnostic events"""
        try:
            async with self.db_manager.get_connection() as connection:
                if event_type:
                    rows = await connection.fetch('''
                        SELECT * FROM diagnostic_events 
                        WHERE event_type = $1 
                        ORDER BY created_at DESC 
                        LIMIT $2
                    ''', event_type, limit)
                else:
                    rows = await connection.fetch('''
                        SELECT * FROM diagnostic_events 
                        ORDER BY created_at DESC 
                        LIMIT $1
                    ''', limit)
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get diagnostic events: {e}")
            return []
    
    async def get_events_by_service(self, service_name: str, limit: int = 100) -> List[CapturedEvent]:
        """Get events by service name"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM diagnostic_events 
                    WHERE service_name = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                ''', service_name, limit)
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get events for service {service_name}: {e}")
            return []
    
    async def get_recent_events(self, hours: int = 24) -> List[CapturedEvent]:
        """Get recent events"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                rows = await connection.fetch('''
                    SELECT * FROM diagnostic_events 
                    WHERE created_at >= $1 
                    ORDER BY created_at DESC
                ''', cutoff_time)
                
                return [self._row_to_event(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []
    
    async def mark_events_processed(self, event_ids: List[str]) -> int:
        """Mark events as processed"""
        try:
            async with self.db_manager.get_connection() as connection:
                result = await connection.execute('''
                    UPDATE diagnostic_events 
                    SET processed = TRUE 
                    WHERE event_id = ANY($1::text[])
                ''', event_ids)
                
                rows_affected = int(result.split()[-1])
                return rows_affected
                
        except Exception as e:
            logger.error(f"Failed to mark events as processed: {e}")
            return 0
    
    async def cleanup_old_events(self, days_old: int = 30) -> int:
        """Cleanup old events"""
        try:
            async with self.db_manager.get_connection() as connection:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
                
                result = await connection.execute('''
                    DELETE FROM diagnostic_events 
                    WHERE created_at < $1
                ''', cutoff_date)
                
                deleted_count = int(result.split()[-1])
                self._last_cleanup = datetime.now(timezone.utc)
                logger.info(f"Cleaned up {deleted_count} old diagnostic events")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Get basic counts
                total_events = await connection.fetchval('SELECT COUNT(*) FROM diagnostic_events')
                processed_events = await connection.fetchval('SELECT COUNT(*) FROM diagnostic_events WHERE processed = TRUE')
                
                # Get service distribution
                service_stats = await connection.fetch('''
                    SELECT service_name, COUNT(*) as count 
                    FROM diagnostic_events 
                    GROUP BY service_name 
                    ORDER BY count DESC
                ''')
                
                # Get event type distribution
                type_stats = await connection.fetch('''
                    SELECT event_type, COUNT(*) as count 
                    FROM diagnostic_events 
                    GROUP BY event_type 
                    ORDER BY count DESC
                ''')
                
                return {
                    "total_events": total_events,
                    "processed_events": processed_events,
                    "pending_events": total_events - processed_events,
                    "service_distribution": {row['service_name']: row['count'] for row in service_stats},
                    "type_distribution": {row['event_type']: row['count'] for row in type_stats},
                    "repository_type": "PostgreSQL",
                    "operation_count": self._operation_count,
                    "error_count": self._error_count,
                    "initialized_at": self._initialized_at.isoformat(),
                    "last_cleanup": self._last_cleanup.isoformat() if self._last_cleanup else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get repository stats: {e}")
            return {
                "error": str(e),
                "repository_type": "PostgreSQL",
                "initialized_at": self._initialized_at.isoformat()
            }
    
    def _row_to_event(self, row) -> CapturedEvent:
        """Convert database row to CapturedEvent"""
        additional_data = json.loads(row['additional_data']) if row['additional_data'] else {}
        
        return CapturedEvent(
            event_id=row['event_id'],
            event_type=row['event_type'],
            service_name=row['service_name'],
            message=row['message'],
            level=row['level'],
            timestamp=row['created_at'],
            module_name=row['module_name'],
            function_name=row['function_name'],
            line_number=row['line_number'],
            additional_data=additional_data,
            processed=row['processed']
        )


class PostgreSQLDiagnosticTestRepository(IDiagnosticTestRepository):
    """PostgreSQL implementation für diagnostic tests"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)
    
    async def initialize_schema(self) -> bool:
        """Initialize diagnostic tests schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create diagnostic_tests table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS diagnostic_tests (
                        id SERIAL PRIMARY KEY,
                        test_id VARCHAR(255) UNIQUE NOT NULL,
                        test_name VARCHAR(200) NOT NULL,
                        service_name VARCHAR(100) NOT NULL,
                        test_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        result_data JSONB,
                        error_message TEXT,
                        execution_time_ms INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        completed_at TIMESTAMPTZ
                    )
                ''')
                
                # Create indexes
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_tests_service 
                    ON diagnostic_tests (service_name)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_tests_status 
                    ON diagnostic_tests (status)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_diagnostic_tests_created 
                    ON diagnostic_tests (created_at)
                ''')
                
                logger.info("Diagnostic tests schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize diagnostic tests schema: {e}")
            return False
    
    async def store_test(self, test: DiagnosticTest) -> bool:
        """Store diagnostic test"""
        try:
            async with self.db_manager.get_connection() as connection:
                result_data_json = json.dumps(test.result_data) if test.result_data else None
                
                await connection.execute('''
                    INSERT INTO diagnostic_tests (
                        test_id, test_name, service_name, test_type, status,
                        result_data, error_message, execution_time_ms,
                        created_at, completed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (test_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        result_data = EXCLUDED.result_data,
                        error_message = EXCLUDED.error_message,
                        execution_time_ms = EXCLUDED.execution_time_ms,
                        completed_at = EXCLUDED.completed_at
                ''',
                    test.test_id,
                    test.test_name,
                    test.service_name,
                    test.test_type,
                    test.status.value,
                    result_data_json,
                    test.error_message,
                    test.execution_time_ms,
                    test.created_at,
                    test.completed_at
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to store diagnostic test {test.test_id}: {e}")
            return False
    
    async def get_tests(self, limit: int = 100, status: Optional[TestResultStatus] = None) -> List[DiagnosticTest]:
        """Get diagnostic tests"""
        try:
            async with self.db_manager.get_connection() as connection:
                if status:
                    rows = await connection.fetch('''
                        SELECT * FROM diagnostic_tests 
                        WHERE status = $1 
                        ORDER BY created_at DESC 
                        LIMIT $2
                    ''', status.value, limit)
                else:
                    rows = await connection.fetch('''
                        SELECT * FROM diagnostic_tests 
                        ORDER BY created_at DESC 
                        LIMIT $1
                    ''', limit)
                
                return [self._row_to_test(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get diagnostic tests: {e}")
            return []
    
    async def get_tests_by_service(self, service_name: str) -> List[DiagnosticTest]:
        """Get tests by service"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM diagnostic_tests 
                    WHERE service_name = $1 
                    ORDER BY created_at DESC
                ''', service_name)
                
                return [self._row_to_test(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get tests for service {service_name}: {e}")
            return []
    
    def _row_to_test(self, row) -> DiagnosticTest:
        """Convert database row to DiagnosticTest"""
        result_data = json.loads(row['result_data']) if row['result_data'] else {}
        
        return DiagnosticTest(
            test_id=row['test_id'],
            test_name=row['test_name'],
            service_name=row['service_name'],
            test_type=row['test_type'],
            status=TestResultStatus(row['status']),
            result_data=result_data,
            error_message=row['error_message'],
            execution_time_ms=row['execution_time_ms'],
            created_at=row['created_at'],
            completed_at=row['completed_at']
        )


class PostgreSQLSystemHealthRepository(ISystemHealthRepository):
    """PostgreSQL implementation für system health snapshots"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)
    
    async def initialize_schema(self) -> bool:
        """Initialize system health schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create system_health table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS system_health (
                        id SERIAL PRIMARY KEY,
                        snapshot_id VARCHAR(255) UNIQUE NOT NULL,
                        service_name VARCHAR(100) NOT NULL,
                        overall_status VARCHAR(20) NOT NULL,
                        component_statuses JSONB NOT NULL,
                        metrics JSONB,
                        error_details JSONB,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                ''')
                
                # Create indexes
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_system_health_service 
                    ON system_health (service_name)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_system_health_status 
                    ON system_health (overall_status)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_system_health_created 
                    ON system_health (created_at)
                ''')
                
                logger.info("System health schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize system health schema: {e}")
            return False
    
    async def store_snapshot(self, snapshot: SystemHealthSnapshot) -> bool:
        """Store health snapshot"""
        try:
            async with self.db_manager.get_connection() as connection:
                component_statuses_json = json.dumps({k: v.value for k, v in snapshot.component_statuses.items()})
                metrics_json = json.dumps(snapshot.metrics) if snapshot.metrics else None
                error_details_json = json.dumps(snapshot.error_details) if snapshot.error_details else None
                
                await connection.execute('''
                    INSERT INTO system_health (
                        snapshot_id, service_name, overall_status,
                        component_statuses, metrics, error_details, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''',
                    snapshot.snapshot_id,
                    snapshot.service_name,
                    snapshot.overall_status.value,
                    component_statuses_json,
                    metrics_json,
                    error_details_json,
                    snapshot.timestamp
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to store health snapshot {snapshot.snapshot_id}: {e}")
            return False
    
    async def get_recent_snapshots(self, service_name: str, limit: int = 50) -> List[SystemHealthSnapshot]:
        """Get recent health snapshots"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM system_health 
                    WHERE service_name = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                ''', service_name, limit)
                
                return [self._row_to_snapshot(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get health snapshots for service {service_name}: {e}")
            return []
    
    def _row_to_snapshot(self, row) -> SystemHealthSnapshot:
        """Convert database row to SystemHealthSnapshot"""
        component_statuses = {k: SystemHealthStatus(v) for k, v in json.loads(row['component_statuses']).items()}
        metrics = json.loads(row['metrics']) if row['metrics'] else {}
        error_details = json.loads(row['error_details']) if row['error_details'] else {}
        
        return SystemHealthSnapshot(
            snapshot_id=row['snapshot_id'],
            service_name=row['service_name'],
            overall_status=SystemHealthStatus(row['overall_status']),
            component_statuses=component_statuses,
            metrics=metrics,
            error_details=error_details,
            timestamp=row['created_at']
        )


class PostgreSQLModuleCommunicationRepository(IModuleCommunicationRepository):
    """PostgreSQL implementation für module communication tests"""
    
    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self._operation_count = 0
        self._initialized_at = datetime.now(timezone.utc)
    
    async def initialize_schema(self) -> bool:
        """Initialize module communication schema"""
        try:
            async with self.db_manager.get_connection() as connection:
                # Create module_communication table
                await connection.execute('''
                    CREATE TABLE IF NOT EXISTS module_communication (
                        id SERIAL PRIMARY KEY,
                        test_id VARCHAR(255) UNIQUE NOT NULL,
                        source_module VARCHAR(100) NOT NULL,
                        target_module VARCHAR(100) NOT NULL,
                        communication_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        response_time_ms INTEGER,
                        error_message TEXT,
                        test_data JSONB,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                ''')
                
                # Create indexes
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_module_comm_source 
                    ON module_communication (source_module)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_module_comm_target 
                    ON module_communication (target_module)
                ''')
                
                await connection.execute('''
                    CREATE INDEX IF NOT EXISTS idx_module_comm_status 
                    ON module_communication (status)
                ''')
                
                logger.info("Module communication schema initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize module communication schema: {e}")
            return False
    
    async def store_test(self, test: ModuleCommunicationTest) -> bool:
        """Store communication test"""
        try:
            async with self.db_manager.get_connection() as connection:
                test_data_json = json.dumps(test.test_data) if test.test_data else None
                
                await connection.execute('''
                    INSERT INTO module_communication (
                        test_id, source_module, target_module, communication_type,
                        status, response_time_ms, error_message, test_data, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (test_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        response_time_ms = EXCLUDED.response_time_ms,
                        error_message = EXCLUDED.error_message,
                        test_data = EXCLUDED.test_data
                ''',
                    test.test_id,
                    test.source_module,
                    test.target_module,
                    test.communication_type,
                    test.status.value,
                    test.response_time_ms,
                    test.error_message,
                    test_data_json,
                    test.timestamp
                )
                
                self._operation_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to store communication test {test.test_id}: {e}")
            return False
    
    async def get_tests(self, limit: int = 100) -> List[ModuleCommunicationTest]:
        """Get communication tests"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM module_communication 
                    ORDER BY created_at DESC 
                    LIMIT $1
                ''', limit)
                
                return [self._row_to_communication_test(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get communication tests: {e}")
            return []
    
    async def get_tests_by_modules(self, source_module: str, target_module: str) -> List[ModuleCommunicationTest]:
        """Get tests between specific modules"""
        try:
            async with self.db_manager.get_connection() as connection:
                rows = await connection.fetch('''
                    SELECT * FROM module_communication 
                    WHERE source_module = $1 AND target_module = $2 
                    ORDER BY created_at DESC
                ''', source_module, target_module)
                
                return [self._row_to_communication_test(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get tests between {source_module} and {target_module}: {e}")
            return []
    
    def _row_to_communication_test(self, row) -> ModuleCommunicationTest:
        """Convert database row to ModuleCommunicationTest"""
        test_data = json.loads(row['test_data']) if row['test_data'] else {}
        
        return ModuleCommunicationTest(
            test_id=row['test_id'],
            source_module=row['source_module'],
            target_module=row['target_module'],
            communication_type=row['communication_type'],
            status=TestResultStatus(row['status']),
            response_time_ms=row['response_time_ms'],
            error_message=row['error_message'],
            test_data=test_data,
            timestamp=row['created_at']
        )