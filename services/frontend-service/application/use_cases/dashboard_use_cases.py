#!/usr/bin/env python3
"""
Dashboard Use Cases - Application Layer
Frontend Service Clean Architecture v1.0.0

APPLICATION LAYER - USE CASES:
- Dashboard Business Logic Orchestration
- Service Coordination
- External System Integration

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Each use case one business operation
- Dependency Inversion: Depends on interfaces, not implementations
- Open/Closed: Extensible without modification

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..interfaces.http_client_interface import IHTTPClient, HTTPClientError
from ..interfaces.template_service_interface import ITemplateService, TemplateTheme
from ...domain.entities.dashboard_entity import DashboardEntity, ServiceInfo, ServiceHealth
from ...domain.value_objects.timeframe_vo import TimeframeValueObject
from ...domain.services.dashboard_domain_service import DashboardOrchestrationService, DashboardHealthAnalyzer


logger = logging.getLogger(__name__)


class GetDashboardUseCase:
    """
    Get Dashboard Use Case
    
    BUSINESS OPERATION: Retrieve and prepare dashboard data
    
    RESPONSIBILITIES:
    - Coordinate dashboard state preparation
    - Orchestrate service health checks
    - Prepare dashboard UI data
    """
    
    def __init__(self, 
                 http_client: IHTTPClient,
                 template_service: ITemplateService,
                 orchestration_service: DashboardOrchestrationService):
        self._http_client = http_client
        self._template_service = template_service
        self._orchestration_service = orchestration_service
    
    async def execute(self, 
                     dashboard_entity: DashboardEntity,
                     timeframe_code: str = "1M",
                     theme: TemplateTheme = TemplateTheme.DEFAULT) -> str:
        """
        Execute dashboard retrieval
        
        Args:
            dashboard_entity: Dashboard entity instance
            timeframe_code: Selected timeframe
            theme: UI theme
            
        Returns:
            Complete dashboard HTML page
            
        Raises:
            DashboardError: On dashboard preparation errors
        """
        try:
            logger.info(f"Executing GetDashboard use case for timeframe {timeframe_code}")
            
            # Create timeframe value object
            timeframe = TimeframeValueObject(timeframe_code)
            
            # Prepare dashboard state
            dashboard_state = self._orchestration_service.prepare_dashboard_state(
                dashboard_entity, timeframe
            )
            
            # Render dashboard template
            dashboard_html = await self._template_service.render_dashboard_template(
                dashboard_state, theme
            )
            
            logger.info("Dashboard use case executed successfully")
            return dashboard_html
            
        except Exception as e:
            logger.error(f"Dashboard use case failed: {str(e)}")
            raise DashboardError(f"Failed to get dashboard: {str(e)}") from e


class UpdateServiceStatusUseCase:
    """
    Update Service Status Use Case
    
    BUSINESS OPERATION: Update individual service health status
    
    RESPONSIBILITIES:
    - Validate service status updates
    - Update dashboard entity
    - Apply business rules for status changes
    """
    
    def __init__(self, 
                 http_client: IHTTPClient,
                 orchestration_service: DashboardOrchestrationService):
        self._http_client = http_client
        self._orchestration_service = orchestration_service
    
    async def execute(self,
                     dashboard_entity: DashboardEntity,
                     service_name: str,
                     new_status: ServiceHealth,
                     response_time_ms: Optional[int] = None,
                     error_message: Optional[str] = None) -> bool:
        """
        Execute service status update
        
        Args:
            dashboard_entity: Dashboard entity to update
            service_name: Name of service to update
            new_status: New service status
            response_time_ms: Service response time (optional)
            error_message: Error message if applicable (optional)
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ServiceUpdateError: On validation or update errors
        """
        try:
            logger.info(f"Updating service {service_name} status to {new_status.value}")
            
            # Validate update request
            updates = [{
                "service_name": service_name,
                "status": new_status.value
            }]
            
            validation_errors = self._orchestration_service.validate_dashboard_update(
                dashboard_entity, updates
            )
            
            if validation_errors:
                raise ServiceUpdateError(f"Validation failed: {', '.join(validation_errors)}")
            
            # Update service status
            dashboard_entity.update_service_status(
                service_name, new_status, response_time_ms, error_message
            )
            
            logger.info(f"Service {service_name} status updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Service status update failed: {str(e)}")
            raise ServiceUpdateError(f"Failed to update service status: {str(e)}") from e


class PerformHealthCheckUseCase:
    """
    Perform Health Check Use Case
    
    BUSINESS OPERATION: Execute health checks for all services
    
    RESPONSIBILITIES:
    - Check all service endpoints
    - Update service statuses based on health checks
    - Calculate response times
    """
    
    def __init__(self, 
                 http_client: IHTTPClient,
                 health_analyzer: DashboardHealthAnalyzer):
        self._http_client = http_client
        self._health_analyzer = health_analyzer
    
    async def execute(self, 
                     dashboard_entity: DashboardEntity,
                     timeout_seconds: int = 10) -> Dict[str, Any]:
        """
        Execute health checks for all services
        
        Args:
            dashboard_entity: Dashboard entity with services
            timeout_seconds: Health check timeout
            
        Returns:
            Health check results summary
            
        Raises:
            HealthCheckError: On health check execution errors
        """
        try:
            logger.info("Executing health checks for all services")
            
            services = dashboard_entity.services
            health_check_results = {}
            
            # Create health check tasks for parallel execution
            health_check_tasks = []
            service_names = []
            
            for service_name, service_info in services.items():
                health_url = f"{service_info.url}/health"
                task = self._check_service_health(health_url, timeout_seconds)
                health_check_tasks.append(task)
                service_names.append(service_name)
            
            # Execute health checks in parallel
            check_results = await asyncio.gather(*health_check_tasks, return_exceptions=True)
            
            # Process results and update dashboard
            for service_name, result in zip(service_names, check_results):
                if isinstance(result, Exception):
                    # Health check failed
                    health_check_results[service_name] = {
                        "healthy": False,
                        "response_time_ms": None,
                        "error": str(result)
                    }
                    
                    # Update service status
                    dashboard_entity.update_service_status(
                        service_name, 
                        ServiceHealth.INACTIVE,
                        error_message=str(result)
                    )
                else:
                    # Health check successful
                    healthy, response_time_ms = result
                    health_check_results[service_name] = {
                        "healthy": healthy,
                        "response_time_ms": response_time_ms,
                        "error": None
                    }
                    
                    # Determine service status based on response time
                    if healthy:
                        if response_time_ms and response_time_ms > 5000:
                            status = ServiceHealth.DEGRADED
                        else:
                            status = ServiceHealth.ACTIVE
                    else:
                        status = ServiceHealth.INACTIVE
                    
                    dashboard_entity.update_service_status(
                        service_name,
                        status,
                        response_time_ms
                    )
            
            # Calculate overall health summary
            services_list = list(dashboard_entity.services.values())
            overall_health_score = self._health_analyzer.calculate_system_health_score(services_list)
            critical_issues = self._health_analyzer.identify_critical_issues(services_list)
            
            summary = {
                "timestamp": datetime.now(),
                "total_services": len(services),
                "healthy_services": sum(1 for r in health_check_results.values() if r["healthy"]),
                "overall_health_score": overall_health_score,
                "critical_issues_count": len(critical_issues),
                "service_results": health_check_results
            }
            
            logger.info(f"Health checks completed: {summary['healthy_services']}/{summary['total_services']} healthy")
            return summary
            
        except Exception as e:
            logger.error(f"Health check execution failed: {str(e)}")
            raise HealthCheckError(f"Failed to perform health checks: {str(e)}") from e
    
    async def _check_service_health(self, health_url: str, timeout_seconds: int) -> tuple[bool, Optional[int]]:
        """
        Check individual service health
        
        Returns:
            Tuple of (is_healthy, response_time_ms)
        """
        start_time = datetime.now()
        
        try:
            is_healthy = await self._http_client.health_check(health_url, timeout_seconds)
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return is_healthy, response_time_ms
            
        except Exception as e:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.warning(f"Health check failed for {health_url}: {str(e)}")
            return False, response_time_ms


class GetSystemStatusUseCase:
    """
    Get System Status Use Case
    
    BUSINESS OPERATION: Retrieve comprehensive system status
    
    RESPONSIBILITIES:
    - Gather system metrics
    - Analyze system health trends  
    - Prepare system status UI
    """
    
    def __init__(self,
                 template_service: ITemplateService,
                 health_analyzer: DashboardHealthAnalyzer):
        self._template_service = template_service
        self._health_analyzer = health_analyzer
    
    async def execute(self, 
                     dashboard_entity: DashboardEntity,
                     include_detailed_metrics: bool = True) -> str:
        """
        Execute system status retrieval
        
        Args:
            dashboard_entity: Dashboard entity with current state
            include_detailed_metrics: Whether to include detailed metrics
            
        Returns:
            System status HTML page
            
        Raises:
            SystemStatusError: On system status preparation errors
        """
        try:
            logger.info("Executing GetSystemStatus use case")
            
            # Get current dashboard metrics
            dashboard_summary = dashboard_entity.get_status_summary()
            
            # Analyze system health
            services_list = list(dashboard_entity.services.values())
            health_score = self._health_analyzer.calculate_system_health_score(services_list)
            critical_issues = self._health_analyzer.identify_critical_issues(services_list)
            
            # Prepare system status data
            system_status_data = {
                "dashboard_info": {
                    "id": dashboard_entity.dashboard_id,
                    "version": dashboard_entity.version,
                    "summary": dashboard_summary
                },
                "health_analysis": {
                    "overall_score": health_score,
                    "critical_issues": critical_issues,
                    "services": services_list
                },
                "detailed_metrics": None
            }
            
            if include_detailed_metrics:
                system_status_data["detailed_metrics"] = self._prepare_detailed_metrics(services_list)
            
            # Render system status template
            status_html = await self._template_service.render_base_template(
                title="System Status",
                content=await self._generate_system_status_content(system_status_data)
            )
            
            logger.info("System status use case executed successfully")
            return status_html
            
        except Exception as e:
            logger.error(f"System status use case failed: {str(e)}")
            raise SystemStatusError(f"Failed to get system status: {str(e)}") from e
    
    def _prepare_detailed_metrics(self, services: List[ServiceInfo]) -> Dict[str, Any]:
        """Prepare detailed system metrics"""
        return {
            "response_time_metrics": {
                "avg_response_time": self._calculate_avg_response_time(services),
                "max_response_time": max(
                    (s.response_time_ms for s in services if s.response_time_ms), default=0
                ),
                "min_response_time": min(
                    (s.response_time_ms for s in services if s.response_time_ms), default=0
                )
            },
            "availability_metrics": {
                "uptime_percentage": (
                    len([s for s in services if s.status == ServiceHealth.ACTIVE]) / len(services) * 100
                    if services else 0
                ),
                "service_count_by_status": {
                    status.value: len([s for s in services if s.status == status])
                    for status in ServiceHealth
                }
            }
        }
    
    def _calculate_avg_response_time(self, services: List[ServiceInfo]) -> float:
        """Calculate average response time"""
        response_times = [s.response_time_ms for s in services if s.response_time_ms]
        return sum(response_times) / len(response_times) if response_times else 0
    
    async def _generate_system_status_content(self, system_data: Dict[str, Any]) -> str:
        """Generate system status content HTML"""
        # This would typically use the template service to render a complex status page
        # For now, return basic HTML structure
        return f"""
        <h2>⚙️ System Status</h2>
        <div class="system-overview">
            <h3>System Overview</h3>
            <p>Health Score: {system_data['health_analysis']['overall_score']:.2f}</p>
            <p>Active Issues: {len(system_data['health_analysis']['critical_issues'])}</p>
        </div>
        """


# Use Case Exceptions
class DashboardError(Exception):
    """Dashboard use case error"""
    pass


class ServiceUpdateError(Exception):
    """Service update use case error"""
    pass


class HealthCheckError(Exception):
    """Health check use case error"""
    pass


class SystemStatusError(Exception):
    """System status use case error"""
    pass