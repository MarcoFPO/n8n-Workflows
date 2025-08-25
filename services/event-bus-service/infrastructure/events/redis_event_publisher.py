"""
Redis Event Publisher Implementation - Infrastructure Layer
Clean Architecture - Concrete Implementation von IEventPublisher

CLEAN ARCHITECTURE: Infrastructure Layer
Redis-basierte Implementierung des Event Publishing Contracts

Code-Qualität: HÖCHSTE PRIORITÄT
Autor: Claude Code - Infrastructure Implementation Specialist
Datum: 24. August 2025
Version: 7.0.0
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

import aioredis
from aioredis import Redis

from application.interfaces.event_publisher import IEventPublisher
from presentation.models import EventMessage, EventTypeEnum


class RedisEventPublisher(IEventPublisher):
    """
    Redis-based Event Publisher Implementation
    
    CLEAN ARCHITECTURE: Infrastructure Layer Implementation
    Implementiert IEventPublisher Interface für Redis Pub/Sub
    """
    
    def __init__(
        self, 
        redis_client: Redis,
        channel_prefix: str = "events",
        event_ttl: int = 86400
    ):
        self.redis_client = redis_client
        self.channel_prefix = channel_prefix
        self.event_ttl = event_ttl
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        
        # Metrics tracking
        self._events_published = 0
        self._events_failed = 0
        self._start_time = datetime.now()
    
    async def initialize(self) -> None:
        """Initialize the Redis event publisher"""
        try:
            # Test Redis connection
            await self.redis_client.ping()
            self._initialized = True
            self.logger.info("✅ Redis Event Publisher initialized")
        except Exception as e:
            self.logger.error(f"❌ Redis Event Publisher initialization failed: {e}")
            raise
    
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
        Publish event to Redis
        
        CLEAN ARCHITECTURE: Infrastructure Implementation
        """
        if not self._initialized:
            raise RuntimeError("Redis Event Publisher not initialized")
        
        try:
            # Generate event ID and correlation ID if not provided
            event_id = str(uuid.uuid4())
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            
            # Build event message
            event_message = {
                "event_id": event_id,
                "event_type": event_type,
                "correlation_id": correlation_id,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "event_data": event_data,
                "metadata": metadata or {},
                "priority": priority,
                "target_services": target_services
            }
            
            # Serialize event
            event_json = json.dumps(event_message, ensure_ascii=False, default=str)
            
            # Publish to Redis channel
            channel = f"{self.channel_prefix}:{event_type}"
            await self.redis_client.publish(channel, event_json)
            
            # Store event with TTL für Event Store Query Support
            event_key = f"event:{event_id}"
            await self.redis_client.setex(
                event_key,
                self.event_ttl,
                event_json
            )
            
            # Update metrics
            self._events_published += 1
            
            self.logger.debug(f"📡 Event published: {event_type} -> {channel}")
            return event_id
            
        except Exception as e:
            self._events_failed += 1
            self.logger.error(f"❌ Event publishing failed: {e}")
            raise
    
    async def publish_event_message(self, event: EventMessage) -> str:
        """
        Publish structured event message
        
        CLEAN ARCHITECTURE: Infrastructure Implementation
        """
        return await self.publish(
            event_type=event.event_type.value if isinstance(event.event_type, EventTypeEnum) else event.event_type,
            event_data=event.event_data,
            source=event.source,
            correlation_id=event.correlation_id,
            metadata=event.metadata,
            priority=event.priority.value if hasattr(event.priority, 'value') else event.priority
        )
    
    async def publish_batch(self, events: List[EventMessage]) -> List[str]:
        """
        Publish multiple events in batch
        
        CLEAN ARCHITECTURE: Infrastructure Implementation
        """
        if not self._initialized:
            raise RuntimeError("Redis Event Publisher not initialized")
        
        event_ids = []
        
        try:
            # Use Redis pipeline für bessere Performance
            pipeline = self.redis_client.pipeline()
            
            for event in events:
                event_id = str(uuid.uuid4())
                correlation_id = event.correlation_id or str(uuid.uuid4())
                
                event_message = {
                    "event_id": event_id,
                    "event_type": event.event_type.value if isinstance(event.event_type, EventTypeEnum) else event.event_type,
                    "correlation_id": correlation_id,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.now().isoformat(),
                    "event_data": event.event_data,
                    "metadata": event.metadata or {},
                    "priority": event.priority.value if hasattr(event.priority, 'value') else event.priority
                }
                
                event_json = json.dumps(event_message, ensure_ascii=False, default=str)
                
                # Add to pipeline
                channel = f"{self.channel_prefix}:{event_message['event_type']}"
                pipeline.publish(channel, event_json)
                pipeline.setex(f"event:{event_id}", self.event_ttl, event_json)
                
                event_ids.append(event_id)
            
            # Execute pipeline
            await pipeline.execute()
            
            # Update metrics
            self._events_published += len(events)
            
            self.logger.debug(f"📡 Batch published: {len(events)} events")
            return event_ids
            
        except Exception as e:
            self._events_failed += len(events)
            self.logger.error(f"❌ Batch event publishing failed: {e}")
            raise
    
    async def get_connected_services(self) -> List[str]:
        """
        Get currently connected services
        
        CLEAN ARCHITECTURE: Infrastructure Implementation
        """
        try:
            # Get active Redis clients via CLIENT LIST
            client_info = await self.redis_client.execute_command("CLIENT", "LIST")
            
            # Parse client information to extract service names
            connected_services = set()
            for line in client_info.split('\n'):
                if 'name=' in line:
                    name_part = [part for part in line.split() if part.startswith('name=')]
                    if name_part:
                        service_name = name_part[0].split('=')[1]
                        if service_name and service_name != 'unknown':
                            connected_services.add(service_name)
            
            return list(connected_services)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get connected services: {e}")
            return []
    
    async def is_healthy(self) -> bool:
        """
        Check Redis publisher health
        
        CLEAN ARCHITECTURE: Infrastructure Health Check
        """
        try:
            if not self._initialized:
                return False
            
            # Test Redis connection
            await self.redis_client.ping()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Redis health check failed: {e}")
            return False
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get publishing metrics
        
        CLEAN ARCHITECTURE: Infrastructure Monitoring
        """
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        return {
            "events_published_total": self._events_published,
            "events_failed_total": self._events_failed,
            "success_rate": (
                self._events_published / (self._events_published + self._events_failed) 
                if (self._events_published + self._events_failed) > 0 else 1.0
            ),
            "uptime_seconds": uptime,
            "redis_connected": await self.is_healthy(),
            "initialized": self._initialized,
            "channel_prefix": self.channel_prefix,
            "event_ttl_seconds": self.event_ttl
        }
    
    async def cleanup(self) -> None:
        """Cleanup Redis resources"""
        try:
            if self.redis_client:
                await self.redis_client.aclose()
            self._initialized = False
            self.logger.info("✅ Redis Event Publisher cleaned up")
        except Exception as e:
            self.logger.error(f"❌ Redis Event Publisher cleanup failed: {e}")