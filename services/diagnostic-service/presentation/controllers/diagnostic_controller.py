#!/usr/bin/env python3
"""
Diagnostic Service - FastAPI Controller
CLEAN ARCHITECTURE - PRESENTATION LAYER

HTTP request handlers and API endpoints
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import HTTPException, BackgroundTasks, Query, Path

# Import Exception-Framework
from .....shared.exceptions import (
    BaseServiceException, 
    DatabaseException, 
    EventBusException,
    ExternalAPIException,
    ValidationException,
    ConfigurationException,
    BusinessLogicException,
    NetworkException,
    get_error_response
)
from .....shared.exception_handler import (
    exception_handler,
    database_exception_handler,
    event_bus_exception_handler,
    api_exception_handler,
    create_fastapi_exception_handler,
    configure_exception_handler,
    ExceptionHandlerConfig
)

from .models.diagnostic_models import (
    # Request models
    StartMonitoringRequest, CreateTestRequest, SendTestMessageRequest, EventFilterRequest,
    # Response models
    BaseResponse, ErrorResponse, MonitoringStatusResponse, EventStatisticsResponse,
    EventsResponse, CreateTestResponse, TestResultsResponse, ModuleCommunicationResponse,
    SendMessageResponse, SystemHealthResponse, HealthTrendResponse, MaintenanceResponse,
    ContainerStatusResponse, DetailedHealthResponse,
    # Utility models
    PaginationParams, TimeRangeParams, MonitoringActionEnum
)
from ...application.use_cases.diagnostic_use_cases import (
    EventMonitoringUseCase, DiagnosticTestingUseCase,
    SystemHealthUseCase, DiagnosticMaintenanceUseCase
)
from ...infrastructure.container import DiagnosticServiceContainer


logger = logging.getLogger(__name__)


class DiagnosticController:
    """
    Diagnostic Service Controller
    PRESENTATION LAYER: HTTP request handling and response formatting
    """
    
    def __init__(self, container: DiagnosticServiceContainer):
        """
        Initialize controller with dependency container
        
        Args:
            container: Initialized service container
        """
        self.container = container
        self.service_started_at = datetime.now()
        
        # Verify container is initialized
        if not container.initialized:
            raise RuntimeError("Container must be initialized before creating controller")
    
    # Event Monitoring Endpoints
    @event_bus_exception_handler()
    async def start_monitoring(self, request: StartMonitoringRequest) -> MonitoringStatusResponse:
        """Start event monitoring for specified event types"""
        try:
            # Validierung der Eingabedaten
            if not request.event_types:
                raise ValidationException(
                    "Event types are required",
                    field_errors={"event_types": "At least one event type must be specified"}
                )
            
            monitoring_use_case = self.container.get_service('event_monitoring_use_case')
            
            if not monitoring_use_case:
                raise ConfigurationException(
                    "Event monitoring use case not available",
                    config_key="event_monitoring_use_case"
                )
            
            result = await monitoring_use_case.start_monitoring(request.event_types)
            
            if result['success']:
                return MonitoringStatusResponse(
                    success=True,
                    message="Event monitoring started successfully",
                    monitoring_active=result['monitoring_active'],
                    subscribed_event_types=result['event_types'],
                    events_captured=0,  # Just started
                    error_events=0
                )
            else:
                raise EventBusException(
                    f"Failed to start monitoring: {result.get('error', 'Unknown error')}",
                    context={"event_types": request.event_types, "result": result}
                )
                
        except HTTPException:
            raise
        except BaseServiceException as e:
            logger.error(f"Service exception in start_monitoring: {e.message}")
            raise HTTPException(status_code=e.http_status_code, detail=get_error_response(e))
        except Exception as e:
            # Unbekannte Exceptions werden zu BaseServiceExceptions konvertiert
            service_exc = BusinessLogicException(
                f"Unexpected error starting monitoring: {str(e)}",
                context={"original_error": str(e), "event_types": request.event_types}
            )
            logger.error(f"Unexpected exception in start_monitoring: {e}")
            raise HTTPException(status_code=service_exc.http_status_code, detail=get_error_response(service_exc))
    
    @event_bus_exception_handler()
    async def stop_monitoring(self) -> MonitoringStatusResponse:
        """Stop event monitoring"""
        try:
            monitoring_use_case = self.container.get_service('event_monitoring_use_case')
            
            if not monitoring_use_case:
                raise ConfigurationException(
                    "Event monitoring use case not available",
                    config_key="event_monitoring_use_case"
                )
            
            result = await monitoring_use_case.stop_monitoring()
            
            if result['success']:
                return MonitoringStatusResponse(
                    success=True,
                    message="Event monitoring stopped",
                    monitoring_active=result['monitoring_active'],
                    subscribed_event_types=[],
                    events_captured=0,  # Status only
                    error_events=0
                )
            else:
                raise EventBusException(
                    f"Failed to stop monitoring: {result.get('error', 'Unknown error')}",
                    context={"result": result}
                )
                
        except HTTPException:
            raise
        except BaseServiceException as e:
            logger.error(f"Service exception in stop_monitoring: {e.message}")
            raise HTTPException(status_code=e.http_status_code, detail=get_error_response(e))
        except Exception as e:
            service_exc = BusinessLogicException(
                f"Unexpected error stopping monitoring: {str(e)}",
                context={"original_error": str(e)}
            )
            logger.error(f"Unexpected exception in stop_monitoring: {e}")
            raise HTTPException(status_code=service_exc.http_status_code, detail=get_error_response(service_exc))
    
    async def get_monitoring_statistics(self) -> EventStatisticsResponse:
        """Get current monitoring statistics"""
        try:
            monitoring_use_case = self.container.get_service('event_monitoring_use_case')
            
            result = await monitoring_use_case.get_monitoring_statistics()
            
            if result['success']:
                stats = result['data']
                return EventStatisticsResponse(
                    success=True,
                    message="Statistics retrieved successfully",
                    total_events=stats.get('total_events', 0),
                    error_events=stats.get('error_events', 0),
                    error_rate_percent=stats.get('error_rate_percent', 0.0),
                    event_type_counts=stats.get('event_type_counts', {}),
                    source_counts=stats.get('source_counts', {}),
                    recent_events_last_hour=stats.get('recent_events_last_hour', 0)
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get statistics: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get monitoring statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_recent_events(self, filter_params: EventFilterRequest) -> EventsResponse:
        """Get recent captured events with filtering"""
        try:
            monitoring_use_case = self.container.get_service('event_monitoring_use_case')
            
            # Build filter criteria
            filter_criteria = {}
            if filter_params.event_type:
                filter_criteria['event_type'] = filter_params.event_type
            if filter_params.source:
                filter_criteria['source'] = filter_params.source
            if filter_params.error_only:
                filter_criteria['error_only'] = True
            if filter_params.max_age_seconds:
                filter_criteria['max_age_seconds'] = filter_params.max_age_seconds
            
            result = await monitoring_use_case.get_recent_events(
                filter_params.limit, 
                filter_criteria if filter_criteria else None
            )
            
            if result['success']:
                data = result['data']
                
                # Convert events to response models
                events = []
                for event_dict in data['events']:
                    # Map domain entity dict to response model
                    event_model = {
                        'capture_id': event_dict.get('capture_id', ''),
                        'event_type': event_dict.get('event_type', ''),
                        'source': event_dict.get('source', ''),
                        'stream_id': event_dict.get('stream_id'),
                        'captured_at': event_dict.get('captured_at', datetime.now()),
                        'error_detected': event_dict.get('error_detected', False),
                        'error_indicators': event_dict.get('error_indicators', []),
                        'processing_time_ms': event_dict.get('processing_time_ms')
                    }
                    events.append(event_model)
                
                return EventsResponse(
                    success=True,
                    message=f"Retrieved {len(events)} events",
                    events=events,
                    count=len(events),
                    total_captured=data.get('total_captured', len(events)),
                    filter_applied=data.get('filter_applied', False)
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get events: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Diagnostic Testing Endpoints
    async def create_test(self, request: CreateTestRequest) -> CreateTestResponse:
        """Create and execute diagnostic test"""
        try:
            testing_use_case = self.container.get_service('diagnostic_testing_use_case')
            
            result = await testing_use_case.create_module_test(
                test_name=request.test_name,
                target_module=request.target_module,
                test_type=request.test_type.value,
                test_data=request.test_data
            )
            
            if result['success']:
                test_result = result['result']
                
                return CreateTestResponse(
                    success=True,
                    message="Test created and executed successfully",
                    test_id=result['test_id'],
                    test_result={
                        'test_id': result['test_id'],
                        'test_name': request.test_name,
                        'status': test_result['status'].value,
                        'execution_time_ms': test_result.get('execution_time_ms'),
                        'retry_count': 0,
                        'success': test_result['status'].value == 'success',
                        'completed': True
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create test: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create test: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def test_module_communication(self, module_name: str) -> ModuleCommunicationResponse:
        """Test communication with specific module"""
        try:
            testing_use_case = self.container.get_service('diagnostic_testing_use_case')
            
            result = await testing_use_case.test_module_communication(module_name)
            
            if result['success']:
                return ModuleCommunicationResponse(
                    success=True,
                    message=f"Communication test with {module_name} completed",
                    communication_test_id=result['communication_test_id'],
                    ping_successful=result['ping_successful'],
                    target_module=result['target_module'],
                    response_time_ms=None  # Could be calculated from test details
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Communication test failed: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to test module communication: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def send_test_message(self, request: SendTestMessageRequest) -> SendMessageResponse:
        """Send test message to target module"""
        try:
            testing_use_case = self.container.get_service('diagnostic_testing_use_case')
            
            result = await testing_use_case.send_test_message(
                target_module=request.target_module,
                message_type=request.message_type,
                custom_data=request.custom_data
            )
            
            if result['success']:
                return SendMessageResponse(
                    success=True,
                    message=f"Test message sent to {request.target_module}",
                    test_id=result['test_id'],
                    correlation_id=result['correlation_id'],
                    message_sent=result.get('message_sent', True)
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send test message: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_test_results(self, test_id: Optional[str] = None) -> TestResultsResponse:
        """Get test results"""
        try:
            testing_use_case = self.container.get_service('diagnostic_testing_use_case')
            
            result = await testing_use_case.get_test_results(test_id)
            
            if result['success']:
                if test_id:
                    # Single test result
                    test_data = result['test']
                    tests = [test_data]
                else:
                    # Multiple test results
                    tests = result['tests']
                
                return TestResultsResponse(
                    success=True,
                    message=f"Retrieved {len(tests)} test result(s)",
                    tests=tests
                )
            else:
                raise HTTPException(
                    status_code=404 if test_id else 500,
                    detail=result.get('error', 'Unknown error')
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get test results: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # System Health Endpoints
    async def get_system_health(self) -> SystemHealthResponse:
        """Get current system health snapshot"""
        try:
            health_use_case = self.container.get_service('system_health_use_case')
            
            result = await health_use_case.generate_health_snapshot()
            
            if result['success']:
                health_data = result['health_snapshot']
                detailed_metrics = result.get('detailed_metrics')
                
                return SystemHealthResponse(
                    success=True,
                    message="System health snapshot generated",
                    health_snapshot={
                        'status': health_data['status'],
                        'health_score': health_data['health_score'],
                        'error_rate_percent': health_data.get('error_rate_percent', 0.0),
                        'total_events': health_data['total_events'],
                        'active_sources_count': health_data['active_sources_count'],
                        'alert_count': health_data.get('alert_count', 0),
                        'timestamp': datetime.now()
                    },
                    detailed_metrics=detailed_metrics
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get system health: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_health_trend(self, hours: int = Query(24, ge=1, le=168)) -> HealthTrendResponse:
        """Get system health trend over time"""
        try:
            health_use_case = self.container.get_service('system_health_use_case')
            
            result = await health_use_case.get_health_trend(hours)
            
            if result['success']:
                trend_data = result['trend']
                analysis = result['analysis']
                
                # Convert trend data to response format
                trend_points = []
                for point in trend_data:
                    trend_points.append({
                        'timestamp': datetime.fromisoformat(point['timestamp']),
                        'health_score': point['health_score'],
                        'status': point['status'],
                        'error_count': point['error_count'],
                        'active_sources_count': point['active_sources_count']
                    })
                
                return HealthTrendResponse(
                    success=True,
                    message=f"Health trend retrieved for {hours} hours",
                    trend=trend_points,
                    analysis=analysis,
                    timeframe_hours=hours
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get health trend: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get health trend: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Maintenance Endpoints
    async def perform_maintenance_cleanup(self, background_tasks: BackgroundTasks) -> MaintenanceResponse:
        """Perform diagnostic data cleanup"""
        try:
            maintenance_use_case = self.container.get_service('diagnostic_maintenance_use_case')
            
            # Run cleanup in background
            result = await maintenance_use_case.cleanup_old_data()
            
            if result['success']:
                return MaintenanceResponse(
                    success=True,
                    message="Maintenance cleanup completed successfully",
                    cleanup_results=result['cleanup_results'],
                    total_items_removed=result['total_items_removed']
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Maintenance cleanup failed: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to perform maintenance cleanup: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get diagnostic data storage statistics"""
        try:
            maintenance_use_case = self.container.get_service('diagnostic_maintenance_use_case')
            
            result = await maintenance_use_case.get_storage_statistics()
            
            if result['success']:
                return {
                    'success': True,
                    'message': "Storage statistics retrieved",
                    'statistics': result['storage_statistics'],
                    'timestamp': result['timestamp']
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get storage statistics: {result.get('error', 'Unknown error')}"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Development/Debug Endpoints
    async def get_container_status(self) -> ContainerStatusResponse:
        """Get container status for debugging"""
        try:
            status = self.container.get_container_status()
            
            return ContainerStatusResponse(
                success=True,
                message="Container status retrieved",
                initialized=status['initialized'],
                total_services=status['total_services'],
                started_services=status['started_services'],
                failed_services=status['failed_services'],
                health_status=status['health_status'],
                service_names=status['service_names']
            )
            
        except Exception as e:
            logger.error(f"Failed to get container status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_detailed_health_report(self) -> DetailedHealthResponse:
        """Get detailed health report for all services"""
        try:
            health_report = await self.container.get_detailed_health_report()
            
            # Calculate health summary
            total_services = len(health_report.get('service_health', {}))
            healthy_services = sum(
                1 for service_health in health_report.get('service_health', {}).values()
                if isinstance(service_health, dict) and service_health.get('is_healthy', False)
            )
            unhealthy_services = [
                service_name for service_name, service_health in health_report.get('service_health', {}).items()
                if isinstance(service_health, dict) and not service_health.get('is_healthy', True)
            ]
            
            health_summary = {
                'total_services': total_services,
                'healthy_services': healthy_services,
                'unhealthy_services_count': len(unhealthy_services),
                'overall_health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 100
            }
            
            return DetailedHealthResponse(
                success=True,
                message="Detailed health report generated",
                container_healthy=health_report['container_healthy'],
                service_health=health_report.get('service_health', {}),
                unhealthy_services=unhealthy_services,
                health_summary=health_summary
            )
            
        except Exception as e:
            logger.error(f"Failed to get detailed health report: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def reset_service_state(self) -> BaseResponse:
        """Reset service state (development endpoint)"""
        try:
            # Clear event publisher events
            event_publisher = self.container.get_service('event_publisher')
            if hasattr(event_publisher, 'clear_events'):
                event_publisher.clear_events()
            
            # Could reset other services if needed
            
            return BaseResponse(
                success=True,
                message="Service state reset completed"
            )
            
        except Exception as e:
            logger.error(f"Failed to reset service state: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Utility Methods
    def _handle_use_case_result(self, result: Dict[str, Any], success_message: str = "Operation completed"):
        """Handle use case result and convert to HTTP response"""
        if result['success']:
            return result.get('data', {})
        else:
            error_message = result.get('error', 'Unknown error occurred')
            logger.warning(f"Use case failed: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get diagnostic service information"""
        uptime = datetime.now() - self.service_started_at
        
        return {
            'service_name': 'Diagnostic Service',
            'version': '6.0.0',
            'architecture': 'Clean Architecture',
            'started_at': self.service_started_at.isoformat(),
            'uptime_seconds': int(uptime.total_seconds()),
            'container_initialized': self.container.initialized,
            'available_endpoints': [
                '/monitoring/start', '/monitoring/stop', '/monitoring/statistics',
                '/monitoring/events', '/testing/create', '/testing/communication/{module}',
                '/testing/message', '/testing/results', '/health/status',
                '/health/trend', '/maintenance/cleanup', '/dev/container-status'
            ]
        }