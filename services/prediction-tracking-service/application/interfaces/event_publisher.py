#!/usr/bin/env python3
"""
Prediction Tracking Service - Event Publisher Interface
Application Layer Interface für Event Publishing

CLEAN ARCHITECTURE - APPLICATION LAYER:
- Defines interfaces for external services
- Port for Event-Driven Architecture integration
- Independent of implementation details

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class IEventPublisher(ABC):
    """
    Event Publisher Interface
    
    PORT INTERFACE: Defines contract for event publishing
    EVENT-DRIVEN ARCHITECTURE: Integration with Event-Bus Service
    DEPENDENCY INVERSION: Application layer depends on this abstraction
    """
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any], entity_id: Optional[str] = None) -> bool:
        """
        Publish an event
        
        Args:
            event_type: Type of event (e.g., 'prediction.stored')
            event_data: Event payload data
            entity_id: Optional entity identifier for correlation
            
        Returns:
            True if published successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if event publishing is available
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get event publisher health status
        
        Returns:
            Health status dictionary
        """
        pass


class PredictionTrackingEvents:
    """
    Prediction Tracking Domain Events
    
    DOMAIN EVENTS: Standard event types for prediction tracking domain
    """
    
    # Prediction Events
    PREDICTION_STORED = "prediction.stored"
    PREDICTION_EVALUATED = "prediction.evaluated"
    PREDICTION_UPDATED = "prediction.updated"
    PREDICTION_EXPIRED = "prediction.expired"
    
    # Performance Events
    PERFORMANCE_CALCULATED = "performance.calculated"
    PERFORMANCE_THRESHOLD_BREACH = "performance.threshold_breach"
    
    # Service Events
    SERVICE_STARTED = "prediction_tracking_service.started"
    SERVICE_STOPPED = "prediction_tracking_service.stopped"
    SERVICE_ERROR = "prediction_tracking_service.error"
    
    # Health Events
    HEALTH_CHECK_OK = "prediction_tracking_service.health.ok"
    HEALTH_CHECK_FAILED = "prediction_tracking_service.health.failed"
    
    # Repository Events
    REPOSITORY_ERROR = "prediction_tracking_service.repository.error"
    CACHE_MISS = "prediction_tracking_service.cache.miss"
    CACHE_HIT = "prediction_tracking_service.cache.hit"
    
    @classmethod
    def get_all_events(cls) -> list[str]:
        """Get all defined event types"""
        return [
            cls.PREDICTION_STORED,
            cls.PREDICTION_EVALUATED,
            cls.PREDICTION_UPDATED,
            cls.PREDICTION_EXPIRED,
            cls.PERFORMANCE_CALCULATED,
            cls.PERFORMANCE_THRESHOLD_BREACH,
            cls.SERVICE_STARTED,
            cls.SERVICE_STOPPED,
            cls.SERVICE_ERROR,
            cls.HEALTH_CHECK_OK,
            cls.HEALTH_CHECK_FAILED,
            cls.REPOSITORY_ERROR,
            cls.CACHE_MISS,
            cls.CACHE_HIT
        ]