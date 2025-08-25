"""
Event Domain Entity - Core business entity for Event Bus
Represents an event in the domain model

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class Event:
    """
    Domain Entity representing an event in the system
    Immutable entity following Clean Architecture principles
    """
    
    event_id: str
    event_type: str
    event_data: Dict[str, Any]
    created_at: datetime
    entity_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Validate event after initialization"""
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())
        
        if not isinstance(self.event_data, dict):
            raise ValueError("event_data must be a dictionary")
        
        if not self.event_type:
            raise ValueError("event_type is required")
    
    def mark_processed(self) -> 'Event':
        """Mark event as processed and return new instance"""
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            event_data=self.event_data,
            created_at=self.created_at,
            entity_id=self.entity_id,
            correlation_id=self.correlation_id,
            metadata=self.metadata,
            processed_at=datetime.utcnow(),
            version=self.version
        )
    
    def with_metadata(self, additional_metadata: Dict[str, Any]) -> 'Event':
        """Add metadata and return new instance"""
        updated_metadata = {**self.metadata, **additional_metadata}
        return Event(
            event_id=self.event_id,
            event_type=self.event_type,
            event_data=self.event_data,
            created_at=self.created_at,
            entity_id=self.entity_id,
            correlation_id=self.correlation_id,
            metadata=updated_metadata,
            processed_at=self.processed_at,
            version=self.version
        )
    
    def is_processed(self) -> bool:
        """Check if event has been processed"""
        return self.processed_at is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "correlation_id": self.correlation_id,
            "event_data": self.event_data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "version": self.version
        }