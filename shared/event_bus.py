#!/usr/bin/env python3
"""
Event Bus Module - Minimal Implementation
Event-Based Communication für Aktienanalyse-Ökosystem
Issue #65 Integration-Fix
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union
from uuid import uuid4

# Fallback logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard Event Types"""
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ERROR = "system.error"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    MARKET_DATA_UPDATE = "market.data.update"
    ORDER_CREATED = "order.created"
    ORDER_EXECUTED = "order.executed"
    PORTFOLIO_UPDATE = "portfolio.update"


@dataclass
class Event:
    """Event Data Structure"""
    event_type: str
    payload: Dict[str, Any]
    event_id: str = None
    timestamp: str = None
    source_service: str = None
    
    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create from dictionary"""
        return cls(**data)


class EventBusConnector:
    """
    Event Bus Connector - Minimale Implementation
    Simuliert Event-Bus Funktionalität für Integration Tests
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.connected = False
        self.logger = logging.getLogger(f"eventbus.{service_name}")
        self.subscribers: Dict[str, List[Callable]] = {}
        self.published_events: List[Event] = []
    
    async def connect(self) -> bool:
        """Connect to Event Bus"""
        try:
            # Simulate connection
            await asyncio.sleep(0.1)
            self.connected = True
            self.logger.info(f"Connected to event bus: {self.service_name}")
            return True
        except Exception as e:
            self.logger.error(f"Event bus connection failed: {self.service_name} - {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from Event Bus"""
        try:
            self.connected = False
            self.logger.info(f"Disconnected from event bus: {self.service_name}")
        except Exception as e:
            self.logger.error(f"Event bus disconnect failed: {self.service_name} - {str(e)}")
    
    async def publish(self, event: Event) -> bool:
        """Publish Event"""
        if not self.connected:
            self.logger.warning("Cannot publish - not connected", service=self.service_name)
            return False
        
        try:
            # Set source if not set
            if event.source_service is None:
                event.source_service = self.service_name
            
            # Store event (simulated)
            self.published_events.append(event)
            
            # Notify subscribers
            event_type = event.event_type
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        await callback(event)
                    except Exception as e:
                        self.logger.error("Subscriber callback failed", 
                                        service=self.service_name,
                                        event_type=event_type,
                                        error=str(e))
            
            self.logger.debug("Event published", 
                            service=self.service_name,
                            event_id=event.event_id,
                            event_type=event.event_type)
            return True
            
        except Exception as e:
            self.logger.error("Event publish failed", 
                            service=self.service_name,
                            error=str(e))
            return False
    
    async def subscribe(self, event_type: str, callback: Callable[[Event], Any]):
        """Subscribe to Event Type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
        self.logger.info("Subscribed to event type", 
                       service=self.service_name,
                       event_type=event_type)
    
    async def publish_event(self, event_type: Union[str, EventType], payload: Dict[str, Any]) -> bool:
        """Convenience method to publish event"""
        if isinstance(event_type, EventType):
            event_type = event_type.value
        
        event = Event(
            event_type=event_type,
            payload=payload,
            source_service=self.service_name
        )
        
        return await self.publish(event)


class EventBusConfig:
    """Event Bus Configuration"""
    
    def __init__(self):
        self.redis_url = "redis://localhost:6379"
        self.rabbitmq_url = "amqp://guest:guest@localhost:5672"
        self.max_retries = 3
        self.timeout = 30
        
        # Default configuration - kann später erweitert werden
        self.config = {
            "redis": {"url": self.redis_url},
            "rabbitmq": {"url": self.rabbitmq_url},
            "retry": {"max_attempts": self.max_retries}
        }


# Legacy Compatibility
class EventBusConnection:
    """Legacy Event Bus Connection für Backward Compatibility"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connector = EventBusConnector("legacy-connection")
    
    async def connect(self) -> bool:
        return await self.connector.connect()
    
    async def disconnect(self):
        await self.connector.disconnect()
    
    async def publish_event(self, event_data: Dict[str, Any]) -> bool:
        event = Event(
            event_type=event_data.get("event_type", "generic"),
            payload=event_data.get("payload", {}),
            source_service=event_data.get("source", "legacy")
        )
        return await self.connector.publish(event)


# Factory Functions
def get_event_bus_connector(service_name: str) -> EventBusConnector:
    """Factory für Event Bus Connector"""
    return EventBusConnector(service_name)


def get_event_bus_config() -> EventBusConfig:
    """Factory für Event Bus Config"""
    return EventBusConfig()