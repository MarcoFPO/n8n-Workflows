#!/usr/bin/env python3
"""
Domain Layer - Repository Interfaces
Unified Profit Engine Enhanced v6.0 - Clean Architecture

REPOSITORY PATTERN:
- Abstract Interfaces für Data Access
- Dependency Inversion Principle
- Domain-driven Design

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal


class ProfitPredictionRepository(ABC):
    """Repository Interface für Profit Predictions"""
    
    @abstractmethod
    async def save(self, prediction) -> None:
        """Speichert eine Profit Prediction"""
        pass


class SOLLISTTrackingRepository(ABC):
    """Repository Interface für SOLL-IST Tracking"""
    
    @abstractmethod
    async def save(self, tracking) -> None:
        """Speichert SOLL-IST Tracking"""
        pass


class MarketDataRepository(ABC):
    """Repository Interface für Market Data"""
    
    @abstractmethod
    async def get_current_data(self, symbol: str):
        """Lädt aktuelle Marktdaten"""
        pass