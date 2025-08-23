"""
Redis Event Bus - Production-Ready Event-Driven Architecture
Implements scalable, persistent, and fault-tolerant event bus using Redis
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem') -> Import Manager

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import redis.asyncio as redis
    import structlog
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # PRODUCTION CODE MUST NEVER USE MOCK REDIS - INFRASTRUCTURE DEPENDENCY REQUIRED
    raise ImportError("CRITICAL: Redis is required for production event bus - mock Redis is forbidden in production deployment")


class EventPriority(Enum):
    """Event priority levels for processing order"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventDeliveryMode(Enum):
    """Event delivery modes"""
    FIRE_AND_FORGET = "fire_and_forget"     # Best effort, no acknowledgment
    AT_LEAST_ONCE = "at_least_once"         # Guaranteed delivery with possible duplicates
    EXACTLY_ONCE = "exactly_once"           # Guaranteed single delivery (slower)


@dataclass
class EventMetadata:
    """Event metadata for tracking and processing"""
    event_id: str
    timestamp: str
    source_service: str
    correlation_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    delivery_mode: EventDeliveryMode = EventDeliveryMode.FIRE_AND_FORGET
    retry_count: int = 0
    max_retries: int = 3
    ttl_seconds: int = 3600
    tags: List[str] = None


@dataclass  
class Event:
    """Event structure for Redis Event Bus"""
    event_type: str
    data: Dict[str, Any]
    metadata: EventMetadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            'event_type': self.event_type,
            'data': self.data,
            'metadata': asdict(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        metadata_dict = data.get('metadata', {})
        
        # Convert priority back to enum
        if 'priority' in metadata_dict:
            if isinstance(metadata_dict['priority'], str):
                metadata_dict['priority'] = EventPriority[metadata_dict['priority']]
            elif isinstance(metadata_dict['priority'], int):
                metadata_dict['priority'] = EventPriority(metadata_dict['priority'])
        
        # Convert delivery mode back to enum  
        if 'delivery_mode' in metadata_dict:
            if isinstance(metadata_dict['delivery_mode'], str):
                metadata_dict['delivery_mode'] = EventDeliveryMode(metadata_dict['delivery_mode'])
        
        metadata = EventMetadata(**metadata_dict)
        
        return cls(
            event_type=data['event_type'],
            data=data['data'],
            metadata=metadata
        )


class RedisEventBusConfig:
    """Configuration for Redis Event Bus"""
    
    def __init__(self):
        # Redis Connection
        self.redis_url = "redis://localhost:6379/0"
        self.connection_pool_size = 10
        self.connection_timeout = 5
        self.socket_keepalive = True
        
        # Event Processing
        self.max_retries = 3
        self.retry_delay_base = 1.0  # seconds
        self.retry_delay_max = 60.0  # seconds
        self.batch_size = 100
        self.processing_timeout = 30  # seconds
        
        # Performance
        self.enable_compression = True
        self.max_event_size = 1024 * 1024  # 1MB
        self.connection_pool_max = 20
        self.subscriber_buffer_size = 1000
        
        # Persistence
        self.enable_persistence = True
        self.persistence_ttl = 86400  # 24 hours
        self.dead_letter_ttl = 604800  # 7 days
        
        # Monitoring
        self.enable_metrics = True
        self.metrics_interval = 60  # seconds
        self.health_check_interval = 30  # seconds
        
        # Circuit Breaker
        self.circuit_breaker_enabled = True
        self.circuit_breaker_failure_threshold = 10
        self.circuit_breaker_timeout = 60  # seconds


class RedisEventBus:
    """Redis-based Event Bus for production workloads"""
    
    def __init__(self, config: RedisEventBusConfig = None, service_name: str = "unknown"):
        self.config = config or RedisEventBusConfig()
        self.service_name = service_name
        self.logger = structlog.get_logger()
        
        # Redis connections
        self.redis_client = None
        self.redis_subscriber = None
        
        # Event handling
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.running = False
        self.subscriber_tasks: List[asyncio.Task] = []
        
        # Metrics and monitoring
        self.metrics = {
            'events_published': 0,
            'events_received': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handlers_registered': 0,
            'last_heartbeat': None,
            'uptime_start': datetime.now()
        }
        
        # Circuit breaker state
        self.circuit_breaker_state = {
            'failures': 0,
            'last_failure': None,
            'state': 'closed'  # closed, open, half_open
        }
        
        # Subscription management
        self.active_subscriptions: Set[str] = set()
        self.subscription_handlers: Dict[str, List[Callable]] = {}
        
    async def initialize(self) -> bool:
        """Initialize Redis Event Bus"""
        try:
            # Create Redis connections
            self.redis_client = redis.from_url(
                self.config.redis_url,
                max_connections=self.config.connection_pool_max,
                socket_keepalive=self.config.socket_keepalive,
                socket_timeout=self.config.connection_timeout,
                decode_responses=False  # We handle encoding/decoding manually
            )
            
            self.redis_subscriber = redis.from_url(
                self.config.redis_url,
                max_connections=self.config.connection_pool_max
            )
            
            # Test connections
            await self.redis_client.ping()
            await self.redis_subscriber.ping()
            
            # Start background tasks
            if self.config.enable_metrics:
                asyncio.create_task(self._metrics_collector())
            
            asyncio.create_task(self._health_checker())
            
            self.running = True
            self.metrics['last_heartbeat'] = datetime.now()
            
            self.logger.info("Redis Event Bus initialized successfully",
                           service=self.service_name,
                           redis_url=self.config.redis_url)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Redis Event Bus",
                            error=str(e),
                            service=self.service_name)
            return False
    
    async def shutdown(self):
        """Shutdown Redis Event Bus gracefully"""
        try:
            self.running = False
            
            # Cancel all subscriber tasks
            for task in self.subscriber_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close Redis connections
            if self.redis_client:
                await self.redis_client.close()
            if self.redis_subscriber:
                await self.redis_subscriber.close()
            
            self.logger.info("Redis Event Bus shutdown completed",
                           service=self.service_name)
            
        except Exception as e:
            self.logger.error("Error during Redis Event Bus shutdown",
                            error=str(e))
    
    async def publish(self, event: Event) -> bool:
        """Publish event to Redis"""
        try:
            # Circuit breaker check
            if not await self._circuit_breaker_check():
                self.logger.warning("Circuit breaker open, dropping event",
                                  event_type=event.event_type)
                return False
            
            # Validate event
            if not await self._validate_event(event):
                return False
            
            # Serialize event
            serialized_event = await self._serialize_event(event)
            if not serialized_event:
                return False
            
            # Determine channel based on event type and priority
            channel = await self._get_channel_name(event)
            
            # Publish to Redis
            result = await self.redis_client.publish(channel, serialized_event)
            
            if result > 0:
                self.metrics['events_published'] += 1
                
                # Store for persistence if enabled
                if self.config.enable_persistence:
                    await self._persist_event(event)
                
                self.logger.debug("Event published successfully",
                                event_id=event.metadata.event_id,
                                event_type=event.event_type,
                                channel=channel,
                                subscribers=result)
                
                # Reset circuit breaker on success
                await self._circuit_breaker_success()
                
                return True
            else:
                self.logger.warning("No subscribers for event",
                                  event_type=event.event_type,
                                  channel=channel)
                return False
                
        except Exception as e:
            await self._circuit_breaker_failure()
            self.metrics['events_failed'] += 1
            self.logger.error("Failed to publish event",
                            event_type=event.event_type,
                            error=str(e))
            return False
    
    async def subscribe(self, event_type: str, handler: Callable) -> bool:
        """Subscribe to events of specific type"""
        try:
            if event_type not in self.subscription_handlers:
                self.subscription_handlers[event_type] = []
                self.active_subscriptions.add(event_type)
                
                # Start subscriber task for this event type
                task = asyncio.create_task(self._event_subscriber(event_type))
                self.subscriber_tasks.append(task)
            
            self.subscription_handlers[event_type].append(handler)
            self.metrics['handlers_registered'] += 1
            
            self.logger.info("Event handler registered",
                           event_type=event_type,
                           service=self.service_name)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to subscribe to event",
                            event_type=event_type,
                            error=str(e))
            return False
    
    async def unsubscribe(self, event_type: str, handler: Callable = None) -> bool:
        """Unsubscribe from events"""
        try:
            if event_type not in self.subscription_handlers:
                return False
            
            if handler:
                # Remove specific handler
                if handler in self.subscription_handlers[event_type]:
                    self.subscription_handlers[event_type].remove(handler)
            else:
                # Remove all handlers
                self.subscription_handlers[event_type].clear()
            
            # If no handlers left, stop subscriber task
            if not self.subscription_handlers[event_type]:
                self.active_subscriptions.discard(event_type)
                # Cancel corresponding subscriber task
                for task in self.subscriber_tasks:
                    if not task.done():
                        task.cancel()
            
            self.logger.info("Event handler unsubscribed",
                           event_type=event_type,
                           service=self.service_name)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to unsubscribe from event",
                            event_type=event_type,
                            error=str(e))
            return False
    
    async def _event_subscriber(self, event_type: str):
        """Background task for subscribing to specific event type"""
        try:
            pubsub = self.redis_subscriber.pubsub()
            
            # Subscribe to all priority channels for this event type
            channels = [
                f"events:{event_type}:low",
                f"events:{event_type}:normal", 
                f"events:{event_type}:high",
                f"events:{event_type}:critical"
            ]
            
            await pubsub.subscribe(*channels)
            
            self.logger.info("Started event subscriber",
                           event_type=event_type,
                           channels=channels)
            
            async for message in pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    await self._handle_received_event(message, event_type)
            
        except asyncio.CancelledError:
            self.logger.info("Event subscriber cancelled",
                           event_type=event_type)
        except Exception as e:
            self.logger.error("Event subscriber error",
                            event_type=event_type,
                            error=str(e))
        finally:
            try:
                await pubsub.close()
            except:
                pass
    
    async def _handle_received_event(self, message: Dict[str, Any], event_type: str):
        """Handle received event message"""
        try:
            # Deserialize event
            event = await self._deserialize_event(message['data'])
            if not event:
                return
            
            self.metrics['events_received'] += 1
            
            # Get handlers for this event type
            handlers = self.subscription_handlers.get(event_type, [])
            if not handlers:
                self.logger.warning("No handlers for event type",
                                  event_type=event_type)
                return
            
            # Process event with all handlers
            for handler in handlers:
                try:
                    # Handle both sync and async handlers
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event.data)
                    else:
                        handler(event.data)
                    
                    self.metrics['events_processed'] += 1
                    
                except Exception as handler_error:
                    self.logger.error("Event handler failed",
                                    event_id=event.metadata.event_id,
                                    event_type=event_type,
                                    handler=str(handler),
                                    error=str(handler_error))
                    
                    # Handle retry logic if needed
                    await self._handle_event_retry(event, handler_error)
            
        except Exception as e:
            self.logger.error("Failed to handle received event",
                            event_type=event_type,
                            error=str(e))
    
    async def _validate_event(self, event: Event) -> bool:
        """Validate event before publishing"""
        try:
            # Check event size
            serialized_size = len(json.dumps(event.to_dict()).encode('utf-8'))
            if serialized_size > self.config.max_event_size:
                self.logger.error("Event too large",
                                event_id=event.metadata.event_id,
                                size=serialized_size,
                                max_size=self.config.max_event_size)
                return False
            
            # Validate required fields
            if not event.event_type or not event.metadata.event_id:
                self.logger.error("Invalid event structure",
                                event_type=event.event_type)
                return False
            
            return True
            
        except Exception as e:
            self.logger.error("Event validation failed",
                            error=str(e))
            return False
    
    async def _serialize_event(self, event: Event) -> Optional[bytes]:
        """Serialize event for Redis transmission"""
        try:
            event_dict = event.to_dict()
            
            # Convert enum values to strings for JSON serialization
            if 'priority' in event_dict['metadata']:
                event_dict['metadata']['priority'] = event_dict['metadata']['priority'].name
            if 'delivery_mode' in event_dict['metadata']:
                event_dict['metadata']['delivery_mode'] = event_dict['metadata']['delivery_mode'].value
            
            json_str = json.dumps(event_dict, default=str)
            
            # Optional compression
            if self.config.enable_compression and len(json_str) > 1024:
                # Simple compression could be added here if needed
                pass
            
            return json_str.encode('utf-8')
            
        except Exception as e:
            self.logger.error("Event serialization failed",
                            event_id=event.metadata.event_id,
                            error=str(e))
            return None
    
    async def _deserialize_event(self, data: bytes) -> Optional[Event]:
        """Deserialize event from Redis"""
        try:
            json_str = data.decode('utf-8')
            event_dict = json.loads(json_str)
            
            return Event.from_dict(event_dict)
            
        except Exception as e:
            self.logger.error("Event deserialization failed",
                            error=str(e))
            return None
    
    async def _get_channel_name(self, event: Event) -> str:
        """Get Redis channel name based on event type and priority"""
        priority_name = event.metadata.priority.name.lower()
        return f"events:{event.event_type}:{priority_name}"
    
    async def _persist_event(self, event: Event):
        """Persist event for recovery and replay"""
        try:
            if not self.config.enable_persistence:
                return
            
            key = f"event_store:{event.metadata.event_id}"
            serialized_event = await self._serialize_event(event)
            
            await self.redis_client.set(
                key, 
                serialized_event,
                ex=self.config.persistence_ttl
            )
            
        except Exception as e:
            self.logger.error("Event persistence failed",
                            event_id=event.metadata.event_id,
                            error=str(e))
    
    async def _handle_event_retry(self, event: Event, error: Exception):
        """Handle event retry logic"""
        try:
            if event.metadata.retry_count >= event.metadata.max_retries:
                # Send to dead letter queue
                await self._send_to_dead_letter(event, error)
                return
            
            # Increment retry count
            event.metadata.retry_count += 1
            
            # Calculate retry delay with exponential backoff
            delay = min(
                self.config.retry_delay_base * (2 ** event.metadata.retry_count),
                self.config.retry_delay_max
            )
            
            # Schedule retry
            await asyncio.sleep(delay)
            await self.publish(event)
            
        except Exception as e:
            self.logger.error("Event retry handling failed",
                            event_id=event.metadata.event_id,
                            error=str(e))
    
    async def _send_to_dead_letter(self, event: Event, error: Exception):
        """Send failed event to dead letter queue"""
        try:
            dead_letter_event = {
                'original_event': event.to_dict(),
                'failure_reason': str(error),
                'failed_at': datetime.now().isoformat(),
                'service': self.service_name
            }
            
            key = f"dead_letter:{event.metadata.event_id}"
            await self.redis_client.set(
                key,
                json.dumps(dead_letter_event),
                ex=self.config.dead_letter_ttl
            )
            
            self.logger.warning("Event sent to dead letter queue",
                              event_id=event.metadata.event_id,
                              error=str(error))
            
        except Exception as e:
            self.logger.error("Failed to send event to dead letter queue",
                            event_id=event.metadata.event_id,
                            error=str(e))
    
    async def _circuit_breaker_check(self) -> bool:
        """Check circuit breaker state"""
        if not self.config.circuit_breaker_enabled:
            return True
        
        current_time = time.time()
        
        if self.circuit_breaker_state['state'] == 'open':
            # Check if we should transition to half-open
            if (self.circuit_breaker_state['last_failure'] and 
                current_time - self.circuit_breaker_state['last_failure'] > self.config.circuit_breaker_timeout):
                self.circuit_breaker_state['state'] = 'half_open'
                self.logger.info("Circuit breaker transitioning to half-open")
                return True
            return False
        
        return True
    
    async def _circuit_breaker_success(self):
        """Record successful operation for circuit breaker"""
        if self.circuit_breaker_state['state'] == 'half_open':
            self.circuit_breaker_state['state'] = 'closed'
            self.circuit_breaker_state['failures'] = 0
            self.logger.info("Circuit breaker closed after successful operation")
    
    async def _circuit_breaker_failure(self):
        """Record failed operation for circuit breaker"""
        if not self.config.circuit_breaker_enabled:
            return
        
        self.circuit_breaker_state['failures'] += 1
        self.circuit_breaker_state['last_failure'] = time.time()
        
        if self.circuit_breaker_state['failures'] >= self.config.circuit_breaker_failure_threshold:
            self.circuit_breaker_state['state'] = 'open'
            self.logger.warning("Circuit breaker opened due to failures",
                              failures=self.circuit_breaker_state['failures'])
    
    async def _metrics_collector(self):
        """Collect and publish metrics periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.config.metrics_interval)
                
                # Store metrics in Redis for monitoring
                metrics_key = f"metrics:{self.service_name}"
                metrics_data = {
                    **self.metrics,
                    'timestamp': datetime.now().isoformat(),
                    'circuit_breaker_state': self.circuit_breaker_state['state']
                }
                
                await self.redis_client.hset(metrics_key, mapping={
                    k: json.dumps(v) if not isinstance(v, (str, int, float)) else str(v)
                    for k, v in metrics_data.items()
                })
                
                # Set expiration
                await self.redis_client.expire(metrics_key, self.config.metrics_interval * 2)
                
            except Exception as e:
                self.logger.error("Metrics collection failed", error=str(e))
    
    async def _health_checker(self):
        """Periodic health check"""
        while self.running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Test Redis connection
                await self.redis_client.ping()
                self.metrics['last_heartbeat'] = datetime.now()
                
                # Health check event
                health_event = Event(
                    event_type='system.health.heartbeat',
                    data={
                        'service': self.service_name,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'healthy',
                        'metrics': self.metrics.copy()
                    },
                    metadata=EventMetadata(
                        event_id=f"health_{uuid.uuid4().hex[:8]}",
                        timestamp=datetime.now().isoformat(),
                        source_service=self.service_name,
                        priority=EventPriority.LOW
                    )
                )
                
                await self.publish(health_event)
                
            except Exception as e:
                self.logger.error("Health check failed", error=str(e))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            **self.metrics.copy(),
            'active_subscriptions': len(self.active_subscriptions),
            'circuit_breaker_state': self.circuit_breaker_state.copy(),
            'uptime_seconds': (datetime.now() - self.metrics['uptime_start']).total_seconds()
        }
    
    async def create_event(self, event_type: str, data: Dict[str, Any], 
                          priority: EventPriority = EventPriority.NORMAL,
                          correlation_id: str = None) -> Event:
        """Helper method to create properly formatted events"""
        
        return Event(
            event_type=event_type,
            data=data,
            metadata=EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                source_service=self.service_name,
                correlation_id=correlation_id,
                priority=priority
            )
        )