"""
Event Controller - Presentation Layer
Clean Architecture - Event API Controller Implementation

CLEAN ARCHITECTURE: Presentation Layer
HTTP API Controller für Event Publishing und Subscription

Code-Qualität: HÖCHSTE PRIORITÄT  
Autor: Claude Code - Controller Implementation Specialist
Datum: 24. August 2025
Version: 7.0.0
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from application.interfaces.event_publisher import IEventPublisher
from application.interfaces.event_subscriber import IEventSubscriber
from application.use_cases.event_publishing import EventPublishingUseCase
from application.use_cases.event_subscription import EventSubscriptionUseCase
from infrastructure.services.event_service_registry import EventServiceRegistry

from presentation.models import (
    EventPublishRequest,
    EventPublishResponse,
    EventSubscribeRequest,  
    EventSubscriptionResponse,
    HealthCheckResponse,
    ServiceMetricsResponse
)


class EventController:
    """
    Event Controller - Presentation Layer
    
    CLEAN ARCHITECTURE: Presentation Layer Controller
    Handles HTTP requests für Event Publishing und Subscription
    """
    
    def __init__(
        self,
        event_publishing_use_case: EventPublishingUseCase,
        event_subscription_use_case: EventSubscriptionUseCase,
        event_publisher: IEventPublisher,
        event_subscriber: IEventSubscriber,
        service_registry: EventServiceRegistry
    ):
        self.event_publishing_use_case = event_publishing_use_case
        self.event_subscription_use_case = event_subscription_use_case
        self.event_publisher = event_publisher
        self.event_subscriber = event_subscriber
        self.service_registry = service_registry
        self.logger = logging.getLogger(__name__)
        
        # Controller metrics
        self._requests_handled = 0
        self._start_time = datetime.now()
    
    async def publish_event(self, request: EventPublishRequest) -> EventPublishResponse:
        """
        Handle event publishing request
        
        CLEAN ARCHITECTURE FLOW:
        Request -> Controller -> Use Case -> Infrastructure -> Response
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"📡 Publishing event: {request.event_type} from {request.source}")
            
            # Use case ausführen
            result = await self.event_publishing_use_case.execute(
                event_type=request.event_type.value,
                event_data=request.event_data,
                source=request.source,
                correlation_id=request.correlation_id,
                metadata=request.metadata,
                priority=request.priority.value,
                persist_to_store=request.persist_to_store,
                broadcast_to_all=request.broadcast_to_all,
                target_services=request.target_services
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._requests_handled += 1
            
            return EventPublishResponse(
                success=True,
                event_id=result["event_id"],
                correlation_id=result["correlation_id"],
                published_to_redis=result["published_to_redis"],
                persisted_to_store=result["persisted_to_store"],
                delivered_to_services=result["delivered_to_services"],
                timestamp=datetime.now(),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"❌ Event publishing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return EventPublishResponse(
                success=False,
                event_id="",
                published_to_redis=False,
                persisted_to_store=False,
                delivered_to_services=0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time
            )
    
    async def subscribe_to_events(self, request: EventSubscribeRequest) -> EventSubscriptionResponse:
        """
        Handle event subscription request
        
        CLEAN ARCHITECTURE FLOW:
        Request -> Controller -> Use Case -> Infrastructure -> Response
        """
        try:
            self.logger.info(f"📥 Setting up subscription for service: {request.service_name}")
            
            # Use case ausführen
            result = await self.event_subscription_use_case.execute(
                service_name=request.service_name,
                event_types=[et.value for et in request.event_types],
                callback_url=request.callback_url,
                filter_criteria=request.filter_criteria,
                priority_threshold=request.priority_threshold.value,
                max_retry_attempts=request.max_retry_attempts
            )
            
            self._requests_handled += 1
            
            return EventSubscriptionResponse(
                success=True,
                subscription_id=result["subscription_id"],
                service_name=request.service_name,
                subscribed_event_types=request.event_types,
                active_subscriptions=result["active_subscriptions"],
                callback_url=request.callback_url,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"❌ Event subscription failed: {e}")
            
            return EventSubscriptionResponse(
                success=False,
                subscription_id="",
                service_name=request.service_name,
                subscribed_event_types=[],
                active_subscriptions=0,
                timestamp=datetime.now()
            )
    
    async def health_check(self) -> HealthCheckResponse:
        """
        Comprehensive health check
        
        CLEAN ARCHITECTURE: Infrastructure Health Monitoring
        """
        try:
            # Check all components
            redis_healthy = await self.event_publisher.is_healthy()
            subscriber_healthy = await self.event_subscriber.is_healthy() if self.event_subscriber else False
            
            # Overall health
            overall_healthy = redis_healthy and subscriber_healthy
            
            # Uptime calculation
            uptime = (datetime.now() - self._start_time).total_seconds()
            
            return HealthCheckResponse(
                healthy=overall_healthy,
                service="event-bus-service",
                version="7.0.0",
                timestamp=datetime.now().isoformat(),
                redis_connected=redis_healthy,
                postgres_connected=True,  # TODO: Add actual PostgreSQL health check
                event_publisher_ready=redis_healthy,
                event_subscriber_ready=subscriber_healthy,
                uptime_seconds=uptime,
                memory_usage_mb=None  # TODO: Add memory monitoring
            )
            
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            
            return HealthCheckResponse(
                healthy=False,
                service="event-bus-service", 
                version="7.0.0",
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def get_service_metrics(self) -> ServiceMetricsResponse:
        """
        Get comprehensive service metrics
        
        CLEAN ARCHITECTURE: Infrastructure Monitoring
        """
        try:
            # Get publisher metrics
            publisher_metrics = await self.event_publisher.get_metrics()
            
            # Get subscriber metrics if available
            subscriber_metrics = {}
            if self.event_subscriber:
                subscriber_metrics = await self.event_subscriber.get_metrics()
            
            # Get service registry metrics
            connected_services = await self.event_publisher.get_connected_services()
            
            return ServiceMetricsResponse(
                service="event-bus-service",
                version="7.0.0",
                timestamp=datetime.now().isoformat(),
                
                # Event metrics
                events_published_total=publisher_metrics.get("events_published_total", 0),
                events_consumed_total=subscriber_metrics.get("events_consumed_total", 0),
                events_failed_total=publisher_metrics.get("events_failed_total", 0),
                
                # Subscription metrics
                active_subscribers=len(connected_services),
                total_subscriptions=subscriber_metrics.get("total_subscriptions", 0),
                
                # Performance metrics
                avg_publish_time_ms=None,  # TODO: Implement average calculation
                avg_query_time_ms=None,    # TODO: Implement average calculation
                
                # Storage metrics
                event_store_size_mb=None,  # TODO: Add PostgreSQL size query
                redis_memory_usage_mb=None # TODO: Add Redis memory query
            )
            
        except Exception as e:
            self.logger.error(f"❌ Metrics collection failed: {e}")
            raise