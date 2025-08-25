#!/usr/bin/env python3
"""
MarketCap Service - Mock Data Provider
Infrastructure Layer External Service Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain provider interface
- Mock implementation for development and testing
- External service adapter pattern

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import random
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
import asyncio

from ...domain.entities.market_data import MarketData
from ...domain.repositories.market_data_repository import IMarketDataProvider


logger = logging.getLogger(__name__)


class MockMarketDataProvider(IMarketDataProvider):
    """
    Mock Market Data Provider Implementation
    
    INFRASTRUCTURE LAYER: External service simulation
    ADAPTER PATTERN: Adapts external data format to domain entities
    DEVELOPMENT/TESTING: Provides realistic mock data
    """
    
    def __init__(self, latency_ms: int = 100, availability: float = 0.95):
        """
        Initialize mock provider
        
        Args:
            latency_ms: Simulated network latency in milliseconds
            availability: Service availability ratio (0.0-1.0)
        """
        self.latency_ms = latency_ms
        self.availability = availability
        self.is_service_available = True
        self.request_count = 0
        self.initialized_at = datetime.now()
        
        # Mock data pool for realistic responses
        self.company_data = {
            'AAPL': {'name': 'Apple Inc.', 'base_price': 175.0, 'base_cap': 2800000000000},
            'GOOGL': {'name': 'Alphabet Inc.', 'base_price': 140.0, 'base_cap': 1700000000000},
            'MSFT': {'name': 'Microsoft Corporation', 'base_price': 380.0, 'base_cap': 2900000000000},
            'AMZN': {'name': 'Amazon.com Inc.', 'base_price': 145.0, 'base_cap': 1500000000000},
            'TSLA': {'name': 'Tesla Inc.', 'base_price': 250.0, 'base_cap': 800000000000},
            'META': {'name': 'Meta Platforms Inc.', 'base_price': 320.0, 'base_cap': 850000000000},
            'NVDA': {'name': 'NVIDIA Corporation', 'base_price': 480.0, 'base_cap': 1200000000000},
            'NFLX': {'name': 'Netflix Inc.', 'base_price': 450.0, 'base_cap': 200000000000},
            'CRM': {'name': 'Salesforce Inc.', 'base_price': 220.0, 'base_cap': 220000000000},
            'ORCL': {'name': 'Oracle Corporation', 'base_price': 110.0, 'base_cap': 320000000000},
            
            # Mid Cap examples
            'SPOT': {'name': 'Spotify Technology', 'base_price': 160.0, 'base_cap': 32000000000},
            'SNAP': {'name': 'Snap Inc.', 'base_price': 12.0, 'base_cap': 18000000000},
            'TWTR': {'name': 'Twitter Inc.', 'base_price': 54.0, 'base_cap': 43000000000},
            'SQ': {'name': 'Block Inc.', 'base_price': 70.0, 'base_cap': 40000000000},
            'ROKU': {'name': 'Roku Inc.', 'base_price': 80.0, 'base_cap': 9000000000},
            
            # Small Cap examples  
            'PLTR': {'name': 'Palantir Technologies', 'base_price': 18.0, 'base_cap': 38000000000},
            'BB': {'name': 'BlackBerry Limited', 'base_price': 5.5, 'base_cap': 3200000000},
            'NOK': {'name': 'Nokia Corporation', 'base_price': 4.2, 'base_cap': 24000000000},
            'GME': {'name': 'GameStop Corp.', 'base_price': 20.0, 'base_cap': 6200000000},
            'AMC': {'name': 'AMC Entertainment', 'base_price': 8.0, 'base_cap': 4300000000}
        }
        
        logger.info(f"Mock Market Data Provider initialized with {len(self.company_data)} symbols")
    
    async def fetch_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Fetch market data from mock external source
        
        Args:
            symbol: Stock symbol to fetch
            
        Returns:
            MarketData entity or None if not available
        """
        self.request_count += 1
        symbol = symbol.upper().strip()
        
        logger.debug(f"Mock provider fetching data for symbol: {symbol}")
        
        # Simulate network latency
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Check service availability
        if not await self.is_available():
            logger.warning(f"Mock provider unavailable for symbol: {symbol}")
            return None
        
        # Check if symbol exists in our mock data
        if symbol not in self.company_data:
            logger.debug(f"Symbol {symbol} not found in mock data")
            return None
        
        try:
            # Generate realistic mock data
            company_info = self.company_data[symbol]
            
            # Add some randomization to make it realistic
            price_variation = random.uniform(-0.05, 0.05)  # ±5% variation
            base_price = company_info['base_price']
            current_price = base_price * (1 + price_variation)
            
            # Calculate daily change
            daily_change = random.uniform(-5.0, 5.0)  # ±5% daily change
            
            # Calculate market cap (price could affect market cap in reality)
            cap_variation = random.uniform(-0.02, 0.02)  # ±2% cap variation
            base_cap = company_info['base_cap']
            current_cap = base_cap * (1 + cap_variation)
            
            # Create MarketData entity
            market_data = MarketData(
                symbol=symbol,
                company_name=company_info['name'],
                market_cap=Decimal(str(int(current_cap))),
                stock_price=Decimal(str(round(current_price, 2))),
                daily_change_percent=Decimal(str(round(daily_change, 2))),
                timestamp=datetime.now(),
                source=f"mock_provider_v6.0.0"
            )
            
            logger.info(f"Mock provider generated data for {symbol}: ${current_price:.2f} ({daily_change:+.2f}%)")
            return market_data
            
        except Exception as e:
            logger.error(f"Error generating mock data for symbol {symbol}: {e}")
            return None
    
    async def is_available(self) -> bool:
        """
        Check if data provider is available
        
        Returns:
            True if available, False otherwise
        """
        # Simulate occasional service unavailability
        if random.random() > self.availability:
            self.is_service_available = False
            logger.warning("Mock provider temporarily unavailable")
            return False
        
        self.is_service_available = True
        return True
    
    async def get_supported_symbols(self) -> List[str]:
        """
        Get list of supported symbols
        
        Returns:
            List of supported stock symbols
        """
        symbols = list(self.company_data.keys())
        logger.debug(f"Mock provider supports {len(symbols)} symbols")
        return symbols
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information
        
        Returns:
            Provider information dictionary
        """
        uptime = datetime.now() - self.initialized_at
        
        return {
            'provider_name': 'Mock Market Data Provider',
            'provider_type': 'mock',
            'version': '6.0.0',
            'supported_symbols_count': len(self.company_data),
            'supported_symbols': list(self.company_data.keys()),
            'availability': self.availability,
            'latency_ms': self.latency_ms,
            'is_available': self.is_service_available,
            'request_count': self.request_count,
            'uptime_seconds': int(uptime.total_seconds()),
            'initialized_at': self.initialized_at.isoformat(),
            'last_check': datetime.now().isoformat(),
            'features': [
                'Real-time mock data generation',
                'Realistic price variations',
                'Market cap classifications',
                'Configurable latency simulation',
                'Availability simulation'
            ]
        }
    
    async def set_availability(self, availability: float) -> None:
        """
        Set service availability for testing
        
        Args:
            availability: New availability ratio (0.0-1.0)
        """
        self.availability = max(0.0, min(1.0, availability))
        logger.info(f"Mock provider availability set to {self.availability:.2%}")
    
    async def set_latency(self, latency_ms: int) -> None:
        """
        Set service latency for testing
        
        Args:
            latency_ms: New latency in milliseconds
        """
        self.latency_ms = max(0, latency_ms)
        logger.info(f"Mock provider latency set to {self.latency_ms}ms")
    
    async def add_symbol(self, symbol: str, company_name: str, base_price: float, base_cap: int) -> None:
        """
        Add new symbol to mock data (for testing)
        
        Args:
            symbol: Stock symbol
            company_name: Company name
            base_price: Base stock price
            base_cap: Base market capitalization
        """
        symbol = symbol.upper().strip()
        self.company_data[symbol] = {
            'name': company_name,
            'base_price': base_price,
            'base_cap': base_cap
        }
        logger.info(f"Added symbol {symbol} ({company_name}) to mock provider")
    
    async def remove_symbol(self, symbol: str) -> bool:
        """
        Remove symbol from mock data (for testing)
        
        Args:
            symbol: Stock symbol to remove
            
        Returns:
            True if removed, False if not found
        """
        symbol = symbol.upper().strip()
        if symbol in self.company_data:
            del self.company_data[symbol]
            logger.info(f"Removed symbol {symbol} from mock provider")
            return True
        return False
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """
        Get detailed provider statistics
        
        Returns:
            Provider statistics dictionary
        """
        uptime = datetime.now() - self.initialized_at
        
        # Calculate cap distribution
        cap_distribution = {"Large Cap": 0, "Mid Cap": 0, "Small Cap": 0}
        for company_info in self.company_data.values():
            base_cap = Decimal(str(company_info['base_cap']))
            if base_cap >= Decimal('10000000000'):  # 10 billion
                cap_distribution["Large Cap"] += 1
            elif base_cap >= Decimal('2000000000'):  # 2 billion
                cap_distribution["Mid Cap"] += 1
            else:
                cap_distribution["Small Cap"] += 1
        
        return {
            'total_symbols': len(self.company_data),
            'cap_distribution': cap_distribution,
            'request_count': self.request_count,
            'uptime_hours': round(uptime.total_seconds() / 3600, 2),
            'average_availability': self.availability,
            'current_latency_ms': self.latency_ms,
            'service_status': 'available' if self.is_service_available else 'unavailable'
        }