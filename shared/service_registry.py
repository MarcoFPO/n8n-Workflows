#!/usr/bin/env python3
"""
Service Registry - Zentrale Service-Discovery für das Aktienanalyse-Ökosystem
Clean Architecture: Dynamische Service-Registrierung und -Erkennung

Code-Qualität: HÖCHSTE PRIORITÄT
- Clean Code Architecture
- Service-Discovery Pattern
- Health-Check Integration
- Automatic Service Registration
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path


class ServiceStatus(Enum):
    """Service Status Enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


@dataclass
class ServiceInfo:
    """Service Information Data Structure"""
    name: str
    host: str
    port: int
    health_endpoint: str
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[str] = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    response_time_ms: int = 0
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
    
    @property
    def url(self) -> str:
        """Vollständige Service-URL"""
        return f"http://{self.host}:{self.port}"
    
    @property
    def health_url(self) -> str:
        """Health-Check-URL"""
        return f"{self.url}{self.health_endpoint}"
    
    def is_healthy(self) -> bool:
        """Service ist gesund"""
        return self.status == ServiceStatus.HEALTHY
    
    def is_available(self) -> bool:
        """Service ist verfügbar"""
        return self.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]


class ServiceRegistry:
    """
    Zentrale Service-Registry mit automatischer Discovery
    Clean Architecture: Service-Discovery Pattern Implementation
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.logger = logging.getLogger(__name__)
        
        # Health Check Configuration
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 10   # seconds
        self.max_failures = 3
        self.failure_counts: Dict[str, int] = {}
        
        # Auto-Discovery
        self._discovery_running = False
        self._discovery_task: Optional[asyncio.Task] = None
        
        # Initialize with known services from central config
        self._initialize_known_services()
    
    def _initialize_known_services(self):
        """Initialisiere bekannte Services aus zentraler Konfiguration"""
        try:
            # Import Manager für korrekte Pfade
            from import_manager import setup_imports
            setup_imports()
            
            from config.central_config_v1_0_0_20250821 import config
            
            for service_name, service_config in config.SERVICES.items():
                service_info = ServiceInfo(
                    name=service_name,
                    host=service_config["host"],
                    port=service_config["port"],
                    health_endpoint=service_config["health_endpoint"],
                    description=f"Auto-discovered {service_name} service"
                )
                self.services[service_name] = service_info
                self.failure_counts[service_name] = 0
                
            self.logger.info(f"Initialized service registry with {len(self.services)} known services")
            
        except ImportError:
            self.logger.warning("Could not import central config - using empty registry")
    
    def register_service(self, service_info: ServiceInfo) -> bool:
        """
        Service registrieren
        Returns: True wenn erfolgreich registriert
        """
        try:
            service_name = service_info.name
            
            # Validate service info
            if not all([service_name, service_info.host, service_info.port]):
                self.logger.error(f"Invalid service info for {service_name}")
                return False
            
            # Register service
            self.services[service_name] = service_info
            self.failure_counts[service_name] = 0
            
            self.logger.info(f"Registered service: {service_name} at {service_info.url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service_info.name}: {e}")
            return False
    
    def unregister_service(self, service_name: str) -> bool:
        """Service deregistrieren"""
        if service_name in self.services:
            del self.services[service_name]
            if service_name in self.failure_counts:
                del self.failure_counts[service_name]
            
            self.logger.info(f"Unregistered service: {service_name}")
            return True
        return False
    
    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Service-Info abrufen"""
        return self.services.get(service_name)
    
    def get_healthy_services(self) -> List[ServiceInfo]:
        """Alle gesunden Services"""
        return [service for service in self.services.values() if service.is_healthy()]
    
    def get_available_services(self) -> List[ServiceInfo]:
        """Alle verfügbaren Services (healthy + degraded)"""
        return [service for service in self.services.values() if service.is_available()]
    
    def get_services_by_capability(self, capability: str) -> List[ServiceInfo]:
        """Services mit bestimmter Capability"""
        return [
            service for service in self.services.values() 
            if capability in service.capabilities and service.is_available()
        ]
    
    def list_all_services(self) -> Dict[str, ServiceInfo]:
        """Alle registrierten Services"""
        return self.services.copy()
    
    async def check_service_health(self, service_info: ServiceInfo) -> ServiceStatus:
        """
        Health-Check für einzelnen Service
        Returns: Aktueller ServiceStatus
        """
        start_time = datetime.now()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service_info.health_url) as response:
                    response_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    service_info.response_time_ms = response_time
                    service_info.last_seen = datetime.now()
                    
                    if response.status == 200:
                        # Reset failure count on success
                        self.failure_counts[service_info.name] = 0
                        
                        try:
                            health_data = await response.json()
                            # Update service info from health response
                            if 'version' in health_data:
                                service_info.version = health_data['version']
                            if 'capabilities' in health_data:
                                service_info.capabilities = health_data['capabilities']
                                
                            service_info.status = ServiceStatus.HEALTHY
                            return ServiceStatus.HEALTHY
                            
                        except json.JSONDecodeError:
                            service_info.status = ServiceStatus.DEGRADED
                            return ServiceStatus.DEGRADED
                    else:
                        self._handle_service_failure(service_info)
                        return ServiceStatus.UNHEALTHY
                        
        except asyncio.TimeoutError:
            self._handle_service_failure(service_info)
            return ServiceStatus.UNHEALTHY
        except aiohttp.ClientConnectorError:
            self._handle_service_failure(service_info)
            return ServiceStatus.OFFLINE
        except Exception as e:
            self.logger.error(f"Unexpected error checking {service_info.name}: {e}")
            self._handle_service_failure(service_info)
            return ServiceStatus.UNKNOWN
    
    def _handle_service_failure(self, service_info: ServiceInfo):
        """Handle service failure"""
        self.failure_counts[service_info.name] = self.failure_counts.get(service_info.name, 0) + 1
        
        if self.failure_counts[service_info.name] >= self.max_failures:
            service_info.status = ServiceStatus.OFFLINE
        else:
            service_info.status = ServiceStatus.UNHEALTHY
    
    async def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Health-Check für alle Services"""
        tasks = []
        for service_info in self.services.values():
            task = self.check_service_health(service_info)
            tasks.append((service_info.name, task))
        
        results = {}
        for service_name, task in tasks:
            try:
                status = await task
                results[service_name] = status
            except Exception as e:
                self.logger.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = ServiceStatus.UNKNOWN
        
        return results
    
    async def start_discovery(self):
        """Starte automatische Service-Discovery"""
        if self._discovery_running:
            return
        
        self._discovery_running = True
        self._discovery_task = asyncio.create_task(self._discovery_loop())
        self.logger.info("Started service discovery")
    
    async def stop_discovery(self):
        """Stoppe automatische Service-Discovery"""
        self._discovery_running = False
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped service discovery")
    
    async def _discovery_loop(self):
        """Discovery Loop für kontinuierliche Health-Checks"""
        while self._discovery_running:
            try:
                await self.check_all_services()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Discovery loop error: {e}")
                await asyncio.sleep(5)  # Short wait on error
    
    def get_service_summary(self) -> Dict:
        """Service-Registry Zusammenfassung"""
        healthy = len(self.get_healthy_services())
        available = len(self.get_available_services())
        total = len(self.services)
        
        return {
            "total_services": total,
            "healthy_services": healthy,
            "available_services": available,
            "offline_services": total - available,
            "discovery_running": self._discovery_running,
            "last_updated": datetime.now().isoformat()
        }
    
    def export_registry(self) -> Dict:
        """Export Service Registry als JSON"""
        return {
            "services": {
                name: {
                    **asdict(service),
                    "status": service.status.value,
                    "last_seen": service.last_seen.isoformat() if service.last_seen else None
                }
                for name, service in self.services.items()
            },
            "summary": self.get_service_summary()
        }


# Globale Service Registry Instanz
service_registry = ServiceRegistry()


# Convenience Functions
def get_service(service_name: str) -> Optional[ServiceInfo]:
    """Convenience-Funktion für Service-Lookup"""
    return service_registry.get_service(service_name)

def get_service_url(service_name: str) -> Optional[str]:
    """Convenience-Funktion für Service-URL"""
    service = service_registry.get_service(service_name)
    return service.url if service else None

def get_healthy_services() -> List[ServiceInfo]:
    """Convenience-Funktion für gesunde Services"""
    return service_registry.get_healthy_services()

async def health_check_all() -> Dict[str, ServiceStatus]:
    """Convenience-Funktion für Health-Check"""
    return await service_registry.check_all_services()


if __name__ == "__main__":
    # Debug/Test-Modus
    async def test_registry():
        print("=== Service Registry Debug ===")
        
        # Show initialized services
        services = service_registry.list_all_services()
        print(f"Initialized {len(services)} services:")
        for name, service in services.items():
            print(f"  - {name}: {service.url}")
        
        # Test health checks
        print("\nTesting health checks...")
        results = await service_registry.check_all_services()
        for service_name, status in results.items():
            print(f"  {service_name}: {status.value}")
        
        # Show summary
        summary = service_registry.get_service_summary()
        print(f"\nSummary: {summary}")
    
    asyncio.run(test_registry())