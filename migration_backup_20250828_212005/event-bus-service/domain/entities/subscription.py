"""
Subscription Domain Entity - Core entity for event subscriptions
Represents a subscription in the domain model

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class Subscription:
    """
    Domain Entity representing an event subscription
    Immutable entity following Clean Architecture principles
    """
    
    subscription_id: str
    event_type: str
    service_name: str
    handler_endpoint: str
    is_active: bool = True
    filters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate subscription after initialization"""
        if not self.subscription_id:
            self.subscription_id = str(uuid.uuid4())
        
        if not self.event_type:
            raise ValueError("event_type is required")
        
        if not self.service_name:
            raise ValueError("service_name is required")
        
        if not self.handler_endpoint:
            raise ValueError("handler_endpoint is required")
        
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def deactivate(self) -> 'Subscription':
        """Deactivate subscription and return new instance"""
        return Subscription(
            subscription_id=self.subscription_id,
            event_type=self.event_type,
            service_name=self.service_name,
            handler_endpoint=self.handler_endpoint,
            is_active=False,
            filters=self.filters,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )
    
    def activate(self) -> 'Subscription':
        """Activate subscription and return new instance"""
        return Subscription(
            subscription_id=self.subscription_id,
            event_type=self.event_type,
            service_name=self.service_name,
            handler_endpoint=self.handler_endpoint,
            is_active=True,
            filters=self.filters,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )
    
    def update_filters(self, new_filters: Dict[str, Any]) -> 'Subscription':
        """Update subscription filters and return new instance"""
        return Subscription(
            subscription_id=self.subscription_id,
            event_type=self.event_type,
            service_name=self.service_name,
            handler_endpoint=self.handler_endpoint,
            is_active=self.is_active,
            filters=new_filters,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=datetime.utcnow()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary representation"""
        return {
            "subscription_id": self.subscription_id,
            "event_type": self.event_type,
            "service_name": self.service_name,
            "handler_endpoint": self.handler_endpoint,
            "is_active": self.is_active,
            "filters": self.filters,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }