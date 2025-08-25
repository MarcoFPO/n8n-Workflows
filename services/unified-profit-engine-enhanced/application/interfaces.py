#!/usr/bin/env python3
"""
Application Layer - Service Interfaces
Unified Profit Engine Enhanced v6.0 - Clean Architecture

INTERFACE SEGREGATION:
- Spezifische Interfaces für verschiedene Concerns
- Dependency Inversion Principle

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any


class EventPublisher(ABC):
    """Interface für Event Publishing"""
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Publiziert Event über Event-Bus"""
        pass


class MLPredictionService(ABC):
    """Interface für ML-basierte Prediction Services"""
    
    @abstractmethod
    async def generate_prediction(self, market_data, horizon) -> Dict[str, Any]:
        """Generiert ML-basierte Prediction"""
        pass