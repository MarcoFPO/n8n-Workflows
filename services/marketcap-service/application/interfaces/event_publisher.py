#!/usr/bin/env python3
"""
MarketCap Service - Event Publisher Interface
Application Layer Interface für Event Publishing

CLEAN ARCHITECTURE - APPLICATION LAYER:
- Defines interfaces for external services
- Port for Event-Driven Architecture integration
- Independent of implementation details

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class IEventPublisher(ABC):
    """
    Event Publisher Interface
    
    PORT INTERFACE: Defines contract for event publishing
    EVENT-DRIVEN ARCHITECTURE: Integration with Event-Bus Service
    DEPENDENCY INVERSION: Application layer depends on this abstraction
    """
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any], entity_id: Optional[str] = None) -> bool:
        """
        Publish an event
        
        Args:
            event_type: Type of event (e.g., 'market_data.retrieved')
            event_data: Event payload data
            entity_id: Optional entity identifier for correlation
            
        Returns:
            True if published successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if event publishing is available
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get event publisher health status
        
        Returns:
            Health status dictionary
        """
        pass


class IEventSubscriber(ABC):
    """
    Event Subscriber Interface
    
    PORT INTERFACE: Defines contract for event subscription
    EVENT-DRIVEN ARCHITECTURE: Receive events from Event-Bus Service
    """
    
    @abstractmethod
    async def subscribe(self, event_types: list[str], callback) -> bool:
        """
        Subscribe to event types
        
        Args:
            event_types: List of event types to subscribe to
            callback: Callback function for event handling
            
        Returns:
            True if subscribed successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, event_types: list[str]) -> bool:
        """
        Unsubscribe from event types
        
        Args:
            event_types: List of event types to unsubscribe from
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        pass


class IEventStore(ABC):
    """
    Event Store Interface
    
    PORT INTERFACE: Defines contract for event storage
    EVENT SOURCING: Store and retrieve domain events
    """
    
    @abstractmethod
    async def store_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        entity_id: str,
        entity_type: str = "market_data"
    ) -> str:
        """
        Store an event
        
        Args:
            event_type: Type of event
            event_data: Event payload
            entity_id: Entity identifier
            entity_type: Type of entity
            
        Returns:
            Event ID if stored successfully
        """
        pass
    
    @abstractmethod
    async def get_events(
        self,
        entity_id: str,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Get events for an entity
        
        Args:
            entity_id: Entity identifier
            event_type: Optional filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of events
        """
        pass


class MarketDataEvents:
    """
    Market Data Domain Events
    
    DOMAIN EVENTS: Standard event types for market data domain
    """
    
    # Market Data Events
    MARKET_DATA_RETRIEVED = "market_data.retrieved"
    MARKET_DATA_UPDATED = "market_data.updated"
    MARKET_DATA_CACHED = "market_data.cached"
    MARKET_DATA_STALE = "market_data.stale"
    
    # Service Events
    SERVICE_STARTED = "marketcap_service.started"
    SERVICE_STOPPED = "marketcap_service.stopped"
    SERVICE_ERROR = "marketcap_service.error"
    
    # Health Events
    HEALTH_CHECK_OK = "marketcap_service.health.ok"
    HEALTH_CHECK_FAILED = "marketcap_service.health.failed"
    
    # Provider Events
    PROVIDER_AVAILABLE = "marketcap_service.provider.available"
    PROVIDER_UNAVAILABLE = "marketcap_service.provider.unavailable"
    
    @classmethod
    def get_all_events(cls) -> list[str]:
        """Get all defined event types"""
        return [
            cls.MARKET_DATA_RETRIEVED,
            cls.MARKET_DATA_UPDATED,
            cls.MARKET_DATA_CACHED,
            cls.MARKET_DATA_STALE,
            cls.SERVICE_STARTED,
            cls.SERVICE_STOPPED,
            cls.SERVICE_ERROR,
            cls.HEALTH_CHECK_OK,
            cls.HEALTH_CHECK_FAILED,
            cls.PROVIDER_AVAILABLE,
            cls.PROVIDER_UNAVAILABLE
        ]