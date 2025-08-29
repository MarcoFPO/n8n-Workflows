#!/usr/bin/env python3
"""
SOLID Principles Foundation Framework
Issue #62 - SOLID-Prinzipien durchsetzen

Dieses Modul implementiert die SOLID-Prinzipien-Foundation für das gesamte System:
- Single Responsibility Principle (SRP): Aufgeteilte Verantwortlichkeiten
- Open/Closed Principle (OCP): Erweiterbar ohne Änderungen  
- Liskov Substitution Principle (LSP): Konsistente Interface-Implementation
- Interface Segregation Principle (ISP): Kleine, spezifische Interfaces
- Dependency Inversion Principle (DIP): Dependency Injection Container

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Callable, Union
from datetime import datetime
from contextlib import asynccontextmanager
from enum import Enum
import inspect

# Exception Framework Integration
from .exceptions import BaseServiceException, ConfigurationException
from .exception_handler import ExceptionHandler

# Logger
logger = logging.getLogger(__name__)


# =============================================================================
# INTERFACE SEGREGATION PRINCIPLE (ISP) - Specific Interfaces
# =============================================================================

class Startable(ABC):
    """ISP: Interface nur für startbare Services"""
    
    @abstractmethod
    async def startup(self) -> bool:
        """Service starten"""
        pass


class Stoppable(ABC):
    """ISP: Interface nur für stoppbare Services"""
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Service stoppen"""
        pass


class Healthable(ABC):
    """ISP: Interface nur für Health-Check-fähige Services"""
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health-Status prüfen"""
        pass


class Configurable(ABC):
    """ISP: Interface nur für konfigurierbare Services"""
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """Service konfigurieren"""
        pass


class Loggable(ABC):
    """ISP: Interface nur für loggingfähige Services"""
    
    @abstractmethod
    def get_logger(self) -> logging.Logger:
        """Logger abrufen"""
        pass


class Routable(ABC):
    """ISP: Interface nur für routingfähige Services"""
    
    @abstractmethod
    def register_routes(self) -> Dict[str, Callable]:
        """Routes registrieren"""
        pass


class Monitorable(ABC):
    """ISP: Interface nur für monitoringfähige Services"""
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Monitoring-Metriken abrufen"""
        pass


# =============================================================================
# SINGLE RESPONSIBILITY PRINCIPLE (SRP) - Separated Components
# =============================================================================

class APIRouter:
    """SRP: Nur verantwortlich für API-Routing"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.routes: Dict[str, Callable] = {}
        self.middleware: List[Callable] = []
        self.logger = logging.getLogger(f"{service_name}.router")
    
    def add_route(self, path: str, method: str, handler: Callable, **kwargs):
        """Route hinzufügen"""
        route_key = f"{method.upper()}:{path}"
        self.routes[route_key] = {
            'handler': handler,
            'path': path,
            'method': method.upper(),
            'metadata': kwargs
        }
        self.logger.debug(f"Route registered: {route_key}")
    
    def add_middleware(self, middleware: Callable):
        """Middleware hinzufügen"""
        self.middleware.append(middleware)
        self.logger.debug(f"Middleware registered: {middleware.__name__}")
    
    def get_routes(self) -> Dict[str, Any]:
        """Alle Routes abrufen"""
        return self.routes


class ServiceManager:
    """SRP: Nur verantwortlich für Service-Lifecycle-Management"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.services: Dict[str, Any] = {}
        self.startup_order: List[str] = []
        self.shutdown_order: List[str] = []
        self.logger = logging.getLogger(f"{service_name}.manager")
        self.is_started = False
    
    def register_service(self, name: str, service: Any, startup_priority: int = 0):
        """Service registrieren"""
        self.services[name] = {
            'instance': service,
            'priority': startup_priority,
            'started': False
        }
        
        # Startup-Reihenfolge nach Priorität sortieren
        self.startup_order = sorted(
            self.services.keys(), 
            key=lambda x: self.services[x]['priority']
        )
        # Shutdown-Reihenfolge ist umgekehrt
        self.shutdown_order = list(reversed(self.startup_order))
        
        self.logger.debug(f"Service registered: {name} (priority: {startup_priority})")
    
    async def start_all(self) -> bool:
        """Alle Services starten"""
        try:
            for service_name in self.startup_order:
                service_info = self.services[service_name]
                service = service_info['instance']
                
                if isinstance(service, Startable):
                    self.logger.info(f"Starting service: {service_name}")
                    success = await service.startup()
                    service_info['started'] = success
                    
                    if not success:
                        self.logger.error(f"Failed to start service: {service_name}")
                        return False
            
            self.is_started = True
            self.logger.info(f"All services started successfully for {self.service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            await self.stop_all()  # Cleanup on failure
            return False
    
    async def stop_all(self) -> bool:
        """Alle Services stoppen"""
        try:
            for service_name in self.shutdown_order:
                service_info = self.services[service_name]
                service = service_info['instance']
                
                if isinstance(service, Stoppable) and service_info['started']:
                    self.logger.info(f"Stopping service: {service_name}")
                    await service.shutdown()
                    service_info['started'] = False
            
            self.is_started = False
            self.logger.info(f"All services stopped successfully for {self.service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
            return False
    
    def get_service(self, name: str) -> Optional[Any]:
        """Service-Instanz abrufen"""
        service_info = self.services.get(name)
        return service_info['instance'] if service_info else None


class HealthMonitor:
    """SRP: Nur verantwortlich für Health-Monitoring"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{service_name}.health")
    
    def register_health_check(self, name: str, check_func: Callable):
        """Health-Check registrieren"""
        self.health_checks[name] = check_func
        self.logger.debug(f"Health check registered: {name}")
    
    async def check_all(self) -> Dict[str, Any]:
        """Alle Health-Checks ausführen"""
        results = {
            'service': self.service_name,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        for check_name, check_func in self.health_checks.items():
            try:
                if inspect.iscoroutinefunction(check_func):
                    check_result = await check_func()
                else:
                    check_result = check_func()
                
                results['checks'][check_name] = {
                    'status': 'healthy',
                    'result': check_result,
                    'error': None
                }
                
            except Exception as e:
                results['checks'][check_name] = {
                    'status': 'unhealthy',
                    'result': None,
                    'error': str(e)
                }
                results['status'] = 'unhealthy'
                self.logger.warning(f"Health check failed: {check_name} - {e}")
        
        self.last_check_results[self.service_name] = results
        return results
    
    async def check_single(self, check_name: str) -> Dict[str, Any]:
        """Einzelnen Health-Check ausführen"""
        if check_name not in self.health_checks:
            raise ValueError(f"Health check not found: {check_name}")
        
        check_func = self.health_checks[check_name]
        try:
            if inspect.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            return {
                'check': check_name,
                'status': 'healthy',
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {check_name} - {e}")
            return {
                'check': check_name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# =============================================================================
# DEPENDENCY INVERSION PRINCIPLE (DIP) - IoC Container
# =============================================================================

T = TypeVar('T')

class ServiceContainer:
    """DIP: Inversion of Control Container für Dependency Injection"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._interfaces: Dict[Type, str] = {}
        self.logger = logging.getLogger(f"container.{name}")
    
    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """Singleton-Service registrieren"""
        interface_name = self._get_interface_name(interface)
        self._singletons[interface_name] = implementation
        self._interfaces[interface] = interface_name
        self.logger.debug(f"Singleton registered: {interface_name}")
    
    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Transient-Service registrieren (neue Instanz bei jedem Abruf)"""
        interface_name = self._get_interface_name(interface)
        self._factories[interface_name] = factory
        self._interfaces[interface] = interface_name
        self.logger.debug(f"Transient registered: {interface_name}")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """Service-Instanz registrieren"""
        interface_name = self._get_interface_name(interface)
        self._services[interface_name] = instance
        self._interfaces[interface] = interface_name
        self.logger.debug(f"Instance registered: {interface_name}")
    
    def resolve(self, interface: Type[T]) -> T:
        """Service-Implementierung auflösen"""
        interface_name = self._interfaces.get(interface)
        if not interface_name:
            raise ConfigurationException(
                f"Interface not registered: {interface.__name__}",
                context={'container': self.name, 'interface': interface.__name__}
            )
        
        # Singleton check
        if interface_name in self._singletons:
            return self._singletons[interface_name]
        
        # Instance check
        if interface_name in self._services:
            return self._services[interface_name]
        
        # Factory check
        if interface_name in self._factories:
            factory = self._factories[interface_name]
            return factory()
        
        raise ConfigurationException(
            f"No implementation found for interface: {interface.__name__}",
            context={'container': self.name, 'interface': interface.__name__}
        )
    
    def resolve_optional(self, interface: Type[T]) -> Optional[T]:
        """Service-Implementierung optional auflösen"""
        try:
            return self.resolve(interface)
        except ConfigurationException:
            return None
    
    def _get_interface_name(self, interface: Type) -> str:
        """Interface-Name bestimmen"""
        return f"{interface.__module__}.{interface.__name__}"
    
    def get_registrations(self) -> Dict[str, str]:
        """Alle Registrierungen abrufen"""
        registrations = {}
        
        for interface_name in self._singletons:
            registrations[interface_name] = 'singleton'
        
        for interface_name in self._services:
            registrations[interface_name] = 'instance'
        
        for interface_name in self._factories:
            registrations[interface_name] = 'transient'
        
        return registrations


# =============================================================================
# SOLID SERVICE ORCHESTRATOR - Combining all SOLID Principles
# =============================================================================

class SOLIDServiceOrchestrator:
    """
    SOLID-konforme Service-Orchestrator Implementation
    
    Vereint alle SOLID-Prinzipien:
    - SRP: Getrennte Komponenten für verschiedene Verantwortlichkeiten
    - OCP: Erweiterbar durch Interfaces ohne Code-Änderung
    - LSP: Konsistente Interface-Implementation
    - ISP: Spezifische, kleine Interfaces
    - DIP: Dependency Injection Container
    """
    
    def __init__(self, service_name: str, container: Optional[ServiceContainer] = None):
        self.service_name = service_name
        self.container = container or ServiceContainer(service_name)
        
        # SRP: Getrennte Komponenten
        self.api_router = APIRouter(service_name)
        self.service_manager = ServiceManager(service_name)
        self.health_monitor = HealthMonitor(service_name)
        
        # Logger
        self.logger = logging.getLogger(service_name)
        
        # Exception Handler
        self.exception_handler = ExceptionHandler()
        
        # Status
        self.is_initialized = False
        self.startup_timestamp: Optional[datetime] = None
    
    async def initialize(self) -> bool:
        """Service-Orchestrator initialisieren"""
        try:
            self.logger.info(f"Initializing SOLID Service Orchestrator: {self.service_name}")
            
            # Container-Services registrieren
            self.container.register_singleton(APIRouter, self.api_router)
            self.container.register_singleton(ServiceManager, self.service_manager)
            self.container.register_singleton(HealthMonitor, self.health_monitor)
            
            # Standard Health-Checks registrieren
            self.health_monitor.register_health_check(
                'orchestrator', 
                lambda: {'status': 'ok', 'initialized': self.is_initialized}
            )
            
            self.is_initialized = True
            self.startup_timestamp = datetime.utcnow()
            
            self.logger.info(f"SOLID Service Orchestrator initialized: {self.service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def start(self) -> bool:
        """Service starten"""
        if not self.is_initialized:
            if not await self.initialize():
                return False
        
        return await self.service_manager.start_all()
    
    async def stop(self) -> bool:
        """Service stoppen"""
        return await self.service_manager.stop_all()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive Health-Check"""
        base_health = await self.health_monitor.check_all()
        
        # Container-Status hinzufügen
        base_health['container'] = {
            'name': self.container.name,
            'registrations': len(self.container.get_registrations())
        }
        
        # Service-Manager-Status hinzufügen
        base_health['service_manager'] = {
            'is_started': self.service_manager.is_started,
            'services_count': len(self.service_manager.services)
        }
        
        return base_health
    
    def get_container(self) -> ServiceContainer:
        """DIP: Container abrufen"""
        return self.container
    
    def get_router(self) -> APIRouter:
        """SRP: Router abrufen"""
        return self.api_router
    
    def get_service_manager(self) -> ServiceManager:
        """SRP: Service-Manager abrufen"""
        return self.service_manager
    
    def get_health_monitor(self) -> HealthMonitor:
        """SRP: Health-Monitor abrufen"""
        return self.health_monitor


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_solid_orchestrator(
    service_name: str,
    container: Optional[ServiceContainer] = None
) -> SOLIDServiceOrchestrator:
    """Factory-Function für SOLID Service Orchestrator"""
    return SOLIDServiceOrchestrator(service_name, container)


def validate_solid_compliance(service_class: Type) -> Dict[str, bool]:
    """SOLID-Compliance eines Service validieren"""
    compliance = {
        'srp': True,  # Single Responsibility - schwer automatisch zu prüfen
        'ocp': hasattr(service_class, '__abstractmethods__'),  # Open/Closed
        'lsp': issubclass(service_class, ABC),  # Liskov Substitution
        'isp': True,  # Interface Segregation - prüfe auf kleine Interfaces
        'dip': True   # Dependency Inversion - prüfe auf Constructor Injection
    }
    
    # ISP: Prüfe Interface-Größe (max 5 abstrakte Methoden)
    if hasattr(service_class, '__abstractmethods__'):
        abstract_methods = len(service_class.__abstractmethods__)
        compliance['isp'] = abstract_methods <= 5
    
    # DIP: Prüfe Constructor für Dependency Injection
    if hasattr(service_class, '__init__'):
        init_signature = inspect.signature(service_class.__init__)
        # Mindestens ein Parameter (außer self) für DI
        compliance['dip'] = len(init_signature.parameters) > 1
    
    return compliance