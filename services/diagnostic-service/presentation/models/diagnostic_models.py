#!/usr/bin/env python3
"""
Diagnostic Service - Pydantic Models
CLEAN ARCHITECTURE - PRESENTATION LAYER

Request/Response DTOs für FastAPI endpoints
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class MonitoringActionEnum(str, Enum):
    """Monitoring action types"""
    START = "start"
    STOP = "stop"
    CLEAR = "clear"
    STATUS = "status"


class TestTypeEnum(str, Enum):
    """Diagnostic test types"""
    PING = "ping"
    MESSAGE = "message"
    COMMUNICATION = "communication"
    CUSTOM = "custom"


class AlertLevelEnum(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Request Models
class StartMonitoringRequest(BaseModel):
    """Request to start event monitoring"""
    event_types: List[str] = Field(
        ..., 
        description="List of event types to monitor",
        min_items=1
    )
    include_error_detection: bool = Field(
        True,
        description="Whether to enable automatic error detection"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "event_types": ["analysis", "portfolio", "trading", "intelligence"],
                "include_error_detection": True
            }
        }


class CreateTestRequest(BaseModel):
    """Request to create diagnostic test"""
    test_name: str = Field(..., description="Name of the test")
    test_type: TestTypeEnum = Field(..., description="Type of diagnostic test")
    target_module: str = Field(..., description="Target module to test")
    test_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Custom test data"
    )
    
    @validator('test_name')
    def validate_test_name(cls, v):
        if not v.strip():
            raise ValueError('Test name cannot be empty')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "test_name": "Analysis Module Connectivity Test",
                "test_type": "ping",
                "target_module": "analysis_module",
                "test_data": {"timeout_seconds": 10}
            }
        }


class SendTestMessageRequest(BaseModel):
    """Request to send test message"""
    target_module: str = Field(..., description="Target module for test message")
    message_type: str = Field(..., description="Type of test message")
    custom_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom message data"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "target_module": "analysis_module",
                "message_type": "analysis_test",
                "custom_data": {
                    "symbol": "AAPL",
                    "test_mode": True
                }
            }
        }


class EventFilterRequest(BaseModel):
    """Request to filter events"""
    event_type: Optional[str] = Field(None, description="Filter by event type")
    source: Optional[str] = Field(None, description="Filter by source")
    error_only: Optional[bool] = Field(False, description="Show only error events")
    max_age_seconds: Optional[int] = Field(None, description="Maximum event age in seconds")
    limit: int = Field(50, description="Maximum number of events to return", ge=1, le=1000)


# Response Models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Whether operation was successful")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    message: Optional[str] = Field(None, description="Response message")


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(False, description="Operation failed")
    error: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "timestamp": "2025-08-25T10:30:00.000Z",
                "message": "Operation failed",
                "error": "Target module not found",
                "error_code": "MODULE_NOT_FOUND"
            }
        }


class MonitoringStatusResponse(BaseResponse):
    """Monitoring status response"""
    monitoring_active: bool = Field(..., description="Whether monitoring is active")
    subscribed_event_types: List[str] = Field(..., description="Currently monitored event types")
    events_captured: int = Field(..., description="Total events captured")
    error_events: int = Field(..., description="Number of error events")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2025-08-25T10:30:00.000Z",
                "monitoring_active": True,
                "subscribed_event_types": ["analysis", "portfolio", "trading"],
                "events_captured": 1542,
                "error_events": 23
            }
        }


class EventStatisticsResponse(BaseResponse):
    """Event statistics response"""
    total_events: int = Field(..., description="Total events captured")
    error_events: int = Field(..., description="Number of error events")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    event_type_counts: Dict[str, int] = Field(..., description="Events by type")
    source_counts: Dict[str, int] = Field(..., description="Events by source")
    recent_events_last_hour: int = Field(..., description="Events in last hour")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timestamp": "2025-08-25T10:30:00.000Z",
                "total_events": 1542,
                "error_events": 23,
                "error_rate_percent": 1.49,
                "event_type_counts": {
                    "analysis": 850,
                    "portfolio": 412,
                    "trading": 280
                },
                "source_counts": {
                    "analysis_module": 850,
                    "portfolio_module": 412,
                    "trading_module": 280
                },
                "recent_events_last_hour": 45
            }
        }


class CapturedEventModel(BaseModel):
    """Captured event model"""
    capture_id: str = Field(..., description="Unique capture ID")
    event_type: str = Field(..., description="Event type")
    source: str = Field(..., description="Event source")
    stream_id: Optional[str] = Field(None, description="Event stream ID")
    captured_at: datetime = Field(..., description="Capture timestamp")
    error_detected: bool = Field(..., description="Whether error was detected")
    error_indicators: List[str] = Field(default_factory=list, description="Error indicators found")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "capture_id": "cap_12345",
                "event_type": "analysis.completed",
                "source": "analysis_module",
                "stream_id": "analysis-AAPL-123",
                "captured_at": "2025-08-25T10:30:00.000Z",
                "error_detected": False,
                "error_indicators": [],
                "processing_time_ms": 12.5
            }
        }


class EventsResponse(BaseResponse):
    """Events list response"""
    events: List[CapturedEventModel] = Field(..., description="List of captured events")
    count: int = Field(..., description="Number of events returned")
    total_captured: int = Field(..., description="Total events captured")
    filter_applied: bool = Field(..., description="Whether filters were applied")


class TestResultModel(BaseModel):
    """Test result model"""
    test_id: str = Field(..., description="Test ID")
    test_name: str = Field(..., description="Test name")
    status: str = Field(..., description="Test status")
    execution_time_ms: Optional[float] = Field(None, description="Execution time")
    retry_count: int = Field(..., description="Number of retries")
    success: bool = Field(..., description="Whether test was successful")
    completed: bool = Field(..., description="Whether test is completed")
    
    class Config:
        schema_extra = {
            "example": {
                "test_id": "test_12345",
                "test_name": "Analysis Module Ping Test",
                "status": "success",
                "execution_time_ms": 45.2,
                "retry_count": 0,
                "success": True,
                "completed": True
            }
        }


class CreateTestResponse(BaseResponse):
    """Create test response"""
    test_id: str = Field(..., description="Created test ID")
    test_result: TestResultModel = Field(..., description="Test execution result")


class TestResultsResponse(BaseResponse):
    """Test results list response"""
    tests: List[TestResultModel] = Field(..., description="List of test results")


class ModuleCommunicationResponse(BaseResponse):
    """Module communication test response"""
    communication_test_id: str = Field(..., description="Communication test ID")
    ping_successful: bool = Field(..., description="Whether ping was successful")
    target_module: str = Field(..., description="Target module name")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")


class SendMessageResponse(BaseResponse):
    """Send test message response"""
    test_id: str = Field(..., description="Test tracking ID")
    correlation_id: str = Field(..., description="Message correlation ID")
    message_sent: bool = Field(..., description="Whether message was sent successfully")


class HealthSnapshotModel(BaseModel):
    """Health snapshot model"""
    status: str = Field(..., description="Overall health status")
    health_score: float = Field(..., description="Health score (0-100)")
    error_rate_percent: float = Field(..., description="Error rate percentage")
    total_events: int = Field(..., description="Total events monitored")
    active_sources_count: int = Field(..., description="Number of active event sources")
    alert_count: int = Field(..., description="Number of active alerts")
    timestamp: datetime = Field(..., description="Snapshot timestamp")


class SystemHealthResponse(BaseResponse):
    """System health response"""
    health_snapshot: HealthSnapshotModel = Field(..., description="Current health snapshot")
    detailed_metrics: Optional[Dict[str, Any]] = Field(None, description="Detailed health metrics")


class HealthTrendPoint(BaseModel):
    """Health trend data point"""
    timestamp: datetime = Field(..., description="Data point timestamp")
    health_score: float = Field(..., description="Health score at this time")
    status: str = Field(..., description="Health status at this time")
    error_count: int = Field(..., description="Error count at this time")
    active_sources_count: int = Field(..., description="Active sources at this time")


class HealthTrendResponse(BaseResponse):
    """Health trend response"""
    trend: List[HealthTrendPoint] = Field(..., description="Health trend data points")
    analysis: Dict[str, Any] = Field(..., description="Trend analysis")
    timeframe_hours: int = Field(..., description="Timeframe in hours")


class MaintenanceResponse(BaseResponse):
    """Maintenance operation response"""
    cleanup_results: Dict[str, int] = Field(..., description="Cleanup operation results")
    total_items_removed: int = Field(..., description="Total items cleaned up")


class ContainerStatusResponse(BaseResponse):
    """Container status response"""
    initialized: bool = Field(..., description="Whether container is initialized")
    total_services: int = Field(..., description="Total number of services")
    started_services: List[str] = Field(..., description="Successfully started services")
    failed_services: List[str] = Field(..., description="Failed services")
    health_status: Dict[str, Any] = Field(..., description="Service health status")
    service_names: List[str] = Field(..., description="All service names")


# Utility Models
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, description="Page number (1-based)", ge=1)
    page_size: int = Field(50, description="Items per page", ge=1, le=1000)
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size


class TimeRangeParams(BaseModel):
    """Time range parameters"""
    from_time: Optional[datetime] = Field(None, description="Start time (ISO format)")
    to_time: Optional[datetime] = Field(None, description="End time (ISO format)")
    hours: Optional[int] = Field(None, description="Hours from now (alternative to from_time)")
    
    @validator('hours')
    def validate_hours(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Hours must be positive')
        return v


class ServiceHealthModel(BaseModel):
    """Individual service health model"""
    service_name: str = Field(..., description="Service name")
    is_healthy: bool = Field(..., description="Whether service is healthy")
    service_type: str = Field(..., description="Type of service")
    last_check: datetime = Field(..., description="Last health check time")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")


class DetailedHealthResponse(BaseResponse):
    """Detailed health report response"""
    container_healthy: bool = Field(..., description="Overall container health")
    service_health: Dict[str, ServiceHealthModel] = Field(..., description="Per-service health status")
    unhealthy_services: List[str] = Field(default_factory=list, description="List of unhealthy services")
    health_summary: Dict[str, Any] = Field(..., description="Health summary statistics")