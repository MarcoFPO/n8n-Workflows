#!/usr/bin/env python3
"""
Domain Layer - Business Entities
Unified Profit Engine Enhanced v6.0 - Clean Architecture

DOMAIN LAYER RESPONSIBILITIES:
- Core Business Logic
- Business Rules Enforcement
- Domain Events
- Value Objects und Entities

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import uuid4
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod


class PredictionHorizon(Enum):
    """Value Object für Prediction Horizonte"""
    ONE_WEEK = "1W"
    ONE_MONTH = "1M" 
    THREE_MONTHS = "3M"
    TWELVE_MONTHS = "12M"
    
    @property
    def days(self) -> int:
        """Konvertiert Horizont zu Tagen"""
        horizon_days = {
            "1W": 7, "1M": 30, "3M": 90, "12M": 365
        }
        return horizon_days[self.value]


@dataclass(frozen=True)
class MarketSymbol:
    """Value Object für Aktien-Symbole mit Business Rules"""
    symbol: str
    company_name: str
    market_region: str
    
    def __post_init__(self):
        """Domain Rules Validation"""
        if not self.symbol or len(self.symbol) < 1:
            raise ValueError("Symbol cannot be empty")
        if not self.company_name:
            raise ValueError("Company name is required")


class DomainEvent(ABC):
    """Base Class für Domain Events"""
    
    def __init__(self, occurred_at: datetime = None):
        self.event_id = str(uuid4())
        self.occurred_at = occurred_at or datetime.now()
    
    @abstractmethod
    def event_type(self) -> str:
        """Event Type Identifier"""
        pass