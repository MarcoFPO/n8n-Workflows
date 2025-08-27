"""
Data Processing Service - Event Publisher Interface
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Event Publisher Interface für Cross-Service Communication (Dependency Inversion Principle)
SOLID Principles: Interface Segregation, Dependency Inversion, Single Responsibility
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class EventPriority(Enum):
    """Event Priority Levels für Message Routing"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    CRITICAL = "critical"


class EventPublisherInterface(ABC):
    """
    Event Publisher Interface für Domain Event Broadcasting
    
    SOLID PRINCIPLES:
    - Interface Segregation: Spezifische Methods für Event Operations
    - Dependency Inversion: Application Layer hängt von Interface ab, nicht Implementation
    - Single Responsibility: Ausschließlich Event Publishing
    
    EVENT SYSTEM REQUIREMENTS:
    - Async Publishing: Non-blocking event dispatch
    - Reliability: At-least-once delivery garantiert
    - Cross-Service Integration: Event routing zu anderen Services
    - Monitoring: Event publishing statistics
    """
    
    @abstractmethod
    async def publish_event(self,
                           event_type: str,
                           event_data: Dict[str, Any],
                           priority: EventPriority = EventPriority.NORMAL,
                           correlation_id: Optional[str] = None) -> bool:
        """
        Publish Domain Event
        
        Args:
            event_type: Event type identifier (e.g., 'aggregation.calculation.completed')
            event_data: Event payload data
            priority: Event priority für routing
            correlation_id: Optional correlation ID für request tracing
            
        Returns:
            bool: Publishing success status
            
        Performance Target: <50ms publishing time
        """
        pass
    
    @abstractmethod
    async def publish_aggregation_calculation_requested(self,
                                                       timeframe: str,
                                                       symbols: List[str],
                                                       request_id: str,
                                                       force_refresh: bool = False) -> bool:
        """
        Publish Aggregation Calculation Requested Event
        
        Args:
            timeframe: Requested timeframe
            symbols: List of symbols to process
            request_id: Unique request identifier
            force_refresh: Whether to bypass cache
            
        Returns:
            bool: Success status
            
        Event Type: 'aggregation.calculation.requested'
        """
        pass
    
    @abstractmethod
    async def publish_aggregation_calculation_completed(self,
                                                       timeframe: str,
                                                       prediction_count: int,
                                                       processing_duration_ms: float,
                                                       average_quality_score: float,
                                                       success_rate: float,
                                                       request_id: Optional[str] = None) -> bool:
        """
        Publish Aggregation Calculation Completed Event
        
        Args:
            timeframe: Processed timeframe
            prediction_count: Number of predictions processed
            processing_duration_ms: Total processing time
            average_quality_score: Average quality score
            success_rate: Success rate (0.0-1.0)
            request_id: Optional request identifier
            
        Returns:
            bool: Success status
            
        Event Type: 'aggregation.calculation.completed'
        """
        pass
    
    @abstractmethod
    async def publish_aggregation_quality_validated(self,
                                                   symbol: str,
                                                   timeframe: str,
                                                   quality_score: float,
                                                   quality_category: str,
                                                   production_ready: bool,
                                                   quality_issues: Dict[str, str],
                                                   aggregation_id: str) -> bool:
        """
        Publish Aggregation Quality Validated Event
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            quality_score: Composite quality score
            quality_category: Quality classification
            production_ready: Whether meets production standards
            quality_issues: Identified quality issues
            aggregation_id: Aggregation identifier
            
        Returns:
            bool: Success status
            
        Event Type: 'aggregation.quality.validated'
        """
        pass
    
    @abstractmethod
    async def publish_aggregation_cache_updated(self,
                                              timeframe: str,
                                              cache_key: str,
                                              prediction_count: int,
                                              ttl_seconds: int,
                                              cache_size_bytes: Optional[int] = None) -> bool:
        """
        Publish Aggregation Cache Updated Event
        
        Args:
            timeframe: Cached timeframe
            cache_key: Cache key used
            prediction_count: Number of cached predictions
            ttl_seconds: Cache TTL
            cache_size_bytes: Optional cache entry size
            
        Returns:
            bool: Success status
            
        Event Type: 'aggregation.cache.updated'
        """
        pass
    
    @abstractmethod
    async def publish_performance_metrics(self,
                                        service_name: str,
                                        operation_name: str,
                                        duration_ms: float,
                                        success: bool,
                                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Publish Performance Metrics Event
        
        Args:
            service_name: Service identifier
            operation_name: Operation name
            duration_ms: Operation duration
            success: Success status
            metadata: Optional additional metrics
            
        Returns:
            bool: Success status
            
        Event Type: 'service.performance.metrics'
        """
        pass
    
    @abstractmethod
    async def publish_error_event(self,
                                 error_type: str,
                                 error_message: str,
                                 operation: str,
                                 severity: str,
                                 context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Publish Error Event für Monitoring
        
        Args:
            error_type: Type of error
            error_message: Error description
            operation: Operation that failed
            severity: Error severity ('low', 'medium', 'high', 'critical')
            context: Optional error context
            
        Returns:
            bool: Success status
            
        Event Type: 'service.error.occurred'
        """
        pass
    
    @abstractmethod
    async def publish_batch_events(self, 
                                  events: List[Dict[str, Any]],
                                  priority: EventPriority = EventPriority.NORMAL) -> Dict[str, bool]:
        """
        Publish Multiple Events in Batch für Performance
        
        Args:
            events: List of event dictionaries containing 'event_type' and 'event_data'
            priority: Priority für all events in batch
            
        Returns:
            Dict[str, bool]: Success status für each event by index
            
        Performance Target: <200ms für batch of 10 events
        """
        pass
    
    @abstractmethod
    async def get_event_publishing_statistics(self) -> Dict[str, Any]:
        """
        Get Event Publishing Performance Statistics
        
        Returns:
            Dict[str, Any]: Statistics containing:
                - total_events_published: int
                - successful_publications: int
                - failed_publications: int
                - average_publish_time_ms: float
                - events_by_type: Dict[str, int]
                - events_by_priority: Dict[str, int]
                - last_publish_timestamp: datetime
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Event Publisher Health Status
        
        Returns:
            Dict[str, Any]: Health status containing:
                - status: str ('healthy', 'degraded', 'unhealthy')
                - connectivity: bool
                - message_queue_depth: int
                - error_rate: float
                - latency_ms: float
        """
        pass
    
    @abstractmethod
    async def configure_event_routing(self, 
                                    event_type: str, 
                                    routing_config: Dict[str, Any]) -> bool:
        """
        Configure Event Routing für Specific Event Types
        
        Args:
            event_type: Event type to configure
            routing_config: Routing configuration
            
        Returns:
            bool: Configuration success status
            
        Use Case: Dynamic routing configuration für different environments
        """
        pass
    
    @abstractmethod
    async def get_event_delivery_status(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Delivery Status für Published Event
        
        Args:
            event_id: Event identifier
            
        Returns:
            Optional[Dict[str, Any]]: Delivery status information or None if not tracked
            
        Use Case: Monitoring event delivery across services
        """
        pass
    
    @abstractmethod
    async def retry_failed_events(self, max_retry_count: int = 3) -> Dict[str, Any]:
        """
        Retry Failed Event Publications
        
        Args:
            max_retry_count: Maximum number of retry attempts
            
        Returns:
            Dict[str, Any]: Retry operation results containing:
                - retried_events: int
                - successful_retries: int
                - permanent_failures: int
        """
        pass
    
    # SPECIALIZED EVENT METHODS für Common Patterns
    
    async def publish_aggregation_workflow_started(self, 
                                                  workflow_id: str,
                                                  timeframe: str,
                                                  total_symbols: int) -> bool:
        """Helper für Workflow Started Event"""
        return await self.publish_event(
            event_type='aggregation.workflow.started',
            event_data={
                'workflow_id': workflow_id,
                'timeframe': timeframe,
                'total_symbols': total_symbols,
                'started_at': datetime.now().isoformat()
            },
            priority=EventPriority.NORMAL
        )
    
    async def publish_aggregation_workflow_completed(self,
                                                   workflow_id: str,
                                                   timeframe: str,
                                                   successful_aggregations: int,
                                                   failed_aggregations: int,
                                                   total_duration_ms: float) -> bool:
        """Helper für Workflow Completed Event"""
        return await self.publish_event(
            event_type='aggregation.workflow.completed',
            event_data={
                'workflow_id': workflow_id,
                'timeframe': timeframe,
                'successful_aggregations': successful_aggregations,
                'failed_aggregations': failed_aggregations,
                'success_rate': successful_aggregations / (successful_aggregations + failed_aggregations),
                'total_duration_ms': total_duration_ms,
                'completed_at': datetime.now().isoformat()
            },
            priority=EventPriority.HIGH
        )