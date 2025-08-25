#!/usr/bin/env python3
"""
MarketCap Service - Mock Event Publisher
Infrastructure Layer Event Publishing Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements application event publisher interface
- Mock implementation for development and testing
- Event-driven architecture adapter

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import uuid

from ...application.interfaces.event_publisher import IEventPublisher


logger = logging.getLogger(__name__)


class MockEventPublisher(IEventPublisher):
    """
    Mock Event Publisher Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of event publisher interface
    DEVELOPMENT/TESTING: Simulates event publishing for development
    EVENT-DRIVEN ARCHITECTURE: Provides observability into domain events
    """
    
    def __init__(self, max_stored_events: int = 1000):
        """
        Initialize mock event publisher
        
        Args:
            max_stored_events: Maximum number of events to store in memory
        """
        self._published_events: List[Dict[str, Any]] = []
        self._max_stored_events = max_stored_events
        self._lock = asyncio.Lock()
        self._initialized_at = datetime.now()
        self._publish_count = 0
        self._failed_publishes = 0
        self._is_available = True
        
        logger.info(f"Mock Event Publisher initialized (max_events: {max_stored_events})")
    
    async def publish(
        self, 
        event_type: str, 
        event_data: Dict[str, Any], 
        entity_id: Optional[str] = None
    ) -> bool:
        """
        Publish an event
        
        Args:
            event_type: Type of event (e.g., 'market_data.retrieved')
            event_data: Event payload data
            entity_id: Optional entity identifier for correlation
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            async with self._lock:
                if not self._is_available:
                    self._failed_publishes += 1
                    logger.warning(f"Event publisher unavailable - failed to publish: {event_type}")
                    return False
                
                # Create event record
                event_record = {
                    'event_id': str(uuid.uuid4()),
                    'event_type': event_type,
                    'entity_id': entity_id,
                    'event_data': event_data.copy(),
                    'published_at': datetime.now().isoformat(),
                    'publisher': 'mock_event_publisher_v6.0.0'
                }
                
                # Store event (with rotation if needed)
                if len(self._published_events) >= self._max_stored_events:
                    self._published_events.pop(0)  # Remove oldest
                
                self._published_events.append(event_record)
                self._publish_count += 1
                
                logger.debug(f"Published event: {event_type} (entity_id: {entity_id})")
                
                # Log interesting events at info level
                if any(keyword in event_type.lower() for keyword in ['error', 'failed', 'success']):
                    logger.info(f"Event published: {event_type} - {event_data.get('symbol', 'N/A')}")
                
                return True
                
        except Exception as e:
            self._failed_publishes += 1
            logger.error(f"Failed to publish event {event_type}: {e}")
            return False
    
    async def is_available(self) -> bool:
        """
        Check if event publishing is available
        
        Returns:
            True if available, False otherwise
        """
        return self._is_available
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get event publisher health status
        
        Returns:
            Health status dictionary
        """
        uptime = datetime.now() - self._initialized_at
        
        return {
            'publisher': 'MockEventPublisher',
            'version': '6.0.0',
            'status': 'available' if self._is_available else 'unavailable',
            'publish_count': self._publish_count,
            'failed_publishes': self._failed_publishes,
            'stored_events': len(self._published_events),
            'max_stored_events': self._max_stored_events,
            'uptime_seconds': int(uptime.total_seconds()),
            'initialized_at': self._initialized_at.isoformat(),
            'last_check': datetime.now().isoformat()
        }
    
    async def get_published_events(
        self, 
        event_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get published events (for testing/debugging)
        
        Args:
            event_type: Optional filter by event type
            entity_id: Optional filter by entity ID
            limit: Maximum number of events to return
            
        Returns:
            List of published events
        """
        async with self._lock:
            events = self._published_events.copy()
            
            # Apply filters
            if event_type:
                events = [e for e in events if e['event_type'] == event_type]
            
            if entity_id:
                events = [e for e in events if e['entity_id'] == entity_id]
            
            # Apply limit and return most recent first
            return events[-limit:][::-1]
    
    async def clear_events(self) -> int:
        """
        Clear stored events (for testing)
        
        Returns:
            Number of events cleared
        """
        async with self._lock:
            count = len(self._published_events)
            self._published_events.clear()
            logger.info(f"Cleared {count} stored events")
            return count
    
    async def set_availability(self, available: bool) -> None:
        """
        Set publisher availability (for testing)
        
        Args:
            available: Whether publisher should be available
        """
        self._is_available = available
        status = "available" if available else "unavailable"
        logger.info(f"Mock Event Publisher set to: {status}")
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get detailed event statistics
        
        Returns:
            Event statistics dictionary
        """
        async with self._lock:
            # Count events by type
            event_type_counts: Dict[str, int] = {}
            recent_events = []
            
            for event in self._published_events:
                event_type = event['event_type']
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
                
                # Keep last 10 events for recent activity
                if len(recent_events) < 10:
                    recent_events.append({
                        'event_type': event['event_type'],
                        'entity_id': event['entity_id'],
                        'published_at': event['published_at']
                    })
            
            success_rate = (
                self._publish_count / (self._publish_count + self._failed_publishes) * 100
                if (self._publish_count + self._failed_publishes) > 0 else 100
            )
            
            return {
                'total_published': self._publish_count,
                'failed_publishes': self._failed_publishes,
                'success_rate_percentage': round(success_rate, 2),
                'event_type_distribution': event_type_counts,
                'recent_events': recent_events,
                'storage_utilization_percentage': round(
                    len(self._published_events) / self._max_stored_events * 100, 2
                )
            }
    
    async def simulate_failure(self, duration_seconds: int = 30) -> None:
        """
        Simulate publisher failure (for testing)
        
        Args:
            duration_seconds: How long to simulate failure
        """
        logger.warning(f"Simulating event publisher failure for {duration_seconds} seconds")
        self._is_available = False
        
        # Schedule recovery
        async def recover():
            await asyncio.sleep(duration_seconds)
            self._is_available = True
            logger.info("Event publisher recovered from simulated failure")
        
        asyncio.create_task(recover())