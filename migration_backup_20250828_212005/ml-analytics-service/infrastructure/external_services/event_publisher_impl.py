#!/usr/bin/env python3
"""
Event Publisher Implementation

Autor: Claude Code - Event-Driven Architecture Implementer
Datum: 26. August 2025  
Clean Architecture v6.0.0 - Infrastructure Layer
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import deque

from ...application.interfaces.event_publisher import IEventPublisher, MLDomainEvents

logger = logging.getLogger(__name__)


@dataclass
class EventMetrics:
    """Event Publishing Metrics"""
    total_published: int = 0
    successful_publishes: int = 0
    failed_publishes: int = 0
    events_pending: int = 0
    last_publish_time: Optional[datetime] = None
    
    def get_success_rate(self) -> float:
        if self.total_published == 0:
            return 0.0
        return (self.successful_publishes / self.total_published) * 100


class EventPublisherImpl(IEventPublisher):
    """
    Concrete Event Publisher Implementation
    
    Infrastructure implementation of IEventPublisher interface
    - In-memory event queue for development/testing
    - Can be extended to use Redis Pub/Sub, RabbitMQ, Apache Kafka, etc.
    - Provides async event publishing with batching support
    """
    
    def __init__(self, max_queue_size: int = 10000, batch_size: int = 100):
        self._max_queue_size = max_queue_size
        self._batch_size = batch_size
        self._is_initialized = False
        
        # Event Queue (in-memory for now)
        self._event_queue = deque(maxlen=max_queue_size)
        self._pending_events = deque()
        
        # Metrics
        self._metrics = EventMetrics()
        
        # Background processing
        self._processing_task = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> bool:
        """Initialize event publisher"""
        
        try:
            # Start background event processing
            self._processing_task = asyncio.create_task(self._process_events_background())
            
            self._is_initialized = True
            logger.info("Event Publisher initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Event Publisher: {str(e)}")
            return False
    
    async def publish(self, event: Dict[str, Any]) -> bool:
        """Publish single domain event"""
        
        if not self._is_initialized:
            logger.error("Event Publisher not initialized")
            return False
        
        try:
            # Enrich event with metadata
            enriched_event = self._enrich_event(event)
            
            # Add to queue
            self._event_queue.append(enriched_event)
            self._metrics.events_pending += 1
            
            logger.debug(f"Event queued: {enriched_event.get('event_type', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue event: {str(e)}")
            self._metrics.failed_publishes += 1
            return False
    
    async def publish_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Publish multiple events as batch"""
        
        if not self._is_initialized:
            logger.error("Event Publisher not initialized")
            return False
        
        successful = 0
        
        for event in events:
            if await self.publish(event):
                successful += 1
        
        success_rate = (successful / len(events)) * 100
        logger.info(f"Batch publish completed: {successful}/{len(events)} events ({success_rate:.1f}%)")
        
        return successful == len(events)
    
    async def get_publisher_health(self) -> Dict[str, Any]:
        """Get event publisher health status"""
        
        return {
            "healthy": self._is_initialized and not self._shutdown_event.is_set(),
            "initialized": self._is_initialized,
            "queue_size": len(self._event_queue),
            "pending_events": self._metrics.events_pending,
            "metrics": {
                "total_published": self._metrics.total_published,
                "successful_publishes": self._metrics.successful_publishes,  
                "failed_publishes": self._metrics.failed_publishes,
                "success_rate": self._metrics.get_success_rate(),
                "last_publish_time": self._metrics.last_publish_time.isoformat() if self._metrics.last_publish_time else None
            },
            "configuration": {
                "max_queue_size": self._max_queue_size,
                "batch_size": self._batch_size,
                "processing_active": self._processing_task is not None and not self._processing_task.done()
            }
        }
    
    def _enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich event with metadata"""
        
        enriched = event.copy()
        
        # Add standard metadata if not present
        if "timestamp" not in enriched:
            enriched["timestamp"] = datetime.utcnow().isoformat()
        
        if "source" not in enriched:
            enriched["source"] = "ml-analytics-service"
        
        if "version" not in enriched:
            enriched["version"] = "1.0"
        
        # Add event ID if not present
        if "event_id" not in enriched:
            from uuid import uuid4
            enriched["event_id"] = str(uuid4())
        
        # Add processing metadata
        enriched["published_at"] = datetime.utcnow().isoformat()
        enriched["publisher"] = "EventPublisherImpl"
        
        return enriched
    
    async def _process_events_background(self) -> None:
        """Background task to process events from queue"""
        
        logger.info("Starting background event processing")
        
        while not self._shutdown_event.is_set():
            try:
                # Process events in batches
                batch = []
                
                # Collect batch of events
                while len(batch) < self._batch_size and self._event_queue:
                    event = self._event_queue.popleft()
                    batch.append(event)
                    self._metrics.events_pending -= 1
                
                if batch:
                    await self._publish_batch_to_destination(batch)
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in background event processing: {str(e)}")
                await asyncio.sleep(1)  # Longer delay on error
        
        logger.info("Background event processing stopped")
    
    async def _publish_batch_to_destination(self, events: List[Dict[str, Any]]) -> None:
        """
        Publish batch of events to actual destination
        
        This is where you would implement actual event publishing:
        - Redis Pub/Sub: redis.publish(channel, json.dumps(event))
        - RabbitMQ: channel.basic_publish(exchange, routing_key, message)
        - Apache Kafka: producer.send(topic, event)
        - HTTP Webhook: aiohttp.post(webhook_url, json=event)
        """
        
        try:
            # Mock implementation - log events and simulate publishing
            for event in events:
                logger.info(f"Publishing event: {event.get('event_type', 'Unknown')} for symbol: {event.get('symbol', 'N/A')}")
                
                # In real implementation, publish to message broker/webhook
                # await self._publish_to_redis(event)
                # await self._publish_to_webhook(event)
                
                # Mock successful publish
                await asyncio.sleep(0.01)  # Simulate network delay
                
                self._metrics.successful_publishes += 1
                self._metrics.last_publish_time = datetime.utcnow()
            
            self._metrics.total_published += len(events)
            
        except Exception as e:
            logger.error(f"Failed to publish batch: {str(e)}")
            self._metrics.failed_publishes += len(events)
            self._metrics.total_published += len(events)
    
    async def _publish_to_redis(self, event: Dict[str, Any]) -> None:
        """Publish event to Redis Pub/Sub (example implementation)"""
        
        # Example Redis implementation:
        # import aioredis
        # redis = aioredis.from_url("redis://localhost:6379")
        # await redis.publish("ml-analytics-events", json.dumps(event))
        pass
    
    async def _publish_to_webhook(self, event: Dict[str, Any]) -> None:
        """Publish event to HTTP webhook (example implementation)"""
        
        # Example webhook implementation:
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.post(webhook_url, json=event) as response:
        #         if response.status != 200:
        #             raise Exception(f"Webhook failed: {response.status}")
        pass
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get detailed event publishing statistics"""
        
        health = await self.get_publisher_health()
        
        # Add additional stats
        health["statistics"] = {
            "queue_utilization": (len(self._event_queue) / self._max_queue_size) * 100,
            "events_per_minute": self._calculate_events_per_minute(),
            "average_batch_size": self._calculate_average_batch_size(),
            "uptime_minutes": self._calculate_uptime_minutes()
        }
        
        return health
    
    def _calculate_events_per_minute(self) -> float:
        """Calculate events per minute (mock calculation)"""
        # In real implementation, would track time windows
        return 10.5  # Mock value
    
    def _calculate_average_batch_size(self) -> float:
        """Calculate average batch size (mock calculation)"""
        if self._metrics.total_published == 0:
            return 0.0
        return min(self._batch_size, self._metrics.total_published)
    
    def _calculate_uptime_minutes(self) -> float:
        """Calculate uptime in minutes (mock calculation)"""
        # In real implementation, would track initialization time
        return 60.0  # Mock value
    
    async def flush_pending_events(self) -> int:
        """Flush any pending events to ensure delivery"""
        
        pending_count = len(self._event_queue)
        
        if pending_count > 0:
            logger.info(f"Flushing {pending_count} pending events")
            
            # Force process all pending events
            batch = []
            while self._event_queue:
                event = self._event_queue.popleft()
                batch.append(event)
                self._metrics.events_pending -= 1
            
            if batch:
                await self._publish_batch_to_destination(batch)
        
        return pending_count
    
    async def shutdown(self) -> None:
        """Graceful shutdown of event publisher"""
        
        logger.info("Shutting down Event Publisher...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Flush pending events
        await self.flush_pending_events()
        
        # Stop background processing
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self._is_initialized = False
        logger.info("Event Publisher shutdown completed")