#!/usr/bin/env python3
"""
Diagnostic Service - Domain Entities
CLEAN ARCHITECTURE - DOMAIN LAYER

Rich domain entities für Event Monitoring und Diagnostic Testing
Autor: Claude Code - Architecture Modernization Specialist  
Datum: 25. August 2025
Version: 6.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
from decimal import Decimal


class DiagnosticEventType(Enum):
    """Diagnostic event types"""
    SYSTEM_PING = "system.ping"
    MODULE_TEST = "module.test" 
    HEALTH_CHECK = "health.check"
    MONITORING_START = "monitoring.start"
    MONITORING_STOP = "monitoring.stop"
    ERROR_DETECTED = "error.detected"
    PERFORMANCE_ALERT = "performance.alert"
    

class TestResultStatus(Enum):
    """Test result status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    

class SystemHealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass(frozen=True)
class CapturedEvent:
    """
    Domain Entity: Captured Event
    Represents a monitored event with metadata and analysis
    """
    capture_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source: str = ""
    stream_id: Optional[str] = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    captured_at: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    processing_time_ms: Optional[float] = None
    error_detected: bool = False
    error_indicators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_error_event(self) -> bool:
        """Check if this event indicates an error condition"""
        return self.error_detected or len(self.error_indicators) > 0
    
    def get_age_seconds(self) -> float:
        """Get age of captured event in seconds"""
        return (datetime.now() - self.captured_at).total_seconds()
    
    def matches_filter(self, filter_criteria: Dict[str, Any]) -> bool:
        """Check if event matches filter criteria"""
        for key, value in filter_criteria.items():
            if key == 'event_type' and self.event_type != value:
                return False
            elif key == 'source' and self.source != value:
                return False
            elif key == 'error_only' and value and not self.is_error_event():
                return False
            elif key == 'max_age_seconds' and self.get_age_seconds() > value:
                return False
        return True


@dataclass(frozen=True) 
class DiagnosticTest:
    """
    Domain Entity: Diagnostic Test
    Represents a test case with execution details
    """
    test_id: str = field(default_factory=lambda: f"diag_test_{uuid.uuid4()}")
    test_name: str = ""
    test_type: str = ""
    target_module: Optional[str] = None
    test_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TestResultStatus = TestResultStatus.PENDING
    result_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def is_completed(self) -> bool:
        """Check if test is completed"""
        return self.status in [TestResultStatus.SUCCESS, TestResultStatus.FAILED]
    
    def is_successful(self) -> bool:
        """Check if test was successful"""
        return self.status == TestResultStatus.SUCCESS
    
    def can_retry(self) -> bool:
        """Check if test can be retried"""
        return (self.status == TestResultStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get test execution summary"""
        return {
            'test_id': self.test_id,
            'test_name': self.test_name,
            'status': self.status.value,
            'execution_time_ms': self.execution_time_ms,
            'retry_count': self.retry_count,
            'success': self.is_successful(),
            'completed': self.is_completed()
        }


@dataclass(frozen=True)
class SystemHealthSnapshot:
    """
    Domain Entity: System Health Snapshot
    Represents system health at a point in time
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    overall_status: SystemHealthStatus = SystemHealthStatus.HEALTHY
    health_score: float = 100.0
    total_events_monitored: int = 0
    error_event_count: int = 0
    active_sources: List[str] = field(default_factory=list)
    event_type_distribution: Dict[str, int] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def calculate_error_rate(self) -> float:
        """Calculate error rate percentage"""
        if self.total_events_monitored == 0:
            return 0.0
        return (self.error_event_count / self.total_events_monitored) * 100
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get health status summary"""
        return {
            'status': self.overall_status.value,
            'health_score': self.health_score,
            'error_rate_percent': self.calculate_error_rate(),
            'total_events': self.total_events_monitored,
            'active_sources_count': len(self.active_sources),
            'alert_count': len(self.alerts),
            'timestamp': self.timestamp.isoformat()
        }
    
    def is_healthy(self) -> bool:
        """Check if system is in healthy state"""
        return self.overall_status == SystemHealthStatus.HEALTHY
    
    def needs_attention(self) -> bool:
        """Check if system needs attention"""
        return (self.overall_status in [SystemHealthStatus.DEGRADED, SystemHealthStatus.UNHEALTHY] or
                len(self.alerts) > 0)


@dataclass(frozen=True)
class ModuleCommunicationTest:
    """
    Domain Entity: Module Communication Test
    Specialized test for module-to-module communication
    """
    test_id: str = field(default_factory=lambda: f"comm_test_{uuid.uuid4()}")
    source_module: str = ""
    target_module: str = ""
    communication_type: str = "ping"  # ping, request_response, publish_subscribe
    test_payload: Dict[str, Any] = field(default_factory=dict)
    initiated_at: datetime = field(default_factory=datetime.now)
    response_received_at: Optional[datetime] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    round_trip_time_ms: Optional[float] = None
    success: bool = False
    error_details: Optional[str] = None
    
    def calculate_round_trip_time(self) -> Optional[float]:
        """Calculate round trip time if response received"""
        if self.response_received_at:
            delta = self.response_received_at - self.initiated_at
            return delta.total_seconds() * 1000
        return None
    
    def is_completed(self) -> bool:
        """Check if communication test is completed"""
        return self.response_received_at is not None or self.error_details is not None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get communication performance metrics"""
        return {
            'round_trip_time_ms': self.round_trip_time_ms or self.calculate_round_trip_time(),
            'success': self.success,
            'communication_type': self.communication_type,
            'source_module': self.source_module,
            'target_module': self.target_module
        }