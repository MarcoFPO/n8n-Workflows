#!/usr/bin/env python3
"""
Diagnostic Service - Dependency Injection Container v6.1.0
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER - PostgreSQL Migration

Dependency injection und service configuration mit Database Manager
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0 (PostgreSQL Migration)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import os
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import (
    DatabaseConnectionManager, 
    DatabaseConfiguration
)

# Domain interfaces
from ..domain.repositories.diagnostic_repository import (
    IDiagnosticEventRepository, IDiagnosticTestRepository,
    ISystemHealthRepository, IModuleCommunicationRepository,
    IDiagnosticEventBusProvider
)

# Application interfaces
from ..application.interfaces.event_publisher import IEventPublisher

# Application use cases
from ..application.use_cases.diagnostic_use_cases import (
    EventMonitoringUseCase, DiagnosticTestingUseCase,
    SystemHealthUseCase, DiagnosticMaintenanceUseCase
)

# Infrastructure implementations - PostgreSQL
from .persistence.postgresql_diagnostic_repository import (
    PostgreSQLDiagnosticEventRepository, PostgreSQLDiagnosticTestRepository,
    PostgreSQLSystemHealthRepository, PostgreSQLModuleCommunicationRepository
)
from .external_services.diagnostic_event_bus_provider import (
    DiagnosticEventBusProvider, MockDiagnosticEventBusProvider
)
from .events.mock_event_publisher import MockEventPublisher


logger = logging.getLogger(__name__)


class DiagnosticServiceContainer:
    """
    Diagnostic Service Dependency Injection Container v6.1.0
    INFRASTRUCTURE LAYER: Service composition mit PostgreSQL Database Manager
    """
    
    def __init__(self):
        self.services = {}
        self.configuration = {
            'database_manager': {
                'auto_initialize_schema': True,
                'enable_connection_pooling': True,
                'pool_health_check_interval': 300  # 5 minutes
            },
            'event_bus_enabled': True,
            'event_bus_host': os.getenv('EVENT_BUS_HOST', '10.1.1.174'),
            'event_bus_port': int(os.getenv('EVENT_BUS_PORT', 6379)),
            'use_mock_event_bus': True,  # For development
            'cleanup_interval_hours': 168,  # 7 days
            'max_events_per_service': 10000
        }
        self.initialized = False
        self.initialization_error = None
        self.initialization_time = None
        self.health_status = {}
        
        # Service lifecycle tracking
        self.started_services = set()
        self.failed_services = set()
        
        # Database Manager
        self._db_manager: Optional[DatabaseConnectionManager] = None
        
    def configure(self, config: Dict[str, Any]):
        """
        Configure container with settings
        
        Args:
            config: Configuration dictionary
        """
        self.configuration.update(config)
        logger.info("Diagnostic Container v6.1.0 configured with PostgreSQL")
    
    async def initialize(self) -> bool:
        """
        Initialize all services and dependencies mit Database Manager
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing Diagnostic Service Container v6.1.0...")
            
            # Initialize Database Manager
            db_config = DatabaseConfiguration()
            self._db_manager = DatabaseConnectionManager(db_config)
            await self._db_manager.initialize()
            
            # Initialize all repository schemas
            if self.configuration['database_manager']['auto_initialize_schema']:
                success = await self._initialize_schemas()
                if not success:
                    logger.error("Failed to initialize database schemas")
                    return False
            
            # Initialize repositories
            await self._initialize_repositories()
            
            # Initialize external services
            await self._initialize_external_services()
            
            # Initialize use cases
            await self._initialize_use_cases()
            
            self.initialized = True
            self.initialization_time = datetime.now(timezone.utc)
            
            logger.info("Diagnostic Service Container v6.1.0 initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Container initialization failed: {e}")
            self.initialization_error = str(e)
            return False
    
    async def _initialize_schemas(self) -> bool:
        """Initialize all database schemas"""
        try:
            # Initialize event repository schema
            event_repo = PostgreSQLDiagnosticEventRepository(self._db_manager)
            if not await event_repo.initialize_schema():
                return False
            
            # Initialize test repository schema
            test_repo = PostgreSQLDiagnosticTestRepository(self._db_manager)
            if not await test_repo.initialize_schema():
                return False
            
            # Initialize health repository schema
            health_repo = PostgreSQLSystemHealthRepository(self._db_manager)
            if not await health_repo.initialize_schema():
                return False
            
            # Initialize communication repository schema
            comm_repo = PostgreSQLModuleCommunicationRepository(self._db_manager)
            if not await comm_repo.initialize_schema():
                return False
                
            logger.info("All diagnostic schemas initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            return False
    
    async def _initialize_repositories(self):
        """Initialize repositories mit PostgreSQL"""
        try:
            # Diagnostic Event Repository
            self.services['event_repository'] = PostgreSQLDiagnosticEventRepository(self._db_manager)
            self.started_services.add('event_repository')
            
            # Diagnostic Test Repository  
            self.services['test_repository'] = PostgreSQLDiagnosticTestRepository(self._db_manager)
            self.started_services.add('test_repository')
            
            # System Health Repository
            self.services['health_repository'] = PostgreSQLSystemHealthRepository(self._db_manager)
            self.started_services.add('health_repository')
            
            # Module Communication Repository
            self.services['communication_repository'] = PostgreSQLModuleCommunicationRepository(self._db_manager)
            self.started_services.add('communication_repository')
            
            logger.info("PostgreSQL repositories initialized")
            
        except Exception as e:
            logger.error(f"Repository initialization failed: {e}")
            self.failed_services.update(['event_repository', 'test_repository', 'health_repository', 'communication_repository'])
            raise
    
    async def _initialize_external_services(self):
        """Initialize external services"""
        try:
            # Event Bus Provider
            if self.configuration.get('use_mock_event_bus', True):
                self.services['event_bus_provider'] = MockDiagnosticEventBusProvider()
            else:
                self.services['event_bus_provider'] = DiagnosticEventBusProvider(
                    host=self.configuration['event_bus_host'],
                    port=self.configuration['event_bus_port']
                )
            
            # Event Publisher
            self.services['event_publisher'] = MockEventPublisher(max_stored_events=500)
            
            self.started_services.update(['event_bus_provider', 'event_publisher'])
            logger.info("External services initialized")
            
        except Exception as e:
            logger.error(f"External services initialization failed: {e}")
            self.failed_services.update(['event_bus_provider', 'event_publisher'])
            raise
    
    async def _initialize_use_cases(self):
        """Initialize use cases mit repository dependencies"""
        try:
            # Event Monitoring Use Case
            self.services['event_monitoring'] = EventMonitoringUseCase(
                event_repository=self.services['event_repository'],
                event_publisher=self.services.get('event_publisher')
            )
            
            # Diagnostic Testing Use Case
            self.services['diagnostic_testing'] = DiagnosticTestingUseCase(
                test_repository=self.services['test_repository'],
                event_publisher=self.services.get('event_publisher')
            )
            
            # System Health Use Case
            self.services['system_health'] = SystemHealthUseCase(
                health_repository=self.services['health_repository'],
                event_repository=self.services['event_repository'],
                event_publisher=self.services.get('event_publisher')
            )
            
            # Diagnostic Maintenance Use Case
            self.services['diagnostic_maintenance'] = DiagnosticMaintenanceUseCase(
                event_repository=self.services['event_repository'],
                test_repository=self.services['test_repository'],
                health_repository=self.services['health_repository'],
                event_publisher=self.services.get('event_publisher')
            )
            
            self.started_services.update([
                'event_monitoring', 'diagnostic_testing', 
                'system_health', 'diagnostic_maintenance'
            ])
            logger.info("Use cases initialized")
            
        except Exception as e:
            logger.error(f"Use cases initialization failed: {e}")
            self.failed_services.update([
                'event_monitoring', 'diagnostic_testing',
                'system_health', 'diagnostic_maintenance'
            ])
            raise
    
    def get_event_repository(self) -> IDiagnosticEventRepository:
        """Get event repository"""
        return self.services['event_repository']
    
    def get_test_repository(self) -> IDiagnosticTestRepository:
        """Get test repository"""
        return self.services['test_repository']
    
    def get_health_repository(self) -> ISystemHealthRepository:
        """Get health repository"""
        return self.services['health_repository']
    
    def get_communication_repository(self) -> IModuleCommunicationRepository:
        """Get communication repository"""
        return self.services['communication_repository']
    
    def get_event_bus_provider(self) -> IDiagnosticEventBusProvider:
        """Get event bus provider"""
        return self.services['event_bus_provider']
    
    def get_event_publisher(self) -> IEventPublisher:
        """Get event publisher"""
        return self.services['event_publisher']
    
    def get_event_monitoring_use_case(self) -> EventMonitoringUseCase:
        """Get event monitoring use case"""
        return self.services['event_monitoring']
    
    def get_diagnostic_testing_use_case(self) -> DiagnosticTestingUseCase:
        """Get diagnostic testing use case"""
        return self.services['diagnostic_testing']
    
    def get_system_health_use_case(self) -> SystemHealthUseCase:
        """Get system health use case"""
        return self.services['system_health']
    
    def get_diagnostic_maintenance_use_case(self) -> DiagnosticMaintenanceUseCase:
        """Get diagnostic maintenance use case"""
        return self.services['diagnostic_maintenance']
    
    def get_database_manager(self) -> DatabaseConnectionManager:
        """Get database manager"""
        if self._db_manager is None:
            raise RuntimeError("Database Manager not initialized")
        return self._db_manager
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Health status dictionary
        """
        try:
            health_data = {
                'container': {
                    'version': '6.1.0',
                    'database': 'PostgreSQL',
                    'initialized': self.initialized,
                    'initialization_time': self.initialization_time.isoformat() if self.initialization_time else None,
                    'initialization_error': self.initialization_error,
                    'started_services': len(self.started_services),
                    'failed_services': len(self.failed_services),
                    'service_list': list(self.started_services)
                },
                'components': {}
            }
            
            # Database Manager Health
            if self._db_manager:
                try:
                    db_health = await self._db_manager.health_check()
                    health_data['components']['database_manager'] = {
                        'status': 'healthy' if db_health.get('healthy') else 'unhealthy',
                        'details': db_health
                    }
                except Exception as e:
                    health_data['components']['database_manager'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            # Repository Health Checks
            repositories = [
                ('event_repository', 'events'),
                ('test_repository', 'tests'),
                ('health_repository', 'health_snapshots'),
                ('communication_repository', 'communication_tests')
            ]
            
            for repo_key, repo_name in repositories:
                if repo_key in self.services:
                    try:
                        repo = self.services[repo_key]
                        if hasattr(repo, 'get_repository_stats'):
                            stats = await repo.get_repository_stats()
                            health_data['components'][repo_name] = {
                                'status': 'healthy',
                                'stats': stats
                            }
                        else:
                            health_data['components'][repo_name] = {
                                'status': 'healthy',
                                'info': 'basic_implementation'
                            }
                    except Exception as e:
                        health_data['components'][repo_name] = {
                            'status': 'unhealthy',
                            'error': str(e)
                        }
            
            # Use Cases Health
            use_cases = [
                'event_monitoring', 'diagnostic_testing',
                'system_health', 'diagnostic_maintenance'
            ]
            
            for use_case in use_cases:
                if use_case in self.services:
                    health_data['components'][use_case] = {
                        'status': 'healthy',
                        'initialized': True
                    }
                else:
                    health_data['components'][use_case] = {
                        'status': 'not_initialized'
                    }
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'container': {
                    'version': '6.1.0',
                    'database': 'PostgreSQL'
                }
            }
    
    async def shutdown(self) -> bool:
        """
        Graceful shutdown of container and resources
        
        Returns:
            True if shutdown successful
        """
        try:
            logger.info("Shutting down Diagnostic Service Container...")
            
            # Clear services
            self.services.clear()
            self.started_services.clear()
            
            # Shutdown database manager
            if self._db_manager:
                await self._db_manager.close()
                self._db_manager = None
            
            self.initialized = False
            
            logger.info("Diagnostic Service Container shutdown completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during container shutdown: {e}")
            return False
    
    async def reset_for_testing(self):
        """Reset container for testing"""
        await self.shutdown()
        self.__init__()


# Global container instance
container = DiagnosticServiceContainer()