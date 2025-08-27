#!/usr/bin/env python3
"""
Dashboard Entity - Domain Layer
Frontend Service Clean Architecture v1.0.0

DOMAIN LAYER - ENTITIES:
- Dashboard State Entity
- Business Rules für Dashboard
- Core Business Logic

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Nur Dashboard State Management
- No Dependencies: Pure business logic, keine external imports
- Immutable State: Value Objects für State Changes

Autor: Claude Code - Clean Architecture Specialist  
Datum: 26. August 2025
Version: 1.0.0
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class DashboardStatus(Enum):
    """Dashboard Status Enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ServiceHealth(Enum):
    """Service Health Status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class ServiceInfo:
    """Service Information Value Object"""
    name: str
    url: str
    port: str
    status: ServiceHealth
    last_check: datetime
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self.status == ServiceHealth.ACTIVE
    
    def is_critical(self) -> bool:
        """Check if service is in critical state"""
        return self.status == ServiceHealth.INACTIVE


@dataclass(frozen=True) 
class DashboardMetrics:
    """Dashboard Metrics Value Object"""
    total_services: int
    healthy_services: int
    warning_services: int
    critical_services: int
    last_updated: datetime
    overall_health_score: float
    
    @property
    def health_percentage(self) -> float:
        """Calculate health percentage"""
        if self.total_services == 0:
            return 0.0
        return (self.healthy_services / self.total_services) * 100
    
    @property
    def dashboard_status(self) -> DashboardStatus:
        """Determine overall dashboard status"""
        if self.health_percentage >= 80:
            return DashboardStatus.HEALTHY
        elif self.health_percentage >= 60:
            return DashboardStatus.WARNING
        elif self.health_percentage > 0:
            return DashboardStatus.CRITICAL
        else:
            return DashboardStatus.UNKNOWN


class DashboardEntity:
    """
    Dashboard Entity - Core Business Entity
    
    BUSINESS RULES:
    - Manages dashboard state and metrics
    - Coordinates service health monitoring
    - Provides system status aggregation
    
    DESIGN PATTERNS:
    - Entity Pattern: Identity and lifecycle
    - Value Object Pattern: Immutable metrics
    - Domain Service Pattern: Business rules
    """
    
    def __init__(self, dashboard_id: str, version: str):
        self._dashboard_id = dashboard_id
        self._version = version
        self._services: Dict[str, ServiceInfo] = {}
        self._last_update: Optional[datetime] = None
        self._metrics: Optional[DashboardMetrics] = None
    
    @property
    def dashboard_id(self) -> str:
        """Get dashboard ID"""
        return self._dashboard_id
    
    @property
    def version(self) -> str:
        """Get dashboard version"""
        return self._version
    
    @property
    def services(self) -> Dict[str, ServiceInfo]:
        """Get all services"""
        return self._services.copy()
    
    @property
    def metrics(self) -> Optional[DashboardMetrics]:
        """Get current metrics"""
        return self._metrics
    
    def add_service(self, service_info: ServiceInfo) -> None:
        """
        Add service to dashboard
        
        BUSINESS RULE: Service names must be unique
        """
        if service_info.name in self._services:
            raise ValueError(f"Service {service_info.name} already exists")
        
        self._services[service_info.name] = service_info
        self._update_metrics()
    
    def update_service_status(self, service_name: str, status: ServiceHealth, 
                            response_time_ms: Optional[int] = None,
                            error_message: Optional[str] = None) -> None:
        """
        Update service status
        
        BUSINESS RULE: Only existing services can be updated
        """
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not found")
        
        current_service = self._services[service_name]
        
        # Create updated service info
        updated_service = ServiceInfo(
            name=current_service.name,
            url=current_service.url,
            port=current_service.port,
            status=status,
            last_check=datetime.now(),
            response_time_ms=response_time_ms,
            error_message=error_message
        )
        
        self._services[service_name] = updated_service
        self._update_metrics()
    
    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get specific service information"""
        return self._services.get(service_name)
    
    def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services"""
        return [service for service in self._services.values() if service.is_healthy()]
    
    def get_critical_services(self) -> List[ServiceInfo]:
        """Get all critical services"""
        return [service for service in self._services.values() if service.is_critical()]
    
    def _update_metrics(self) -> None:
        """
        Update dashboard metrics
        
        BUSINESS RULE: Metrics calculated from current service states
        """
        if not self._services:
            self._metrics = None
            return
        
        services_by_status = {
            ServiceHealth.ACTIVE: 0,
            ServiceHealth.INACTIVE: 0,
            ServiceHealth.DEGRADED: 0,
            ServiceHealth.MAINTENANCE: 0
        }
        
        for service in self._services.values():
            services_by_status[service.status] += 1
        
        total_services = len(self._services)
        healthy_services = services_by_status[ServiceHealth.ACTIVE]
        warning_services = services_by_status[ServiceHealth.DEGRADED] + services_by_status[ServiceHealth.MAINTENANCE]
        critical_services = services_by_status[ServiceHealth.INACTIVE]
        
        # Calculate overall health score (weighted)
        health_score = (
            (healthy_services * 1.0) +
            (warning_services * 0.5) +
            (critical_services * 0.0)
        ) / total_services if total_services > 0 else 0.0
        
        self._metrics = DashboardMetrics(
            total_services=total_services,
            healthy_services=healthy_services,
            warning_services=warning_services,
            critical_services=critical_services,
            last_updated=datetime.now(),
            overall_health_score=health_score
        )
        
        self._last_update = datetime.now()
    
    def is_healthy(self) -> bool:
        """
        Check if dashboard is healthy
        
        BUSINESS RULE: Dashboard healthy if ≥80% services active
        """
        return self._metrics is not None and self._metrics.dashboard_status == DashboardStatus.HEALTHY
    
    def requires_attention(self) -> bool:
        """
        Check if dashboard requires attention
        
        BUSINESS RULE: Requires attention if any critical services or <60% health
        """
        if self._metrics is None:
            return True
        
        return (self._metrics.dashboard_status in [DashboardStatus.CRITICAL, DashboardStatus.WARNING] or
                self._metrics.critical_services > 0)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get dashboard status summary
        
        Returns formatted dashboard status for UI display
        """
        if self._metrics is None:
            return {
                "status": DashboardStatus.UNKNOWN.value,
                "message": "No metrics available",
                "services": {},
                "last_updated": None
            }
        
        return {
            "status": self._metrics.dashboard_status.value,
            "message": self._get_status_message(),
            "services": {
                "total": self._metrics.total_services,
                "healthy": self._metrics.healthy_services,
                "warning": self._metrics.warning_services,
                "critical": self._metrics.critical_services
            },
            "health_percentage": self._metrics.health_percentage,
            "health_score": self._metrics.overall_health_score,
            "last_updated": self._metrics.last_updated
        }
    
    def _get_status_message(self) -> str:
        """Generate status message based on current state"""
        if self._metrics is None:
            return "Dashboard status unknown"
        
        status = self._metrics.dashboard_status
        
        if status == DashboardStatus.HEALTHY:
            return f"All systems operational ({self._metrics.health_percentage:.1f}% healthy)"
        elif status == DashboardStatus.WARNING:
            return f"Some services degraded ({self._metrics.critical_services} critical, {self._metrics.warning_services} warning)"
        elif status == DashboardStatus.CRITICAL:
            return f"System issues detected ({self._metrics.critical_services} critical services)"
        else:
            return "Dashboard status unknown"