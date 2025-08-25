"""
Data Processing Service - Event Publisher Interface
Clean Architecture v6.0.0

Interface für Domain Event Publishing
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IEventPublisher(ABC):
    """Interface für Domain Event Publishing"""

    @abstractmethod
    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish domain event"""
        pass

    @abstractmethod
    async def publish_batch_events(
        self,
        events: list[Dict[str, Any]]
    ) -> int:
        """Publish multiple events in batch, return number published"""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if event publisher is healthy"""
        pass

    @abstractmethod
    async def get_publisher_statistics(self) -> Dict[str, Any]:
        """Get event publishing statistics"""
        pass