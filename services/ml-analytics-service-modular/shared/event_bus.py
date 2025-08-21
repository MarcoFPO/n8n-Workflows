#!/usr/bin/env python3
"""
Event Bus Integration v1.0.0
Redis-basierte Event-Bus-Integration für ML-Pipeline

Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
import uuid

import redis.asyncio as redis
try:
    from redis.asyncio.retry import Retry
    from redis.asyncio.backoff import ExponentialBackoff
except ImportError:
    # Fallback für ältere Redis-Versionen
    Retry = None
    ExponentialBackoff = None

logger = logging.getLogger(__name__)


class EventBusConnection:
    """
    Event Bus Connection für ML-Pipeline
    Redis-basierte Event-Publishing und Subscription
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Redis Connections
        self.redis_client = None
        self.pubsub_client = None
        self.pubsub = None
        
        # Event Handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Connection State
        self.is_connected = False
        self.is_listening = False
        
        # Event Statistics
        self.events_published = 0
        self.events_received = 0
        self.event_publish_times = []
        
        # Background Tasks
        self.listener_task = None
        self.heartbeat_task = None
    
    async def connect(self):
        """Verbindet mit Redis Event Bus"""
        try:
            self.logger.info("Connecting to Redis Event Bus...")
            
            # Redis Connection Pool
            connection_pool = redis.ConnectionPool.from_url(
                self.config['redis_url'],
                max_connections=self.config.get('max_connections', 20),
                retry_on_timeout=True,
                retry=Retry(ExponentialBackoff(), retries=3),
                socket_connect_timeout=self.config.get('connect_timeout', 10),
                socket_timeout=self.config.get('socket_timeout', 30)
            )
            
            # Main Redis Client für Publishing
            self.redis_client = redis.Redis(
                connection_pool=connection_pool,
                decode_responses=True
            )
            
            # Separate Client für PubSub
            self.pubsub_client = redis.Redis(
                connection_pool=connection_pool,
                decode_responses=True
            )
            
            # Connection testen
            await self.redis_client.ping()
            await self.pubsub_client.ping()
            
            # PubSub initialisieren
            self.pubsub = self.pubsub_client.pubsub()
            
            self.is_connected = True
            self.logger.info("Event Bus connected successfully")
            
            # Heartbeat starten
            self.heartbeat_task = asyncio.create_task(self._heartbeat_worker())
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Event Bus: {str(e)}")
            raise
    
    async def disconnect(self):
        """Trennt Event Bus Verbindung"""
        try:
            self.logger.info("Disconnecting from Event Bus...")
            
            # Listener stoppen
            if self.listener_task:
                self.listener_task.cancel()
                try:
                    await self.listener_task
                except asyncio.CancelledError:
                    pass
            
            # Heartbeat stoppen
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # PubSub schließen
            if self.pubsub:
                await self.pubsub.unsubscribe()
                await self.pubsub.aclose()
            
            # Redis Clients schließen
            if self.pubsub_client:
                await self.pubsub_client.aclose()
            
            if self.redis_client:
                await self.redis_client.aclose()
            
            self.is_connected = False
            self.is_listening = False
            
            self.logger.info("Event Bus disconnected")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting Event Bus: {str(e)}")
    
    async def publish_event(self, event_type: str, payload: Dict[str, Any], 
                           correlation_id: Optional[str] = None, 
                           target_service: Optional[str] = None) -> str:
        """
        Publiziert Event über Event Bus
        Verwendet aktienanalyse-ökosystem Event-Schema
        """
        if not self.is_connected:
            raise RuntimeError("Event Bus not connected")
        
        start_time = time.time()
        event_id = str(uuid.uuid4())
        
        try:
            # Event-Envelope erstellen (gemäß Schema)
            event_envelope = {
                'event_id': event_id,
                'event_type': event_type,
                'correlation_id': correlation_id or str(uuid.uuid4()),
                'source_service': self.config.get('service_name', 'ml-analytics'),
                'target_service': target_service,
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0',
                'payload': payload,
                'metadata': {
                    'trace_id': correlation_id,
                    'retry_count': 0,
                    'ttl_seconds': self.config.get('event_ttl', 3600)
                }
            }
            
            # Event als JSON serialisieren
            event_json = json.dumps(event_envelope, default=str)
            
            # Event publizieren
            channel = self._get_channel_for_event(event_type)
            await self.redis_client.publish(channel, event_json)
            
            # Event Store (optional für Persistenz)
            if self.config.get('store_events', True):
                store_key = f"events:{event_type}:{event_id}"
                await self.redis_client.setex(
                    store_key, 
                    self.config.get('event_store_ttl', 86400),  # 24h
                    event_json
                )
            
            # Statistics
            self.events_published += 1
            publish_time = (time.time() - start_time) * 1000
            self.event_publish_times.append(publish_time)
            
            self.logger.debug(f"Event published: {event_type} ({publish_time:.1f}ms)")
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {str(e)}")
            raise
    
    async def publish_ml_event(self, ml_event_type: str, payload: Dict[str, Any], 
                              correlation_id: Optional[str] = None) -> str:
        """
        Convenience-Methode für ML-spezifische Events
        Automatisches Präfix für ML-Event-Types
        """
        return await self.publish_event(
            event_type=ml_event_type,
            payload=payload,
            correlation_id=correlation_id,
            target_service=None  # Broadcast für ML-Events
        )
    
    async def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Abonniert Event-Type mit Handler-Funktion"""
        if not self.is_connected:
            raise RuntimeError("Event Bus not connected")
        
        try:
            # Handler registrieren
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            
            self.event_handlers[event_type].append(handler)
            
            # Channel für Event-Type abonnieren
            channel = self._get_channel_for_event(event_type)
            await self.pubsub.subscribe(channel)
            
            # Listener starten falls noch nicht aktiv
            if not self.is_listening:
                self.listener_task = asyncio.create_task(self._event_listener())
                self.is_listening = True
            
            self.logger.info(f"Subscribed to event type: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to {event_type}: {str(e)}")
            raise
    
    async def unsubscribe(self, event_type: str):
        """Deabonniert Event-Type"""
        try:
            if event_type in self.event_handlers:
                del self.event_handlers[event_type]
            
            channel = self._get_channel_for_event(event_type)
            await self.pubsub.unsubscribe(channel)
            
            self.logger.info(f"Unsubscribed from event type: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from {event_type}: {str(e)}")
    
    def _get_channel_for_event(self, event_type: str) -> str:
        """Mappt Event-Type zu Redis-Channel"""
        
        # ML-Events haben eigene Channels
        if event_type.startswith('ml.'):
            return f"events:ml:{event_type.replace('.', ':')}"
        
        # Standard aktienanalyse-ökosystem Events
        event_mapping = {
            'market.data.updated': 'events:market:data:updated',
            'market.data.daily.stored': 'events:market:data:daily:stored',
            'intelligence.analysis.completed': 'events:intelligence:analysis:completed',
            'portfolio.order.executed': 'events:portfolio:order:executed',
            'notification.alert.triggered': 'events:notification:alert:triggered',
            'user.interaction.tracked': 'events:user:interaction:tracked'
        }
        
        return event_mapping.get(event_type, f"events:general:{event_type.replace('.', ':')}")
    
    async def _event_listener(self):
        """Background Event Listener"""
        self.logger.info("Event listener started")
        
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_received_event(message)
                    
        except asyncio.CancelledError:
            self.logger.info("Event listener cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Event listener error: {str(e)}")
            
            # Reconnection Logic
            await asyncio.sleep(5)
            if self.is_connected:
                self.logger.info("Restarting event listener...")
                self.listener_task = asyncio.create_task(self._event_listener())
    
    async def _handle_received_event(self, message: Dict[str, Any]):
        """Behandelt empfangene Events"""
        try:
            # Event deserialisieren
            event_data = json.loads(message['data'])
            event_type = event_data.get('event_type')
            
            if not event_type:
                self.logger.warning("Received event without event_type")
                return
            
            # Statistics
            self.events_received += 1
            
            # Handler ausführen
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        # Handler asynchron ausführen
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)
                    except Exception as e:
                        self.logger.error(f"Event handler error for {event_type}: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle received event: {str(e)}")
    
    async def _heartbeat_worker(self):
        """Heartbeat Worker für Connection Health"""
        while self.is_connected:
            try:
                await self.redis_client.ping()
                await asyncio.sleep(self.config.get('heartbeat_interval', 30))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat failed: {str(e)}")
                self.is_connected = False
                break
    
    async def get_event_statistics(self) -> Dict[str, Any]:
        """Event Bus Statistiken"""
        try:
            # Redis Info
            redis_info = await self.redis_client.info()
            
            # Performance Metrics
            avg_publish_time = (
                sum(self.event_publish_times[-100:]) / len(self.event_publish_times[-100:])
                if self.event_publish_times else 0
            )
            
            return {
                'connection_status': 'connected' if self.is_connected else 'disconnected',
                'is_listening': self.is_listening,
                'events_published': self.events_published,
                'events_received': self.events_received,
                'avg_publish_time_ms': round(avg_publish_time, 2),
                'subscribed_event_types': list(self.event_handlers.keys()),
                'redis_connected_clients': redis_info.get('connected_clients', 0),
                'redis_memory_usage_mb': round(redis_info.get('used_memory', 0) / 1024 / 1024, 2)
            }
            
        except Exception as e:
            return {
                'connection_status': 'error',
                'error': str(e)
            }
    
    async def publish_heartbeat(self, service_name: str, service_status: Dict[str, Any]):
        """Publiziert Service-Heartbeat"""
        heartbeat_payload = {
            'service_name': service_name,
            'heartbeat_timestamp': datetime.utcnow().isoformat(),
            'service_status': service_status,
            'uptime_seconds': service_status.get('uptime_seconds', 0)
        }
        
        await self.publish_event(
            'service.heartbeat',
            heartbeat_payload,
            target_service='monitoring'
        )
    
    async def request_response(self, request_type: str, payload: Dict[str, Any], 
                             timeout_seconds: int = 30) -> Optional[Dict[str, Any]]:
        """
        Request-Response Pattern über Event Bus
        Publiziert Request und wartet auf Response
        """
        correlation_id = str(uuid.uuid4())
        response_channel = f"response:{correlation_id}"
        
        try:
            # Response Channel abonnieren
            temp_pubsub = self.pubsub_client.pubsub()
            await temp_pubsub.subscribe(response_channel)
            
            # Request publizieren
            await self.publish_event(
                request_type,
                {**payload, 'response_channel': response_channel},
                correlation_id=correlation_id
            )
            
            # Auf Response warten
            try:
                async with asyncio.timeout(timeout_seconds):
                    async for message in temp_pubsub.listen():
                        if message['type'] == 'message':
                            response_data = json.loads(message['data'])
                            if response_data.get('correlation_id') == correlation_id:
                                await temp_pubsub.unsubscribe(response_channel)
                                await temp_pubsub.aclose()
                                return response_data.get('payload')
                            
            except asyncio.TimeoutError:
                self.logger.warning(f"Request {request_type} timed out after {timeout_seconds}s")
                return None
            
        except Exception as e:
            self.logger.error(f"Request-Response failed for {request_type}: {str(e)}")
            return None
        
        finally:
            try:
                await temp_pubsub.unsubscribe(response_channel)
                await temp_pubsub.aclose()
            except:
                pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Event Bus"""
        try:
            if not self.is_connected:
                return {'status': 'disconnected'}
            
            # Connection Test
            ping_start = time.time()
            await self.redis_client.ping()
            ping_time = (time.time() - ping_start) * 1000
            
            # Statistics
            stats = await self.get_event_statistics()
            
            return {
                'status': 'healthy',
                'ping_time_ms': round(ping_time, 2),
                'connection_stable': ping_time < 100,  # < 100ms als stabil
                'statistics': stats
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }