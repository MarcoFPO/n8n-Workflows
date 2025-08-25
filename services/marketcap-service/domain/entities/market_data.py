#!/usr/bin/env python3
"""
MarketCap Service - Domain Entities
Market Data Entity with Business Logic

CLEAN ARCHITECTURE - DOMAIN LAYER:
- Contains business entities with core business logic
- Independent of external concerns
- Immutable data structures where possible

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class MarketData:
    """
    Market Data Domain Entity
    
    IMMUTABLE: Core business entity representing market data
    BUSINESS LOGIC: Contains validation and business rules
    """
    
    symbol: str
    company_name: str
    market_cap: Decimal
    stock_price: Decimal
    daily_change_percent: Decimal
    timestamp: datetime
    source: str
    
    def __post_init__(self):
        """Validate business rules"""
        self._validate_symbol()
        self._validate_market_cap()
        self._validate_stock_price()
        self._validate_daily_change()
    
    def _validate_symbol(self):
        """Validate stock symbol"""
        if not self.symbol or len(self.symbol.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        if len(self.symbol) > 10:
            raise ValueError("Symbol cannot be longer than 10 characters")
        if not self.symbol.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Symbol must contain only alphanumeric characters, dots, and hyphens")
    
    def _validate_market_cap(self):
        """Validate market capitalization"""
        if self.market_cap < 0:
            raise ValueError("Market cap cannot be negative")
        if self.market_cap > Decimal('1000000000000000'):  # 1 quadrillion limit
            raise ValueError("Market cap exceeds maximum allowed value")
    
    def _validate_stock_price(self):
        """Validate stock price"""
        if self.stock_price < 0:
            raise ValueError("Stock price cannot be negative")
        if self.stock_price > Decimal('1000000'):  # 1 million per share limit
            raise ValueError("Stock price exceeds maximum allowed value")
    
    def _validate_daily_change(self):
        """Validate daily change percentage"""
        if self.daily_change_percent < -100:
            raise ValueError("Daily change cannot be less than -100%")
        if self.daily_change_percent > 1000:  # 1000% change limit
            raise ValueError("Daily change cannot exceed 1000%")
    
    def is_positive_performance(self) -> bool:
        """Business logic: Check if stock performed positively"""
        return self.daily_change_percent > 0
    
    def is_large_cap(self) -> bool:
        """Business logic: Determine if this is a large cap stock"""
        return self.market_cap >= Decimal('10000000000')  # 10 billion
    
    def is_mid_cap(self) -> bool:
        """Business logic: Determine if this is a mid cap stock"""
        return Decimal('2000000000') <= self.market_cap < Decimal('10000000000')  # 2-10 billion
    
    def is_small_cap(self) -> bool:
        """Business logic: Determine if this is a small cap stock"""
        return self.market_cap < Decimal('2000000000')  # < 2 billion
    
    def get_cap_classification(self) -> str:
        """Business logic: Get market cap classification"""
        if self.is_large_cap():
            return "Large Cap"
        elif self.is_mid_cap():
            return "Mid Cap"
        else:
            return "Small Cap"
    
    def calculate_market_value(self, shares_outstanding: Optional[Decimal] = None) -> Optional[Decimal]:
        """Business logic: Calculate total market value"""
        if shares_outstanding is None:
            return self.market_cap
        return self.stock_price * shares_outstanding
    
    def is_data_fresh(self, max_age_minutes: int = 15) -> bool:
        """Business logic: Check if market data is fresh"""
        now = datetime.now()
        age_minutes = (now - self.timestamp).total_seconds() / 60
        return age_minutes <= max_age_minutes
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'market_cap': str(self.market_cap),
            'stock_price': str(self.stock_price),
            'daily_change_percent': str(self.daily_change_percent),
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'cap_classification': self.get_cap_classification(),
            'is_positive_performance': self.is_positive_performance(),
            'is_data_fresh': self.is_data_fresh()
        }


@dataclass(frozen=True)
class MarketDataRequest:
    """
    Market Data Request Domain Entity
    
    IMMUTABLE: Represents a request for market data
    """
    
    symbol: str
    requested_at: datetime
    source: str = "marketcap_service"
    
    def __post_init__(self):
        """Validate request"""
        if not self.symbol or len(self.symbol.strip()) == 0:
            raise ValueError("Symbol is required for market data request")
        if len(self.symbol) > 10:
            raise ValueError("Symbol cannot be longer than 10 characters")
    
    def is_request_valid(self) -> bool:
        """Business logic: Check if request is still valid"""
        now = datetime.now()
        age_minutes = (now - self.requested_at).total_seconds() / 60
        return age_minutes <= 60  # Request valid for 1 hour
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            'symbol': self.symbol,
            'requested_at': self.requested_at.isoformat(),
            'source': self.source,
            'is_valid': self.is_request_valid()
        }