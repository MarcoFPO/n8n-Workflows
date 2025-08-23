#!/usr/bin/env python3
"""
Service Base Architecture v1.0.0 - SOLID Service Foundation
Eliminiert DRY-Verletzungen und implementiert Clean Architecture für Services

Code-Qualität: HÖCHSTE PRIORITÄT
- Single Responsibility: Service-spezifische Abstraktion
- Open/Closed: Erweiterbar für neue Service-Types
- Liskov Substitution: Vererbung ohne Breaking Changes
- Interface Segregation: Getrennte Service Concerns
- Dependency Inversion: Abstract Dependencies
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Protocol
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

# Import Management - CLEAN ARCHITECTURE  
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()

# Service Discovery Integration
from shared.config_manager_v1_0_0_20250822 import (
    get_service_discovery, 
    get_config_manager,
    ServiceType
)

class ServiceState(Enum):
    """Service State Enumeration"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class HealthStatus(Enum):
    """Health Check Status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceMetrics:
    """Service Performance Metrics"""
    requests_total: int = 0
    requests_success: int = 0
    requests_error: int = 0
    response_time_avg: float = 0.0
    uptime_seconds: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_success / self.requests_total) * 100.0
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_error / self.requests_total) * 100.0

@dataclass
class HealthCheckResult:
    """Health Check Result"""
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0

# INTERFACES - Interface Segregation Principle

class IHealthCheckable(Protocol):
    """Health Check Interface"""
    async def health_check(self) -> HealthCheckResult:
        """Perform health check"""
        ...

class IMetricsProvider(Protocol):
    """Metrics Provider Interface"""
    def get_metrics(self) -> ServiceMetrics:
        """Get service metrics"""
        ...

class IConfigurable(Protocol):
    """Configuration Interface"""
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure service"""
        ...

class ILifecycleManaged(Protocol):
    """Lifecycle Management Interface"""
    async def start(self) -> bool:
        """Start service"""
        ...
        
    async def stop(self) -> bool:
        """Stop service"""
        ...
        
    async def restart(self) -> bool:
        """Restart service"""
        ...

# BASE ABSTRACTIONS

class BaseService(ABC, IHealthCheckable, IMetricsProvider, ILifecycleManaged):
    """
    Base Service Class - Single Responsibility
    Provides common service functionality following SOLID principles
    """
    
    def __init__(self, 
                 service_name: str,
                 service_type: ServiceType,
                 version: str = "1.0.0"):
        self.service_name = service_name
        self.service_type = service_type
        self.version = version
        self.state = ServiceState.INITIALIZING
        self.logger = logging.getLogger(service_name)
        
        # Service Discovery Integration
        self.service_discovery = get_service_discovery()
        self.config_manager = get_config_manager()
        
        # Metrics and Health
        self.metrics = ServiceMetrics()
        self.start_time = datetime.now()
        self.last_health_check: Optional[HealthCheckResult] = None
        
        # Configuration
        self._config: Dict[str, Any] = {}
        
    @property
    def service_url(self) -> str:
        """Get service URL via Service Discovery"""
        return self.service_discovery.get_service_url(self.service_type)
    
    @property
    def health_url(self) -> str:
        """Get health check URL"""
        return self.service_discovery.get_health_url(self.service_type)
    
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure service - Interface Segregation"""
        try:
            self._config.update(config)
            self.logger.info(f"Service {self.service_name} configured")
            return True
        except Exception as e:
            self.logger.error(f"Configuration failed: {e}")
            return False
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def update_metrics(self, 
                      request_success: bool = True,
                      response_time: float = 0.0) -> None:
        """Update service metrics"""
        self.metrics.requests_total += 1
        
        if request_success:
            self.metrics.requests_success += 1
        else:
            self.metrics.requests_error += 1
        
        # Update average response time
        if self.metrics.requests_total > 1:
            self.metrics.response_time_avg = (
                (self.metrics.response_time_avg * (self.metrics.requests_total - 1) + response_time) 
                / self.metrics.requests_total
            )
        else:
            self.metrics.response_time_avg = response_time
        
        # Update uptime
        self.metrics.uptime_seconds = int((datetime.now() - self.start_time).total_seconds())
    
    def get_metrics(self) -> ServiceMetrics:
        """Get current service metrics"""
        self.metrics.uptime_seconds = int((datetime.now() - self.start_time).total_seconds())
        return self.metrics
    
    async def health_check(self) -> HealthCheckResult:
        """Default health check implementation"""
        try:
            # Basic health check
            health_details = {
                "service_name": self.service_name,
                "version": self.version,
                "state": self.state.value,
                "uptime_seconds": self.metrics.uptime_seconds,
                "success_rate": self.metrics.success_rate
            }
            
            # Determine health status
            if self.state == ServiceState.RUNNING:
                if self.metrics.success_rate >= 95.0:
                    status = HealthStatus.HEALTHY
                    message = "Service is healthy"
                elif self.metrics.success_rate >= 80.0:
                    status = HealthStatus.DEGRADED
                    message = "Service is degraded"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = "Service is unhealthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Service state: {self.state.value}"
            
            result = HealthCheckResult(
                status=status,
                message=message,
                details=health_details
            )
            
            self.last_health_check = result
            return result
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {e}",
                details={"error": str(e)}
            )
    
    async def start(self) -> bool:
        """Start service - Template Method Pattern"""
        try:
            self.state = ServiceState.INITIALIZING
            self.logger.info(f"Starting service {self.service_name}")
            
            # Call template method
            if await self._initialize():
                self.state = ServiceState.RUNNING
                self.start_time = datetime.now()
                self.logger.info(f"Service {self.service_name} started successfully")
                return True
            else:
                self.state = ServiceState.ERROR
                self.logger.error(f"Service {self.service_name} failed to start")
                return False
                
        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Error starting service {self.service_name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop service - Template Method Pattern"""
        try:
            self.state = ServiceState.STOPPING
            self.logger.info(f"Stopping service {self.service_name}")
            
            # Call template method
            if await self._cleanup():
                self.state = ServiceState.STOPPED
                self.logger.info(f"Service {self.service_name} stopped successfully")
                return True
            else:
                self.state = ServiceState.ERROR
                self.logger.error(f"Service {self.service_name} failed to stop cleanly")
                return False
                
        except Exception as e:
            self.state = ServiceState.ERROR
            self.logger.error(f"Error stopping service {self.service_name}: {e}")
            return False
    
    async def restart(self) -> bool:
        """Restart service"""
        self.logger.info(f"Restarting service {self.service_name}")
        if await self.stop():
            await asyncio.sleep(1.0)  # Brief pause
            return await self.start()
        return False
    
    # TEMPLATE METHODS - Open/Closed Principle
    
    @abstractmethod
    async def _initialize(self) -> bool:
        """Initialize service - Template method for subclasses"""
        pass
    
    @abstractmethod
    async def _cleanup(self) -> bool:
        """Cleanup service - Template method for subclasses"""
        pass
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information"""
        return {
            "service_name": self.service_name,
            "service_type": self.service_type.value,
            "version": self.version,
            "state": self.state.value,
            "service_url": self.service_url,
            "health_url": self.health_url,
            "metrics": {
                "requests_total": self.metrics.requests_total,
                "success_rate": self.metrics.success_rate,
                "error_rate": self.metrics.error_rate,
                "response_time_avg": self.metrics.response_time_avg,
                "uptime_seconds": self.metrics.uptime_seconds
            },
            "last_health_check": {
                "status": self.last_health_check.status.value if self.last_health_check else "unknown",
                "timestamp": self.last_health_check.timestamp.isoformat() if self.last_health_check else None
            } if self.last_health_check else None
        }

# SPECIALIZED SERVICE TYPES

class WebService(BaseService):
    """
    Web Service Base - Single Responsibility
    Common functionality for HTTP/REST services
    """
    
    def __init__(self, 
                 service_name: str,
                 service_type: ServiceType,
                 port: int,
                 host: str = "0.0.0.0",
                 version: str = "1.0.0"):
        super().__init__(service_name, service_type, version)
        self.port = port
        self.host = host
        self.app: Optional[Any] = None  # FastAPI/Flask app
        
    @property
    def listen_address(self) -> str:
        """Get listen address"""
        return f"{self.host}:{self.port}"
    
    async def _initialize(self) -> bool:
        """Default web service initialization"""
        self.logger.info(f"Web service {self.service_name} listening on {self.listen_address}")
        return True
    
    async def _cleanup(self) -> bool:
        """Default web service cleanup"""
        self.logger.info(f"Web service {self.service_name} stopped")
        return True

class DataService(BaseService):
    """
    Data Service Base - Single Responsibility  
    Common functionality for data processing services
    """
    
    def __init__(self,
                 service_name: str,
                 service_type: ServiceType,
                 data_sources: List[str] = None,
                 version: str = "1.0.0"):
        super().__init__(service_name, service_type, version)
        self.data_sources = data_sources or []
        self.data_connections: Dict[str, Any] = {}
        
    async def _initialize(self) -> bool:
        """Default data service initialization"""
        self.logger.info(f"Data service {self.service_name} initialized with {len(self.data_sources)} sources")
        return True
    
    async def _cleanup(self) -> bool:
        """Default data service cleanup"""
        # Close data connections
        for name, connection in self.data_connections.items():
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
                self.logger.info(f"Closed data connection: {name}")
            except Exception as e:
                self.logger.warning(f"Error closing connection {name}: {e}")
        
        self.data_connections.clear()
        return True

class EventService(BaseService):
    """
    Event Service Base - Single Responsibility
    Common functionality for event-driven services
    """
    
    def __init__(self,
                 service_name: str,
                 service_type: ServiceType,
                 event_bus_url: Optional[str] = None,
                 version: str = "1.0.0"):
        super().__init__(service_name, service_type, version)
        self.event_bus_url = event_bus_url or self.service_discovery.get_service_url(ServiceType.EVENT_BUS)
        self.event_subscriptions: List[str] = []
        
    async def _initialize(self) -> bool:
        """Default event service initialization"""
        self.logger.info(f"Event service {self.service_name} connecting to event bus: {self.event_bus_url}")
        return True
    
    async def _cleanup(self) -> bool:
        """Default event service cleanup"""
        self.logger.info(f"Event service {self.service_name} unsubscribing from {len(self.event_subscriptions)} events")
        self.event_subscriptions.clear()
        return True

# SERVICE FACTORY - Factory Pattern

class ServiceFactory:
    """
    Service Factory - Factory Pattern
    Creates appropriate service instances based on type
    """
    
    @staticmethod
    def create_web_service(service_name: str,
                          service_type: ServiceType,
                          port: int,
                          host: str = "0.0.0.0",
                          version: str = "1.0.0") -> WebService:
        """Create web service instance"""
        return WebService(service_name, service_type, port, host, version)
    
    @staticmethod
    def create_data_service(service_name: str,
                           service_type: ServiceType,
                           data_sources: List[str] = None,
                           version: str = "1.0.0") -> DataService:
        """Create data service instance"""
        return DataService(service_name, service_type, data_sources, version)
    
    @staticmethod
    def create_event_service(service_name: str,
                            service_type: ServiceType,
                            event_bus_url: Optional[str] = None,
                            version: str = "1.0.0") -> EventService:
        """Create event service instance"""
        return EventService(service_name, service_type, event_bus_url, version)

# SERVICE REGISTRY - Singleton Pattern

class ServiceRegistry:
    """
    Service Registry - Singleton Pattern
    Centralized service management and discovery
    """
    
    _instance: Optional['ServiceRegistry'] = None
    _services: Dict[str, BaseService] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register_service(self, service: BaseService) -> bool:
        """Register a service"""
        try:
            self._services[service.service_name] = service
            logging.info(f"Service registered: {service.service_name}")
            return True
        except Exception as e:
            logging.error(f"Failed to register service {service.service_name}: {e}")
            return False
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister a service"""
        try:
            if service_name in self._services:
                del self._services[service_name]
                logging.info(f"Service unregistered: {service_name}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to unregister service {service_name}: {e}")
            return False
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get service by name"""
        return self._services.get(service_name)
    
    def get_all_services(self) -> Dict[str, BaseService]:
        """Get all registered services"""
        return self._services.copy()
    
    def get_services_by_type(self, service_type: ServiceType) -> List[BaseService]:
        """Get services by type"""
        return [service for service in self._services.values() 
                if service.service_type == service_type]
    
    async def health_check_all(self) -> Dict[str, HealthCheckResult]:
        """Perform health check on all services"""
        results = {}
        for service_name, service in self._services.items():
            try:
                results[service_name] = await service.health_check()
            except Exception as e:
                results[service_name] = HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {e}"
                )
        return results

# GLOBAL REGISTRY INSTANCE
def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance"""
    return ServiceRegistry()

if __name__ == "__main__":
    # Test the service base architecture
    import asyncio
    
    async def test_service_base():
        print("=== Service Base Architecture Test ===")
        
        # Create different service types
        web_service = ServiceFactory.create_web_service(
            "test-frontend", ServiceType.FRONTEND, 8080, version="1.0.0"
        )
        
        data_service = ServiceFactory.create_data_service(
            "test-data", ServiceType.DATA_PROCESSING, ["db", "api"], version="1.0.0"
        )
        
        event_service = ServiceFactory.create_event_service(
            "test-events", ServiceType.EVENT_BUS, version="1.0.0"
        )
        
        # Register services
        registry = get_service_registry()
        registry.register_service(web_service)
        registry.register_service(data_service)
        registry.register_service(event_service)
        
        print(f"Registered {len(registry.get_all_services())} services")
        
        # Test service info
        for service_name, service in registry.get_all_services().items():
            print(f"\n--- {service_name} ---")
            info = service.get_service_info()
            print(f"Type: {info['service_type']}")
            print(f"URL: {info['service_url']}")
            print(f"Health URL: {info['health_url']}")
        
        # Test health checks
        print("\n=== Health Check Results ===")
        health_results = await registry.health_check_all()
        for service_name, result in health_results.items():
            print(f"{service_name}: {result.status.value} - {result.message}")
        
        print("\n✅ Service Base Architecture test completed!")
    
    asyncio.run(test_service_base())