#!/usr/bin/env python3
"""
Diagnostic Service - Dependency Injection Container
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER

Dependency injection und service configuration
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os

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

# Infrastructure implementations
from .persistence.sqlite_diagnostic_repository import (
    SQLiteDiagnosticEventRepository, SQLiteDiagnosticTestRepository,
    SQLiteSystemHealthRepository
)
from .external_services.diagnostic_event_bus_provider import (
    DiagnosticEventBusProvider, MockDiagnosticEventBusProvider
)
from .events.mock_event_publisher import MockEventPublisher


logger = logging.getLogger(__name__)


class DiagnosticServiceContainer:
    """
    Dependency Injection Container
    INFRASTRUCTURE LAYER: Service composition and configuration
    """
    
    def __init__(self):
        self.services = {}
        self.configuration = {}
        self.initialized = False
        self.initialization_error = None
        self.initialization_time = None
        self.health_status = {}
        
        # Service lifecycle tracking
        self.started_services = set()
        self.failed_services = set()
        
    def configure(self, config: Dict[str, Any]):
        """
        Configure container with settings
        
        Args:
            config: Configuration dictionary
        """
        self.configuration.update(config)
        logger.info("Container configured with settings")
    
    async def initialize(self) -> bool:
        """
        Initialize all services and dependencies
        
        Returns:
            bool: True if initialization successful
        """
        try:
            start_time = datetime.now()
            logger.info("Initializing Diagnostic Service Container...")
            
            # Initialize repositories
            await self._initialize_repositories()
            
            # Initialize external services
            await self._initialize_external_services()
            
            # Initialize application services
            await self._initialize_application_services()
            
            # Initialize use cases
            await self._initialize_use_cases()
            
            # Perform health checks
            await self._perform_initialization_health_checks()
            
            self.initialized = True
            self.initialization_time = datetime.now() - start_time
            
            logger.info(
                f"✅ Diagnostic Service Container initialized successfully "
                f"in {self.initialization_time.total_seconds():.2f}s"
            )
            
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"❌ Container initialization failed: {e}")
            return False
    
    async def _initialize_repositories(self):
        """Initialize repository implementations"""
        try:
            # Database paths from configuration
            events_db = self.configuration.get('events_database_path', 'diagnostic_events.db')
            tests_db = self.configuration.get('tests_database_path', 'diagnostic_tests.db')
            health_db = self.configuration.get('health_database_path', 'diagnostic_health.db')
            
            # Initialize SQLite repositories
            event_repo = SQLiteDiagnosticEventRepository(events_db)
            await event_repo.initialize()
            self.services['event_repository'] = event_repo
            self.started_services.add('event_repository')
            
            test_repo = SQLiteDiagnosticTestRepository(tests_db)
            await test_repo.initialize()
            self.services['test_repository'] = test_repo
            self.started_services.add('test_repository')
            
            health_repo = SQLiteSystemHealthRepository(health_db)
            await health_repo.initialize()
            self.services['health_repository'] = health_repo
            self.started_services.add('health_repository')
            
            # Mock communication repository (could be replaced with real implementation)
            from .persistence.mock_communication_repository import MockModuleCommunicationRepository
            comm_repo = MockModuleCommunicationRepository()
            self.services['communication_repository'] = comm_repo
            self.started_services.add('communication_repository')
            
            logger.info("Repository implementations initialized")
            
        except Exception as e:
            logger.error(f"Repository initialization failed: {e}")
            raise
    
    async def _initialize_external_services(self):
        """Initialize external service providers"""
        try:
            # Event Bus Provider
            use_real_event_bus = self.configuration.get('use_real_event_bus', False)
            event_bus_connector = self.configuration.get('event_bus_connector')
            
            if use_real_event_bus and event_bus_connector:
                event_bus_provider = DiagnosticEventBusProvider(event_bus_connector)
            else:
                event_bus_provider = MockDiagnosticEventBusProvider()
                
            self.services['event_bus_provider'] = event_bus_provider
            self.started_services.add('event_bus_provider')
            
            # Event Publisher
            event_publisher = MockEventPublisher(max_events=1000)
            
            # Configure failure simulation if specified
            simulate_failures = self.configuration.get('simulate_event_failures', False)
            failure_rate = self.configuration.get('event_failure_rate', 0.0)
            if simulate_failures:
                event_publisher.configure_failure_simulation(True, failure_rate)
            
            self.services['event_publisher'] = event_publisher
            self.started_services.add('event_publisher')
            
            logger.info("External service providers initialized")
            
        except Exception as e:
            logger.error(f"External services initialization failed: {e}")
            raise
    
    async def _initialize_application_services(self):
        """Initialize application layer services"""
        try:
            # Application services could include:
            # - Notification services
            # - Reporting services
            # - Alerting services
            # etc.
            
            # For now, placeholder
            logger.info("Application services initialized")
            
        except Exception as e:
            logger.error(f"Application services initialization failed: {e}")
            raise
    
    async def _initialize_use_cases(self):
        """Initialize use case orchestrators"""
        try:
            # Get dependencies
            event_repo = self.services['event_repository']
            test_repo = self.services['test_repository']
            health_repo = self.services['health_repository']
            comm_repo = self.services['communication_repository']
            event_bus_provider = self.services['event_bus_provider']
            event_publisher = self.services['event_publisher']
            
            # Initialize use cases
            self.services['event_monitoring_use_case'] = EventMonitoringUseCase(
                event_repo, event_bus_provider, event_publisher
            )
            
            self.services['diagnostic_testing_use_case'] = DiagnosticTestingUseCase(
                test_repo, comm_repo, event_bus_provider, event_publisher
            )
            
            self.services['system_health_use_case'] = SystemHealthUseCase(
                event_repo, health_repo, event_bus_provider, event_publisher
            )
            
            self.services['diagnostic_maintenance_use_case'] = DiagnosticMaintenanceUseCase(
                event_repo, test_repo, health_repo, comm_repo, event_publisher
            )
            
            logger.info("Use cases initialized")
            
        except Exception as e:
            logger.error(f"Use cases initialization failed: {e}")
            raise
    
    async def _perform_initialization_health_checks(self):
        """Perform health checks on initialized services"""
        try:
            # Check event bus provider
            event_bus_provider = self.services['event_bus_provider']
            bus_healthy = await event_bus_provider.is_event_bus_healthy()
            self.health_status['event_bus'] = bus_healthy
            
            # Check event publisher
            event_publisher = self.services['event_publisher']
            publisher_health = await event_publisher.get_publisher_health()
            self.health_status['event_publisher'] = publisher_health['is_healthy']
            
            # Check repository connectivity (basic operations)
            event_repo = self.services['event_repository']
            repo_stats = await event_repo.get_event_statistics()
            self.health_status['event_repository'] = True  # If no exception, it's working
            
            logger.info("Initialization health checks completed")
            
        except Exception as e:
            logger.warning(f"Health checks during initialization failed: {e}")
            # Don't fail initialization just because health checks failed
    
    def get_service(self, service_name: str) -> Any:
        """
        Get service instance by name
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        if not self.initialized:
            raise RuntimeError("Container not initialized. Call initialize() first.")
            
        service = self.services.get(service_name)
        if service is None:
            logger.warning(f"Service '{service_name}' not found in container")
            
        return service
    
    def has_service(self, service_name: str) -> bool:
        """
        Check if service exists in container
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            bool: True if service exists
        """
        return service_name in self.services
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services"""
        return self.services.copy()
    
    def get_container_status(self) -> Dict[str, Any]:
        """Get comprehensive container status"""
        return {
            'initialized': self.initialized,
            'initialization_error': self.initialization_error,
            'initialization_time_seconds': (
                self.initialization_time.total_seconds() 
                if self.initialization_time else None
            ),
            'total_services': len(self.services),
            'started_services': list(self.started_services),
            'failed_services': list(self.failed_services),
            'health_status': self.health_status,
            'configuration': {
                key: value for key, value in self.configuration.items()
                if 'password' not in key.lower() and 'secret' not in key.lower()
            },
            'service_names': list(self.services.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_detailed_health_report(self) -> Dict[str, Any]:
        """Get detailed health report for all services"""
        try:
            if not self.initialized:
                return {
                    'container_healthy': False,
                    'error': 'Container not initialized',
                    'timestamp': datetime.now().isoformat()
                }
            
            health_report = {
                'container_healthy': True,
                'timestamp': datetime.now().isoformat(),
                'service_health': {}
            }
            
            # Check each service health
            for service_name, service in self.services.items():
                try:
                    if hasattr(service, 'get_publisher_health'):
                        # Event publisher
                        service_health = await service.get_publisher_health()
                    elif hasattr(service, 'is_event_bus_healthy'):
                        # Event bus provider
                        service_health = {
                            'is_healthy': await service.is_event_bus_healthy(),
                            'service_type': 'event_bus_provider'
                        }
                    elif hasattr(service, 'get_event_statistics'):
                        # Event repository
                        stats = await service.get_event_statistics()
                        service_health = {
                            'is_healthy': True,
                            'service_type': 'repository',
                            'statistics': stats
                        }
                    else:
                        # Generic service
                        service_health = {
                            'is_healthy': True,
                            'service_type': type(service).__name__
                        }
                    
                    health_report['service_health'][service_name] = service_health
                    
                except Exception as e:
                    health_report['service_health'][service_name] = {
                        'is_healthy': False,
                        'error': str(e),
                        'service_type': type(service).__name__
                    }
                    health_report['container_healthy'] = False
            
            return health_report
            
        except Exception as e:
            return {
                'container_healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """Cleanup container and all services"""
        try:
            logger.info("Cleaning up Diagnostic Service Container...")
            
            # Could implement specific cleanup for each service type
            # For now, just clear references
            cleanup_tasks = []
            
            for service_name, service in self.services.items():
                if hasattr(service, 'cleanup'):
                    cleanup_tasks.append(service.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self.services.clear()
            self.started_services.clear()
            self.initialized = False
            
            logger.info("Container cleanup completed")
            
        except Exception as e:
            logger.error(f"Container cleanup failed: {e}")


# Mock Communication Repository for development
class MockModuleCommunicationRepository:
    """Mock implementation für development"""
    
    def __init__(self):
        self.communication_tests = {}
    
    async def save_communication_test(self, test) -> bool:
        """Mock save communication test"""
        self.communication_tests[test.test_id] = test
        return True
    
    async def update_test_response(
        self, 
        test_id: str,
        response_data: Dict[str, Any],
        success: bool,
        error_details: Optional[str] = None
    ) -> bool:
        """Mock update test response"""
        if test_id in self.communication_tests:
            # Update would happen here
            return True
        return False
    
    async def get_communication_test(self, test_id: str):
        """Mock get communication test"""
        return self.communication_tests.get(test_id)
    
    async def get_communication_tests(
        self, 
        source_module: Optional[str] = None,
        target_module: Optional[str] = None,
        limit: int = 100
    ):
        """Mock get communication tests"""
        tests = list(self.communication_tests.values())
        
        if source_module:
            tests = [t for t in tests if t.source_module == source_module]
        
        if target_module:
            tests = [t for t in tests if t.target_module == target_module]
            
        return tests[:limit]
    
    async def get_module_connectivity_stats(self, module_name: str) -> Dict[str, Any]:
        """Mock get connectivity stats"""
        return {
            'module_name': module_name,
            'total_tests': len(self.communication_tests),
            'successful_tests': len(self.communication_tests),  # Mock all successful
            'failed_tests': 0,
            'average_response_time_ms': 50.0,
            'last_test_at': datetime.now().isoformat()
        }


# Global container instance
diagnostic_container = DiagnosticServiceContainer()