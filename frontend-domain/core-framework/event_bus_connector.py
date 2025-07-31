"""
Event-Bus Connector - Frontend-Domain
Verbindung zum zentralen Event-Bus für lose gekoppelte Kommunikation
"""

import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class EventBusConnector:
    """Event-Bus Connector für Frontend-Domain"""
    
    def __init__(self, bus_url: str = "redis://localhost:6379"):
        self.bus_url = bus_url
        self.subscribers = {}
        self.connected = False
        self.logger = logger
        
    async def connect(self):
        """Verbindung zum Event-Bus herstellen"""
        try:
            # Hier würde Redis-Verbindung implementiert werden
            # Für jetzt: Mock-Implementation
            self.connected = True
            self.logger.info("✅ Event-Bus Connection established")
            
            # Frontend-Domain Events abonnieren
            await self.subscribe("system.health.*", self._handle_system_health)
            await self.subscribe("data.market.updated", self._handle_market_data_update)
            await self.subscribe("user.interaction.*", self._handle_user_interaction)
            
        except Exception as e:
            self.logger.error(f"❌ Event-Bus Connection failed: {e}")
            self.connected = False
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Event senden"""
        try:
            if not self.connected:
                await self.connect()
            
            event = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "source": "frontend-domain",
                "data": data
            }
            
            # Event über Bus senden (Mock)
            self.logger.info(f"📤 Event emitted: {event_type}")
            self.logger.debug(f"Event data: {json.dumps(event, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"❌ Event emit failed: {e}")
    
    async def subscribe(self, pattern: str, handler: Callable):
        """Event-Pattern abonnieren"""
        try:
            self.subscribers[pattern] = handler
            self.logger.info(f"📥 Subscribed to: {pattern}")
            
        except Exception as e:
            self.logger.error(f"❌ Subscribe failed: {e}")
    
    async def _handle_system_health(self, event: Dict[str, Any]):
        """System Health Events verarbeiten"""
        try:
            self.logger.info(f"🏥 System Health Event: {event.get('type')}")
            
            # Frontend-Update Events senden
            if event.get('type') == 'system.health.metrics':
                await self.emit("frontend.dashboard.update_metrics", {
                    "metrics": event.get('data', {})
                })
                
        except Exception as e:
            self.logger.error(f"❌ System health handler failed: {e}")
    
    async def _handle_market_data_update(self, event: Dict[str, Any]):
        """Market Data Update Events verarbeiten"""
        try:
            self.logger.info(f"📈 Market Data Update: {event.get('data', {}).get('symbol')}")
            
            # Predictions-Table Update triggern
            await self.emit("frontend.predictions.refresh", {
                "trigger": "market_data_update",
                "affected_symbols": event.get('data', {}).get('symbols', [])
            })
            
        except Exception as e:
            self.logger.error(f"❌ Market data handler failed: {e}")
    
    async def _handle_user_interaction(self, event: Dict[str, Any]):
        """User Interaction Events verarbeiten"""
        try:
            event_type = event.get('type', '')
            
            if 'timeframe.change' in event_type:
                # Timeframe-Change Event an API weiterleiten
                await self.emit("api.predictions.timeframe_change", {
                    "new_timeframe": event.get('data', {}).get('timeframe'),
                    "user_session": event.get('data', {}).get('session_id')
                })
                
            elif 'navigation' in event_type:
                # Navigation Events verarbeiten
                await self.emit("frontend.navigation.changed", {
                    "section": event.get('data', {}).get('section'),
                    "previous_section": event.get('data', {}).get('previous_section')
                })
                
        except Exception as e:
            self.logger.error(f"❌ User interaction handler failed: {e}")
            
    async def disconnect(self):
        """Event-Bus Verbindung beenden"""
        try:
            self.connected = False
            self.subscribers.clear()
            self.logger.info("📤 Event-Bus disconnected")
            
        except Exception as e:
            self.logger.error(f"❌ Disconnect failed: {e}")


# Global Event-Bus Instance
_event_bus_instance = None

def get_event_bus() -> EventBusConnector:
    """Singleton Event-Bus Instance"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBusConnector()
    return _event_bus_instance