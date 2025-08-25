"""
Event Publishing Use Case - Clean Architecture Application Layer
Handles business logic for event publishing through the Event Bus

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from application.interfaces.event_publisher import IEventPublisher
from application.interfaces.event_repository import IEventRepository
from domain.entities.event import Event
from domain.services.event_validator import EventValidatorService


class EventPublishingUseCase:
    """
    Use Case for publishing events through the Event Bus system
    Implements Clean Architecture principles for event handling
    """
    
    def __init__(
        self,
        event_publisher: IEventPublisher,
        event_repository: IEventRepository,
        event_validator: EventValidatorService
    ):
        """
        Initialize EventPublishingUseCase with required dependencies
        
        Args:
            event_publisher: Infrastructure layer event publisher
            event_repository: Infrastructure layer event repository
            event_validator: Domain layer validation service
        """
        self.event_publisher = event_publisher
        self.event_repository = event_repository
        self.event_validator = event_validator
        self.logger = logging.getLogger(__name__)
    
    async def execute(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute event publishing workflow
        
        Args:
            event_type: Type of event to publish
            event_data: Event payload data
            entity_id: Optional entity identifier
            correlation_id: Optional correlation ID for event tracing
            metadata: Optional event metadata
            
        Returns:
            Dict containing event publishing result
        """
        try:
            # Generate IDs if not provided
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            
            event_id = str(uuid.uuid4())
            
            # Create domain event entity
            event = Event(
                event_id=event_id,
                event_type=event_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                event_data=event_data,
                metadata=metadata or {},
                created_at=datetime.utcnow()
            )
            
            # Validate event using domain service
            validation_result = await self.event_validator.validate(event)
            if not validation_result.is_valid:
                self.logger.warning(f"Event validation failed: {validation_result.errors}")
                return {
                    "success": False,
                    "event_id": event_id,
                    "errors": validation_result.errors
                }
            
            # Publish event through infrastructure
            publish_result = await self.event_publisher.publish(event)
            
            # Persist event to repository
            await self.event_repository.save(event)
            
            self.logger.info(f"Event published successfully: {event_type} ({event_id})")
            
            return {
                "success": True,
                "event_id": event_id,
                "correlation_id": correlation_id,
                "published_at": datetime.utcnow().isoformat(),
                "channel": f"events:{event_type}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to publish event: {str(e)}")
            return {
                "success": False,
                "event_id": event_id if 'event_id' in locals() else None,
                "error": str(e)
            }
    
    async def publish_batch(
        self,
        events: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Publish multiple events in batch
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Dict containing batch publishing results
        """
        results = []
        successful = 0
        failed = 0
        
        for event_data in events:
            result = await self.execute(
                event_type=event_data.get("event_type"),
                event_data=event_data.get("event_data", {}),
                entity_id=event_data.get("entity_id"),
                correlation_id=event_data.get("correlation_id"),
                metadata=event_data.get("metadata")
            )
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
            
            results.append(result)
        
        return {
            "total": len(events),
            "successful": successful,
            "failed": failed,
            "results": results
        }