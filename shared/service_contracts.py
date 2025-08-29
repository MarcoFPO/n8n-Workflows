#!/usr/bin/env python3
"""
Service Contracts - ISP-compliant Interface Segregation
Issue #62 - SOLID-Prinzipien durchsetzen - Phase 3: ISP-Compliance

Implementiert fein-granulare Service-Contracts für Interface Segregation Principle:
- Kleine, spezifische Interfaces statt monolithischer Contracts
- Komposition von Interfaces für komplexe Services
- Role-based Interface-Segregation

Author: System Modernization Team
Version: 1.0.0
Date: 2025-08-29
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Callable, AsyncContextManager
from datetime import datetime
from enum import Enum
import asyncio

# Exception Framework Integration
from .exceptions import BaseServiceException


# =============================================================================
# LIFECYCLE CONTRACTS (ISP - Fine-grained Lifecycle Interfaces)
# =============================================================================

class Initializable(ABC):
    """ISP: Interface nur für initialisierbare Services"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Service initialisieren"""
        pass
    
    @abstractmethod
    def is_initialized(self) -> bool:
        """Initialisierungs-Status prüfen"""
        pass


class Startable(ABC):
    """ISP: Interface nur für startbare Services"""
    
    @abstractmethod
    async def start(self) -> bool:
        """Service starten"""
        pass
    
    @abstractmethod
    def is_started(self) -> bool:
        """Start-Status prüfen"""
        pass


class Stoppable(ABC):
    """ISP: Interface nur für stoppbare Services"""
    
    @abstractmethod
    async def stop(self) -> bool:
        """Service stoppen"""
        pass
    
    @abstractmethod
    def is_stopped(self) -> bool:
        """Stop-Status prüfen"""
        pass


class Pausable(ABC):
    """ISP: Interface nur für pausierbare Services"""
    
    @abstractmethod
    async def pause(self) -> bool:
        """Service pausieren"""
        pass
    
    @abstractmethod
    async def resume(self) -> bool:
        """Service fortsetzen"""
        pass
    
    @abstractmethod
    def is_paused(self) -> bool:
        """Pause-Status prüfen"""
        pass


class Restartable(ABC):
    """ISP: Interface nur für neustartbare Services"""
    
    @abstractmethod
    async def restart(self) -> bool:
        """Service neu starten"""
        pass


# =============================================================================
# MONITORING CONTRACTS (ISP - Specific Monitoring Interfaces)
# =============================================================================

class Healthable(ABC):
    """ISP: Interface nur für Health-Check-fähige Services"""
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Health-Status prüfen"""
        pass


class Metricable(ABC):
    """ISP: Interface nur für Metrik-fähige Services"""
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Metriken abrufen"""
        pass


class Stateful(ABC):
    """ISP: Interface nur für zustandsbehaftete Services"""
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Aktuellen Zustand abrufen"""
        pass
    
    @abstractmethod
    async def save_state(self) -> bool:
        """Zustand persistieren"""
        pass
    
    @abstractmethod
    async def restore_state(self, state: Dict[str, Any]) -> bool:
        """Zustand wiederherstellen"""
        pass


class Diagnosticable(ABC):
    """ISP: Interface nur für diagnose-fähige Services"""
    
    @abstractmethod
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Diagnose ausführen"""
        pass
    
    @abstractmethod
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Diagnose-Informationen abrufen"""
        pass


# =============================================================================
# CONFIGURATION CONTRACTS (ISP - Configuration-specific Interfaces)
# =============================================================================

class Configurable(ABC):
    """ISP: Interface nur für konfigurierbare Services"""
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """Service konfigurieren"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Aktuelle Konfiguration abrufen"""
        pass


class Reconfigurable(ABC):
    """ISP: Interface nur für rekonfigurierbare Services"""
    
    @abstractmethod
    async def reconfigure(self, config: Dict[str, Any]) -> bool:
        """Service zur Laufzeit rekonfigurieren"""
        pass
    
    @abstractmethod
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Konfiguration validieren"""
        pass


class EnvironmentAware(ABC):
    """ISP: Interface nur für umgebungsbewusste Services"""
    
    @abstractmethod
    def get_environment(self) -> str:
        """Aktuelle Umgebung abrufen (dev, staging, prod)"""
        pass
    
    @abstractmethod
    def supports_environment(self, env: str) -> bool:
        """Prüfen ob Umgebung unterstützt wird"""
        pass


# =============================================================================
# COMMUNICATION CONTRACTS (ISP - Communication-specific Interfaces)
# =============================================================================

class EventPublisher(ABC):
    """ISP: Interface nur für Event-Publisher"""
    
    @abstractmethod
    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Event publizieren"""
        pass


class EventSubscriber(ABC):
    """ISP: Interface nur für Event-Subscriber"""
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable) -> str:
        """Event abonnieren"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Event-Abonnement aufheben"""
        pass


class MessageSender(ABC):
    """ISP: Interface nur für Message-Sender"""
    
    @abstractmethod
    async def send_message(self, recipient: str, message: Dict[str, Any]) -> bool:
        """Nachricht senden"""
        pass


class MessageReceiver(ABC):
    """ISP: Interface nur für Message-Receiver"""
    
    @abstractmethod
    async def receive_message(self, timeout_seconds: int = 30) -> Optional[Dict[str, Any]]:
        """Nachricht empfangen"""
        pass


class NotificationSender(ABC):
    """ISP: Interface nur für Notification-Sender"""
    
    @abstractmethod
    async def send_notification(
        self, 
        notification_type: str, 
        content: str, 
        recipients: List[str]
    ) -> bool:
        """Benachrichtigung senden"""
        pass


# =============================================================================
# DATA CONTRACTS (ISP - Data-specific Interfaces)
# =============================================================================

class Readable(ABC):
    """ISP: Interface nur für lesende Services"""
    
    @abstractmethod
    async def read(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Daten lesen"""
        pass


class Writable(ABC):
    """ISP: Interface nur für schreibende Services"""
    
    @abstractmethod
    async def write(self, identifier: str, data: Dict[str, Any]) -> bool:
        """Daten schreiben"""
        pass


class Queryable(ABC):
    """ISP: Interface nur für abfragbare Services"""
    
    @abstractmethod
    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Daten abfragen"""
        pass


class Indexable(ABC):
    """ISP: Interface nur für indexierbare Services"""
    
    @abstractmethod
    async def create_index(self, field: str) -> bool:
        """Index erstellen"""
        pass
    
    @abstractmethod
    async def rebuild_indices(self) -> bool:
        """Indizes neu erstellen"""
        pass


class Cacheable(ABC):
    """ISP: Interface nur für Cache-fähige Services"""
    
    @abstractmethod
    async def cache_get(self, key: str) -> Optional[Any]:
        """Wert aus Cache abrufen"""
        pass
    
    @abstractmethod
    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Wert in Cache setzen"""
        pass
    
    @abstractmethod
    async def cache_invalidate(self, pattern: str) -> bool:
        """Cache invalidieren"""
        pass


# =============================================================================
# PROCESSING CONTRACTS (ISP - Processing-specific Interfaces)
# =============================================================================

class Processable(ABC):
    """ISP: Interface nur für verarbeitende Services"""
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Daten verarbeiten"""
        pass


class BatchProcessable(ABC):
    """ISP: Interface nur für Batch-verarbeitende Services"""
    
    @abstractmethod
    async def process_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch-Daten verarbeiten"""
        pass
    
    @abstractmethod
    def get_batch_size(self) -> int:
        """Optimale Batch-Größe abrufen"""
        pass


class Schedulable(ABC):
    """ISP: Interface nur für planbare Services"""
    
    @abstractmethod
    async def schedule_task(self, task_id: str, schedule: str) -> bool:
        """Aufgabe planen"""
        pass
    
    @abstractmethod
    async def cancel_scheduled_task(self, task_id: str) -> bool:
        """Geplante Aufgabe abbrechen"""
        pass


class Transformable(ABC):
    """ISP: Interface nur für transformierende Services"""
    
    @abstractmethod
    async def transform(
        self, 
        data: Dict[str, Any], 
        transformation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Daten transformieren"""
        pass


# =============================================================================
# SECURITY CONTRACTS (ISP - Security-specific Interfaces)
# =============================================================================

class Authenticatable(ABC):
    """ISP: Interface nur für authentifizierbare Services"""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Benutzer authentifizieren"""
        pass


class Authorizable(ABC):
    """ISP: Interface nur für autorisierbare Services"""
    
    @abstractmethod
    async def authorize(self, user: Dict[str, Any], resource: str, action: str) -> bool:
        """Berechtigung prüfen"""
        pass


class Auditable(ABC):
    """ISP: Interface nur für auditierbare Services"""
    
    @abstractmethod
    async def log_audit_event(self, event: Dict[str, Any]) -> bool:
        """Audit-Event protokollieren"""
        pass
    
    @abstractmethod
    async def get_audit_trail(self, resource: str) -> List[Dict[str, Any]]:
        """Audit-Trail abrufen"""
        pass


# =============================================================================
# COMPOSITE SERVICE CONTRACTS (ISP - Interface Composition)
# =============================================================================

class BasicService(Initializable, Startable, Stoppable, Healthable):
    """Basis-Service mit minimalen Lifecycle-Requirements"""
    pass


class ManagedService(BasicService, Configurable, Metricable, Stateful):
    """Verwalteter Service mit Config- und Monitoring-Capabilities"""
    pass


class EventDrivenService(BasicService, EventPublisher, EventSubscriber):
    """Event-getriebener Service"""
    pass


class DataService(BasicService, Readable, Writable, Queryable):
    """Daten-Service mit CRUD-Operations"""
    pass


class ProcessingService(BasicService, Processable, BatchProcessable):
    """Verarbeitungs-Service"""
    pass


class SecureService(BasicService, Authenticatable, Authorizable, Auditable):
    """Sicherheits-bewusster Service"""
    pass


class FullFeaturedService(
    ManagedService, 
    EventDrivenService, 
    Cacheable, 
    Transformable, 
    Reconfigurable
):
    """Vollständiger Service mit allen Features"""
    pass


# =============================================================================
# SERVICE CONTRACT REGISTRY
# =============================================================================

class ServiceContractRegistry:
    """Registry für Service-Contract-Definitionen und -Validierung"""
    
    def __init__(self):
        self._contracts: Dict[str, Dict[str, Any]] = {}
        self._interface_hierarchy: Dict[type, List[type]] = {}
        self._build_interface_hierarchy()
    
    def _build_interface_hierarchy(self):
        """Interface-Hierarchie aufbauen"""
        interfaces = [
            # Lifecycle
            Initializable, Startable, Stoppable, Pausable, Restartable,
            # Monitoring
            Healthable, Metricable, Stateful, Diagnosticable,
            # Configuration
            Configurable, Reconfigurable, EnvironmentAware,
            # Communication
            EventPublisher, EventSubscriber, MessageSender, MessageReceiver, NotificationSender,
            # Data
            Readable, Writable, Queryable, Indexable, Cacheable,
            # Processing
            Processable, BatchProcessable, Schedulable, Transformable,
            # Security
            Authenticatable, Authorizable, Auditable
        ]
        
        for interface in interfaces:
            self._interface_hierarchy[interface] = []
    
    def register_service_contract(
        self, 
        service_name: str, 
        required_interfaces: List[type],
        optional_interfaces: List[type] = None
    ):
        """Service-Contract registrieren"""
        self._contracts[service_name] = {
            'required': required_interfaces or [],
            'optional': optional_interfaces or [],
            'composite': self._find_composite_interfaces(required_interfaces or [])
        }
    
    def _find_composite_interfaces(self, interfaces: List[type]) -> List[type]:
        """Zusammengesetzte Interfaces finden"""
        composites = []
        composite_interfaces = [
            BasicService, ManagedService, EventDrivenService,
            DataService, ProcessingService, SecureService, FullFeaturedService
        ]
        
        for composite in composite_interfaces:
            composite_bases = [base for base in composite.__mro__ if base in interfaces]
            if len(composite_bases) == len([base for base in composite.__mro__ if base != composite and base != object]):
                composites.append(composite)
        
        return composites
    
    def validate_service_contract(self, service_instance: Any, service_name: str) -> Dict[str, Any]:
        """Service-Contract validieren"""
        if service_name not in self._contracts:
            return {'valid': False, 'error': f'Contract not found: {service_name}'}
        
        contract = self._contracts[service_name]
        result = {
            'valid': True,
            'service_name': service_name,
            'required_compliance': {},
            'optional_compliance': {},
            'missing_required': [],
            'available_optional': []
        }
        
        # Required Interfaces prüfen
        for required_interface in contract['required']:
            compliant = isinstance(service_instance, required_interface)
            result['required_compliance'][required_interface.__name__] = compliant
            
            if not compliant:
                result['valid'] = False
                result['missing_required'].append(required_interface.__name__)
        
        # Optional Interfaces prüfen
        for optional_interface in contract.get('optional', []):
            compliant = isinstance(service_instance, optional_interface)
            result['optional_compliance'][optional_interface.__name__] = compliant
            
            if compliant:
                result['available_optional'].append(optional_interface.__name__)
        
        return result
    
    def get_contract_requirements(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Contract-Anforderungen abrufen"""
        return self._contracts.get(service_name)
    
    def list_available_interfaces(self) -> List[str]:
        """Alle verfügbaren Interfaces auflisten"""
        return [interface.__name__ for interface in self._interface_hierarchy.keys()]
    
    def get_interface_dependencies(self, interface: type) -> List[type]:
        """Interface-Abhängigkeiten abrufen"""
        dependencies = []
        if hasattr(interface, '__mro__'):
            for base in interface.__mro__:
                if base != interface and base != object and issubclass(base, ABC):
                    dependencies.append(base)
        return dependencies


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_service_contract_for_role(role: str) -> List[type]:
    """Service-Contract für spezifische Rolle erstellen"""
    role_contracts = {
        'api-service': [Initializable, Startable, Stoppable, Healthable, Configurable],
        'data-service': [Initializable, Startable, Stoppable, Healthable, Readable, Writable, Queryable],
        'event-service': [Initializable, Startable, Stoppable, Healthable, EventPublisher, EventSubscriber],
        'processing-service': [Initializable, Startable, Stoppable, Healthable, Processable, BatchProcessable],
        'monitoring-service': [Initializable, Startable, Stoppable, Healthable, Metricable, Diagnosticable],
        'security-service': [Initializable, Startable, Stoppable, Healthable, Authenticatable, Authorizable, Auditable]
    }
    
    return role_contracts.get(role, [BasicService])


def validate_interface_segregation(service_class: type) -> Dict[str, Any]:
    """Interface Segregation Principle validieren"""
    interfaces = [base for base in service_class.__mro__ if issubclass(base, ABC) and base != ABC]
    
    validation_result = {
        'class': service_class.__name__,
        'interface_count': len(interfaces),
        'interfaces': [interface.__name__ for interface in interfaces],
        'segregation_score': 0,
        'recommendations': []
    }
    
    # ISP-Score berechnen
    # Viele kleine Interfaces = besser als wenige große
    if len(interfaces) > 0:
        avg_methods_per_interface = sum(
            len(getattr(interface, '__abstractmethods__', set()))
            for interface in interfaces
        ) / len(interfaces)
        
        # Score: weniger Methoden pro Interface = besser
        validation_result['segregation_score'] = max(0, 100 - (avg_methods_per_interface * 10))
        validation_result['avg_methods_per_interface'] = avg_methods_per_interface
        
        if avg_methods_per_interface > 5:
            validation_result['recommendations'].append(
                f"Consider splitting interfaces with >5 methods (avg: {avg_methods_per_interface:.1f})"
            )
        
        if len(interfaces) < 2:
            validation_result['recommendations'].append(
                "Consider implementing multiple specific interfaces instead of one large interface"
            )
    
    return validation_result