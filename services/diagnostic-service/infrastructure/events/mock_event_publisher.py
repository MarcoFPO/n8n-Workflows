#!/usr/bin/env python3
"""
Diagnostic Service - Mock Event Publisher
CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER

Mock implementation für Event Publishing (Development)
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import json

from ...application.interfaces.event_publisher import IEventPublisher


logger = logging.getLogger(__name__)


class MockEventPublisher(IEventPublisher):
    """
    Mock Event Publisher Implementation
    INFRASTRUCTURE LAYER: Development/Testing event publishing
    """
    
    def __init__(self, max_events: int = 500):
        """
        Initialize mock event publisher
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.published_events = deque(maxlen=max_events)
        self.event_count = 0
        self.failed_publications = 0
        self.started_at = datetime.now()
        self.is_healthy = True
        self.simulate_failures = False  # For testing failure scenarios
        self.failure_rate = 0.0  # 0.0 = never fail, 1.0 = always fail
        
        logger.info("Mock Event Publisher initialized")
    
    async def publish_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Publish domain event (mock implementation)
        
        Args:
            event_data: Event data containing type, data, metadata
            
        Returns:
            bool: True if published successfully
        """
        try:
            # Simulate failure if configured
            if self.simulate_failures:
                import random
                if random.random() < self.failure_rate:
                    self.failed_publications += 1
                    logger.warning(f"[MOCK] Simulated event publication failure")
                    return False
            
            # Create mock event record
            mock_event = {
                'event_id': f"mock_event_{self.event_count + 1}",
                'event_type': event_data.get('event_type', 'unknown'),
                'data': event_data.get('data', {}),
                'metadata': event_data.get('metadata', {}),
                'published_at': datetime.now().isoformat(),
                'source': 'diagnostic_service',
                'mock_published': True
            }
            
            # Store in memory
            self.published_events.append(mock_event)
            self.event_count += 1
            
            # Log publication
            logger.debug(
                f"[MOCK] Event published: {mock_event['event_type']} "
                f"(ID: {mock_event['event_id']})"
            )
            
            # Simulate async processing delay
            await asyncio.sleep(0.001)  # 1ms delay
            
            return True
            
        except Exception as e:
            logger.error(f"[MOCK] Failed to publish event: {e}")
            self.failed_publications += 1
            return False
    
    async def publish_batch_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish multiple events in batch
        
        Args:
            events: List of event data dictionaries
            
        Returns:
            Dict with success status and results
        """
        try:
            successful_publications = 0
            failed_publications = 0
            published_event_ids = []
            
            for event_data in events:
                success = await self.publish_event(event_data)
                if success:
                    successful_publications += 1
                    # Get the last published event ID
                    if self.published_events:
                        published_event_ids.append(self.published_events[-1]['event_id'])
                else:
                    failed_publications += 1
            
            result = {
                'success': successful_publications > 0,
                'total_events': len(events),
                'successful_publications': successful_publications,
                'failed_publications': failed_publications,
                'published_event_ids': published_event_ids,
                'batch_published_at': datetime.now().isoformat()
            }
            
            logger.info(
                f"[MOCK] Batch publication completed: "
                f"{successful_publications}/{len(events)} successful"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[MOCK] Batch publication failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_events': len(events),
                'successful_publications': 0,
                'failed_publications': len(events)
            }
    
    async def get_publisher_health(self) -> Dict[str, Any]:
        """
        Get event publisher health status
        
        Returns:
            Health status information
        """
        uptime = datetime.now() - self.started_at
        total_operations = self.event_count + self.failed_publications
        
        success_rate = 100.0
        if total_operations > 0:
            success_rate = (self.event_count / total_operations) * 100
        
        return {
            'publisher_type': 'mock',
            'is_healthy': self.is_healthy,
            'uptime_seconds': int(uptime.total_seconds()),
            'total_events_published': self.event_count,
            'failed_publications': self.failed_publications,
            'success_rate_percent': round(success_rate, 2),
            'events_in_memory': len(self.published_events),
            'max_events_capacity': self.published_events.maxlen,
            'simulate_failures': self.simulate_failures,
            'failure_rate': self.failure_rate,
            'last_event_at': (
                self.published_events[-1]['published_at'] 
                if self.published_events else None
            ),
            'started_at': self.started_at.isoformat()
        }
    
    async def get_published_events_count(self) -> int:
        """
        Get total number of events published
        
        Returns:
            Total events published count
        """
        return self.event_count
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent published events
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        # Convert deque to list and get last N events
        events_list = list(self.published_events)
        return events_list[-limit:] if events_list else []
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get events by type
        
        Args:
            event_type: Event type to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the type
        """
        matching_events = []
        for event in reversed(self.published_events):
            if event['event_type'] == event_type:
                matching_events.append(event)
                if len(matching_events) >= limit:
                    break
        
        return matching_events
    
    def clear_events(self):
        """Clear all stored events"""
        self.published_events.clear()
        logger.info("[MOCK] All published events cleared")
    
    def configure_failure_simulation(self, enable: bool, failure_rate: float = 0.1):
        """
        Configure failure simulation for testing
        
        Args:
            enable: Whether to enable failure simulation
            failure_rate: Rate of failures (0.0 to 1.0)
        """
        self.simulate_failures = enable
        self.failure_rate = max(0.0, min(1.0, failure_rate))  # Clamp between 0-1
        
        logger.info(
            f"[MOCK] Failure simulation {'enabled' if enable else 'disabled'} "
            f"(rate: {self.failure_rate:.1%})"
        )
    
    def set_health_status(self, is_healthy: bool):
        """
        Set mock health status
        
        Args:
            is_healthy: Health status to simulate
        """
        self.is_healthy = is_healthy
        logger.info(f"[MOCK] Health status set to: {'healthy' if is_healthy else 'unhealthy'}")
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        Get detailed event statistics
        
        Returns:
            Event statistics and analytics
        """
        # Analyze event types
        event_type_counts = {}
        hourly_distribution = {}
        
        for event in self.published_events:
            event_type = event['event_type']
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            # Parse hour from timestamp for distribution
            try:
                published_time = datetime.fromisoformat(event['published_at'])
                hour_key = published_time.strftime('%Y-%m-%d %H:00')
                hourly_distribution[hour_key] = hourly_distribution.get(hour_key, 0) + 1
            except:
                pass  # Skip timestamp parsing errors
        
        return {
            'total_events': self.event_count,
            'events_in_memory': len(self.published_events),
            'failed_publications': self.failed_publications,
            'event_type_distribution': event_type_counts,
            'hourly_event_distribution': hourly_distribution,
            'most_common_event_type': (
                max(event_type_counts.items(), key=lambda x: x[1])[0]
                if event_type_counts else None
            ),
            'average_events_per_hour': (
                len(self.published_events) / max(1, len(hourly_distribution))
                if hourly_distribution else 0
            )
        }
    
    async def flush_events_to_file(self, filepath: str) -> bool:
        """
        Flush all events to JSON file (for persistence/debugging)
        
        Args:
            filepath: File path to write events to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            events_data = {
                'export_timestamp': datetime.now().isoformat(),
                'publisher_stats': await self.get_publisher_health(),
                'event_statistics': self.get_event_statistics(),
                'events': list(self.published_events)
            }
            
            with open(filepath, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.info(f"[MOCK] Flushed {len(self.published_events)} events to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"[MOCK] Failed to flush events to file: {e}")
            return False


class InMemoryEventStore:
    """
    In-memory event store for development/testing
    Provides event querying and persistence capabilities
    """
    
    def __init__(self):
        self.events = []
        self.event_streams = {}  # stream_id -> events
        self.event_types = {}    # event_type -> events
        
    def add_event(self, event: Dict[str, Any]):
        """Add event to store"""
        self.events.append(event)
        
        # Index by stream
        stream_id = event.get('stream_id', 'default')
        if stream_id not in self.event_streams:
            self.event_streams[stream_id] = []
        self.event_streams[stream_id].append(event)
        
        # Index by type
        event_type = event.get('event_type', 'unknown')
        if event_type not in self.event_types:
            self.event_types[event_type] = []
        self.event_types[event_type].append(event)
    
    def get_events_by_stream(self, stream_id: str) -> List[Dict[str, Any]]:
        """Get events by stream ID"""
        return self.event_streams.get(stream_id, [])
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get events by type"""
        return self.event_types.get(event_type, [])
    
    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all events"""
        return self.events.copy()
    
    def clear(self):
        """Clear all events"""
        self.events.clear()
        self.event_streams.clear()
        self.event_types.clear()