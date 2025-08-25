"""
Data Processing Service - Mock Event Publisher
Clean Architecture v6.0.0

Mock Implementation für Event Publishing
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from application.interfaces.event_publisher import IEventPublisher

logger = structlog.get_logger(__name__)


class MockEventPublisher(IEventPublisher):
    """Mock Event Publisher für Development und Testing"""
    
    def __init__(self):
        self.published_events = []
        self.event_count = 0

    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish mock domain event"""
        try:
            event = {
                "event_type": event_type,
                "event_data": event_data,
                "correlation_id": correlation_id,
                "timestamp": datetime.now().isoformat(),
                "event_id": f"mock_{self.event_count}"
            }
            
            self.published_events.append(event)
            self.event_count += 1
            
            logger.info(f"📤 Published event: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}")
            return False

    async def publish_batch_events(self, events: list[Dict[str, Any]]) -> int:
        """Publish multiple events in batch"""
        published_count = 0
        
        for event in events:
            success = await self.publish_event(
                event.get("event_type", "unknown"),
                event.get("event_data", {}),
                event.get("correlation_id")
            )
            if success:
                published_count += 1
        
        return published_count

    async def is_healthy(self) -> bool:
        """Check if event publisher is healthy"""
        return True

    async def get_publisher_statistics(self) -> Dict[str, Any]:
        """Get event publishing statistics"""
        return {
            "total_events_published": self.event_count,
            "recent_events": len(self.published_events),
            "is_healthy": True,
            "publisher_type": "mock"
        }