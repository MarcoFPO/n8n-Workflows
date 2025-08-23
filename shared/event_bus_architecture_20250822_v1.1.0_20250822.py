#!/usr/bin/env python3
"""
Event Bus Architecture v1.0.0 - Clean Architecture Event System
Trennt Mixed Concerns im Event-Bus und implementiert SOLID Principles

Code-Qualität: HÖCHSTE PRIORITÄT
- Single Responsibility: Separate Router/Subscriber/Publisher
- Open/Closed: Erweiterbar für neue Event-Types
- Liskov Substitution: Interface-based Event Handling
- Interface Segregation: Separate Event Concerns
- Dependency Inversion: Abstract Event Bus Interface
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from uuid import uuid4, UUID

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()

# Service Discovery Integration
from shared.config_manager_v1_0_0_20250822 import get_service_discovery, ServiceType

logger = logging.getLogger(__name__)

# EVENT SYSTEM TYPES

class EventPriority(Enum):
    """Event Priority Levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class EventStatus(Enum):
    """Event Processing Status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class EventMetadata:
    """Event Metadata"""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    source_service: str = ""
    target_services: List[str] = field(default_factory=list)
    priority: EventPriority = EventPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30

@dataclass
class Event:
    """Base Event Structure"""
    event_type: str
    data: Dict[str, Any]
    metadata: EventMetadata = field(default_factory=EventMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "metadata": {
                "event_id": self.metadata.event_id,
                "correlation_id": self.metadata.correlation_id,
                "causation_id": self.metadata.causation_id,
                "timestamp": self.metadata.timestamp.isoformat(),
                "source_service": self.metadata.source_service,
                "target_services": self.metadata.target_services,
                "priority": self.metadata.priority.value,
                "retry_count": self.metadata.retry_count,
                "max_retries": self.metadata.max_retries,
                "timeout_seconds": self.metadata.timeout_seconds
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        metadata_dict = data.get("metadata", {})
        metadata = EventMetadata(
            event_id=metadata_dict.get("event_id", str(uuid4())),
            correlation_id=metadata_dict.get("correlation_id"),
            causation_id=metadata_dict.get("causation_id"),
            timestamp=datetime.fromisoformat(metadata_dict.get("timestamp", datetime.now().isoformat())),
            source_service=metadata_dict.get("source_service", ""),
            target_services=metadata_dict.get("target_services", []),
            priority=EventPriority(metadata_dict.get("priority", EventPriority.NORMAL.value)),
            retry_count=metadata_dict.get("retry_count", 0),
            max_retries=metadata_dict.get("max_retries", 3),
            timeout_seconds=metadata_dict.get("timeout_seconds", 30)
        )
        
        return cls(
            event_type=data["event_type"],
            data=data["data"],
            metadata=metadata
        )

# INTERFACES - Interface Segregation Principle

class IEventPublisher(ABC):
    """Event Publisher Interface"""
    
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """Publish event"""
        pass

class IEventSubscriber(ABC):
    """Event Subscriber Interface"""
    
    @abstractmethod
    async def subscribe(self, event_type: str, handler: Callable[[Event], Any]) -> str:
        """Subscribe to event type"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        pass

class IEventRouter(ABC):
    """Event Router Interface"""
    
    @abstractmethod
    async def route_event(self, event: Event) -> List[str]:
        """Route event to appropriate handlers"""
        pass
    
    @abstractmethod
    def add_routing_rule(self, rule: 'RoutingRule') -> bool:
        """Add routing rule"""
        pass

class IEventStore(ABC):
    """Event Store Interface"""
    
    @abstractmethod
    async def store_event(self, event: Event) -> bool:
        """Store event"""
        pass
    
    @abstractmethod
    async def get_events(self, 
                        event_types: Optional[List[str]] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Event]:
        """Get events from store"""
        pass

# ROUTING SYSTEM

@dataclass
class RoutingRule:
    """Event Routing Rule"""
    rule_id: str
    event_type_pattern: str
    target_services: List[str]
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True

class EventRouter(IEventRouter):
    """
    Event Router - Single Responsibility
    Handles event routing logic only
    """
    
    def __init__(self):
        self.routing_rules: Dict[str, RoutingRule] = {}
        self.service_discovery = get_service_discovery()
        
    async def route_event(self, event: Event) -> List[str]:
        """Route event to appropriate services"""
        target_services = set()
        
        # Apply routing rules
        for rule in sorted(self.routing_rules.values(), key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue
                
            if self._matches_pattern(event.event_type, rule.event_type_pattern):
                if self._matches_conditions(event, rule.conditions):
                    target_services.update(rule.target_services)
        
        # Add explicitly targeted services
        if event.metadata.target_services:
            target_services.update(event.metadata.target_services)
        
        return list(target_services)
    
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add routing rule"""
        try:
            self.routing_rules[rule.rule_id] = rule
            logger.info(f"Routing rule added: {rule.rule_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add routing rule {rule.rule_id}: {e}")
            return False
    
    def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove routing rule"""
        try:
            if rule_id in self.routing_rules:
                del self.routing_rules[rule_id]
                logger.info(f"Routing rule removed: {rule_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove routing rule {rule_id}: {e}")
            return False
    
    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if event type matches pattern"""
        # Simple pattern matching (can be extended with regex)
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return event_type.startswith(pattern[:-1])
        return event_type == pattern
    
    def _matches_conditions(self, event: Event, conditions: Dict[str, Any]) -> bool:
        """Check if event matches additional conditions"""
        if not conditions:
            return True
        
        for key, expected_value in conditions.items():
            if key == "source_service":
                if event.metadata.source_service != expected_value:
                    return False
            elif key == "priority":
                if event.metadata.priority.value < expected_value:
                    return False
            elif key in event.data:
                if event.data[key] != expected_value:
                    return False
            else:
                return False
        
        return True

# SUBSCRIPTION SYSTEM

@dataclass
class Subscription:
    """Event Subscription"""
    subscription_id: str
    event_type: str
    handler: Callable[[Event], Any]
    service_name: str
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True

class EventSubscriptionManager(IEventSubscriber):
    """
    Event Subscription Manager - Single Responsibility
    Handles event subscriptions only
    """
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.event_handlers: Dict[str, List[str]] = {}  # event_type -> subscription_ids
        
    async def subscribe(self, event_type: str, handler: Callable[[Event], Any], service_name: str = "unknown") -> str:
        """Subscribe to event type"""
        try:
            subscription_id = str(uuid4())
            
            subscription = Subscription(
                subscription_id=subscription_id,
                event_type=event_type,
                handler=handler,
                service_name=service_name
            )
            
            self.subscriptions[subscription_id] = subscription
            
            # Add to event type mapping
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(subscription_id)
            
            logger.info(f"Subscription added: {subscription_id} for {event_type}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {event_type}: {e}")
            raise
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            if subscription_id not in self.subscriptions:
                return False
            
            subscription = self.subscriptions[subscription_id]
            
            # Remove from event type mapping
            if subscription.event_type in self.event_handlers:
                if subscription_id in self.event_handlers[subscription.event_type]:
                    self.event_handlers[subscription.event_type].remove(subscription_id)
                
                # Clean up empty event type mappings
                if not self.event_handlers[subscription.event_type]:
                    del self.event_handlers[subscription.event_type]
            
            # Remove subscription
            del self.subscriptions[subscription_id]
            
            logger.info(f"Subscription removed: {subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscription_id}: {e}")
            return False
    
    async def dispatch_event(self, event: Event) -> Dict[str, bool]:
        """Dispatch event to subscribers"""
        results = {}
        
        # Get subscriptions for this event type
        subscription_ids = self.event_handlers.get(event.event_type, [])
        
        for subscription_id in subscription_ids:
            if subscription_id not in self.subscriptions:
                continue
            
            subscription = self.subscriptions[subscription_id]
            if not subscription.active:
                continue
            
            try:
                # Call handler
                if asyncio.iscoroutinefunction(subscription.handler):
                    await subscription.handler(event)
                else:
                    subscription.handler(event)
                
                results[subscription_id] = True
                logger.debug(f"Event dispatched to {subscription_id}")
                
            except Exception as e:
                results[subscription_id] = False
                logger.error(f"Error dispatching event to {subscription_id}: {e}")
        
        return results
    
    def get_subscriptions_for_event_type(self, event_type: str) -> List[Subscription]:
        """Get all subscriptions for event type"""
        subscription_ids = self.event_handlers.get(event_type, [])
        return [self.subscriptions[sub_id] for sub_id in subscription_ids 
                if sub_id in self.subscriptions and self.subscriptions[sub_id].active]

# PUBLICATION SYSTEM

class EventPublisher(IEventPublisher):
    """
    Event Publisher - Single Responsibility
    Handles event publication only
    """
    
    def __init__(self, 
                 router: IEventRouter,
                 subscription_manager: EventSubscriptionManager,
                 event_store: Optional[IEventStore] = None):
        self.router = router
        self.subscription_manager = subscription_manager
        self.event_store = event_store
        self.publish_queue = asyncio.Queue()
        self.processing_events = set()
        
    async def publish(self, event: Event) -> bool:
        """Publish event"""
        try:
            # Store event if event store is available
            if self.event_store:
                await self.event_store.store_event(event)
            
            # Route event
            target_services = await self.router.route_event(event)
            event.metadata.target_services = target_services
            
            # Dispatch to local subscribers
            dispatch_results = await self.subscription_manager.dispatch_event(event)
            
            # TODO: Send to remote services based on routing
            
            logger.info(f"Event published: {event.event_type} ({event.metadata.event_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.metadata.event_id}: {e}")
            return False
    
    async def publish_async(self, event: Event) -> None:
        """Publish event asynchronously"""
        await self.publish_queue.put(event)
    
    async def process_queue(self) -> None:
        """Process publish queue"""
        while True:
            try:
                event = await self.publish_queue.get()
                if event.metadata.event_id not in self.processing_events:
                    self.processing_events.add(event.metadata.event_id)
                    await self.publish(event)
                    self.processing_events.discard(event.metadata.event_id)
                
                self.publish_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing publish queue: {e}")
                await asyncio.sleep(1.0)

# EVENT STORE IMPLEMENTATION

class InMemoryEventStore(IEventStore):
    """
    In-Memory Event Store - Simple Implementation
    For production, replace with persistent storage
    """
    
    def __init__(self, max_events: int = 10000):
        self.events: List[Event] = []
        self.max_events = max_events
        
    async def store_event(self, event: Event) -> bool:
        """Store event in memory"""
        try:
            self.events.append(event)
            
            # Keep only latest events
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event {event.metadata.event_id}: {e}")
            return False
    
    async def get_events(self,
                        event_types: Optional[List[str]] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[Event]:
        """Get events from memory store"""
        try:
            filtered_events = self.events
            
            # Filter by event types
            if event_types:
                filtered_events = [e for e in filtered_events if e.event_type in event_types]
            
            # Filter by time range
            if start_time:
                filtered_events = [e for e in filtered_events if e.metadata.timestamp >= start_time]
            
            if end_time:
                filtered_events = [e for e in filtered_events if e.metadata.timestamp <= end_time]
            
            # Sort by timestamp (newest first) and limit
            filtered_events.sort(key=lambda e: e.metadata.timestamp, reverse=True)
            
            return filtered_events[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []

# MAIN EVENT BUS

class CleanEventBus:
    """
    Clean Event Bus - Composition over Inheritance
    Orchestrates clean event system components
    """
    
    def __init__(self, event_store: Optional[IEventStore] = None):
        # Create components - Dependency Injection
        self.router = EventRouter()
        self.subscription_manager = EventSubscriptionManager()
        self.event_store = event_store or InMemoryEventStore()
        self.publisher = EventPublisher(self.router, self.subscription_manager, self.event_store)
        
        # Initialize default routing rules
        self._setup_default_routing()
        
        # Start background processing
        self._background_task: Optional[asyncio.Task] = None
    
    def _setup_default_routing(self) -> None:
        """Setup default routing rules"""
        # Route all events to subscribers by default
        default_rule = RoutingRule(
            rule_id="default_subscriber_routing",
            event_type_pattern="*",
            target_services=["local_subscribers"],
            priority=0
        )
        self.router.add_routing_rule(default_rule)
        
        # High priority events to monitoring
        monitoring_rule = RoutingRule(
            rule_id="monitoring_high_priority",
            event_type_pattern="*",
            target_services=["monitoring"],
            conditions={"priority": EventPriority.HIGH.value},
            priority=10
        )
        self.router.add_routing_rule(monitoring_rule)
    
    async def start(self) -> bool:
        """Start event bus"""
        try:
            # Start background queue processing
            self._background_task = asyncio.create_task(self.publisher.process_queue())
            logger.info("Clean Event Bus started")
            return True
        except Exception as e:
            logger.error(f"Failed to start event bus: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop event bus"""
        try:
            if self._background_task:
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Clean Event Bus stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop event bus: {e}")
            return False
    
    # DELEGATED METHODS - Clean Interface
    
    async def publish(self, event_type: str, data: Dict[str, Any], 
                     source_service: str = "", correlation_id: Optional[str] = None) -> bool:
        """Publish event (convenience method)"""
        metadata = EventMetadata(
            source_service=source_service,
            correlation_id=correlation_id
        )
        
        event = Event(
            event_type=event_type,
            data=data,
            metadata=metadata
        )
        
        return await self.publisher.publish(event)
    
    async def subscribe(self, event_type: str, handler: Callable[[Event], Any], service_name: str = "unknown") -> str:
        """Subscribe to events"""
        return await self.subscription_manager.subscribe(event_type, handler, service_name)
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        return await self.subscription_manager.unsubscribe(subscription_id)
    
    def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add routing rule"""
        return self.router.add_routing_rule(rule)
    
    async def get_events(self, **kwargs) -> List[Event]:
        """Get events from store"""
        return await self.event_store.get_events(**kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            "total_subscriptions": len(self.subscription_manager.subscriptions),
            "active_subscriptions": len([s for s in self.subscription_manager.subscriptions.values() if s.active]),
            "event_types": list(self.subscription_manager.event_handlers.keys()),
            "routing_rules": len(self.router.routing_rules),
            "stored_events": len(self.event_store.events) if hasattr(self.event_store, 'events') else 0,
            "processing_events": len(self.publisher.processing_events)
        }

# GLOBAL EVENT BUS INSTANCE
_event_bus: Optional[CleanEventBus] = None

def get_event_bus() -> CleanEventBus:
    """Get global event bus instance"""
    global _event_bus
    
    if _event_bus is None:
        _event_bus = CleanEventBus()
    
    return _event_bus

if __name__ == "__main__":
    # Test the clean event bus architecture
    async def test_event_bus():
        print("=== Clean Event Bus Architecture Test ===")
        
        event_bus = get_event_bus()
        await event_bus.start()
        
        # Test event handler
        async def test_handler(event: Event):
            print(f"Received event: {event.event_type} - {event.data}")
        
        # Subscribe to events
        subscription_id = await event_bus.subscribe("test.event", test_handler, "test_service")
        print(f"Subscribed with ID: {subscription_id}")
        
        # Publish test event
        await event_bus.publish("test.event", {"message": "Hello Clean Architecture!"}, "test_publisher")
        
        # Wait a bit for processing
        await asyncio.sleep(0.1)
        
        # Get stats
        stats = event_bus.get_stats()
        print(f"\nEvent Bus Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Cleanup
        await event_bus.unsubscribe(subscription_id)
        await event_bus.stop()
        
        print("\n✅ Clean Event Bus Architecture test completed!")
    
    asyncio.run(test_event_bus())