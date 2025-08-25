#!/usr/bin/env python3
"""
Diagnostic Service - Application Use Cases
CLEAN ARCHITECTURE - APPLICATION LAYER

Business logic orchestration für diagnostic operations
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from ..interfaces.event_publisher import IEventPublisher
from ...domain.entities.diagnostic_event import (
    CapturedEvent, DiagnosticTest, SystemHealthSnapshot, 
    ModuleCommunicationTest, TestResultStatus, SystemHealthStatus,
    DiagnosticEventType
)
from ...domain.repositories.diagnostic_repository import (
    IDiagnosticEventRepository, IDiagnosticTestRepository,
    ISystemHealthRepository, IModuleCommunicationRepository,
    IDiagnosticEventBusProvider
)


logger = logging.getLogger(__name__)


class EventMonitoringUseCase:
    """
    Use Case: Event Monitoring and Capture
    APPLICATION LAYER: Pure business logic orchestration
    """
    
    def __init__(
        self,
        event_repository: IDiagnosticEventRepository,
        event_bus_provider: IDiagnosticEventBusProvider,
        event_publisher: IEventPublisher
    ):
        self.event_repository = event_repository
        self.event_bus_provider = event_bus_provider
        self.event_publisher = event_publisher
        self.monitoring_active = False
        self.error_patterns = [
            'error', 'fail', 'exception', 'timeout', 'disconnect',
            'denied', 'refused', 'unavailable', 'critical'
        ]
    
    async def start_monitoring(self, event_types: List[str]) -> Dict[str, Any]:
        """Start monitoring specified event types"""
        try:
            # Subscribe to event types via event bus
            subscription_success = await self.event_bus_provider.subscribe_to_events(event_types)
            
            if subscription_success:
                self.monitoring_active = True
                
                # Publish monitoring started event
                await self.event_publisher.publish_event({
                    'event_type': 'diagnostic.monitoring.started',
                    'data': {
                        'event_types': event_types,
                        'started_at': datetime.now().isoformat()
                    }
                })
                
                logger.info(f"Event monitoring started for {len(event_types)} event types")
                return {'success': True, 'monitoring_active': True, 'event_types': event_types}
            else:
                return {'success': False, 'error': 'Failed to subscribe to event types'}
                
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop event monitoring"""
        try:
            self.monitoring_active = False
            
            # Publish monitoring stopped event
            await self.event_publisher.publish_event({
                'event_type': 'diagnostic.monitoring.stopped',
                'data': {'stopped_at': datetime.now().isoformat()}
            })
            
            logger.info("Event monitoring stopped")
            return {'success': True, 'monitoring_active': False}
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    async def capture_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and capture incoming event"""
        try:
            # Analyze event for error patterns
            error_indicators = self._detect_error_patterns(event_data)
            error_detected = len(error_indicators) > 0
            
            # Create captured event entity
            captured_event = CapturedEvent(
                event_type=event_data.get('event_type', 'unknown'),
                source=event_data.get('source', 'unknown'),
                stream_id=event_data.get('stream_id'),
                event_data=event_data.get('data', {}),
                correlation_id=event_data.get('correlation_id'),
                error_detected=error_detected,
                error_indicators=error_indicators,
                metadata={'monitoring_active': self.monitoring_active}
            )
            
            # Save captured event
            save_success = await self.event_repository.save_event(captured_event)
            
            if save_success and error_detected:
                # Publish error detection event
                await self.event_publisher.publish_event({
                    'event_type': 'diagnostic.error.detected',
                    'data': {
                        'capture_id': captured_event.capture_id,
                        'source_event_type': captured_event.event_type,
                        'error_indicators': error_indicators
                    }
                })
            
            return {
                'success': save_success,
                'capture_id': captured_event.capture_id,
                'error_detected': error_detected
            }
            
        except Exception as e:
            logger.error(f"Failed to capture event: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        try:
            stats = await self.event_repository.get_event_statistics()
            stats.update({
                'monitoring_active': self.monitoring_active,
                'timestamp': datetime.now().isoformat()
            })
            return {'success': True, 'data': stats}
            
        except Exception as e:
            logger.error(f"Failed to get monitoring statistics: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_recent_events(
        self, 
        limit: int = 50, 
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get recent captured events with filtering"""
        try:
            events = await self.event_repository.get_events(limit, filter_criteria)
            
            return {
                'success': True,
                'data': {
                    'events': [event.__dict__ for event in events],
                    'count': len(events),
                    'filter_applied': filter_criteria is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return {'success': False, 'error': str(e)}
    
    def _detect_error_patterns(self, event_data: Dict[str, Any]) -> List[str]:
        """Detect error patterns in event data"""
        indicators = []
        event_str = str(event_data).lower()
        
        for pattern in self.error_patterns:
            if pattern in event_str:
                indicators.append(pattern)
        
        return indicators


class DiagnosticTestingUseCase:
    """
    Use Case: Diagnostic Testing and Module Communication
    APPLICATION LAYER: Test orchestration and management
    """
    
    def __init__(
        self,
        test_repository: IDiagnosticTestRepository,
        communication_repository: IModuleCommunicationRepository,
        event_bus_provider: IDiagnosticEventBusProvider,
        event_publisher: IEventPublisher
    ):
        self.test_repository = test_repository
        self.communication_repository = communication_repository
        self.event_bus_provider = event_bus_provider
        self.event_publisher = event_publisher
    
    async def create_module_test(
        self, 
        test_name: str,
        target_module: str,
        test_type: str = "ping",
        test_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create and execute module diagnostic test"""
        try:
            # Create test entity
            diagnostic_test = DiagnosticTest(
                test_name=test_name,
                test_type=test_type,
                target_module=target_module,
                test_data=test_data or {}
            )
            
            # Save test
            await self.test_repository.save_test(diagnostic_test)
            
            # Execute test based on type
            if test_type == "ping":
                result = await self._execute_ping_test(diagnostic_test)
            elif test_type == "message":
                result = await self._execute_message_test(diagnostic_test)
            else:
                result = await self._execute_custom_test(diagnostic_test)
            
            # Update test with result
            await self.test_repository.update_test_status(
                diagnostic_test.test_id,
                result['status'],
                result.get('data'),
                result.get('error')
            )
            
            # Publish test completed event
            await self.event_publisher.publish_event({
                'event_type': 'diagnostic.test.completed',
                'data': {
                    'test_id': diagnostic_test.test_id,
                    'test_type': test_type,
                    'target_module': target_module,
                    'success': result['status'] == TestResultStatus.SUCCESS
                }
            })
            
            return {
                'success': True,
                'test_id': diagnostic_test.test_id,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create module test: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_module_communication(self, target_module: str) -> Dict[str, Any]:
        """Test communication with specific module"""
        try:
            # Create communication test
            comm_test = ModuleCommunicationTest(
                source_module="diagnostic_service",
                target_module=target_module,
                communication_type="ping",
                test_payload={'ping': True, 'timestamp': datetime.now().isoformat()}
            )
            
            # Save communication test
            await self.communication_repository.save_communication_test(comm_test)
            
            # Execute ping
            ping_success = await self.event_bus_provider.ping_module(target_module)
            
            # Update with result
            await self.communication_repository.update_test_response(
                comm_test.test_id,
                {'ping_response': ping_success},
                ping_success
            )
            
            return {
                'success': True,
                'communication_test_id': comm_test.test_id,
                'ping_successful': ping_success,
                'target_module': target_module
            }
            
        except Exception as e:
            logger.error(f"Failed to test module communication: {e}")
            return {'success': False, 'error': str(e)}
    
    async def send_test_message(
        self, 
        target_module: str,
        message_type: str,
        custom_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send test message to target module"""
        try:
            correlation_id = await self.event_bus_provider.send_test_message(
                target_module, 
                {
                    'message_type': message_type,
                    'test_data': custom_data,
                    'source': 'diagnostic_service'
                }
            )
            
            # Create tracking test
            test = DiagnosticTest(
                test_name=f"Message Test - {target_module}",
                test_type="message",
                target_module=target_module,
                test_data={
                    'message_type': message_type,
                    'correlation_id': correlation_id,
                    'custom_data': custom_data
                }
            )
            
            await self.test_repository.save_test(test)
            
            return {
                'success': True,
                'test_id': test.test_id,
                'correlation_id': correlation_id,
                'message_sent': True
            }
            
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_test_results(self, test_id: Optional[str] = None) -> Dict[str, Any]:
        """Get test results"""
        try:
            if test_id:
                test = await self.test_repository.get_test_by_id(test_id)
                if test:
                    return {
                        'success': True,
                        'test': test.get_execution_summary()
                    }
                else:
                    return {'success': False, 'error': 'Test not found'}
            else:
                tests = await self.test_repository.get_tests(limit=50)
                return {
                    'success': True,
                    'tests': [test.get_execution_summary() for test in tests]
                }
                
        except Exception as e:
            logger.error(f"Failed to get test results: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_ping_test(self, test: DiagnosticTest) -> Dict[str, Any]:
        """Execute ping test"""
        try:
            success = await self.event_bus_provider.ping_module(test.target_module)
            return {
                'status': TestResultStatus.SUCCESS if success else TestResultStatus.FAILED,
                'data': {'ping_successful': success}
            }
        except Exception as e:
            return {
                'status': TestResultStatus.FAILED,
                'error': str(e)
            }
    
    async def _execute_message_test(self, test: DiagnosticTest) -> Dict[str, Any]:
        """Execute message test"""
        try:
            correlation_id = await self.event_bus_provider.send_test_message(
                test.target_module, 
                test.test_data
            )
            return {
                'status': TestResultStatus.SUCCESS,
                'data': {'correlation_id': correlation_id, 'message_sent': True}
            }
        except Exception as e:
            return {
                'status': TestResultStatus.FAILED,
                'error': str(e)
            }
    
    async def _execute_custom_test(self, test: DiagnosticTest) -> Dict[str, Any]:
        """Execute custom test logic"""
        # Default implementation for custom tests
        return {
            'status': TestResultStatus.SUCCESS,
            'data': {'custom_test_executed': True}
        }


class SystemHealthUseCase:
    """
    Use Case: System Health Monitoring and Assessment
    APPLICATION LAYER: Health analysis and reporting
    """
    
    def __init__(
        self,
        event_repository: IDiagnosticEventRepository,
        health_repository: ISystemHealthRepository,
        event_bus_provider: IDiagnosticEventBusProvider,
        event_publisher: IEventPublisher
    ):
        self.event_repository = event_repository
        self.health_repository = health_repository
        self.event_bus_provider = event_bus_provider
        self.event_publisher = event_publisher
    
    async def generate_health_snapshot(self) -> Dict[str, Any]:
        """Generate current system health snapshot"""
        try:
            # Gather health metrics
            event_stats = await self.event_repository.get_event_statistics()
            error_events = await self.event_repository.get_error_events(limit=100)
            event_bus_healthy = await self.event_bus_provider.is_event_bus_healthy()
            connected_modules = await self.event_bus_provider.get_connected_modules()
            
            # Calculate health score
            health_score = await self._calculate_health_score(
                event_stats, error_events, event_bus_healthy, connected_modules
            )
            
            # Determine overall status
            overall_status = self._determine_health_status(health_score, error_events)
            
            # Generate alerts and recommendations
            alerts = self._generate_health_alerts(error_events, event_stats, event_bus_healthy)
            recommendations = self._generate_recommendations(health_score, alerts)
            
            # Create health snapshot
            snapshot = SystemHealthSnapshot(
                overall_status=overall_status,
                health_score=health_score,
                total_events_monitored=event_stats.get('total_events', 0),
                error_event_count=len(error_events),
                active_sources=connected_modules,
                event_type_distribution=event_stats.get('event_type_counts', {}),
                performance_metrics={
                    'event_bus_healthy': event_bus_healthy,
                    'connected_modules_count': len(connected_modules)
                },
                alerts=alerts,
                recommendations=recommendations
            )
            
            # Save snapshot
            await self.health_repository.save_health_snapshot(snapshot)
            
            # Publish health update if significant change
            await self._publish_health_update_if_needed(snapshot)
            
            return {
                'success': True,
                'health_snapshot': snapshot.get_status_summary(),
                'detailed_metrics': snapshot.__dict__
            }
            
        except Exception as e:
            logger.error(f"Failed to generate health snapshot: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_health_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get system health trend over time"""
        try:
            snapshots = await self.health_repository.get_health_trend(hours)
            
            if not snapshots:
                return {'success': True, 'trend': [], 'message': 'No health data available'}
            
            trend_data = []
            for snapshot in snapshots:
                trend_data.append({
                    'timestamp': snapshot.timestamp.isoformat(),
                    'health_score': snapshot.health_score,
                    'status': snapshot.overall_status.value,
                    'error_count': snapshot.error_event_count,
                    'active_sources_count': len(snapshot.active_sources)
                })
            
            # Analyze trend direction
            trend_analysis = self._analyze_health_trend(snapshots)
            
            return {
                'success': True,
                'trend': trend_data,
                'analysis': trend_analysis,
                'timeframe_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get health trend: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _calculate_health_score(
        self, 
        event_stats: Dict[str, Any],
        error_events: List[CapturedEvent],
        event_bus_healthy: bool,
        connected_modules: List[str]
    ) -> float:
        """Calculate overall health score (0-100)"""
        base_score = 100.0
        
        # Penalize based on error rate
        total_events = event_stats.get('total_events', 0)
        if total_events > 0:
            error_rate = len(error_events) / total_events
            base_score -= (error_rate * 50)  # Max 50 points penalty for errors
        
        # Penalize for event bus issues
        if not event_bus_healthy:
            base_score -= 30
        
        # Penalize for low connectivity
        if len(connected_modules) < 2:
            base_score -= 20
        
        # Recent error penalty
        recent_errors = [e for e in error_events if e.get_age_seconds() < 3600]  # Last hour
        if len(recent_errors) > 5:
            base_score -= 15
        
        return max(0.0, min(100.0, base_score))
    
    def _determine_health_status(
        self, 
        health_score: float, 
        error_events: List[CapturedEvent]
    ) -> SystemHealthStatus:
        """Determine overall health status based on metrics"""
        critical_errors = [e for e in error_events if 'critical' in e.error_indicators]
        
        if critical_errors or health_score < 30:
            return SystemHealthStatus.CRITICAL
        elif health_score < 50:
            return SystemHealthStatus.UNHEALTHY
        elif health_score < 80:
            return SystemHealthStatus.DEGRADED
        else:
            return SystemHealthStatus.HEALTHY
    
    def _generate_health_alerts(
        self, 
        error_events: List[CapturedEvent],
        event_stats: Dict[str, Any],
        event_bus_healthy: bool
    ) -> List[str]:
        """Generate health alerts"""
        alerts = []
        
        if not event_bus_healthy:
            alerts.append("Event bus connectivity issues detected")
        
        recent_errors = [e for e in error_events if e.get_age_seconds() < 1800]  # Last 30 min
        if len(recent_errors) > 10:
            alerts.append(f"High error rate: {len(recent_errors)} errors in last 30 minutes")
        
        total_events = event_stats.get('total_events', 0)
        if total_events == 0:
            alerts.append("No events captured - monitoring may be inactive")
        
        return alerts
    
    def _generate_recommendations(
        self, 
        health_score: float, 
        alerts: List[str]
    ) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        if health_score < 70:
            recommendations.append("Investigate recent errors and system performance")
        
        if "Event bus" in str(alerts):
            recommendations.append("Check event bus service status and connectivity")
        
        if "High error rate" in str(alerts):
            recommendations.append("Review error patterns and implement fixes")
        
        if len(recommendations) == 0:
            recommendations.append("System health is good - continue monitoring")
        
        return recommendations
    
    def _analyze_health_trend(self, snapshots: List[SystemHealthSnapshot]) -> Dict[str, Any]:
        """Analyze health trend direction"""
        if len(snapshots) < 2:
            return {'trend': 'insufficient_data', 'direction': 'unknown'}
        
        scores = [s.health_score for s in snapshots[-10:]]  # Last 10 snapshots
        
        if len(scores) < 2:
            return {'trend': 'stable', 'direction': 'stable'}
        
        # Simple trend analysis
        recent_avg = sum(scores[-3:]) / 3 if len(scores) >= 3 else scores[-1]
        older_avg = sum(scores[:3]) / 3 if len(scores) >= 3 else scores[0]
        
        if recent_avg > older_avg + 5:
            direction = 'improving'
        elif recent_avg < older_avg - 5:
            direction = 'declining'
        else:
            direction = 'stable'
        
        return {
            'trend': direction,
            'recent_average': recent_avg,
            'older_average': older_avg,
            'score_change': recent_avg - older_avg
        }
    
    async def _publish_health_update_if_needed(self, snapshot: SystemHealthSnapshot):
        """Publish health update if significant change detected"""
        try:
            latest_previous = await self.health_repository.get_latest_snapshot()
            
            if latest_previous:
                status_changed = latest_previous.overall_status != snapshot.overall_status
                significant_score_change = abs(
                    latest_previous.health_score - snapshot.health_score
                ) > 10
                
                if status_changed or significant_score_change:
                    await self.event_publisher.publish_event({
                        'event_type': 'diagnostic.health.status_changed',
                        'data': {
                            'previous_status': latest_previous.overall_status.value,
                            'new_status': snapshot.overall_status.value,
                            'score_change': snapshot.health_score - latest_previous.health_score,
                            'snapshot_id': snapshot.snapshot_id
                        }
                    })
        except Exception as e:
            logger.warning(f"Failed to publish health update: {e}")


class DiagnosticMaintenanceUseCase:
    """
    Use Case: Diagnostic Data Maintenance and Cleanup
    APPLICATION LAYER: Data lifecycle management
    """
    
    def __init__(
        self,
        event_repository: IDiagnosticEventRepository,
        test_repository: IDiagnosticTestRepository,
        health_repository: ISystemHealthRepository,
        communication_repository: IModuleCommunicationRepository,
        event_publisher: IEventPublisher
    ):
        self.event_repository = event_repository
        self.test_repository = test_repository
        self.health_repository = health_repository
        self.communication_repository = communication_repository
        self.event_publisher = event_publisher
    
    async def cleanup_old_data(self) -> Dict[str, Any]:
        """Perform comprehensive data cleanup"""
        try:
            cleanup_results = {}
            
            # Clean up old events (older than 7 days)
            events_removed = await self.event_repository.cleanup_old_events(7)
            cleanup_results['events_removed'] = events_removed
            
            # Clean up completed tests (older than 24 hours)
            tests_removed = await self.test_repository.cleanup_completed_tests(24)
            cleanup_results['tests_removed'] = tests_removed
            
            # Clean up old health snapshots (older than 30 days)
            snapshots_removed = await self.health_repository.cleanup_old_snapshots(30)
            cleanup_results['snapshots_removed'] = snapshots_removed
            
            # Publish cleanup completed event
            await self.event_publisher.publish_event({
                'event_type': 'diagnostic.maintenance.cleanup_completed',
                'data': {
                    'cleanup_results': cleanup_results,
                    'cleaned_at': datetime.now().isoformat()
                }
            })
            
            logger.info(f"Diagnostic data cleanup completed: {cleanup_results}")
            
            return {
                'success': True,
                'cleanup_results': cleanup_results,
                'total_items_removed': sum(cleanup_results.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get diagnostic data storage statistics"""
        try:
            event_stats = await self.event_repository.get_event_statistics()
            
            # Get counts for other repositories
            all_tests = await self.test_repository.get_tests(limit=10000)  # Get all
            all_snapshots = await self.health_repository.get_snapshots(limit=10000)
            
            storage_stats = {
                'total_events': event_stats.get('total_events', 0),
                'total_tests': len(all_tests),
                'total_health_snapshots': len(all_snapshots),
                'event_types_count': len(event_stats.get('event_type_counts', {})),
                'active_sources_count': len(event_stats.get('source_counts', {})),
                'completed_tests': len([t for t in all_tests if t.is_completed()]),
                'pending_tests': len([t for t in all_tests if not t.is_completed()])
            }
            
            return {
                'success': True,
                'storage_statistics': storage_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {'success': False, 'error': str(e)}