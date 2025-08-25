#!/usr/bin/env python3
"""
Infrastructure Layer - Redis Event Publisher
Unified Profit Engine Enhanced v6.0 - Clean Architecture

EVENT PUBLISHER ADAPTER:
- Implementiert EventPublisher Interface
- Redis Event-Bus Integration (Port 8014)
- Event Persistence in PostgreSQL Event Store  
- Retry Logic und Error Handling

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

import json
import asyncio
import aioredis
import asyncpg
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4
import logging

from ...application.interfaces import EventPublisher


logger = logging.getLogger(__name__)


class RedisEventPublisher(EventPublisher):
    """
    Redis Event-Bus Integration für Event-Driven Architecture
    
    FEATURES:
    - Event Publishing über Redis Channels
    - Event Persistence in PostgreSQL Event Store
    - Retry Logic für fehlerhafte Events
    - Batch Event Publishing
    """
    
    def __init__(self, 
                 redis_client: aioredis.Redis,
                 db_pool: Optional[asyncpg.Pool] = None,
                 retry_count: int = 3):
        self.redis = redis_client
        self.db_pool = db_pool
        self.retry_count = retry_count
        
        # Service Metadata
        self.service_name = "unified-profit-engine-enhanced"
        self.service_version = "6.0"
    
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Publiziert einzelnes Event über Redis Event-Bus
        
        Event Format entspricht LLD v6.0 Spezifikation:
        - Event-Bus Integration über Port 8014
        - Event Persistence für Audit Trail
        - Correlation IDs für Event Tracing
        """
        event = self._create_event_envelope(event_type, event_data)
        
        for attempt in range(self.retry_count):
            try:
                logger.info(f"Publishing event {event_type} (attempt {attempt + 1})")
                
                # 1. Event in Redis Channel publizieren
                channel = f"events:{event_type}"
                await self.redis.publish(channel, json.dumps(event))
                
                # 2. Event in PostgreSQL Event Store persistieren (wenn verfügbar)
                if self.db_pool:
                    await self._persist_event(event)
                
                logger.info(f"Successfully published event {event['event_id']} to {channel}")
                return
                
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type} (attempt {attempt + 1}): {e}")
                
                if attempt == self.retry_count - 1:
                    logger.error(f"Failed to publish event {event_type} after {self.retry_count} attempts: {e}")
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def publish_batch(self, events: List[Dict[str, Any]]) -> None:
        """
        Publiziert mehrere Events in Batch für bessere Performance
        
        Format: List[{"event_type": str, "event_data": Dict}]
        """
        if not events:
            return
        
        logger.info(f"Publishing batch of {len(events)} events")
        
        try:
            # Events zu Event Envelopes konvertieren
            event_envelopes = []
            for event_spec in events:
                if "event_type" not in event_spec or "event_data" not in event_spec:
                    logger.error(f"Invalid event specification: {event_spec}")
                    continue
                
                envelope = self._create_event_envelope(
                    event_spec["event_type"], 
                    event_spec["event_data"]
                )
                event_envelopes.append(envelope)
            
            # Batch Publishing über Redis Pipeline
            pipe = self.redis.pipeline()
            
            for envelope in event_envelopes:
                channel = f"events:{envelope['metadata']['event_type']}"
                pipe.publish(channel, json.dumps(envelope))
            
            # Pipeline ausführen
            results = await pipe.execute()
            
            # Event Store Persistence (wenn verfügbar)
            if self.db_pool:
                await self._persist_events_batch(event_envelopes)
            
            successful_events = sum(1 for r in results if r > 0)
            logger.info(f"Successfully published {successful_events}/{len(event_envelopes)} events in batch")
            
        except Exception as e:
            logger.error(f"Batch event publishing failed: {e}")
            raise
    
    def _create_event_envelope(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Erstellt Event Envelope entsprechend LLD v6.0 Format
        
        Event Envelope Structure:
        - event_id: Unique Event ID
        - correlation_id: Für Event Tracing
        - event_type: Event Type Identifier
        - event_data: Actual Event Payload
        - metadata: Service Metadata und Timing
        """
        return {
            "event_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "event_type": event_type,
            "event_data": event_data,
            "metadata": {
                "service": self.service_name,
                "version": self.service_version,
                "published_at": datetime.now().isoformat(),
                "event_type": event_type,
                "publisher_host": "unified-profit-engine-enhanced",
                "sequence_number": None  # Kann für Event Ordering genutzt werden
            },
            "created_at": datetime.now().isoformat()
        }
    
    async def _persist_event(self, event: Dict[str, Any]) -> None:
        """
        Persistiert Event in PostgreSQL Event Store für Audit Trail
        
        Event Store Schema:
        - event_id (UUID)
        - event_type (VARCHAR)
        - event_data (JSONB)
        - metadata (JSONB)  
        - created_at (TIMESTAMP)
        """
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO event_store 
                    (event_id, correlation_id, event_type, event_data, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                event["event_id"],
                event["correlation_id"],
                event["event_type"],
                json.dumps(event["event_data"]),
                json.dumps(event["metadata"]),
                datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
                )
                
        except Exception as e:
            logger.error(f"Failed to persist event {event['event_id']} to event store: {e}")
            # Don't raise - Event Publishing sollte nicht wegen Event Store Fehlern fehlschlagen
    
    async def _persist_events_batch(self, events: List[Dict[str, Any]]) -> None:
        """Persistiert Batch von Events in Event Store"""
        if not self.db_pool or not events:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Batch Insert mit executemany
                values = []
                for event in events:
                    values.append((
                        event["event_id"],
                        event["correlation_id"], 
                        event["event_type"],
                        json.dumps(event["event_data"]),
                        json.dumps(event["metadata"]),
                        datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
                    ))
                
                await conn.executemany("""
                    INSERT INTO event_store 
                    (event_id, correlation_id, event_type, event_data, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, values)
                
                logger.info(f"Persisted {len(events)} events to event store")
                
        except Exception as e:
            logger.error(f"Failed to persist event batch to event store: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Event Publisher"""
        try:
            # Redis Connectivity Test
            await self.redis.ping()
            redis_healthy = True
            redis_error = None
        except Exception as e:
            redis_healthy = False
            redis_error = str(e)
        
        # Database Connectivity Test
        db_healthy = True
        db_error = None
        
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            except Exception as e:
                db_healthy = False
                db_error = str(e)
        
        overall_healthy = redis_healthy and db_healthy
        
        return {
            "healthy": overall_healthy,
            "redis": {
                "healthy": redis_healthy,
                "error": redis_error
            },
            "database": {
                "healthy": db_healthy,
                "error": db_error,
                "enabled": self.db_pool is not None
            },
            "service": {
                "name": self.service_name,
                "version": self.service_version
            },
            "checked_at": datetime.now().isoformat()
        }