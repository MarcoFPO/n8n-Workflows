#!/usr/bin/env python3
"""
Frontend Service Dependency Injection Container - Clean Architecture v1.0.0
Composition Root for Frontend Service Dependencies

INFRASTRUCTURE LAYER - DEPENDENCY INJECTION:
- Complete DI Container für alle Frontend Components
- Configurable service implementations  
- Health monitoring and lifecycle management
- Service integration orchestration

DESIGN PATTERNS IMPLEMENTED:
- Dependency Injection: Centralized dependency management
- Factory Pattern: Service instance creation
- Singleton Pattern: Single container instance
- Observer Pattern: Health monitoring

Based on: ML-Analytics Container Template (successful migration)

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Type, Callable
import os

# Application Layer Imports
from ..application.use_cases.dashboard_use_cases import (
    GetDashboardUseCase,
    UpdateServiceStatusUseCase, 
    PerformHealthCheckUseCase,
    GetSystemStatusUseCase
)
from ..application.interfaces.http_client_interface import IHTTPClient
from ..application.interfaces.template_service_interface import ITemplateService

# Domain Layer Imports  
from ..domain.entities.dashboard_entity import DashboardEntity, ServiceInfo, ServiceHealth
from ..domain.services.dashboard_domain_service import (
    DashboardOrchestrationService,
    DashboardHealthAnalyzer
)

# Infrastructure Layer Imports
from .http_clients.aiohttp_client import AioHTTPClientService
from .external_services.service_client_pool import ServiceClientPool
from ..presentation.templates.html_template_service import HTMLTemplateService
from .configuration.frontend_config import FrontendServiceConfig


logger = logging.getLogger(__name__)


class FrontendServiceContainer:
    """
    Frontend Service Dependency Injection Container
    
    COMPOSITION ROOT PATTERN:
    - Single point of dependency configuration
    - Manages service lifecycles
    - Provides dependency resolution
    - Handles service health monitoring
    
    BASED ON: ML-Analytics Container Success Pattern
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize container with configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._is_initialized = False
        self._health_check_interval = 60  # seconds
        self._health_monitor_task: Optional[asyncio.Task] = None
        
        logger.info("Frontend Service Container initialized")
    
    async def initialize(self) -> None:
        """
        Initialize all container services
        
        INITIALIZATION ORDER (Critical for Dependencies):
        1. Configuration Services
        2. Infrastructure Services  
        3. Domain Services
        4. Application Services
        5. Health Monitoring
        """
        if self._is_initialized:
            logger.warning("Container already initialized")
            return
        
        try:
            logger.info("Initializing Frontend Service Container...")
            
            # 1. Configuration Services
            await self._initialize_configuration()
            
            # 2. Infrastructure Services
            await self._initialize_infrastructure_services()
            
            # 3. Domain Services
            await self._initialize_domain_services()
            
            # 4. Application Services
            await self._initialize_application_services()
            
            # 5. Dashboard Entity with Services
            await self._initialize_dashboard_entity()
            
            # 6. Health Monitoring
            await self._start_health_monitoring()
            
            self._is_initialized = True
            logger.info("Frontend Service Container initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Container initialization failed: {str(e)}")
            raise ContainerInitializationError(f"Failed to initialize container: {str(e)}") from e
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all services"""
        try:
            logger.info("Shutting down Frontend Service Container...")
            
            # Stop health monitoring
            if self._health_monitor_task:
                self._health_monitor_task.cancel()
                try:
                    await self._health_monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown services (reverse order)
            for service_name in reversed(list(self._services.keys())):
                service = self._services[service_name]
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
            
            self._is_initialized = False
            logger.info("Frontend Service Container shutdown completed")
            
        except Exception as e:
            logger.error(f"Container shutdown error: {str(e)}")
    
    # ==========================================================================
    # SERVICE GETTERS (Public API)
    # ==========================================================================
    
    def get_dashboard_use_case(self) -> GetDashboardUseCase:
        """Get Dashboard Use Case"""
        return self._get_service('dashboard_use_case')
    
    def get_service_status_use_case(self) -> UpdateServiceStatusUseCase:
        """Get Service Status Update Use Case"""
        return self._get_service('service_status_use_case')
    
    def get_health_check_use_case(self) -> PerformHealthCheckUseCase:
        """Get Health Check Use Case"""
        return self._get_service('health_check_use_case')
    
    def get_system_status_use_case(self) -> GetSystemStatusUseCase:
        """Get System Status Use Case"""
        return self._get_service('system_status_use_case')
    
    def get_dashboard_entity(self) -> DashboardEntity:
        """Get Dashboard Entity (Singleton)"""
        return self._get_service('dashboard_entity')
    
    def get_http_client(self) -> IHTTPClient:
        """Get HTTP Client"""
        return self._get_service('http_client')
    
    def get_template_service(self) -> ITemplateService:
        """Get Template Service"""
        return self._get_service('template_service')
    
    def get_config(self) -> FrontendServiceConfig:
        """Get Frontend Configuration"""
        return self._get_service('config')
    
    # ==========================================================================
    # INITIALIZATION METHODS (Private)
    # ==========================================================================
    
    async def _initialize_configuration(self) -> None:
        """Initialize configuration services"""
        logger.info("Initializing configuration services...")
        
        # Frontend Service Configuration
        config = FrontendServiceConfig(self._config)
        await config.initialize()
        self._services['config'] = config
        
        logger.info("Configuration services initialized")
    
    async def _initialize_infrastructure_services(self) -> None:
        """Initialize infrastructure layer services"""
        logger.info("Initializing infrastructure services...")
        
        config = self._services['config']
        
        # HTTP Client Service
        http_client = AioHTTPClientService(
            timeout_seconds=config.get_http_timeout(),
            max_connections=config.get_max_connections()
        )
        await http_client.initialize()
        self._services['http_client'] = http_client
        
        # Service Client Pool
        service_pool = ServiceClientPool(http_client, config.get_service_urls())
        await service_pool.initialize()
        self._services['service_pool'] = service_pool
        
        # Template Service
        template_service = HTMLTemplateService(
            version=config.get_version(),
            theme=config.get_default_theme()
        )
        await template_service.initialize()
        self._services['template_service'] = template_service
        
        logger.info("Infrastructure services initialized")
    
    async def _initialize_domain_services(self) -> None:
        """Initialize domain layer services"""
        logger.info("Initializing domain services...")
        
        # Dashboard Health Analyzer
        health_analyzer = DashboardHealthAnalyzer()
        self._services['health_analyzer'] = health_analyzer
        
        # Dashboard Orchestration Service
        orchestration_service = DashboardOrchestrationService()
        self._services['orchestration_service'] = orchestration_service
        
        logger.info("Domain services initialized")
    
    async def _initialize_application_services(self) -> None:
        """Initialize application layer services"""
        logger.info("Initializing application services...")
        
        http_client = self._services['http_client']
        template_service = self._services['template_service'] 
        orchestration_service = self._services['orchestration_service']
        health_analyzer = self._services['health_analyzer']
        
        # Dashboard Use Case
        dashboard_use_case = GetDashboardUseCase(
            http_client, template_service, orchestration_service
        )
        self._services['dashboard_use_case'] = dashboard_use_case
        
        # Service Status Update Use Case
        service_status_use_case = UpdateServiceStatusUseCase(
            http_client, orchestration_service
        )
        self._services['service_status_use_case'] = service_status_use_case
        
        # Health Check Use Case
        health_check_use_case = PerformHealthCheckUseCase(
            http_client, health_analyzer
        )
        self._services['health_check_use_case'] = health_check_use_case
        
        # System Status Use Case
        system_status_use_case = GetSystemStatusUseCase(
            template_service, health_analyzer
        )
        self._services['system_status_use_case'] = system_status_use_case
        
        logger.info("Application services initialized")
    
    async def _initialize_dashboard_entity(self) -> None:
        """Initialize dashboard entity with configured services"""
        logger.info("Initializing dashboard entity...")
        
        config = self._services['config']
        
        # Create dashboard entity
        dashboard = DashboardEntity(
            dashboard_id="frontend-dashboard",
            version=config.get_version()
        )
        
        # Add configured services
        service_configs = config.get_service_configurations()
        
        for service_config in service_configs:
            service_info = ServiceInfo(
                name=service_config['name'],
                url=service_config['url'],
                port=service_config['port'],
                status=ServiceHealth.UNKNOWN,  # Will be updated by health checks
                last_check=datetime.now()
            )
            dashboard.add_service(service_info)
        
        self._services['dashboard_entity'] = dashboard
        
        logger.info(f"Dashboard entity initialized with {len(service_configs)} services")
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring"""
        logger.info("Starting health monitoring...")
        
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        logger.info("Health monitoring started")
    
    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop"""
        health_check_use_case = self._services['health_check_use_case']
        dashboard_entity = self._services['dashboard_entity']
        
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                logger.debug("Performing periodic health checks...")
                health_summary = await health_check_use_case.execute(dashboard_entity)
                
                logger.info(
                    f"Health check completed: {health_summary['healthy_services']}"
                    f"/{health_summary['total_services']} services healthy"
                )
                
            except asyncio.CancelledError:
                logger.info("Health monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {str(e)}")
                # Continue monitoring despite errors
    
    # ==========================================================================
    # UTILITY METHODS (Private)
    # ==========================================================================
    
    def _get_service(self, service_name: str) -> Any:
        """Get service by name"""
        if not self._is_initialized:
            raise ContainerNotInitializedError("Container not initialized")
        
        if service_name not in self._services:
            raise ServiceNotFoundError(f"Service '{service_name}' not found")
        
        return self._services[service_name]
    
    def is_initialized(self) -> bool:
        """Check if container is initialized"""
        return self._is_initialized
    
    def get_service_health_summary(self) -> Dict[str, Any]:
        """Get summary of all service health"""
        if not self._is_initialized:
            return {"status": "container_not_initialized"}
        
        dashboard_entity = self._services.get('dashboard_entity')
        if not dashboard_entity:
            return {"status": "dashboard_not_available"}
        
        return dashboard_entity.get_status_summary()


# =============================================================================
# CONTAINER EXCEPTIONS
# =============================================================================

class ContainerError(Exception):
    """Base container error"""
    pass


class ContainerInitializationError(ContainerError):
    """Container initialization error"""
    pass


class ContainerNotInitializedError(ContainerError):
    """Container not initialized error"""
    pass


class ServiceNotFoundError(ContainerError):
    """Service not found error"""
    pass


class ServiceConfigurationError(ContainerError):
    """Service configuration error"""
    pass


# =============================================================================
# CONTAINER FACTORY
# =============================================================================

class FrontendContainerFactory:
    """
    Factory for creating Frontend Service Containers
    
    FACTORY PATTERN: Simplifies container creation with different configurations
    """
    
    @staticmethod
    def create_production_container() -> FrontendServiceContainer:
        """Create container for production environment"""
        config = {
            'environment': 'production',
            'host': os.getenv('FRONTEND_HOST', '0.0.0.0'),
            'port': int(os.getenv('FRONTEND_PORT', '8080')),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'health_check_interval': 60
        }
        return FrontendServiceContainer(config)
    
    @staticmethod
    def create_development_container() -> FrontendServiceContainer:
        """Create container for development environment"""
        config = {
            'environment': 'development',
            'host': 'localhost',
            'port': 8080,
            'log_level': 'DEBUG',
            'health_check_interval': 30
        }
        return FrontendServiceContainer(config)
    
    @staticmethod
    def create_test_container() -> FrontendServiceContainer:
        """Create container for testing environment"""
        config = {
            'environment': 'test',
            'host': 'localhost',
            'port': 8081,
            'log_level': 'DEBUG',
            'health_check_interval': 10,
            'use_mock_services': True
        }
        return FrontendServiceContainer(config)