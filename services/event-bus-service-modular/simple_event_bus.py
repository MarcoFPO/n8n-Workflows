"""
Vereinfachter Event-Bus Service für aktienanalyse-ökosystem
Standalone Service ohne komplexe Dependencies
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import redis.asyncio as aioredis
import aio_pika
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event-bus-simple")

# Pydantic Models
class EventMessage(BaseModel):
    event_type: str
    stream_id: Optional[str] = None
    data: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class EventQuery(BaseModel):
    event_types: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    limit: int = 100

class SimpleEventBus:
    """Vereinfachter Event-Bus Service"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Event-Bus Service Simple",
            description="Vereinfachter zentraler Event-Hub",
            version="1.0.0"
        )
        
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Storage
        self.redis_client = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.published_events = 0
        self.stored_events = 0
        
        # Routes registrieren
        self._register_routes()
        
        # Events
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)
    
    async def startup(self):
        """Service startup"""
        try:
            logger.info("Starting Simple Event-Bus Service...")
            
            # Redis verbinden
            self.redis_client = aioredis.from_url(
                "redis://localhost:6379/1",
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connected")
            
            # RabbitMQ verbinden
            self.rabbitmq_connection = await aio_pika.connect_robust(
                "amqp://guest:guest@localhost:5672/"
            )
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            await self.rabbitmq_channel.declare_exchange(
                "aktienanalyse_events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            logger.info("RabbitMQ connected")
            
            logger.info("Simple Event-Bus Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            raise
    
    async def shutdown(self):
        """Service shutdown"""
        try:
            logger.info("Shutting down Simple Event-Bus Service...")
            
            if self.rabbitmq_connection:
                await self.rabbitmq_connection.close()
            
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("Simple Event-Bus Service shut down")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _register_routes(self):
        """API Routes registrieren"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "event-bus-simple",
                "version": "1.0.0",
                "status": "running",
                "port": 8014,
                "published_events": self.published_events,
                "stored_events": self.stored_events
            }
        
        @self.app.get("/health")
        async def health():
            redis_ok = False
            rabbitmq_ok = False
            
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    redis_ok = True
            except:
                pass
                
            rabbitmq_ok = self.rabbitmq_connection and not self.rabbitmq_connection.is_closed
            
            return {
                "status": "healthy" if redis_ok and rabbitmq_ok else "unhealthy",
                "service": "event-bus-simple",
                "redis_connected": redis_ok,
                "rabbitmq_connected": rabbitmq_ok,
                "published_events": self.published_events,
                "stored_events": self.stored_events
            }
        
        @self.app.post("/events/publish")
        async def publish_event(event: EventMessage):
            """Event publizieren"""
            try:
                # Event-ID generieren
                event_id = str(uuid4())
                stream_id = event.stream_id or f"event-{event_id[:8]}"
                correlation_id = event.correlation_id or str(uuid4())
                
                # Event-Daten zusammenstellen
                event_data = {
                    "id": event_id,
                    "event_type": event.event_type,
                    "stream_id": stream_id,
                    "data": event.data,
                    "source": event.source,
                    "correlation_id": correlation_id,
                    "metadata": event.metadata or {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "published_by": "event-bus-simple"
                }
                
                # In Redis speichern
                if self.redis_client:
                    await self._store_event(event_data)
                
                # Über RabbitMQ publizieren
                if self.rabbitmq_channel:
                    await self._publish_to_rabbitmq(event_data)
                
                self.published_events += 1
                
                return {
                    "status": "published",
                    "event_id": event_id,
                    "stream_id": stream_id,
                    "event_type": event.event_type,
                    "timestamp": event_data["timestamp"]
                }
                
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/events/query")
        async def query_events(
            event_types: Optional[str] = None,
            sources: Optional[str] = None,
            limit: int = 100
        ):
            """Events aus Store abfragen"""
            try:
                if not self.redis_client:
                    return {"events": [], "count": 0}
                
                # Simple Query-Implementierung
                events = []
                
                # Scan für Events
                cursor = 0
                count = 0
                
                while cursor != 0 or count == 0:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match="event:*",
                        count=min(limit, 100)
                    )
                    
                    for key in keys:
                        if len(events) >= limit:
                            break
                            
                        event_data = await self.redis_client.hget(key, "data")
                        if event_data:
                            event = json.loads(event_data)
                            
                            # Filter anwenden
                            if event_types and event.get("event_type") not in event_types.split(","):
                                continue
                            if sources and event.get("source") not in sources.split(","):
                                continue
                                
                            events.append(event)
                    
                    count += 1
                    if len(events) >= limit or count > 10:  # Max 10 scans
                        break
                
                # Nach Timestamp sortieren
                events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                return {
                    "events": events[:limit],
                    "count": len(events)
                }
                
            except Exception as e:
                logger.error(f"Failed to query events: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/statistics")
        async def statistics():
            """Service-Statistiken"""
            redis_connected = False
            redis_keys_count = 0
            
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    redis_connected = True
                    redis_keys_count = await self.redis_client.dbsize()
            except:
                pass
            
            return {
                "service": "event-bus-simple",
                "status": "running",
                "published_events": self.published_events,
                "stored_events": self.stored_events,
                "redis": {
                    "connected": redis_connected,
                    "keys_count": redis_keys_count
                },
                "rabbitmq": {
                    "connected": self.rabbitmq_connection and not self.rabbitmq_connection.is_closed
                }
            }
    
    async def _store_event(self, event_data: Dict[str, Any]):
        """Event in Redis speichern"""
        try:
            event_id = event_data["id"]
            event_key = f"event:{event_id}"
            
            # Event speichern
            await self.redis_client.hset(event_key, mapping={
                "data": json.dumps(event_data),
                "event_type": event_data["event_type"],
                "source": event_data["source"],
                "timestamp": event_data["timestamp"]
            })
            
            # Index aktualisieren
            await self.redis_client.sadd(f"events_by_type:{event_data['event_type']}", event_id)
            await self.redis_client.sadd(f"events_by_source:{event_data['source']}", event_id)
            
            # TTL setzen (7 Tage)
            await self.redis_client.expire(event_key, 7 * 24 * 3600)
            
            self.stored_events += 1
            
            logger.debug(f"Event stored: {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
    
    async def _publish_to_rabbitmq(self, event_data: Dict[str, Any]):
        """Event über RabbitMQ publizieren"""
        try:
            routing_key = f"events.{event_data['event_type']}.{event_data['source']}"
            
            message = aio_pika.Message(
                json.dumps(event_data).encode(),
                content_type="application/json",
                correlation_id=event_data["correlation_id"],
                message_id=event_data["id"],
                timestamp=datetime.utcnow()
            )
            
            exchange = await self.rabbitmq_channel.get_exchange("aktienanalyse_events")
            await exchange.publish(message, routing_key=routing_key)
            
            logger.debug(f"Event published to RabbitMQ: {routing_key}")
            
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")


def main():
    """Main entry point"""
    event_bus = SimpleEventBus()
    
    logger.info("Starting Simple Event-Bus Service on port 8014...")
    
    config = uvicorn.Config(
        app=event_bus.app,
        host="0.0.0.0",
        port=8014,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        raise


if __name__ == "__main__":
    main()