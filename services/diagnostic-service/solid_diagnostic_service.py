#!/usr/bin/env python3
"""
SOLID-konformer Diagnostic Service - Pilot Migration
Issue #62 - SOLID-Prinzipien durchsetzen - Phase 4: Pilot-Migration

Vollständige SOLID-konforme Reimplementierung des Diagnostic Services als Pilot:
- S: Single Responsibility - getrennte Komponenten
- O: Open/Closed - erweiterbar durch Interfaces
- L: Liskov Substitution - konsistente Interface-Implementation  
- I: Interface Segregation - spezifische, kleine Interfaces
- D: Dependency Inversion - Repository Pattern, DI Container

Author: System Modernization Team
Version: 2.0.0 (SOLID-compliant)
Date: 2025-08-29
"""

import asyncio
import logging
import psutil
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# SOLID Foundation
from ...shared.solid_foundations import (
    SOLIDServiceOrchestrator,
    ServiceContainer,
    APIRouter,
    ServiceManager,
    HealthMonitor
)

# Service Contracts (ISP)
from ...shared.service_contracts import (
    Initializable,
    Startable,
    Stoppable,
    Healthable,
    Configurable,
    Metricable,
    Diagnosticable,
    Cacheable,
    EventPublisher,
    create_service_contract_for_role,
    ServiceContractRegistry
)

# Repository Pattern (DIP)
from ...shared.repositories import (
    Repository,
    ConfigRepository,
    CacheRepository,
    InMemoryRepository,
    RepositoryFactory,
    RepositoryRegistry
)

# Exception Framework Integration
from ...shared.exceptions import (
    BaseServiceException,
    ConfigurationException,
    get_error_response
)
from ...shared.exception_handler import (
    ExceptionHandler,
    handle_exceptions
)

# Logger
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class SystemInfo:
    """System-Informationen Datenmodell"""
    hostname: str
    platform: str
    architecture: str
    processor: str
    python_version: str
    boot_time: str
    uptime_seconds: int


@dataclass
class ResourceMetrics:
    """Ressourcen-Metriken Datenmodell"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: int
    memory_used_mb: int
    memory_total_mb: int
    disk_usage_percent: float
    disk_free_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int


@dataclass
class DiagnosticResult:
    """Diagnose-Ergebnis Datenmodell"""
    timestamp: str
    service_name: str
    system_info: SystemInfo
    resource_metrics: ResourceMetrics
    service_status: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    recommendations: List[str]


# =============================================================================
# SRP: SYSTEM INFORMATION COLLECTOR
# =============================================================================

class SystemInfoCollector:
    """SRP: Nur verantwortlich für System-Information-Sammlung"""
    
    def __init__(self):
        self.logger = logging.getLogger("diagnostic.system-info")
    
    @handle_exceptions
    async def collect_system_info(self) -> SystemInfo:
        """System-Informationen sammeln"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return SystemInfo(
                hostname=platform.node(),
                platform=platform.platform(),
                architecture=platform.architecture()[0],
                processor=platform.processor() or "Unknown",
                python_version=platform.python_version(),
                boot_time=boot_time.isoformat(),
                uptime_seconds=int(uptime.total_seconds())
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect system info: {e}")
            # Fallback mit minimalen Infos
            return SystemInfo(
                hostname="unknown",
                platform="unknown",
                architecture="unknown",
                processor="unknown",
                python_version="unknown",
                boot_time="unknown",
                uptime_seconds=0
            )


# =============================================================================
# SRP: RESOURCE METRICS COLLECTOR
# =============================================================================

class ResourceMetricsCollector:
    """SRP: Nur verantwortlich für Ressourcen-Metriken-Sammlung"""
    
    def __init__(self):
        self.logger = logging.getLogger("diagnostic.resource-metrics")
    
    @handle_exceptions
    async def collect_resource_metrics(self) -> ResourceMetrics:
        """Ressourcen-Metriken sammeln"""
        try:
            # CPU Metriken
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory Metriken
            memory = psutil.virtual_memory()
            memory_used_mb = int(memory.used / (1024 * 1024))
            memory_available_mb = int(memory.available / (1024 * 1024))
            memory_total_mb = int(memory.total / (1024 * 1024))
            
            # Disk Metriken
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 ** 3)
            disk_free_gb = disk.free / (1024 ** 3)
            disk_usage_percent = (disk.used / disk.total) * 100
            
            # Network Metriken
            network = psutil.net_io_counters()
            
            return ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_mb=memory_available_mb,
                memory_used_mb=memory_used_mb,
                memory_total_mb=memory_total_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=round(disk_free_gb, 2),
                disk_total_gb=round(disk_total_gb, 2),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect resource metrics: {e}")
            # Fallback mit Null-Werten
            return ResourceMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0,
                memory_used_mb=0,
                memory_total_mb=0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                disk_total_gb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0
            )


# =============================================================================
# SRP: DIAGNOSTIC ANALYZER
# =============================================================================

class DiagnosticAnalyzer:
    """SRP: Nur verantwortlich für Diagnose-Analyse und Alert-Generierung"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger("diagnostic.analyzer")
        
        # Schwellwerte aus Config (Repository Pattern)
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_warning': 80.0,
            'disk_critical': 90.0
        }
    
    async def analyze_system_health(
        self, 
        system_info: SystemInfo, 
        metrics: ResourceMetrics
    ) -> Dict[str, Any]:
        """System-Health analysieren und Alerts generieren"""
        
        alerts = []
        recommendations = []
        health_score = 100
        
        # CPU-Analyse
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append({
                'level': 'critical',
                'type': 'cpu',
                'message': f'Critical CPU usage: {metrics.cpu_percent:.1f}%',
                'value': metrics.cpu_percent,
                'threshold': self.thresholds['cpu_critical']
            })
            recommendations.append('Consider scaling up CPU resources or optimizing CPU-intensive processes')
            health_score -= 30
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append({
                'level': 'warning',
                'type': 'cpu',
                'message': f'High CPU usage: {metrics.cpu_percent:.1f}%',
                'value': metrics.cpu_percent,
                'threshold': self.thresholds['cpu_warning']
            })
            recommendations.append('Monitor CPU usage and consider optimization')
            health_score -= 15
        
        # Memory-Analyse
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append({
                'level': 'critical',
                'type': 'memory',
                'message': f'Critical memory usage: {metrics.memory_percent:.1f}%',
                'value': metrics.memory_percent,
                'threshold': self.thresholds['memory_critical']
            })
            recommendations.append('Immediate memory cleanup or scaling required')
            health_score -= 30
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append({
                'level': 'warning',
                'type': 'memory',
                'message': f'High memory usage: {metrics.memory_percent:.1f}%',
                'value': metrics.memory_percent,
                'threshold': self.thresholds['memory_warning']
            })
            recommendations.append('Monitor memory usage and consider cleanup')
            health_score -= 15
        
        # Disk-Analyse
        if metrics.disk_usage_percent >= self.thresholds['disk_critical']:
            alerts.append({
                'level': 'critical',
                'type': 'disk',
                'message': f'Critical disk usage: {metrics.disk_usage_percent:.1f}%',
                'value': metrics.disk_usage_percent,
                'threshold': self.thresholds['disk_critical']
            })
            recommendations.append('Immediate disk cleanup required')
            health_score -= 25
        elif metrics.disk_usage_percent >= self.thresholds['disk_warning']:
            alerts.append({
                'level': 'warning',
                'type': 'disk',
                'message': f'High disk usage: {metrics.disk_usage_percent:.1f}%',
                'value': metrics.disk_usage_percent,
                'threshold': self.thresholds['disk_warning']
            })
            recommendations.append('Consider disk cleanup or expansion')
            health_score -= 10
        
        # Positive Empfehlungen
        if not alerts:
            recommendations.append('System performance is within normal parameters')
        
        if system_info.uptime_seconds < 3600:  # Weniger als 1 Stunde
            recommendations.append('System recently restarted - monitor for stability')
        
        return {
            'alerts': alerts,
            'recommendations': recommendations,
            'health_score': max(0, health_score),
            'status': 'critical' if health_score < 50 else 'warning' if health_score < 80 else 'healthy'
        }


# =============================================================================
# DIP: DIAGNOSTIC SERVICE (Business Logic)
# =============================================================================

class SOLIDDiagnosticService(
    Initializable, 
    Startable, 
    Stoppable, 
    Healthable,
    Configurable, 
    Metricable, 
    Diagnosticable,
    Cacheable,
    EventPublisher
):
    """
    SOLID-konformer Diagnostic Service
    
    Implementiert alle relevanten Service-Contracts:
    - Lifecycle: Initializable, Startable, Stoppable
    - Monitoring: Healthable, Metricable, Diagnosticable  
    - Configuration: Configurable
    - Performance: Cacheable
    - Communication: EventPublisher
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger("diagnostic.service")
        
        # Service State
        self._initialized = False
        self._started = False
        self._stopped = False
        self._config: Dict[str, Any] = {}
        
        # Components (SRP)
        self.system_collector = SystemInfoCollector()
        self.metrics_collector = ResourceMetricsCollector()
        self.analyzer = DiagnosticAnalyzer(container)
        
        # Timestamps
        self.initialization_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        # Caching
        self._cache_ttl = 30  # 30 Sekunden
        self._last_diagnostic: Optional[DiagnosticResult] = None
        self._last_diagnostic_time: Optional[datetime] = None
    
    # ISP: Initializable Interface
    async def initialize(self) -> bool:
        """Service initialisieren"""
        try:
            self.logger.info("Initializing SOLID Diagnostic Service...")
            
            # Repositories auflösen (DIP)
            config_repo = self.container.resolve_optional(ConfigRepository)
            if config_repo:
                self._config = await config_repo.get_all_configs() or {}
                self.logger.debug(f"Loaded {len(self._config)} configuration items")
            
            # Cache Repository
            cache_repo = self.container.resolve_optional(CacheRepository)
            if cache_repo:
                self.logger.debug("Cache repository available")
            
            self._initialized = True
            self.initialization_time = datetime.utcnow()
            
            self.logger.info("SOLID Diagnostic Service initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize service: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Initialisierungs-Status prüfen"""
        return self._initialized
    
    # ISP: Startable Interface
    async def start(self) -> bool:
        """Service starten"""
        try:
            if not self._initialized:
                if not await self.initialize():
                    return False
            
            self.logger.info("Starting SOLID Diagnostic Service...")
            
            self._started = True
            self._stopped = False
            self.start_time = datetime.utcnow()
            
            # Start Event publizieren
            await self.publish_event("service.started", {
                'service': 'diagnostic-service-solid',
                'version': '2.0.0',
                'timestamp': self.start_time.isoformat()
            })
            
            self.logger.info("SOLID Diagnostic Service started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False
    
    def is_started(self) -> bool:
        """Start-Status prüfen"""
        return self._started
    
    # ISP: Stoppable Interface
    async def stop(self) -> bool:
        """Service stoppen"""
        try:
            self.logger.info("Stopping SOLID Diagnostic Service...")
            
            # Stop Event publizieren
            if self._started:
                await self.publish_event("service.stopped", {
                    'service': 'diagnostic-service-solid',
                    'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            self._started = False
            self._stopped = True
            
            self.logger.info("SOLID Diagnostic Service stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False
    
    def is_stopped(self) -> bool:
        """Stop-Status prüfen"""
        return self._stopped
    
    # ISP: Healthable Interface
    async def health_check(self) -> Dict[str, Any]:
        """Health-Status prüfen"""
        health_status = {
            'service': 'diagnostic-service-solid',
            'version': '2.0.0',
            'status': 'healthy' if (self._initialized and self._started and not self._stopped) else 'unhealthy',
            'initialized': self._initialized,
            'started': self._started,
            'stopped': self._stopped,
            'initialization_time': self.initialization_time.isoformat() if self.initialization_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
            'components': {
                'system_collector': 'available',
                'metrics_collector': 'available', 
                'analyzer': 'available'
            },
            'repositories': {}
        }
        
        # Repository-Status prüfen
        config_repo = self.container.resolve_optional(ConfigRepository)
        cache_repo = self.container.resolve_optional(CacheRepository)
        
        health_status['repositories']['config'] = 'available' if config_repo else 'not_available'
        health_status['repositories']['cache'] = 'available' if cache_repo else 'not_available'
        
        return health_status
    
    # ISP: Configurable Interface
    def configure(self, config: Dict[str, Any]) -> bool:
        """Service konfigurieren"""
        try:
            self._config.update(config)
            
            # Analyzer-Thresholds aktualisieren
            if 'thresholds' in config:
                self.analyzer.thresholds.update(config['thresholds'])
            
            # Cache TTL aktualisieren
            if 'cache_ttl' in config:
                self._cache_ttl = config['cache_ttl']
            
            self.logger.debug(f"Service configured with {len(config)} items")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure service: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Aktuelle Konfiguration abrufen"""
        return self._config.copy()
    
    # ISP: Metricable Interface
    async def get_metrics(self) -> Dict[str, Any]:
        """Service-Metriken abrufen"""
        metrics = {
            'service_metrics': {
                'initialized': self._initialized,
                'started': self._started,
                'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
                'cache_ttl': self._cache_ttl,
                'last_diagnostic_age_seconds': (
                    (datetime.utcnow() - self._last_diagnostic_time).total_seconds() 
                    if self._last_diagnostic_time else None
                )
            }
        }
        
        # System-Metriken hinzufügen
        try:
            resource_metrics = await self.metrics_collector.collect_resource_metrics()
            metrics['system_metrics'] = asdict(resource_metrics)
        except Exception as e:
            self.logger.warning(f"Failed to collect system metrics: {e}")
            metrics['system_metrics'] = {'error': str(e)}
        
        return metrics
    
    # ISP: Diagnosticable Interface
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Vollständige Diagnose ausführen"""
        try:
            # Cache prüfen
            if (self._last_diagnostic_time and 
                (datetime.utcnow() - self._last_diagnostic_time).total_seconds() < self._cache_ttl):
                
                self.logger.debug("Returning cached diagnostic result")
                return asdict(self._last_diagnostic)
            
            self.logger.info("Running comprehensive system diagnostics...")
            
            # System-Info sammeln
            system_info = await self.system_collector.collect_system_info()
            
            # Ressourcen-Metriken sammeln
            resource_metrics = await self.metrics_collector.collect_resource_metrics()
            
            # Service-Status
            service_status = await self.health_check()
            
            # Analyse durchführen
            analysis = await self.analyzer.analyze_system_health(system_info, resource_metrics)
            
            # Diagnostic Result zusammenstellen
            diagnostic_result = DiagnosticResult(
                timestamp=datetime.utcnow().isoformat(),
                service_name='diagnostic-service-solid',
                system_info=system_info,
                resource_metrics=resource_metrics,
                service_status=service_status,
                alerts=analysis['alerts'],
                recommendations=analysis['recommendations']
            )
            
            # Cache aktualisieren
            self._last_diagnostic = diagnostic_result
            self._last_diagnostic_time = datetime.utcnow()
            
            # Cache Repository speichern (falls verfügbar)
            cache_repo = self.container.resolve_optional(CacheRepository)
            if cache_repo:
                await cache_repo.set(
                    'diagnostic_result', 
                    asdict(diagnostic_result),
                    ttl_seconds=self._cache_ttl
                )
            
            # Diagnostic Event publizieren
            await self.publish_event("diagnostic.completed", {
                'health_score': analysis.get('health_score', 0),
                'alert_count': len(analysis['alerts']),
                'status': analysis.get('status', 'unknown'),
                'timestamp': diagnostic_result.timestamp
            })
            
            self.logger.info(f"Diagnostics completed - Health Score: {analysis.get('health_score', 0)}")
            return asdict(diagnostic_result)
            
        except Exception as e:
            self.logger.error(f"Failed to run diagnostics: {e}")
            raise BaseServiceException(
                "Diagnostic execution failed",
                original_exception=e,
                context={'service': 'diagnostic-service-solid'}
            )
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Diagnose-Informationen abrufen"""
        return {
            'last_diagnostic_time': self._last_diagnostic_time.isoformat() if self._last_diagnostic_time else None,
            'cache_ttl_seconds': self._cache_ttl,
            'thresholds': self.analyzer.thresholds.copy(),
            'components': ['system_collector', 'metrics_collector', 'analyzer']
        }
    
    # ISP: Cacheable Interface
    async def cache_get(self, key: str) -> Optional[Any]:
        """Wert aus Cache abrufen"""
        cache_repo = self.container.resolve_optional(CacheRepository)
        if cache_repo:
            return await cache_repo.get(key)
        return None
    
    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Wert in Cache setzen"""
        cache_repo = self.container.resolve_optional(CacheRepository)
        if cache_repo:
            return await cache_repo.set(key, value, ttl or self._cache_ttl)
        return False
    
    async def cache_invalidate(self, pattern: str) -> bool:
        """Cache invalidieren"""
        cache_repo = self.container.resolve_optional(CacheRepository)
        if cache_repo:
            # Vereinfachte Implementation - würde Pattern-Matching benötigen
            if pattern == 'diagnostic_result':
                return await cache_repo.delete('diagnostic_result')
        return False
    
    # ISP: EventPublisher Interface
    async def publish_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Event publizieren"""
        try:
            # Mock Event-Publishing - würde echte Event-Bus-Integration benötigen
            event_id = f"event_{datetime.utcnow().timestamp()}"
            self.logger.debug(f"Event published: {event_type} ({event_id})")
            return event_id
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {e}")
            raise BaseServiceException(f"Event publishing failed: {event_type}", original_exception=e)


# =============================================================================
# API CONTROLLER (SRP)
# =============================================================================

class DiagnosticAPIController:
    """SRP: Nur verantwortlich für API-Endpoint-Definition"""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.logger = logging.getLogger("diagnostic.api-controller")
    
    def register_routes(self) -> Dict[str, Any]:
        """API-Routes definieren"""
        return {
            'GET:/': self.root_endpoint,
            'GET:/health': self.health_endpoint,
            'GET:/diagnostics': self.run_diagnostics_endpoint,
            'GET:/metrics': self.metrics_endpoint,
            'GET:/system-info': self.system_info_endpoint,
            'POST:/config': self.update_config_endpoint,
            'GET:/config': self.get_config_endpoint
        }
    
    async def root_endpoint(self) -> Dict[str, Any]:
        """Root endpoint"""
        return {
            'service': 'diagnostic-service-solid',
            'version': '2.0.0',
            'description': 'SOLID-compliant Diagnostic Service',
            'architecture': 'SOLID principles implementation',
            'endpoints': [
                '/health', '/diagnostics', '/metrics', 
                '/system-info', '/config'
            ]
        }
    
    async def health_endpoint(self) -> Dict[str, Any]:
        """Health endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        return await service.health_check()
    
    @handle_exceptions
    async def run_diagnostics_endpoint(self) -> Dict[str, Any]:
        """Diagnostics endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        return await service.run_diagnostics()
    
    @handle_exceptions
    async def metrics_endpoint(self) -> Dict[str, Any]:
        """Metrics endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        return await service.get_metrics()
    
    @handle_exceptions
    async def system_info_endpoint(self) -> Dict[str, Any]:
        """System info endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        # Direkt vom Collector abrufen
        collector = SystemInfoCollector()
        system_info = await collector.collect_system_info()
        return asdict(system_info)
    
    @handle_exceptions
    async def update_config_endpoint(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Config update endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        success = service.configure(config)
        return {'success': success, 'message': 'Configuration updated' if success else 'Configuration update failed'}
    
    @handle_exceptions
    async def get_config_endpoint(self) -> Dict[str, Any]:
        """Config get endpoint"""
        service = self.container.resolve(SOLIDDiagnosticService)
        return service.get_config()


# =============================================================================
# SOLID DIAGNOSTIC ORCHESTRATOR
# =============================================================================

class SOLIDDiagnosticOrchestrator:
    """
    SOLID-konformer Diagnostic Service Orchestrator
    
    Demonstriert vollständige SOLID-Compliance:
    - S: Getrennte Verantwortlichkeiten (Service, API, Collectors)
    - O: Erweiterbar durch Container-Registration
    - L: Konsistente Interface-Implementation
    - I: Spezifische Service-Contracts
    - D: Dependency Injection über Container
    """
    
    def __init__(self):
        self.logger = logging.getLogger("diagnostic.solid-orchestrator")
        
        # SOLID Foundation
        self.solid_orchestrator = SOLIDServiceOrchestrator("diagnostic-service-solid")
        self.container = self.solid_orchestrator.get_container()
        
        # Service Contract Registry
        self.contract_registry = ServiceContractRegistry()
        
        # Services registrieren
        self._register_services()
        self._register_repositories()
        self._register_contracts()
    
    def _register_services(self):
        """Services im Container registrieren"""
        
        # Exception Handler
        exception_handler = ExceptionHandler()
        self.container.register_singleton(ExceptionHandler, exception_handler)
        
        # Haupt-Service
        diagnostic_service = SOLIDDiagnosticService(self.container)
        self.container.register_singleton(SOLIDDiagnosticService, diagnostic_service)
        
        # API Controller
        api_controller = DiagnosticAPIController(self.container)
        self.container.register_singleton(DiagnosticAPIController, api_controller)
        
        # Service Manager registrieren
        service_manager = self.solid_orchestrator.get_service_manager()
        service_manager.register_service("diagnostic", diagnostic_service, priority=1)
        
        # Health Checks registrieren
        health_monitor = self.solid_orchestrator.get_health_monitor()
        health_monitor.register_health_check("diagnostic", diagnostic_service.health_check)
        
        self.logger.info("All services registered in container")
    
    def _register_repositories(self):
        """Repository-Pattern Setup (DIP)"""
        
        # In-Memory Repositories für Pilot (Produktion würde Redis verwenden)
        config_repo = InMemoryRepository()
        cache_repo = InMemoryRepository()
        
        # Default-Konfigurationen setzen
        asyncio.create_task(self._setup_default_configs(config_repo))
        
        # Im Container registrieren
        self.container.register_singleton(ConfigRepository, config_repo)
        self.container.register_singleton(CacheRepository, cache_repo)
        
        self.logger.info("Repositories registered (in-memory for pilot)")
    
    async def _setup_default_configs(self, config_repo):
        """Default-Konfigurationen setzen"""
        default_configs = {
            'cache_ttl': 30,
            'thresholds': {
                'cpu_warning': 70.0,
                'cpu_critical': 85.0,
                'memory_warning': 80.0,
                'memory_critical': 90.0,
                'disk_warning': 80.0,
                'disk_critical': 90.0
            }
        }
        
        for key, value in default_configs.items():
            await config_repo.save(key, value)
    
    def _register_contracts(self):
        """Service-Contracts registrieren (ISP)"""
        
        # Diagnostic Service Contract
        required_interfaces = [
            Initializable, Startable, Stoppable, Healthable,
            Configurable, Metricable, Diagnosticable
        ]
        optional_interfaces = [
            Cacheable, EventPublisher
        ]
        
        self.contract_registry.register_service_contract(
            'diagnostic-service-solid',
            required_interfaces,
            optional_interfaces
        )
        
        self.container.register_singleton(ServiceContractRegistry, self.contract_registry)
        self.logger.info("Service contracts registered")
    
    async def initialize(self) -> bool:
        """Orchestrator initialisieren"""
        try:
            self.logger.info("Initializing SOLID Diagnostic Orchestrator...")
            
            # SOLID Foundation initialisieren
            if not await self.solid_orchestrator.initialize():
                return False
            
            # Contract-Compliance validieren
            diagnostic_service = self.container.resolve(SOLIDDiagnosticService)
            compliance = self.contract_registry.validate_service_contract(
                diagnostic_service, 
                'diagnostic-service-solid'
            )
            
            if not compliance['valid']:
                self.logger.error(f"Service contract validation failed: {compliance}")
                return False
            
            self.logger.info(f"Service contract validation passed: {compliance['service_name']}")
            
            self.logger.info("SOLID Diagnostic Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize orchestrator: {e}")
            return False
    
    async def start(self) -> bool:
        """Orchestrator starten"""
        if not await self.initialize():
            return False
        
        return await self.solid_orchestrator.start()
    
    async def stop(self) -> bool:
        """Orchestrator stoppen"""
        return await self.solid_orchestrator.stop()
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive Health Check"""
        base_health = await self.solid_orchestrator.health_check()
        
        # Service-spezifische Health-Infos hinzufügen
        diagnostic_service = self.container.resolve_optional(SOLIDDiagnosticService)
        if diagnostic_service:
            service_health = await diagnostic_service.health_check()
            base_health['diagnostic_service'] = service_health
        
        # Contract-Compliance hinzufügen
        if diagnostic_service:
            compliance = self.contract_registry.validate_service_contract(
                diagnostic_service,
                'diagnostic-service-solid'
            )
            base_health['contract_compliance'] = compliance
        
        return base_health
    
    def get_fastapi_app(self) -> FastAPI:
        """FastAPI App für Integration erstellen"""
        app = FastAPI(
            title="SOLID Diagnostic Service",
            description="SOLID-compliant System Diagnostic Service",
            version="2.0.0"
        )
        
        # CORS Middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Exception Handler
        @app.exception_handler(BaseServiceException)
        async def service_exception_handler(request: Request, exc: BaseServiceException):
            return JSONResponse(
                status_code=exc.status_code,
                content=get_error_response(exc)
            )
        
        # Routes registrieren
        api_controller = self.container.resolve(DiagnosticAPIController)
        routes = api_controller.register_routes()
        
        for route_key, handler in routes.items():
            method, path = route_key.split(':', 1)
            
            if method == 'GET':
                app.get(path)(handler)
            elif method == 'POST':
                app.post(path)(handler)
        
        return app


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def create_solid_diagnostic_service() -> SOLIDDiagnosticOrchestrator:
    """Factory für SOLID Diagnostic Service"""
    return SOLIDDiagnosticOrchestrator()


async def main():
    """Main entry point"""
    orchestrator = create_solid_diagnostic_service()
    
    # Starten
    if not await orchestrator.start():
        logger.error("Failed to start SOLID Diagnostic Service")
        return
    
    # FastAPI App
    app = orchestrator.get_fastapi_app()
    
    # Uvicorn Server
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8015,  # Neuer Port für SOLID Version
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    logger.info("SOLID Diagnostic Service starting on port 8015...")
    
    try:
        await server.serve()
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())