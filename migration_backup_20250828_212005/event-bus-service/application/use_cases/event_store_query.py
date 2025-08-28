"""
Event Store Query Use Case - Clean Architecture Application Layer
Handles querying and retrieval of events from the event store

Code-Qualität: HÖCHSTE PRIORITÄT
Version: 7.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from application.interfaces.event_repository import IEventRepository
from domain.services.event_aggregation_service import EventAggregationService


class EventStoreQueryUseCase:
    """
    Use Case for querying events from the Event Store
    Provides advanced query capabilities and aggregations
    """
    
    def __init__(
        self,
        event_repository: IEventRepository,
        aggregation_service: EventAggregationService
    ):
        """
        Initialize EventStoreQueryUseCase with dependencies
        
        Args:
            event_repository: Infrastructure layer event repository
            aggregation_service: Domain layer aggregation service
        """
        self.event_repository = event_repository
        self.aggregation_service = aggregation_service
        self.logger = logging.getLogger(__name__)
    
    async def query_events(
        self,
        event_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query events from the event store with filters
        
        Args:
            event_type: Filter by event type
            entity_id: Filter by entity ID
            correlation_id: Filter by correlation ID
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            Dict containing query results
        """
        try:
            # Query events from repository
            events = await self.event_repository.query_events(
                event_type=event_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )
            
            # Convert events to dict format
            event_list = [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "entity_id": event.entity_id,
                    "correlation_id": event.correlation_id,
                    "event_data": event.event_data,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "processed_at": event.processed_at.isoformat() if event.processed_at else None
                }
                for event in events
            ]
            
            # Get total count for pagination
            total_count = await self.event_repository.count_events(
                event_type=event_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "success": True,
                "events": event_list,
                "count": len(event_list),
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(event_list)) < total_count
            }
            
        except Exception as e:
            self.logger.error(f"Failed to query events: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "events": []
            }
    
    async def get_event_by_id(self, event_id: str) -> Dict[str, Any]:
        """
        Get a specific event by ID
        
        Args:
            event_id: Event identifier
            
        Returns:
            Dict containing event details
        """
        try:
            event = await self.event_repository.get_event_by_id(event_id)
            
            if not event:
                return {
                    "success": False,
                    "error": "Event not found"
                }
            
            return {
                "success": True,
                "event": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "entity_id": event.entity_id,
                    "correlation_id": event.correlation_id,
                    "event_data": event.event_data,
                    "metadata": event.metadata,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                    "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                    "version": event.version
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_event_stream(
        self,
        entity_id: str,
        event_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get complete event stream for an entity
        
        Args:
            entity_id: Entity identifier
            event_types: Optional filter for event types
            
        Returns:
            Dict containing event stream
        """
        try:
            events = await self.event_repository.get_entity_events(
                entity_id=entity_id,
                event_types=event_types
            )
            
            # Aggregate events using domain service
            aggregated = await self.aggregation_service.aggregate_entity_stream(
                entity_id=entity_id,
                events=events
            )
            
            return {
                "success": True,
                "entity_id": entity_id,
                "event_count": len(events),
                "events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "created_at": event.created_at.isoformat() if event.created_at else None
                    }
                    for event in events
                ],
                "aggregated_state": aggregated
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event stream: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_event_statistics(
        self,
        time_range: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get event statistics for monitoring
        
        Args:
            time_range: Time range for statistics (e.g., "1h", "24h", "7d")
            
        Returns:
            Dict containing event statistics
        """
        try:
            # Parse time range
            now = datetime.utcnow()
            if time_range == "1h":
                start_date = now - timedelta(hours=1)
            elif time_range == "24h":
                start_date = now - timedelta(days=1)
            elif time_range == "7d":
                start_date = now - timedelta(days=7)
            else:
                start_date = now - timedelta(days=1)
            
            # Get statistics from repository
            stats = await self.event_repository.get_event_statistics(
                start_date=start_date,
                end_date=now
            )
            
            # Get event type distribution
            type_distribution = await self.event_repository.get_event_type_distribution(
                start_date=start_date,
                end_date=now
            )
            
            return {
                "success": True,
                "time_range": time_range,
                "start_date": start_date.isoformat(),
                "end_date": now.isoformat(),
                "statistics": {
                    "total_events": stats.get("total_events", 0),
                    "unique_entities": stats.get("unique_entities", 0),
                    "unique_correlations": stats.get("unique_correlations", 0),
                    "events_per_hour": stats.get("events_per_hour", 0),
                    "average_processing_time_ms": stats.get("avg_processing_time_ms", 0)
                },
                "event_type_distribution": type_distribution
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get event statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }