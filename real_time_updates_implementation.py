#!/usr/bin/env python3
"""
Real-time Updates Implementation v1.0.0
WebSocket-basierte Real-time Updates zwischen Frontend und Backend über Event Bus

FEATURES:
- WebSocket-Verbindung zu Event Bus (Port 8014)
- Real-time Data Streaming für Dashboard
- Event-Subscriptions für Timeline-Updates
- Auto-refresh bei neuen Prognosen
- Service Communication Optimization
- Live Status Updates

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Real-time Communication
- Open/Closed: Erweiterbar für neue Event Types
- Interface Segregation: Spezifische WebSocket Interfaces
- Dependency Inversion: Event-abstraction Layer

Autor: Claude Code
Datum: 27. August 2025  
Version: 1.0.0
"""

import os
import sys
import json
import logging
import asyncio
import websockets
import aiohttp
import redis
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class RealTimeConfig:
    """Configuration für Real-time Updates"""
    
    # Event Bus Configuration
    event_bus_host: str = os.getenv("EVENT_BUS_HOST", "10.1.1.174")
    event_bus_port: int = int(os.getenv("EVENT_BUS_PORT", "8014"))
    event_bus_url: str = None
    
    # Redis Configuration für Event Bus
    redis_host: str = os.getenv("REDIS_HOST", "10.1.1.174")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # WebSocket Configuration
    websocket_port: int = int(os.getenv("WEBSOCKET_PORT", "8090"))
    websocket_host: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
    
    # Service URLs für Data Fetching
    ml_analytics_url: str = os.getenv("ML_ANALYTICS_URL", "http://10.1.1.174:8021")
    prediction_tracking_url: str = os.getenv("PREDICTION_TRACKING_URL", "http://10.1.1.174:8018")
    data_processing_url: str = os.getenv("DATA_PROCESSING_URL", "http://10.1.1.174:8017")
    
    # Update Intervals (seconds)
    prediction_update_interval: int = 30
    status_update_interval: int = 10
    timeline_update_interval: int = 60
    
    def __post_init__(self):
        if self.event_bus_url is None:
            self.event_bus_url = f"http://{self.event_bus_host}:{self.event_bus_port}"

config = RealTimeConfig()

# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType(str, Enum):
    """Event Types für Real-time Updates"""
    
    # Prediction Events
    PREDICTION_UPDATED = "prediction_updated"
    PREDICTION_GENERATED = "prediction_generated"
    PREDICTION_ACCURACY_CHANGED = "prediction_accuracy_changed"
    
    # Timeline Events
    TIMELINE_NAVIGATION = "timeline_navigation"
    TIMEFRAME_CHANGED = "timeframe_changed"
    
    # Service Events
    SERVICE_STATUS_CHANGED = "service_status_changed"
    SERVICE_HEALTH_UPDATE = "service_health_update"
    
    # Data Events
    DATA_REFRESH_REQUIRED = "data_refresh_required"
    CSV_PROCESSING_COMPLETED = "csv_processing_completed"
    
    # User Events
    USER_ACTION = "user_action"
    DASHBOARD_VIEW_CHANGED = "dashboard_view_changed"
    
    # System Events
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_METRIC = "performance_metric"

@dataclass
class RealTimeEvent:
    """Real-time Event Data Structure"""
    
    event_type: EventType
    data: Dict[str, Any]
    timestamp: str = None
    source_service: str = "real_time_updates"
    event_id: str = None
    user_session: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging() -> logging.Logger:
    """Setup centralized logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/opt/aktienanalyse-ökosystem/logs/real-time-updates.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# EVENT BUS CONNECTION
# =============================================================================

class IEventBusConnection:
    """Interface für Event Bus Connection (Interface Segregation)"""
    
    async def connect(self) -> bool:
        """Verbinde zu Event Bus"""
        raise NotImplementedError
    
    async def disconnect(self) -> bool:
        """Trenne Event Bus Verbindung"""
        raise NotImplementedError
    
    async def publish_event(self, event: RealTimeEvent) -> bool:
        """Publiziere Event"""
        raise NotImplementedError
    
    async def subscribe_to_events(self, event_types: List[EventType], callback: Callable) -> bool:
        """Subscribe zu Event Types"""
        raise NotImplementedError

class RedisEventBusConnection(IEventBusConnection):
    """
    Redis-based Event Bus Connection
    
    SOLID Principles:
    - Single Responsibility: Event Bus Communication
    - Dependency Inversion: Implementiert Interface
    """
    
    def __init__(self, config: RealTimeConfig):
        self.config = config
        self.redis_client = None
        self.pubsub = None
        self.subscriptions: Set[str] = set()
        self.connected = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def connect(self) -> bool:
        """Verbinde zu Redis Event Bus"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            self.connected = True
            
            self.logger.info(f"✅ Connected to Redis Event Bus: {self.config.redis_host}:{self.config.redis_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Redis Event Bus: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Trenne Redis Event Bus Verbindung"""
        try:
            if self.pubsub:
                self.pubsub.close()
            if self.redis_client:
                self.redis_client.close()
            
            self.connected = False
            self.logger.info("🔌 Disconnected from Redis Event Bus")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error disconnecting from Redis Event Bus: {e}")
            return False
    
    async def publish_event(self, event: RealTimeEvent) -> bool:
        """Publiziere Event über Redis"""
        try:
            if not self.connected:
                await self.connect()
            
            channel = f"aktienanalyse.{event.event_type.value}"
            message = event.to_json()
            
            self.redis_client.publish(channel, message)
            self.logger.info(f"📤 Published event: {event.event_type.value} to {channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to publish event {event.event_type.value}: {e}")
            return False
    
    async def subscribe_to_events(self, event_types: List[EventType], callback: Callable) -> bool:
        """Subscribe zu Event Types"""
        try:
            if not self.connected:
                await self.connect()
            
            # Subscribe to channels
            channels = [f"aktienanalyse.{event_type.value}" for event_type in event_types]
            self.pubsub.subscribe(*channels)
            self.subscriptions.update(channels)
            
            self.logger.info(f"📥 Subscribed to events: {[et.value for et in event_types]}")
            
            # Listen for messages
            asyncio.create_task(self._listen_for_messages(callback))
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to events: {e}")
            return False
    
    async def _listen_for_messages(self, callback: Callable):
        """Listen for Redis messages"""
        try:
            while self.connected:
                message = self.pubsub.get_message(timeout=1)
                if message and message['type'] == 'message':
                    try:
                        event_data = json.loads(message['data'])
                        event = RealTimeEvent(
                            event_type=EventType(event_data['event_type']),
                            data=event_data['data'],
                            timestamp=event_data.get('timestamp'),
                            source_service=event_data.get('source_service'),
                            event_id=event_data.get('event_id')
                        )
                        await callback(event)
                    except Exception as e:
                        self.logger.error(f"❌ Error processing message: {e}")
                
                await asyncio.sleep(0.1)  # Prevent busy waiting
                
        except Exception as e:
            self.logger.error(f"❌ Error listening for messages: {e}")

# =============================================================================
# WEBSOCKET SERVER
# =============================================================================

class WebSocketHandler:
    """
    WebSocket Handler für Real-time Communication
    
    SOLID Principles:
    - Single Responsibility: WebSocket Communication
    - Open/Closed: Erweiterbar für neue Message Types
    """
    
    def __init__(self, event_bus: IEventBusConnection):
        self.event_bus = event_bus
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_sessions: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Register neuen WebSocket Client"""
        try:
            self.clients.add(websocket)
            session_id = str(uuid.uuid4())
            self.client_sessions[websocket] = session_id
            
            self.logger.info(f"👤 New client connected: {session_id} (Total: {len(self.clients)})")
            
            # Send welcome message
            welcome_event = RealTimeEvent(
                event_type=EventType.USER_ACTION,
                data={
                    "action": "connected",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            await self.send_to_client(websocket, welcome_event)
            
            # Listen for client messages
            await self.listen_to_client(websocket)
            
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"🔌 Client disconnected")
        except Exception as e:
            self.logger.error(f"❌ Error handling client: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister WebSocket Client"""
        try:
            self.clients.discard(websocket)
            session_id = self.client_sessions.pop(websocket, "unknown")
            self.logger.info(f"👋 Client disconnected: {session_id} (Remaining: {len(self.clients)})")
        except Exception as e:
            self.logger.error(f"❌ Error unregistering client: {e}")
    
    async def listen_to_client(self, websocket: websockets.WebSocketServerProtocol):
        """Listen for messages from client"""
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.logger.error(f"❌ Error listening to client: {e}")
    
    async def handle_client_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """Handle message from client"""
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'subscribe_events':
                event_types = [EventType(et) for et in data.get('event_types', [])]
                await self.subscribe_client_to_events(websocket, event_types)
            
            elif message_type == 'timeline_navigation':
                await self.handle_timeline_navigation(websocket, data)
            
            elif message_type == 'request_data_refresh':
                await self.handle_data_refresh_request(websocket, data)
            
            elif message_type == 'ping':
                await self.send_pong(websocket)
            
            else:
                self.logger.warning(f"⚠️ Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Error handling client message: {e}")
    
    async def subscribe_client_to_events(self, websocket: websockets.WebSocketServerProtocol, event_types: List[EventType]):
        """Subscribe client zu bestimmten Event Types"""
        try:
            session_id = self.client_sessions.get(websocket, "unknown")
            self.logger.info(f"📥 Client {session_id} subscribed to: {[et.value for et in event_types]}")
            
            # Send confirmation
            confirm_event = RealTimeEvent(
                event_type=EventType.USER_ACTION,
                data={
                    "action": "subscription_confirmed",
                    "event_types": [et.value for et in event_types],
                    "session_id": session_id
                }
            )
            
            await self.send_to_client(websocket, confirm_event)
            
        except Exception as e:
            self.logger.error(f"❌ Error subscribing client to events: {e}")
    
    async def handle_timeline_navigation(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle Timeline Navigation from client"""
        try:
            session_id = self.client_sessions.get(websocket, "unknown")
            
            # Create timeline navigation event
            timeline_event = RealTimeEvent(
                event_type=EventType.TIMELINE_NAVIGATION,
                data={
                    "direction": data.get('direction'),
                    "timeframe": data.get('timeframe'),
                    "timestamp": data.get('timestamp'),
                    "session_id": session_id
                },
                user_session=session_id
            )
            
            # Publish to event bus
            await self.event_bus.publish_event(timeline_event)
            
            self.logger.info(f"🧭 Timeline navigation from {session_id}: {data.get('direction')} {data.get('timeframe')}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling timeline navigation: {e}")
    
    async def handle_data_refresh_request(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle Data Refresh Request from client"""
        try:
            session_id = self.client_sessions.get(websocket, "unknown")
            
            # Create data refresh event
            refresh_event = RealTimeEvent(
                event_type=EventType.DATA_REFRESH_REQUIRED,
                data={
                    "data_type": data.get('data_type'),
                    "timeframe": data.get('timeframe'),
                    "session_id": session_id
                },
                user_session=session_id
            )
            
            # Publish to event bus
            await self.event_bus.publish_event(refresh_event)
            
            self.logger.info(f"🔄 Data refresh request from {session_id}: {data.get('data_type')}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling data refresh request: {e}")
    
    async def send_pong(self, websocket: websockets.WebSocketServerProtocol):
        """Send pong response"""
        try:
            pong_event = RealTimeEvent(
                event_type=EventType.USER_ACTION,
                data={"action": "pong", "timestamp": datetime.now().isoformat()}
            )
            await self.send_to_client(websocket, pong_event)
        except Exception as e:
            self.logger.error(f"❌ Error sending pong: {e}")
    
    async def send_to_client(self, websocket: websockets.WebSocketServerProtocol, event: RealTimeEvent):
        """Send event to specific client"""
        try:
            await websocket.send(event.to_json())
        except Exception as e:
            self.logger.error(f"❌ Error sending to client: {e}")
    
    async def broadcast_event(self, event: RealTimeEvent):
        """Broadcast event to all connected clients"""
        if not self.clients:
            return
        
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                await client.send(event.to_json())
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                self.logger.error(f"❌ Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Clean up disconnected clients
        for client in disconnected_clients:
            await self.unregister_client(client)
        
        if disconnected_clients:
            self.logger.info(f"🧹 Cleaned up {len(disconnected_clients)} disconnected clients")

# =============================================================================
# DATA FETCHER SERVICE
# =============================================================================

class IDataFetcher:
    """Interface für Data Fetching (Interface Segregation)"""
    
    async def fetch_predictions(self, timeframe: str) -> Dict[str, Any]:
        """Fetch predictions data"""
        raise NotImplementedError
    
    async def fetch_soll_ist_comparison(self, timeframe: str) -> Dict[str, Any]:
        """Fetch SOLL-IST comparison data"""
        raise NotImplementedError
    
    async def fetch_service_health(self) -> Dict[str, Any]:
        """Fetch service health status"""
        raise NotImplementedError

class HTTPDataFetcher(IDataFetcher):
    """
    HTTP-based Data Fetcher
    
    SOLID Principles:
    - Single Responsibility: Data Fetching
    - Dependency Inversion: HTTP abstraction
    """
    
    def __init__(self, config: RealTimeConfig):
        self.config = config
        self.session = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def init_session(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def fetch_predictions(self, timeframe: str) -> Dict[str, Any]:
        """Fetch predictions data from ML Analytics Service"""
        try:
            await self.init_session()
            
            url = f"{self.config.ml_analytics_url}/api/v1/predictions"
            params = {"timeframe": timeframe}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"📊 Fetched predictions for {timeframe}")
                    return {"status": "success", "data": data}
                else:
                    self.logger.warning(f"⚠️ Predictions fetch failed: {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"❌ Error fetching predictions: {e}")
            return {"status": "error", "error": str(e)}
    
    async def fetch_soll_ist_comparison(self, timeframe: str) -> Dict[str, Any]:
        """Fetch SOLL-IST comparison from Prediction Tracking Service"""
        try:
            await self.init_session()
            
            url = f"{self.config.prediction_tracking_url}/api/v1/soll-ist-comparison"
            params = {"timeframe": timeframe}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"⚖️ Fetched SOLL-IST comparison for {timeframe}")
                    return {"status": "success", "data": data}
                else:
                    self.logger.warning(f"⚠️ SOLL-IST fetch failed: {response.status}")
                    return {"status": "error", "error": f"HTTP {response.status}"}
                    
        except Exception as e:
            self.logger.error(f"❌ Error fetching SOLL-IST comparison: {e}")
            return {"status": "error", "error": str(e)}
    
    async def fetch_service_health(self) -> Dict[str, Any]:
        """Fetch service health from all services"""
        try:
            await self.init_session()
            
            services = [
                {"name": "ML Analytics", "url": f"{self.config.ml_analytics_url}/health"},
                {"name": "Prediction Tracking", "url": f"{self.config.prediction_tracking_url}/health"},
                {"name": "Data Processing", "url": f"{self.config.data_processing_url}/health"}
            ]
            
            health_status = {"timestamp": datetime.now().isoformat(), "services": []}
            
            for service in services:
                try:
                    async with self.session.get(service["url"]) as response:
                        if response.status == 200:
                            service_data = await response.json()
                            health_status["services"].append({
                                "name": service["name"],
                                "status": "healthy",
                                "data": service_data
                            })
                        else:
                            health_status["services"].append({
                                "name": service["name"],
                                "status": "unhealthy",
                                "error": f"HTTP {response.status}"
                            })
                except Exception as e:
                    health_status["services"].append({
                        "name": service["name"],
                        "status": "error",
                        "error": str(e)
                    })
            
            self.logger.info(f"🏥 Fetched health status for {len(services)} services")
            return {"status": "success", "data": health_status}
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching service health: {e}")
            return {"status": "error", "error": str(e)}

# =============================================================================
# REAL-TIME UPDATE SERVICE
# =============================================================================

class RealTimeUpdateService:
    """
    Main Real-time Update Service
    
    SOLID Principles:
    - Single Responsibility: Real-time Update Orchestration
    - Open/Closed: Erweiterbar für neue Update Types
    - Dependency Inversion: Abhängig von Interfaces
    """
    
    def __init__(self, config: RealTimeConfig = None):
        self.config = config or RealTimeConfig()
        self.event_bus = RedisEventBusConnection(self.config)
        self.websocket_handler = WebSocketHandler(self.event_bus)
        self.data_fetcher = HTTPDataFetcher(self.config)
        self.running = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Background tasks
        self.background_tasks = []
    
    async def start(self):
        """Start Real-time Update Service"""
        try:
            self.logger.info("🚀 Starting Real-time Update Service")
            
            # Connect to Event Bus
            await self.event_bus.connect()
            
            # Subscribe to events
            await self.event_bus.subscribe_to_events(
                [EventType.PREDICTION_UPDATED, EventType.TIMELINE_NAVIGATION, EventType.SERVICE_STATUS_CHANGED],
                self._handle_event_bus_event
            )
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._periodic_prediction_updates()),
                asyncio.create_task(self._periodic_health_checks()),
                asyncio.create_task(self._start_websocket_server())
            ]
            
            self.running = True
            self.logger.info("✅ Real-time Update Service started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*self.background_tasks)
            
        except Exception as e:
            self.logger.error(f"❌ Error starting Real-time Update Service: {e}")
            raise
    
    async def stop(self):
        """Stop Real-time Update Service"""
        try:
            self.logger.info("🛑 Stopping Real-time Update Service")
            
            self.running = False
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Disconnect from Event Bus
            await self.event_bus.disconnect()
            
            # Close HTTP session
            await self.data_fetcher.close_session()
            
            self.logger.info("✅ Real-time Update Service stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping Real-time Update Service: {e}")
    
    async def _start_websocket_server(self):
        """Start WebSocket server"""
        try:
            self.logger.info(f"🔌 Starting WebSocket server on {self.config.websocket_host}:{self.config.websocket_port}")
            
            server = await websockets.serve(
                self.websocket_handler.register_client,
                self.config.websocket_host,
                self.config.websocket_port
            )
            
            self.logger.info("✅ WebSocket server started")
            await server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"❌ Error starting WebSocket server: {e}")
    
    async def _handle_event_bus_event(self, event: RealTimeEvent):
        """Handle Event Bus events"""
        try:
            self.logger.info(f"📨 Received event: {event.event_type.value}")
            
            # Broadcast to WebSocket clients
            await self.websocket_handler.broadcast_event(event)
            
            # Handle specific event types
            if event.event_type == EventType.PREDICTION_UPDATED:
                await self._handle_prediction_update(event)
            elif event.event_type == EventType.TIMELINE_NAVIGATION:
                await self._handle_timeline_navigation(event)
            elif event.event_type == EventType.SERVICE_STATUS_CHANGED:
                await self._handle_service_status_change(event)
            
        except Exception as e:
            self.logger.error(f"❌ Error handling event bus event: {e}")
    
    async def _handle_prediction_update(self, event: RealTimeEvent):
        """Handle prediction update events"""
        try:
            timeframe = event.data.get('timeframe', '1M')
            predictions = await self.data_fetcher.fetch_predictions(timeframe)
            
            if predictions['status'] == 'success':
                update_event = RealTimeEvent(
                    event_type=EventType.DATA_REFRESH_REQUIRED,
                    data={
                        "data_type": "predictions",
                        "timeframe": timeframe,
                        "predictions": predictions['data']
                    }
                )
                
                await self.websocket_handler.broadcast_event(update_event)
                self.logger.info(f"📊 Broadcasted prediction updates for {timeframe}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling prediction update: {e}")
    
    async def _handle_timeline_navigation(self, event: RealTimeEvent):
        """Handle timeline navigation events"""
        try:
            # Fetch relevant data for new timeline position
            timeframe = event.data.get('timeframe', '1M')
            
            # Fetch predictions and SOLL-IST for new timeline position
            predictions_task = self.data_fetcher.fetch_predictions(timeframe)
            soll_ist_task = self.data_fetcher.fetch_soll_ist_comparison(timeframe)
            
            predictions, soll_ist = await asyncio.gather(predictions_task, soll_ist_task)
            
            # Create timeline update event
            timeline_update = RealTimeEvent(
                event_type=EventType.TIMEFRAME_CHANGED,
                data={
                    "timeframe": timeframe,
                    "direction": event.data.get('direction'),
                    "predictions": predictions.get('data') if predictions['status'] == 'success' else None,
                    "soll_ist": soll_ist.get('data') if soll_ist['status'] == 'success' else None
                }
            )
            
            await self.websocket_handler.broadcast_event(timeline_update)
            self.logger.info(f"🧭 Broadcasted timeline navigation update: {timeframe}")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling timeline navigation: {e}")
    
    async def _handle_service_status_change(self, event: RealTimeEvent):
        """Handle service status change events"""
        try:
            service_health = await self.data_fetcher.fetch_service_health()
            
            if service_health['status'] == 'success':
                status_event = RealTimeEvent(
                    event_type=EventType.SERVICE_HEALTH_UPDATE,
                    data=service_health['data']
                )
                
                await self.websocket_handler.broadcast_event(status_event)
                self.logger.info("🏥 Broadcasted service health update")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling service status change: {e}")
    
    async def _periodic_prediction_updates(self):
        """Periodic prediction updates"""
        try:
            while self.running:
                await asyncio.sleep(self.config.prediction_update_interval)
                
                if not self.running:
                    break
                
                # Create periodic update event
                update_event = RealTimeEvent(
                    event_type=EventType.PREDICTION_UPDATED,
                    data={"source": "periodic_update"}
                )
                
                await self.event_bus.publish_event(update_event)
                self.logger.info("⏰ Triggered periodic prediction update")
                
        except Exception as e:
            self.logger.error(f"❌ Error in periodic prediction updates: {e}")
    
    async def _periodic_health_checks(self):
        """Periodic health checks"""
        try:
            while self.running:
                await asyncio.sleep(self.config.status_update_interval)
                
                if not self.running:
                    break
                
                # Fetch and broadcast health status
                health_data = await self.data_fetcher.fetch_service_health()
                
                if health_data['status'] == 'success':
                    health_event = RealTimeEvent(
                        event_type=EventType.SERVICE_HEALTH_UPDATE,
                        data=health_data['data']
                    )
                    
                    await self.websocket_handler.broadcast_event(health_event)
                    self.logger.info("💓 Broadcasted periodic health check")
                
        except Exception as e:
            self.logger.error(f"❌ Error in periodic health checks: {e}")

# =============================================================================
# CLIENT-SIDE JAVASCRIPT INTEGRATION
# =============================================================================

def generate_websocket_client_js() -> str:
    """Generate JavaScript für WebSocket Client Integration"""
    
    return f"""
// Real-time WebSocket Client for Aktienanalyse System
// Auto-generated v1.0.0

class AktienanalyseWebSocketClient {{
    constructor(wsUrl = 'ws://10.1.1.174:{config.websocket_port}') {{
        this.wsUrl = wsUrl;
        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.eventHandlers = {{}};
        this.sessionId = null;
        
        console.log('🔌 WebSocket Client initialized for Aktienanalyse System');
    }}
    
    async connect() {{
        try {{
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = (event) => {{
                this.connected = true;
                this.reconnectAttempts = 0;
                console.log('✅ WebSocket connected to Aktienanalyse backend');
                this.sendHeartbeat();
            }};
            
            this.ws.onmessage = (event) => {{
                this.handleMessage(JSON.parse(event.data));
            }};
            
            this.ws.onclose = (event) => {{
                this.connected = false;
                console.log('🔌 WebSocket connection closed');
                this.attemptReconnect();
            }};
            
            this.ws.onerror = (error) => {{
                console.error('❌ WebSocket error:', error);
            }};
            
        }} catch (error) {{
            console.error('❌ Error connecting WebSocket:', error);
        }}
    }}
    
    disconnect() {{
        if (this.ws) {{
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }}
    }}
    
    attemptReconnect() {{
        if (this.reconnectAttempts < this.maxReconnectAttempts) {{
            this.reconnectAttempts++;
            console.log(`🔄 Reconnecting WebSocket (attempt ${{this.reconnectAttempts}})...`);
            
            setTimeout(() => {{
                this.connect();
            }}, 2000 * this.reconnectAttempts); // Exponential backoff
        }} else {{
            console.error('❌ Max reconnection attempts reached');
        }}
    }}
    
    handleMessage(data) {{
        try {{
            const eventType = data.event_type;
            const eventData = data.data;
            
            // Store session ID
            if (eventData.session_id) {{
                this.sessionId = eventData.session_id;
            }}
            
            console.log('📨 Received real-time event:', eventType, eventData);
            
            // Handle specific event types
            switch (eventType) {{
                case 'prediction_updated':
                    this.handlePredictionUpdate(eventData);
                    break;
                case 'timeline_navigation':
                    this.handleTimelineNavigation(eventData);
                    break;
                case 'service_health_update':
                    this.handleServiceHealthUpdate(eventData);
                    break;
                case 'data_refresh_required':
                    this.handleDataRefresh(eventData);
                    break;
                case 'timeframe_changed':
                    this.handleTimeframeChanged(eventData);
                    break;
                default:
                    console.log('📡 Unhandled event type:', eventType);
            }}
            
            // Call registered event handlers
            if (this.eventHandlers[eventType]) {{
                this.eventHandlers[eventType].forEach(handler => {{
                    try {{
                        handler(eventData);
                    }} catch (error) {{
                        console.error('❌ Error in event handler:', error);
                    }}
                }});
            }}
            
        }} catch (error) {{
            console.error('❌ Error handling WebSocket message:', error);
        }}
    }}
    
    handlePredictionUpdate(data) {{
        // Update prediction displays
        const predictionElements = document.querySelectorAll('[data-prediction-timeframe]');
        if (predictionElements.length > 0 && data.predictions) {{
            console.log('📊 Updating prediction displays');
            // Trigger UI update
            window.dispatchEvent(new CustomEvent('predictionUpdate', {{ detail: data }}));
        }}
    }}
    
    handleTimelineNavigation(data) {{
        // Handle timeline navigation events
        console.log('🧭 Timeline navigation:', data.direction, data.timeframe);
        
        // Update timeline indicators
        this.updateTimelineUI(data);
        
        // Trigger page refresh if needed
        if (data.predictions || data.soll_ist) {{
            window.dispatchEvent(new CustomEvent('timelineDataUpdate', {{ detail: data }}));
        }}
    }}
    
    handleServiceHealthUpdate(data) {{
        // Update service status indicators
        const statusElements = document.querySelectorAll('[data-service-status]');
        if (statusElements.length > 0) {{
            console.log('🏥 Updating service health indicators');
            window.dispatchEvent(new CustomEvent('serviceHealthUpdate', {{ detail: data }}));
        }}
    }}
    
    handleDataRefresh(data) {{
        // Handle data refresh requirements
        console.log('🔄 Data refresh required:', data.data_type);
        
        if (data.data_type === 'predictions' && window.location.pathname.includes('prognosen')) {{
            window.location.reload();
        }} else if (data.data_type === 'soll_ist' && window.location.pathname.includes('vergleichsanalyse')) {{
            window.location.reload();
        }}
    }}
    
    handleTimeframeChanged(data) {{
        console.log('📅 Timeframe changed:', data.timeframe);
        // Update timeframe selector UI
        this.updateTimeframeSelectorUI(data.timeframe);
    }}
    
    updateTimelineUI(data) {{
        // Update timeline navigation UI
        const timelineElements = document.querySelectorAll('.timeline-navigation');
        timelineElements.forEach(element => {{
            element.style.borderLeftColor = '#28a745'; // Green for successful navigation
            
            // Add success indicator
            const indicator = element.querySelector('.timeline-success-indicator') || document.createElement('div');
            indicator.className = 'timeline-success-indicator';
            indicator.innerHTML = '<small style="color: #28a745;">✅ Navigation erfolgreich</small>';
            if (!element.querySelector('.timeline-success-indicator')) {{
                element.appendChild(indicator);
            }}
            
            setTimeout(() => {{
                if (indicator.parentNode) {{
                    indicator.remove();
                }}
            }}, 3000);
        }});
    }}
    
    updateTimeframeSelectorUI(activeTimeframe) {{
        // Update timeframe selector buttons
        const buttons = document.querySelectorAll('[data-timeframe]');
        buttons.forEach(button => {{
            const buttonTimeframe = button.getAttribute('data-timeframe');
            if (buttonTimeframe === activeTimeframe) {{
                button.classList.add('btn-primary');
                button.classList.remove('btn-outline-primary');
                button.disabled = true;
            }} else {{
                button.classList.remove('btn-primary');
                button.classList.add('btn-outline-primary');
                button.disabled = false;
            }}
        }});
    }}
    
    // Outgoing message methods
    subscribeToEvents(eventTypes) {{
        if (this.connected) {{
            this.send({{
                type: 'subscribe_events',
                event_types: eventTypes
            }});
        }}
    }}
    
    notifyTimelineNavigation(direction, timeframe) {{
        if (this.connected) {{
            this.send({{
                type: 'timeline_navigation',
                direction: direction,
                timeframe: timeframe,
                timestamp: Math.floor(Date.now() / 1000)
            }});
        }}
    }}
    
    requestDataRefresh(dataType, timeframe) {{
        if (this.connected) {{
            this.send({{
                type: 'request_data_refresh',
                data_type: dataType,
                timeframe: timeframe
            }});
        }}
    }}
    
    send(data) {{
        if (this.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {{
            this.ws.send(JSON.stringify(data));
        }} else {{
            console.warn('⚠️ WebSocket not connected, message not sent');
        }}
    }}
    
    sendHeartbeat() {{
        if (this.connected) {{
            this.send({{ type: 'ping' }});
            
            // Schedule next heartbeat
            setTimeout(() => {{
                this.sendHeartbeat();
            }}, 30000); // Every 30 seconds
        }}
    }}
    
    // Event handler registration
    on(eventType, handler) {{
        if (!this.eventHandlers[eventType]) {{
            this.eventHandlers[eventType] = [];
        }}
        this.eventHandlers[eventType].push(handler);
    }}
    
    off(eventType, handler) {{
        if (this.eventHandlers[eventType]) {{
            this.eventHandlers[eventType] = this.eventHandlers[eventType].filter(h => h !== handler);
        }}
    }}
}}

// Global WebSocket client instance
window.aktienanalyseWS = new AktienanalyseWebSocketClient();

// Auto-connect when page loads
document.addEventListener('DOMContentLoaded', () => {{
    window.aktienanalyseWS.connect();
    
    // Subscribe to relevant events
    window.aktienanalyseWS.subscribeToEvents([
        'prediction_updated',
        'timeline_navigation', 
        'service_health_update',
        'data_refresh_required',
        'timeframe_changed'
    ]);
    
    console.log('🌟 Aktienanalyse Real-time WebSocket client initialized');
}});

// Integration with existing timeline navigation
if (typeof window.TimelineNavigation !== 'undefined') {{
    const originalNavigateTimeline = window.TimelineNavigation.navigateTimeline;
    
    window.TimelineNavigation.navigateTimeline = function(direction, timeframe, pageType) {{
        // Notify WebSocket server
        if (window.aktienanalyseWS && window.aktienanalyseWS.connected) {{
            window.aktienanalyseWS.notifyTimelineNavigation(direction, timeframe);
        }}
        
        // Call original function
        return originalNavigateTimeline.call(this, direction, timeframe, pageType);
    }};
}}

console.log('🔌 Real-time WebSocket integration loaded successfully');
"""

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main execution function"""
    logger.info("🚀 Starting Real-time Updates Implementation")
    
    try:
        # Generate WebSocket client JavaScript
        js_client_code = generate_websocket_client_js()
        
        # Save JavaScript client
        js_output_path = "/home/mdoehler/aktienanalyse-ökosystem/websocket_client.js"
        with open(js_output_path, 'w', encoding='utf-8') as f:
            f.write(js_client_code)
        
        logger.info(f"✅ WebSocket client JavaScript saved to: {js_output_path}")
        
        # Initialize and start real-time service
        service = RealTimeUpdateService(config)
        
        print("\n" + "="*80)
        print("🔌 REAL-TIME UPDATES IMPLEMENTATION")
        print("="*80)
        print(f"WebSocket Server: {config.websocket_host}:{config.websocket_port}")
        print(f"Event Bus: {config.event_bus_url}")
        print(f"Redis: {config.redis_host}:{config.redis_port}")
        print(f"JavaScript Client: {js_output_path}")
        print("\n📡 Starting real-time services...")
        
        # Start service (this will run indefinitely)
        await service.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal, shutting down...")
        if 'service' in locals():
            await service.stop()
    except Exception as e:
        logger.error(f"❌ Error in main execution: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())