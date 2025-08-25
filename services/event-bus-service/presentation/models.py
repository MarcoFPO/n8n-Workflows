"""
Event-Bus Service Presentation Models
Clean Architecture - Request/Response Models für Event-Bus API

CLEAN ARCHITECTURE: Presentation Layer
- Request Models für Event Publishing, Subscription, Queries
- Response Models für API Responses
- Validation und Serialization

Code-Qualität: HÖCHSTE PRIORITÄT
Autor: Claude Code - Presentation Models Specialist  
Datum: 24. August 2025
Version: 7.0.0
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


# =============================================================================
# EVENT TYPE DEFINITIONS
# =============================================================================

class EventTypeEnum(str, Enum):
    """
    Domain Event Types für aktienanalyse-ökosystem
    
    CLEAN ARCHITECTURE: Domain Event Definitions
    """
    # Analysis Events
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_STARTED = "analysis.started" 
    ANALYSIS_FAILED = "analysis.failed"
    ANALYSIS_STATE_CHANGED = "analysis.state.changed"
    
    # Trading Events
    TRADING_SIGNAL_GENERATED = "trading.signal.generated"
    TRADING_ORDER_CREATED = "trading.order.created"
    TRADING_ORDER_EXECUTED = "trading.order.executed"
    TRADING_STATE_CHANGED = "trading.state.changed"
    
    # Data Events
    DATA_SYNCHRONIZED = "data.synchronized"
    DATA_UPDATED = "data.updated"
    DATA_VALIDATION_FAILED = "data.validation.failed"
    
    # System Events
    SYSTEM_ALERT_RAISED = "system.alert.raised"
    SYSTEM_HEALTH_CHANGED = "system.health.changed"
    SYSTEM_SERVICE_STARTED = "system.service.started"
    SYSTEM_SERVICE_STOPPED = "system.service.stopped"
    
    # ML Events
    ML_MODEL_TRAINED = "ml.model.trained"
    ML_PREDICTION_GENERATED = "ml.prediction.generated"
    ML_MODEL_EVALUATION_COMPLETED = "ml.model.evaluation.completed"
    
    # SOLL-IST Tracking Events  
    SOLL_IST_CALCULATED = "soll_ist.calculated"
    SOLL_IST_UPDATED = "soll_ist.updated"
    SOLL_IST_PERFORMANCE_ANALYZED = "soll_ist.performance.analyzed"
    
    # Test Events
    SYSTEM_TEST_EVENT_FLOW = "system.test.event_flow"


class EventPriorityEnum(str, Enum):
    """Event Priority Levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# CORE EVENT MODELS
# =============================================================================

class EventMessage(BaseModel):
    """
    Core Event Message Model
    
    CLEAN ARCHITECTURE: Domain Event Representation
    """
    event_type: EventTypeEnum = Field(..., description="Type of the event")
    event_id: Optional[str] = Field(None, description="Unique event identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for event tracing")
    source: str = Field(..., description="Source service that generated the event")
    timestamp: Optional[datetime] = Field(None, description="Event generation timestamp")
    
    event_data: Dict[str, Any] = Field(..., description="Event payload data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event metadata")
    
    priority: EventPriorityEnum = Field(EventPriorityEnum.NORMAL, description="Event priority level")
    ttl: Optional[int] = Field(None, description="Time-to-live in seconds")
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "event_type": "analysis.completed",
                "source": "intelligent-core-service",
                "event_data": {
                    "symbol": "AAPL",
                    "analysis_result": "BUY",
                    "confidence": 0.85
                },
                "metadata": {
                    "model_version": "v2.1.0",
                    "processing_time_ms": 1250
                },
                "priority": "high"
            }
        }


# =============================================================================
# REQUEST MODELS
# =============================================================================

class EventPublishRequest(BaseModel):
    """
    Event Publishing Request Model
    
    CLEAN ARCHITECTURE: Presentation Layer Request
    """
    event_type: EventTypeEnum = Field(..., description="Type of event to publish")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    source: str = Field(..., description="Source service publishing the event")
    
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    priority: EventPriorityEnum = Field(EventPriorityEnum.NORMAL, description="Event priority")
    
    # Event-Bus specific options
    persist_to_store: bool = Field(True, description="Whether to persist event to PostgreSQL Event Store")
    broadcast_to_all: bool = Field(True, description="Whether to broadcast to all subscribers")
    target_services: Optional[List[str]] = Field(None, description="Specific target services (if not broadcast)")
    
    @validator('event_data')
    def validate_event_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError('event_data must be a dictionary')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "trading.signal.generated",
                "source": "intelligent-core-service",
                "event_data": {
                    "symbol": "TSLA",
                    "signal": "SELL",
                    "confidence": 0.92,
                    "target_price": 185.50
                },
                "priority": "high",
                "persist_to_store": True,
                "broadcast_to_all": True
            }
        }


class EventSubscribeRequest(BaseModel):
    """
    Event Subscription Request Model
    
    CLEAN ARCHITECTURE: Presentation Layer Request
    """
    service_name: str = Field(..., description="Name of subscribing service")
    event_types: List[EventTypeEnum] = Field(..., description="Event types to subscribe to")
    callback_url: Optional[str] = Field(None, description="Webhook URL for event delivery")
    
    # Subscription options
    filter_criteria: Optional[Dict[str, Any]] = Field(None, description="Event filtering criteria")
    priority_threshold: EventPriorityEnum = Field(EventPriorityEnum.LOW, description="Minimum priority level")
    max_retry_attempts: int = Field(3, description="Maximum retry attempts for failed deliveries")
    
    class Config:
        schema_extra = {
            "example": {
                "service_name": "frontend-service",
                "event_types": ["analysis.completed", "trading.signal.generated"],
                "callback_url": "http://localhost:8000/api/v1/events/receive",
                "priority_threshold": "normal"
            }
        }


class EventQueryRequest(BaseModel):
    """
    Event Store Query Request Model
    
    CLEAN ARCHITECTURE: Presentation Layer Request
    """
    event_types: Optional[List[EventTypeEnum]] = Field(None, description="Filter by event types")
    sources: Optional[List[str]] = Field(None, description="Filter by source services")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    
    # Time range filters
    start_time: Optional[datetime] = Field(None, description="Start time for query range")
    end_time: Optional[datetime] = Field(None, description="End time for query range")
    
    # Result options
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
    order_by: str = Field("timestamp", description="Field to order results by")
    order_desc: bool = Field(True, description="Descending order")
    
    # Additional filters
    priority: Optional[EventPriorityEnum] = Field(None, description="Filter by priority level")
    metadata_filters: Optional[Dict[str, Any]] = Field(None, description="Additional metadata filters")
    
    class Config:
        schema_extra = {
            "example": {
                "event_types": ["analysis.completed", "trading.order.executed"],
                "sources": ["intelligent-core-service", "broker-gateway-service"],
                "start_time": "2025-08-24T00:00:00Z",
                "end_time": "2025-08-24T23:59:59Z",
                "limit": 50,
                "priority": "high"
            }
        }


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class EventPublishResponse(BaseModel):
    """
    Event Publishing Response Model
    
    CLEAN ARCHITECTURE: Presentation Layer Response
    """
    success: bool = Field(..., description="Whether event was published successfully")
    event_id: str = Field(..., description="Generated unique event ID")
    correlation_id: Optional[str] = Field(None, description="Event correlation ID")
    
    # Publishing results
    published_to_redis: bool = Field(..., description="Successfully published to Redis")
    persisted_to_store: bool = Field(..., description="Successfully persisted to Event Store")
    delivered_to_services: int = Field(..., description="Number of services that received the event")
    
    # Metadata
    timestamp: datetime = Field(..., description="Publishing timestamp")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "event_id": "evt_01J6ABCD1234567890EFGH",
                "correlation_id": "corr_01J6ABCD1234567890WXYZ",
                "published_to_redis": True,
                "persisted_to_store": True,
                "delivered_to_services": 3,
                "timestamp": "2025-08-24T12:30:45.123Z",
                "processing_time_ms": 45.2
            }
        }


class EventQueryResponse(BaseModel):
    """
    Event Store Query Response Model
    
    CLEAN ARCHITECTURE: Presentation Layer Response
    """
    success: bool = Field(..., description="Whether query was successful")
    events: List[EventMessage] = Field(..., description="Retrieved events")
    total_count: int = Field(..., description="Total number of matching events")
    
    # Pagination
    limit: int = Field(..., description="Query limit used")
    offset: int = Field(..., description="Query offset used")
    has_more: bool = Field(..., description="Whether more results are available")
    
    # Query metadata
    query_time_ms: Optional[float] = Field(None, description="Query execution time")
    timestamp: datetime = Field(..., description="Query execution timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "events": [
                    {
                        "event_type": "analysis.completed",
                        "source": "intelligent-core-service",
                        "event_data": {"symbol": "AAPL", "result": "BUY"},
                        "timestamp": "2025-08-24T12:30:00Z"
                    }
                ],
                "total_count": 150,
                "limit": 100,
                "offset": 0,
                "has_more": True,
                "query_time_ms": 23.5
            }
        }


class EventSubscriptionResponse(BaseModel):
    """
    Event Subscription Response Model
    
    CLEAN ARCHITECTURE: Presentation Layer Response
    """
    success: bool = Field(..., description="Whether subscription was successful")
    subscription_id: str = Field(..., description="Generated subscription ID")
    service_name: str = Field(..., description="Subscribing service name")
    subscribed_event_types: List[EventTypeEnum] = Field(..., description="Successfully subscribed event types")
    
    # Subscription details
    active_subscriptions: int = Field(..., description="Total active subscriptions for this service")
    callback_url: Optional[str] = Field(None, description="Configured callback URL")
    
    timestamp: datetime = Field(..., description="Subscription timestamp")
    
    class Config:
        use_enum_values = True
        schema_extra = {
            "example": {
                "success": True,
                "subscription_id": "sub_01J6ABCD1234567890KLMN",
                "service_name": "frontend-service",
                "subscribed_event_types": ["analysis.completed", "trading.signal.generated"],
                "active_subscriptions": 5,
                "callback_url": "http://localhost:8000/api/v1/events/receive",
                "timestamp": "2025-08-24T12:35:00Z"
            }
        }


# =============================================================================
# HEALTH CHECK AND MONITORING MODELS
# =============================================================================

class HealthCheckResponse(BaseModel):
    """
    Event-Bus Service Health Check Response
    
    CLEAN ARCHITECTURE: Infrastructure Health Monitoring
    """
    healthy: bool = Field(..., description="Overall service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Health check timestamp")
    
    # Component health status
    redis_connected: Optional[bool] = Field(None, description="Redis connection status")
    postgres_connected: Optional[bool] = Field(None, description="PostgreSQL connection status")
    event_publisher_ready: Optional[bool] = Field(None, description="Event publisher status")
    event_subscriber_ready: Optional[bool] = Field(None, description="Event subscriber status")
    
    # Performance metrics
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    class Config:
        schema_extra = {
            "example": {
                "healthy": True,
                "service": "event-bus-service",
                "version": "7.0.0",
                "timestamp": "2025-08-24T12:40:00Z",
                "redis_connected": True,
                "postgres_connected": True,
                "event_publisher_ready": True,
                "event_subscriber_ready": True,
                "uptime_seconds": 3600.5,
                "memory_usage_mb": 128.3
            }
        }


class ServiceMetricsResponse(BaseModel):
    """
    Event-Bus Service Metrics Response
    
    CLEAN ARCHITECTURE: Infrastructure Monitoring
    """
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Metrics collection timestamp")
    
    # Event metrics
    events_published_total: int = Field(..., description="Total events published")
    events_consumed_total: int = Field(..., description="Total events consumed")
    events_failed_total: int = Field(..., description="Total failed events")
    
    # Subscription metrics
    active_subscribers: int = Field(..., description="Number of active subscribers")
    total_subscriptions: int = Field(..., description="Total number of subscriptions")
    
    # Performance metrics
    avg_publish_time_ms: Optional[float] = Field(None, description="Average publishing time")
    avg_query_time_ms: Optional[float] = Field(None, description="Average query time")
    
    # Storage metrics
    event_store_size_mb: Optional[float] = Field(None, description="Event store size in MB")
    redis_memory_usage_mb: Optional[float] = Field(None, description="Redis memory usage in MB")
    
    class Config:
        schema_extra = {
            "example": {
                "service": "event-bus-service",
                "version": "7.0.0",
                "timestamp": "2025-08-24T12:45:00Z",
                "events_published_total": 15420,
                "events_consumed_total": 46260,
                "events_failed_total": 12,
                "active_subscribers": 8,
                "total_subscriptions": 24,
                "avg_publish_time_ms": 23.5,
                "avg_query_time_ms": 45.2,
                "event_store_size_mb": 512.8,
                "redis_memory_usage_mb": 64.2
            }
        }


# =============================================================================
# ERROR MODELS
# =============================================================================

class EventBusErrorResponse(BaseModel):
    """
    Standard Error Response Model
    
    CLEAN ARCHITECTURE: Error Handling
    """
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    service: str = Field(..., description="Service that generated the error")
    timestamp: str = Field(..., description="Error timestamp")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "EVENT_VALIDATION_FAILED",
                "message": "Event data validation failed",
                "details": {
                    "field": "event_data.symbol",
                    "reason": "Required field is missing"
                },
                "service": "event-bus-service",
                "timestamp": "2025-08-24T12:50:00Z",
                "correlation_id": "corr_01J6ABCD1234567890WXYZ"
            }
        }