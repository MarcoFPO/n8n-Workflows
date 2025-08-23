"""
Real Event-Bus implementation for Aktienanalyse-Ökosystem
Replaces Mock implementations with actual Redis + RabbitMQ integration
"""

import os
import json
import asyncio
import redis.asyncio as aioredis
import aio_pika
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import structlog
from dataclasses import dataclass, asdict
from enum import Enum

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Standardized event types"""
    # State Change Events
    ANALYSIS_STATE_CHANGED = "analysis.state.changed"
    PORTFOLIO_STATE_CHANGED = "portfolio.state.changed"
    TRADING_STATE_CHANGED = "trading.state.changed"
    INTELLIGENCE_TRIGGERED = "intelligence.triggered"
    DATA_SYNCHRONIZED = "data.synchronized"
    SYSTEM_ALERT_RAISED = "system.alert.raised"
    USER_INTERACTION_LOGGED = "user.interaction.logged"
    CONFIG_UPDATED = "config.updated"
    
    # Request/Response Events for Event-Bus-Compliance
    DASHBOARD_REQUEST = "dashboard.request"
    DASHBOARD_RESPONSE = "dashboard.response"
    MARKET_DATA_REQUEST = "market.data.request"
    MARKET_DATA_RESPONSE = "market.data.response"
    TRADING_REQUEST = "trading.request"
    TRADING_RESPONSE = "trading.response"
    ACCOUNT_BALANCE_REQUEST = "account.balance.request"
    ACCOUNT_BALANCE_RESPONSE = "account.balance.response"
    ORDER_REQUEST = "order.request"
    ORDER_RESPONSE = "order.response"
    
    # System Events
    SYSTEM_HEALTH_REQUEST = "system.health.request"
    SYSTEM_HEALTH_RESPONSE = "system.health.response"
    MODULE_TEST_REQUEST = "module.test.request"
    MODULE_TEST_RESPONSE = "module.test.response"
    
    # Module Communication Events
    MODULE_REQUEST = "module.request"
    MODULE_RESPONSE = "module.response"


@dataclass
class Event:
    """Standardized event structure"""
    event_type: str
    stream_id: str
    data: Dict[str, Any]
    source: str
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Create event from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class EventBusConfig:
    """Event-Bus configuration from environment"""
    
    def __init__(self):
        # Redis configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD")
        
        # RabbitMQ configuration
        self.rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.rabbitmq_vhost = os.getenv("RABBITMQ_VHOST", "/")
        
        # Event-Bus settings
        self.exchange_name = "aktienanalyse_events"
        self.dead_letter_exchange = "aktienanalyse_events_dlx"
        self.retry_attempts = 3
        self.retry_delay = 5  # seconds


class EventBusConnector:
    """Real Event-Bus connector with Redis + RabbitMQ"""
    
    def __init__(self, service_name: str, config: EventBusConfig = None):
        self.service_name = service_name
        self.config = config or EventBusConfig()
        
        # Connections
        self.redis: Optional[aioredis.Redis] = None
        self.rabbitmq_connection: Optional[aio_pika.Connection] = None
        self.rabbitmq_channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        
        # State
        self.connected = False
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.consumers: List[aio_pika.Consumer] = []
        
    async def connect(self) -> bool:
        """Connect to Redis and RabbitMQ"""
        try:
            # Connect to Redis
            await self._connect_redis()
            
            # Connect to RabbitMQ
            await self._connect_rabbitmq()
            
            self.connected = True
            logger.info("Event-Bus connection established", 
                       service=self.service_name,
                       redis_connected=self.redis is not None,
                       rabbitmq_connected=self.rabbitmq_connection is not None)
            
            return True
            
        except Exception as e:
            logger.error("Failed to connect to Event-Bus", 
                        service=self.service_name,
                        error=str(e))
            await self.disconnect()
            return False
    
    async def _connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis = aioredis.from_url(
                self.config.redis_url,
                decode_responses=True
            )
            
            # Test connection
            await self.redis.ping()
            logger.debug("Redis connection established", service=self.service_name)
            
        except Exception as e:
            logger.error("Failed to connect to Redis", 
                        service=self.service_name,
                        error=str(e))
            raise
    
    async def _connect_rabbitmq(self):
        """Connect to RabbitMQ"""
        try:
            self.rabbitmq_connection = await aio_pika.connect_robust(
                self.config.rabbitmq_url,
                client_properties={"service": self.service_name}
            )
            
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()
            await self.rabbitmq_channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.rabbitmq_channel.declare_exchange(
                self.config.exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Declare dead letter exchange
            await self.rabbitmq_channel.declare_exchange(
                self.config.dead_letter_exchange,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            logger.debug("RabbitMQ connection established", service=self.service_name)
            
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", 
                        service=self.service_name,
                        error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from Redis and RabbitMQ"""
        # Stop consumers safely
        for consumer in self.consumers:
            try:
                if hasattr(consumer, 'cancel'):
                    await consumer.cancel()
            except Exception as e:
                logger.warning("Error cancelling consumer", 
                              service=self.service_name, error=str(e))
        self.consumers.clear()
        
        # Close RabbitMQ
        if self.rabbitmq_channel:
            await self.rabbitmq_channel.close()
        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()
        
        # Close Redis
        if self.redis:
            await self.redis.close()
        
        self.connected = False
        logger.info("Event-Bus disconnected", service=self.service_name)
    
    def is_connected(self) -> bool:
        """Check if Event-Bus is connected"""
        return self.connected
    
    async def publish(self, event_data) -> bool:
        """Publish event - accepts both Event objects and dict-based events"""
        if isinstance(event_data, dict):
            # Convert dict to Event object for backwards compatibility
            event = Event(
                event_type=event_data.get('event_type', 'unknown'),
                stream_id=event_data.get('stream_id', f"{self.service_name}-{datetime.now().timestamp()}"),
                data=event_data.get('data', {}),
                source=event_data.get('source', self.service_name),
                timestamp=event_data.get('timestamp'),
                correlation_id=event_data.get('correlation_id'),
                metadata=event_data.get('metadata')
            )
        else:
            event = event_data
        
        return await self._publish_event_object(event)
    
    async def _publish_event_object(self, event: Event) -> bool:
        """Publish event to both Redis and RabbitMQ"""
        if not self.connected:
            logger.error("Event-Bus not connected", service=self.service_name)
            return False
        
        try:
            event_json = event.to_json()
            
            # Publish to Redis for real-time subscribers
            await self._publish_to_redis(event, event_json)
            
            # Publish to RabbitMQ for persistent processing
            await self._publish_to_rabbitmq(event, event_json)
            
            logger.debug("Event published successfully", 
                        service=self.service_name,
                        event_type=event.event_type,
                        stream_id=event.stream_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish event", 
                        service=self.service_name,
                        event_type=event.event_type,
                        error=str(e))
            return False
    
    async def _publish_to_redis(self, event: Event, event_json: str):
        """Publish event to Redis Pub/Sub"""
        channel = f"events.{event.event_type}"
        await self.redis.publish(channel, event_json)
        logger.debug("Event published to Redis", 
                    service=self.service_name,
                    channel=channel)
    
    async def _publish_to_rabbitmq(self, event: Event, event_json: str):
        """Publish event to RabbitMQ"""
        routing_key = f"{event.source}.{event.event_type}"
        
        message = aio_pika.Message(
            event_json.encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={
                "source": event.source,
                "event_type": event.event_type,
                "timestamp": event.timestamp
            }
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
        logger.debug("Event published to RabbitMQ", 
                    service=self.service_name,
                    routing_key=routing_key)
    
    async def subscribe(self, event_type: str, handler: Callable[[Event], None], 
                       queue_name: str = None) -> bool:
        """Subscribe to events via RabbitMQ"""
        if not self.connected:
            logger.error("Event-Bus not connected", service=self.service_name)
            return False
        
        try:
            # Create queue name if not provided
            if queue_name is None:
                queue_name = f"{self.service_name}.{event_type.replace('.', '_')}"
            
            # Declare queue with dead letter exchange
            queue = await self.rabbitmq_channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": self.config.dead_letter_exchange,
                    "x-dead-letter-routing-key": f"failed.{queue_name}"
                }
            )
            
            # Bind queue to exchange
            routing_key = f"*.{event_type}"
            await queue.bind(self.exchange, routing_key=routing_key)
            
            # Create message handler
            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        event = Event.from_json(message.body.decode())
                        await handler(event)
                        logger.debug("Event processed successfully", 
                                   service=self.service_name,
                                   event_type=event.event_type)
                    except Exception as e:
                        logger.error("Failed to process event", 
                                   service=self.service_name,
                                   error=str(e))
                        raise
            
            # Start consuming
            consumer = await queue.consume(message_handler)
            self.consumers.append(consumer)
            
            logger.info("Event subscription created", 
                       service=self.service_name,
                       event_type=event_type,
                       queue_name=queue_name)
            
            return True
            
        except Exception as e:
            logger.error("Failed to subscribe to events", 
                        service=self.service_name,
                        event_type=event_type,
                        error=str(e))
            return False
    
    async def subscribe_realtime(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """Subscribe to real-time events via Redis Pub/Sub"""
        if not self.connected:
            logger.error("Event-Bus not connected", service=self.service_name)
            return False
        
        try:
            channel = f"events.{event_type}"
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            
            async def message_handler():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            event = Event.from_json(message["data"])
                            await handler(event)
                        except Exception as e:
                            logger.error("Failed to process real-time event", 
                                       service=self.service_name,
                                       error=str(e))
            
            # Start listening in background
            asyncio.create_task(message_handler())
            
            logger.info("Real-time event subscription created", 
                       service=self.service_name,
                       event_type=event_type,
                       channel=channel)
            
            return True
            
        except Exception as e:
            logger.error("Failed to subscribe to real-time events", 
                        service=self.service_name,
                        event_type=event_type,
                        error=str(e))
            return False


# Convenience functions for creating events
def create_analysis_event(symbol: str, score: float, recommendation: str, 
                         source: str, confidence: float = None) -> Event:
    """Create stock analysis event"""
    return Event(
        event_type=EventType.ANALYSIS_STATE_CHANGED.value,
        stream_id=f"stock-{symbol}",
        data={
            "symbol": symbol,
            "score": score,
            "recommendation": recommendation,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        },
        source=source
    )


def create_portfolio_event(portfolio_id: str, performance: Dict[str, Any], 
                          source: str) -> Event:
    """Create portfolio performance event"""
    return Event(
        event_type=EventType.PORTFOLIO_STATE_CHANGED.value,
        stream_id=f"portfolio-{portfolio_id}",
        data={
            "portfolio_id": portfolio_id,
            "performance": performance,
            "timestamp": datetime.now().isoformat()
        },
        source=source
    )


def create_trading_event(symbol: str, action: str, details: Dict[str, Any], 
                        source: str) -> Event:
    """Create trading activity event"""
    return Event(
        event_type=EventType.TRADING_STATE_CHANGED.value,
        stream_id=f"trading-{symbol}",
        data={
            "symbol": symbol,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        },
        source=source
    )