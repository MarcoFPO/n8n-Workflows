"""
Simple Event Bus implementation für Testing
Vereinfachte Version ohne externe Dependencies für erste Tests
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Standard event types for the system"""
    STOCK_ANALYZED = "stock_analyzed"
    ORDER_CREATED = "order_created"
    ORDER_EXECUTED = "order_executed"
    DATA_SYNCHRONIZED = "data_synchronized"
    PERFORMANCE_CALCULATED = "performance_calculated"
    SYSTEM_ALERT = "system_alert"


class EventBusConnector:
    """Simplified Event Bus Connector for testing"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.connected = False
        self.subscribers: Dict[str, Callable] = {}
        
    async def connect(self):
        """Connect to event bus"""
        try:
            # Simulate connection
            await asyncio.sleep(0.1)
            self.connected = True
            logger.info("Event bus connected", service=self.service_name)
        except Exception as e:
            logger.error("Failed to connect to event bus", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from event bus"""
        try:
            self.connected = False
            self.subscribers.clear()
            logger.info("Event bus disconnected", service=self.service_name)
        except Exception as e:
            logger.error("Failed to disconnect from event bus", error=str(e))
    
    async def publish(self, event: Dict[str, Any]):
        """Publish event to bus"""
        try:
            if not self.connected:
                raise RuntimeError("Event bus not connected")
            
            # For testing, just log the event
            logger.info("Event published",
                       event_type=event.get("event_type"),
                       source=event.get("source"),
                       service=self.service_name)
            
        except Exception as e:
            logger.error("Failed to publish event", error=str(e))
            raise
    
    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to event type"""
        try:
            if not self.connected:
                raise RuntimeError("Event bus not connected")
            
            self.subscribers[event_type] = handler
            logger.info("Subscribed to event",
                       event_type=event_type,
                       service=self.service_name)
            
        except Exception as e:
            logger.error("Failed to subscribe to event", error=str(e))
            raise


def create_analysis_event(symbol: str, score: float, recommendation: str, 
                         source: str, confidence: float = None) -> Dict[str, Any]:
    """Create standardized analysis event"""
    return {
        "event_id": f"analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "event_type": EventType.STOCK_ANALYZED.value,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "data": {
            "symbol": symbol,
            "score": score,
            "recommendation": recommendation,
            "confidence": confidence
        },
        "metadata": {
            "version": "1.0",
            "format": "json"
        }
    }


def create_order_event(symbol: str, action: str, quantity: int, 
                      price: float, source: str) -> Dict[str, Any]:
    """Create standardized order event"""
    return {
        "event_id": f"order_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "event_type": EventType.ORDER_CREATED.value,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "data": {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price
        },
        "metadata": {
            "version": "1.0",
            "format": "json"
        }
    }


def create_performance_event(total_return: float, sharpe_ratio: float,
                           max_drawdown: float, source: str) -> Dict[str, Any]:
    """Create standardized performance event"""
    return {
        "event_id": f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "event_type": EventType.PERFORMANCE_CALCULATED.value,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "data": {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown
        },
        "metadata": {
            "version": "1.0",
            "format": "json"
        }
    }