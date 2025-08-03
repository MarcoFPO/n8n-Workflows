"""
Event-Bus Service für aktienanalyse-ökosystem
Zentrale Event-Routing und Pub/Sub Koordination
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import redis.asyncio as redis
import aio_pika
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# ================================================================
# MODELS
# ================================================================

class Event(BaseModel):
    event_id: Optional[str] = None
    stream_id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    event_data: Dict
    metadata: Dict = {}
    created_at: Optional[datetime] = None

class EventSubscription(BaseModel):
    subscriber_id: str
    event_types: List[str]
    callback_url: Optional[str] = None

# ================================================================
# EVENT-BUS SERVICE
# ================================================================

class EventBusService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.rabbitmq_connection: Optional[aio_pika.Connection] = None
        self.rabbitmq_channel: Optional[aio_pika.Channel] = None
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, EventSubscription] = {}
        
    async def initialize(self):
        """Initialize connections to Redis and RabbitMQ"""
        try:
            # Redis connection
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url)
            await self.redis.ping()
            logger.info("Redis connection established", url=redis_url)
            
            # RabbitMQ connection
            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://aktienanalyse:secure_password@localhost:5672/aktienanalyse")
            self.rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            
            # Declare exchanges
            await self.rabbitmq_channel.declare_exchange(
                "events", aio_pika.ExchangeType.TOPIC, durable=True
            )
            await self.rabbitmq_channel.declare_exchange(
                "commands", aio_pika.ExchangeType.DIRECT, durable=True
            )
            
            logger.info("RabbitMQ connection established", url=rabbitmq_url)
            
        except Exception as e:
            logger.error("Failed to initialize connections", error=str(e))
            raise
    
    async def publish_event(self, event: Event) -> bool:
        """Publish event to both Redis and RabbitMQ"""
        try:
            event_json = event.model_dump_json()
            
            # Publish to Redis (Pub/Sub for real-time)
            redis_channel = f"events.{event.event_type}"
            await self.redis.publish(redis_channel, event_json)
            
            # Publish to RabbitMQ (Persistent queuing)
            routing_key = f"{event.aggregate_type}.{event.event_type}"
            await self.rabbitmq_channel.default_exchange.publish(
                aio_pika.Message(
                    event_json.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={"event_type": event.event_type}
                ),
                routing_key=routing_key
            )
            
            # Broadcast to WebSocket connections
            await self._broadcast_websocket(event)
            
            logger.info(
                "Event published successfully",
                event_type=event.event_type,
                stream_id=event.stream_id,
                redis_channel=redis_channel,
                routing_key=routing_key
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event.event_type,
                error=str(e)
            )
            return False
    
    async def _broadcast_websocket(self, event: Event):
        """Broadcast event to all WebSocket connections"""
        if not self.websocket_connections:
            return
            
        event_json = event.model_dump_json()
        disconnected_clients = []
        
        for client_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_text(event_json)
            except Exception as e:
                logger.warning(
                    "Failed to send event to WebSocket client",
                    client_id=client_id,
                    error=str(e)
                )
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.websocket_connections.pop(client_id, None)
    
    async def subscribe_events(self, subscription: EventSubscription):
        """Subscribe to specific event types"""
        self.subscriptions[subscription.subscriber_id] = subscription
        logger.info(
            "Event subscription created",
            subscriber_id=subscription.subscriber_id,
            event_types=subscription.event_types
        )
    
    async def add_websocket_connection(self, client_id: str, websocket: WebSocket):
        """Add WebSocket connection for real-time events"""
        self.websocket_connections[client_id] = websocket
        logger.info("WebSocket connection added", client_id=client_id)
    
    async def remove_websocket_connection(self, client_id: str):
        """Remove WebSocket connection"""
        self.websocket_connections.pop(client_id, None)
        logger.info("WebSocket connection removed", client_id=client_id)

# ================================================================
# FASTAPI APPLICATION
# ================================================================

# Global event bus instance
event_bus = EventBusService()

app = FastAPI(
    title="Aktienanalyse Event-Bus Service",
    description="Central Event-Bus for aktienanalyse-ökosystem with Redis Pub/Sub and RabbitMQ",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize event bus on startup"""
    await event_bus.initialize()
    logger.info("Event-Bus Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if event_bus.rabbitmq_connection:
        await event_bus.rabbitmq_connection.close()
    if event_bus.redis:
        await event_bus.redis.close()
    logger.info("Event-Bus Service shutdown completed")

# ================================================================
# API ENDPOINTS
# ================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        await event_bus.redis.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"
    
    try:
        # Check RabbitMQ
        if event_bus.rabbitmq_connection and not event_bus.rabbitmq_connection.is_closed:
            rabbitmq_status = "healthy"
        else:
            rabbitmq_status = "unhealthy"
    except:
        rabbitmq_status = "unhealthy"
    
    return {
        "service": "event-bus",
        "status": "healthy" if redis_status == "healthy" and rabbitmq_status == "healthy" else "degraded",
        "redis": redis_status,
        "rabbitmq": rabbitmq_status,
        "websocket_connections": len(event_bus.websocket_connections),
        "subscriptions": len(event_bus.subscriptions),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/events/publish")
async def publish_event(event: Event):
    """Publish event to the event bus"""
    if not event.created_at:
        event.created_at = datetime.now()
    
    success = await event_bus.publish_event(event)
    
    if success:
        return {"status": "published", "event_id": event.event_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to publish event")

@app.post("/events/subscribe")
async def subscribe_events(subscription: EventSubscription):
    """Subscribe to specific event types"""
    await event_bus.subscribe_events(subscription)
    return {"status": "subscribed", "subscriber_id": subscription.subscriber_id}

@app.get("/events/subscriptions")
async def list_subscriptions():
    """List all active subscriptions"""
    return {
        "subscriptions": list(event_bus.subscriptions.values()),
        "count": len(event_bus.subscriptions)
    }

@app.websocket("/events/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming"""
    await websocket.accept()
    
    client_id = f"ws_{datetime.now().timestamp()}"
    await event_bus.add_websocket_connection(client_id, websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back for ping/pong
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("WebSocket error", client_id=client_id, error=str(e))
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.remove_websocket_connection(client_id)

# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
        reload=False
    )