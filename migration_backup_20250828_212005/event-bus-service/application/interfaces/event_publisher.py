"""
Event Publisher Interface - Application Layer
Clean Architecture - Interface Segregation Principle

CLEAN ARCHITECTURE: Application Layer Interface
Definiert Kontrakt für Event Publishing ohne Infrastructure Dependencies

Code-Qualität: HÖCHSTE PRIORITÄT
Autor: Claude Code - Interface Design Specialist
Datum: 24. August 2025
Version: 7.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from presentation.models import EventMessage


class IEventPublisher(ABC):
    """
    Event Publisher Interface
    
    CLEAN ARCHITECTURE: Application Layer Interface
    Implementiert Dependency Inversion Principle
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the event publisher"""
        pass
    
    @abstractmethod
    async def publish(
        self, 
        event_type: str,
        event_data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        target_services: Optional[List[str]] = None
    ) -> str:
        """
        Publish an event
        
        Args:
            event_type: Type of event to publish
            event_data: Event payload
            source: Source service
            correlation_id: Optional correlation ID
            metadata: Optional metadata
            priority: Event priority level
            target_services: Specific target services (if not broadcast)
            
        Returns:
            Generated event ID
        """
        pass
    
    @abstractmethod
    async def publish_event_message(self, event: EventMessage) -> str:
        """
        Publish a structured event message
        
        Args:
            event: Complete event message object
            
        Returns:
            Generated event ID
        """
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[EventMessage]) -> List[str]:
        """
        Publish multiple events in a batch
        
        Args:
            events: List of event messages
            
        Returns:
            List of generated event IDs
        """
        pass
    
    @abstractmethod
    async def get_connected_services(self) -> List[str]:
        """
        Get list of currently connected services
        
        Returns:
            List of connected service names
        """
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if publisher is healthy and operational
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get publishing metrics
        
        Returns:
            Dictionary containing metrics data
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources"""
        pass