"""
ML Event Publisher v1.0.0
Event-Bus Integration für ML Analytics Service

Autor: Claude Code
Datum: 18. August 2025
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Import Event-Bus aus shared module
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))
    from event_bus import EventBusConnector
    EVENT_BUS_AVAILABLE = True
except ImportError as e:
    EVENT_BUS_AVAILABLE = False
    EventBusConnector = None

logger = logging.getLogger(__name__)

class MLEventPublisher:
    """
    Publisher für ML-bezogene Events über Event-Bus
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.event_bus = None
        self.connected = False
        
        if not EVENT_BUS_AVAILABLE:
            logger.warning("Event-Bus not available - ML events will not be published")
    
    async def initialize(self) -> bool:
        """
        Initialisiert Event-Bus Connection
        """
        if not EVENT_BUS_AVAILABLE:
            return False
            
        try:
            self.event_bus = EventBusConnector(
                redis_url=self.redis_url,
                service_name="ml-analytics"
            )
            await self.event_bus.connect()
            self.connected = True
            logger.info("ML Event Publisher initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ML Event Publisher: {str(e)}")
            self.connected = False
            return False
    
    async def close(self):
        """
        Schließt Event-Bus Connection
        """
        if self.event_bus and self.connected:
            await self.event_bus.disconnect()
            self.connected = False
            logger.info("ML Event Publisher connection closed")
    
    async def publish_feature_calculated(self, symbol: str, features: Dict[str, Any], quality_score: float):
        """
        Event: Features wurden für Symbol berechnet
        """
        event_data = {
            "event_type": "features_calculated",
            "symbol": symbol,
            "feature_count": len(features),
            "quality_score": quality_score,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-features-stream", event_data)
    
    async def publish_model_training_started(self, symbol: str, model_type: str, horizon_days: int):
        """
        Event: Model-Training gestartet
        """
        event_data = {
            "event_type": "model_training_started",
            "symbol": symbol,
            "model_type": model_type,
            "horizon_days": horizon_days,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-training-stream", event_data)
    
    async def publish_model_training_completed(self, symbol: str, model_type: str, 
                                             horizon_days: int, model_id: str, 
                                             metrics: Dict[str, float]):
        """
        Event: Model-Training abgeschlossen
        """
        event_data = {
            "event_type": "model_training_completed",
            "symbol": symbol,
            "model_type": model_type,
            "horizon_days": horizon_days,
            "model_id": model_id,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-training-stream", event_data)
    
    async def publish_prediction_generated(self, symbol: str, model_type: str, 
                                         horizon_days: int, predicted_price: float, 
                                         confidence_score: float):
        """
        Event: Prognose wurde generiert
        """
        event_data = {
            "event_type": "prediction_generated",
            "symbol": symbol,
            "model_type": model_type,
            "horizon_days": horizon_days,
            "predicted_price": predicted_price,
            "confidence_score": confidence_score,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-predictions-stream", event_data)
    
    async def publish_model_performance_alert(self, model_id: str, model_type: str, 
                                            performance_degradation: float, 
                                            alert_level: str = "warning"):
        """
        Event: Model-Performance-Alert
        """
        event_data = {
            "event_type": "model_performance_alert",
            "model_id": model_id,
            "model_type": model_type,
            "performance_degradation": performance_degradation,
            "alert_level": alert_level,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-alerts-stream", event_data)
    
    async def publish_ml_system_status(self, status: str, active_models_count: int, 
                                     last_prediction_time: Optional[str] = None):
        """
        Event: ML-System Status Update
        """
        event_data = {
            "event_type": "ml_system_status",
            "status": status,
            "active_models_count": active_models_count,
            "last_prediction_time": last_prediction_time,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ml-analytics"
        }
        
        await self._publish_event("ml-system-stream", event_data)
    
    async def _publish_event(self, stream: str, event_data: Dict[str, Any]):
        """
        Interner Event-Publisher
        """
        if not self.connected or not self.event_bus:
            logger.debug(f"Event-Bus not connected - skipping event: {event_data.get('event_type')}")
            return
            
        try:
            # Erstelle Event mit Korrelations-ID
            event = {
                "correlation_id": f"ml-{int(datetime.utcnow().timestamp() * 1000)}",
                "data": event_data
            }
            
            await self.event_bus.publish_event(stream, event)
            logger.debug(f"Published event to {stream}: {event_data.get('event_type')}")
            
        except Exception as e:
            logger.error(f"Failed to publish event to {stream}: {str(e)}")

# Singleton Instance für Service
ml_event_publisher = MLEventPublisher()

# Export für einfache Imports
__all__ = ['MLEventPublisher', 'ml_event_publisher']