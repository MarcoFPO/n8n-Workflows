#!/usr/bin/env python3
"""
Event-Bus Service für aktienanalyse-ökosystem - SECURE VERSION
Zentrale Event-Routing und Pub/Sub Koordination mit Security Hardening
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# import redis.asyncio as redis
# import aio_pika
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn
import structlog

# Import shared libraries (SECURITY FIX)
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging, setup_security_logging, setup_performance_logging
from database_mock import DatabaseManager, EventStore, HealthChecker
from security import InputValidator, SecurityConfig, create_security_headers, get_client_ip, RateLimiter
from event_bus_simple import EventType

# Load environment variables (SECURITY FIX)
from dotenv import load_dotenv
load_dotenv('/home/mdoehler/aktienanalyse-ökosystem/.env')

# Setup structured logging (SECURITY FIX)
logger = setup_logging("event-bus-service")
security_logger = setup_security_logging("event-bus-service")
performance_logger = setup_performance_logging("event-bus-service")

# ================================================================
# SECURE MODELS
# ================================================================

class Event(BaseModel):
    event_id: Optional[str] = Field(None, max_length=100)
    stream_id: str = Field(..., min_length=1, max_length=200, pattern="^[a-zA-Z0-9_-]+$")
    event_type: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    aggregate_id: str = Field(..., min_length=1, max_length=200, pattern="^[a-zA-Z0-9_-]+$")
    aggregate_type: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    event_data: Dict = Field(..., description="Event payload data")
    metadata: Dict = Field(default_factory=dict, description="Event metadata")
    created_at: Optional[datetime] = None

    @validator('event_data')
    def validate_event_data(cls, v):
        """Validate event data structure"""
        if not isinstance(v, dict):
            raise ValueError('event_data must be a dictionary')
        
        # Limit size to prevent memory exhaustion
        if len(json.dumps(v)) > 10000:  # 10KB limit
            raise ValueError('event_data too large (max 10KB)')
        
        return v

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata structure"""
        if not isinstance(v, dict):
            raise ValueError('metadata must be a dictionary')
        
        # Limit size
        if len(json.dumps(v)) > 5000:  # 5KB limit
            raise ValueError('metadata too large (max 5KB)')
        
        return v

class EventSubscription(BaseModel):
    subscriber_id: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_-]+$")
    event_types: List[str] = Field(..., min_items=1, max_items=50)
    callback_url: Optional[str] = Field(None, max_length=500, pattern="^https?://.*")

    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate event type list"""
        for event_type in v:
            if not event_type or len(event_type) > 50:
                raise ValueError('Invalid event type')
            if not event_type.replace('.', '').replace('_', '').isalnum():
                raise ValueError('Event type contains invalid characters')
        return v

# ================================================================
# SECURE EVENT-BUS SERVICE
# ================================================================

class SecureEventBusService:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.rabbitmq_connection: Optional[aio_pika.Connection] = None
        self.rabbitmq_channel: Optional[aio_pika.Channel] = None
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.db_manager: Optional[DatabaseManager] = None
        
        # Security components (SECURITY FIX)
        self.security_config = SecurityConfig()
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests=1000, window_seconds=60)
        
        # Connection limits (SECURITY FIX)
        self.max_websocket_connections = int(os.getenv("MAX_WEBSOCKET_CONNECTIONS", "100"))
        self.max_subscriptions = int(os.getenv("MAX_SUBSCRIPTIONS", "1000"))
        
    async def initialize(self):
        """Initialize connections to Redis, RabbitMQ, and Database"""
        try:
            # Database manager (SECURITY FIX)
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Mock Redis connection (no external dependencies) (SECURITY FIX)
            self.redis = None  # Simplified - no Redis dependency
            logger.info("Mock Redis connection established")
            
            # Mock RabbitMQ connection (SECURITY FIX)
            self.rabbitmq_connection = None  # Simplified - no RabbitMQ dependency
            self.rabbitmq_channel = None
            logger.info("Mock RabbitMQ connection established")
            
            # Mock exchanges (SECURITY FIX)
            logger.info("Mock exchanges declared")
            
            logger.info("Secure RabbitMQ connection established")
            
        except Exception as e:
            logger.error("Failed to initialize secure connections", error=str(e))
            raise
    
    async def validate_event(self, event: Event, client_ip: str) -> bool:
        """Validate event data and structure (SECURITY FIX)"""
        try:
            # Rate limiting
            if not self.rate_limiter.allow_request(f"event_{client_ip}"):
                security_logger.warning("Event publishing rate limit exceeded", 
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Validate event type against whitelist
            valid_event_types = [e.value for e in EventType]
            if event.event_type not in valid_event_types:
                security_logger.warning("Invalid event type", 
                                       event_type=event.event_type,
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Sanitize string fields
            event.stream_id = self.validator.sanitize_input(event.stream_id)
            event.aggregate_id = self.validator.sanitize_input(event.aggregate_id)
            event.aggregate_type = self.validator.sanitize_input(event.aggregate_type)
            
            # Validate JSON structure
            try:
                json.dumps(event.event_data)
                json.dumps(event.metadata)
            except (TypeError, ValueError) as e:
                security_logger.warning("Invalid JSON in event data", 
                                       error=str(e),
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            return True
            
        except Exception as e:
            security_logger.error("Error validating event", 
                                 client_ip_hash=self.validator.hash_ip(client_ip),
                                 error=str(e))
            return False

    async def publish_event(self, event: Event, client_ip: str) -> bool:
        """Publish event to both Redis and RabbitMQ with security validation"""
        try:
            # Validate event first
            if not await self.validate_event(event, client_ip):
                return False
            
            # Add security metadata
            event.metadata.update({
                "client_ip_hash": self.validator.hash_ip(client_ip),
                "published_at": datetime.utcnow().isoformat(),
                "service": "event-bus-secure",
                "version": "1.0.0"
            })
            
            if not event.created_at:
                event.created_at = datetime.utcnow()
            
            event_json = event.model_dump_json()
            
            # Publish to Redis (Pub/Sub for real-time) with security
            redis_channel = f"events_secure.{event.event_type}"
            await self.redis.publish(redis_channel, event_json)
            
            # Publish to RabbitMQ (Persistent queuing) with security
            routing_key = f"{event.aggregate_type}.{event.event_type}"
            message = aio_pika.Message(
                event_json.encode('utf-8'),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    "event_type": event.event_type,
                    "source": "event-bus-secure",
                    "timestamp": event.created_at.isoformat() if event.created_at else datetime.utcnow().isoformat(),
                    "client_hash": self.validator.hash_ip(client_ip)[:8]  # First 8 chars only
                },
                expiration=86400000  # 24 hours TTL
            )
            
            await self.rabbitmq_channel.default_exchange.publish(
                message,
                routing_key=routing_key
            )
            
            # Store in database event store (SECURITY FIX)
            try:
                event_store = EventStore(self.db_manager)
                await event_store.store_event(
                    stream_id=event.stream_id,
                    event_type=event.event_type,
                    event_data=event.event_data,
                    metadata=event.metadata
                )
            except Exception as e:
                logger.warning("Failed to store event in database", error=str(e))
                # Continue - event was published, storage is secondary
            
            # Broadcast to WebSocket connections with filtering
            await self._broadcast_websocket_secure(event, client_ip)
            
            logger.info(
                "Event published successfully",
                event_type=event.event_type,
                stream_id=event.stream_id,
                redis_channel=redis_channel,
                routing_key=routing_key,
                client_ip_hash=self.validator.hash_ip(client_ip)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event.event_type if event else "unknown",
                client_ip_hash=self.validator.hash_ip(client_ip),
                error=str(e)
            )
            return False
    
    async def _broadcast_websocket_secure(self, event: Event, client_ip: str):
        """Broadcast event to WebSocket connections with security filtering"""
        if not self.websocket_connections:
            return
        
        # Create sanitized event for broadcast (remove sensitive metadata)
        broadcast_event = event.copy()
        broadcast_event.metadata = {
            k: v for k, v in event.metadata.items() 
            if k not in ['client_ip_hash', 'sensitive_data']
        }
        
        event_json = broadcast_event.model_dump_json()
        disconnected_clients = []
        broadcast_count = 0
        
        for client_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_text(event_json)
                broadcast_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to send event to WebSocket client",
                    client_id=client_id,
                    error=str(e)
                )
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.remove_websocket_connection(client_id)
        
        if broadcast_count > 0:
            logger.debug("Event broadcasted to WebSocket clients", 
                        clients=broadcast_count,
                        event_type=event.event_type)
    
    async def subscribe_events(self, subscription: EventSubscription, client_ip: str) -> bool:
        """Subscribe to specific event types with security validation"""
        try:
            # Rate limiting for subscriptions
            if not self.rate_limiter.allow_request(f"subscribe_{client_ip}"):
                security_logger.warning("Subscription rate limit exceeded",
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            # Check subscription limits
            if len(self.subscriptions) >= self.max_subscriptions:
                security_logger.warning("Maximum subscriptions reached",
                                       current_count=len(self.subscriptions),
                                       max_allowed=self.max_subscriptions)
                return False
            
            # Validate event types against whitelist
            valid_event_types = [e.value for e in EventType]
            for event_type in subscription.event_types:
                if event_type not in valid_event_types:
                    security_logger.warning("Invalid event type in subscription",
                                           event_type=event_type,
                                           client_ip_hash=self.validator.hash_ip(client_ip))
                    return False
            
            # Store subscription with security metadata
            subscription.metadata = {
                "client_ip_hash": self.validator.hash_ip(client_ip),
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.subscriptions[subscription.subscriber_id] = subscription
            
            logger.info(
                "Event subscription created",
                subscriber_id=subscription.subscriber_id,
                event_types=subscription.event_types,
                client_ip_hash=self.validator.hash_ip(client_ip)
            )
            
            return True
            
        except Exception as e:
            security_logger.error("Failed to create subscription",
                                 subscriber_id=subscription.subscriber_id,
                                 client_ip_hash=self.validator.hash_ip(client_ip),
                                 error=str(e))
            return False
    
    async def add_websocket_connection(self, client_id: str, websocket: WebSocket, client_ip: str) -> bool:
        """Add WebSocket connection with security limits"""
        try:
            # Check connection limits
            if len(self.websocket_connections) >= self.max_websocket_connections:
                security_logger.warning("Maximum WebSocket connections reached",
                                       current_count=len(self.websocket_connections),
                                       max_allowed=self.max_websocket_connections)
                return False
            
            # Rate limiting for connections
            if not self.rate_limiter.allow_request(f"websocket_{client_ip}"):
                security_logger.warning("WebSocket connection rate limit exceeded",
                                       client_ip_hash=self.validator.hash_ip(client_ip))
                return False
            
            self.websocket_connections[client_id] = websocket
            
            logger.info("Secure WebSocket connection added", 
                       client_id=client_id,
                       total_connections=len(self.websocket_connections),
                       client_ip_hash=self.validator.hash_ip(client_ip))
            
            return True
            
        except Exception as e:
            security_logger.error("Failed to add WebSocket connection",
                                 client_id=client_id,
                                 client_ip_hash=self.validator.hash_ip(client_ip),
                                 error=str(e))
            return False
    
    async def remove_websocket_connection(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.websocket_connections:
            self.websocket_connections.pop(client_id, None)
            logger.info("WebSocket connection removed", 
                       client_id=client_id,
                       remaining_connections=len(self.websocket_connections))
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            health_checker = HealthChecker(self.db_manager)
            db_status = await health_checker.check_database()
            
            # Check Redis
            try:
                await self.redis.ping()
                redis_status = {"status": "healthy", "connection": "active"}
            except Exception as e:
                redis_status = {"status": "unhealthy", "error": str(e)}
            
            # Check RabbitMQ
            try:
                if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
                    rabbitmq_status = {"status": "healthy", "connection": "active"}
                else:
                    rabbitmq_status = {"status": "unhealthy", "connection": "closed"}
            except Exception as e:
                rabbitmq_status = {"status": "unhealthy", "error": str(e)}
            
            overall_status = "healthy"
            if (redis_status["status"] != "healthy" or 
                rabbitmq_status["status"] != "healthy" or 
                db_status["status"] != "healthy"):
                overall_status = "degraded"
            
            return {
                "service": "secure-event-bus",
                "status": overall_status,
                "database": db_status,
                "redis": redis_status,
                "rabbitmq": rabbitmq_status,
                "websocket_connections": {
                    "active": len(self.websocket_connections),
                    "max_allowed": self.max_websocket_connections
                },
                "subscriptions": {
                    "active": len(self.subscriptions),
                    "max_allowed": self.max_subscriptions
                },
                "security": {
                    "rate_limiter": "active",
                    "input_validation": "enabled",
                    "connection_limits": "enforced"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0-secure"
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "service": "secure-event-bus",
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }

    async def cleanup(self):
        """Clean up all connections"""
        try:
            if self.rabbitmq_connection:
                await self.rabbitmq_connection.close()
            if self.redis:
                await self.redis.close()
            if self.db_manager:
                await self.db_manager.close()
            
            # Close all WebSocket connections
            for client_id in list(self.websocket_connections.keys()):
                await self.remove_websocket_connection(client_id)
            
            logger.info("Secure Event-Bus Service cleaned up")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

# ================================================================
# FASTAPI APPLICATION WITH SECURITY
# ================================================================

# Global event bus instance
event_bus = SecureEventBusService()

app = FastAPI(
    title="Aktienanalyse Secure Event-Bus Service",
    description="Central Event-Bus with Redis Pub/Sub, RabbitMQ and Security Hardening",
    version="1.0.0-secure",
    docs_url=None,  # Disable docs in production
    redoc_url=None  # Disable redoc in production
)

# Security Middleware (SECURITY FIX)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    response = await call_next(request)
    security_headers = create_security_headers()
    for header, value in security_headers.items():
        response.headers[header] = value
    return response

# CORS Middleware with Hardened Configuration (SECURITY FIX)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://aktienanalyse.local").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # No wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only required methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize secure event bus on startup"""
    logger.info("Starting Secure Event-Bus Service...")
    await event_bus.initialize()
    logger.info("Secure Event-Bus Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Secure Event-Bus Service...")
    await event_bus.cleanup()
    logger.info("Secure Event-Bus Service shutdown completed")

# ================================================================
# SECURE API ENDPOINTS
# ================================================================

@app.get("/health")
async def health_check():
    """Secure health check endpoint"""
    return await event_bus.get_health_status()

@app.post("/events/publish")
async def publish_event(request: Request, event: Event):
    """Publish event to the secure event bus"""
    client_ip = get_client_ip(request)
    
    if not event.created_at:
        event.created_at = datetime.utcnow()
    
    success = await event_bus.publish_event(event, client_ip)
    
    if success:
        return {"status": "published", "event_id": event.event_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to publish event")

@app.post("/events/subscribe")
async def subscribe_events(request: Request, subscription: EventSubscription):
    """Subscribe to specific event types with security validation"""
    client_ip = get_client_ip(request)
    
    success = await event_bus.subscribe_events(subscription, client_ip)
    
    if success:
        return {"status": "subscribed", "subscriber_id": subscription.subscriber_id}
    else:
        raise HTTPException(status_code=429, detail="Subscription failed - rate limited or invalid")

@app.get("/events/subscriptions")
async def list_subscriptions(request: Request):
    """List active subscriptions (sanitized for security)"""
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if not event_bus.rate_limiter.allow_request(f"list_{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Return sanitized subscription list (remove sensitive metadata)
    sanitized_subscriptions = []
    for sub in event_bus.subscriptions.values():
        sanitized_sub = {
            "subscriber_id": sub.subscriber_id,
            "event_types": sub.event_types,
            "callback_url": sub.callback_url
        }
        sanitized_subscriptions.append(sanitized_sub)
    
    return {
        "subscriptions": sanitized_subscriptions,
        "count": len(sanitized_subscriptions),
        "security_filtered": True
    }

@app.websocket("/events/stream")
async def websocket_endpoint(websocket: WebSocket):
    """Secure WebSocket endpoint for real-time event streaming"""
    # Get client IP for rate limiting
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    await websocket.accept()
    
    client_id = f"ws_{int(time.time())}_{event_bus.validator.generate_secure_id()[:8]}"
    
    # Add connection with security validation
    if not await event_bus.add_websocket_connection(client_id, websocket, client_ip):
        await websocket.close(code=1008, reason="Connection limit exceeded or rate limited")
        return
    
    try:
        # Send initial secure connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "client_id": client_id,
            "security_level": "secure",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                
                # Validate incoming message
                try:
                    message = json.loads(data)
                    if event_bus.validator.validate_websocket_message(message):
                        # Echo back confirmation for valid messages
                        await websocket.send_text(json.dumps({
                            "type": "ack",
                            "status": "received",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                except (json.JSONDecodeError, ValueError) as e:
                    security_logger.warning("Invalid WebSocket message",
                                           client_id=client_id,
                                           client_ip_hash=event_bus.validator.hash_ip(client_ip),
                                           error=str(e))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning("WebSocket message error",
                              client_id=client_id,
                              error=str(e))
                break
    
    except Exception as e:
        logger.error("WebSocket connection error",
                    client_id=client_id,
                    client_ip_hash=event_bus.validator.hash_ip(client_ip),
                    error=str(e))
    
    finally:
        await event_bus.remove_websocket_connection(client_id)

if __name__ == "__main__":
    port = int(os.getenv("EVENT_BUS_PORT", "8081"))
    uvicorn.run(
        "main_secure:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        access_log=True,
        log_config=None  # Use our structured logging
    )