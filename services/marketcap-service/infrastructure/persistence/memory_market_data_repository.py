#!/usr/bin/env python3
"""
MarketCap Service - Memory Market Data Repository
Infrastructure Layer Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain repository interfaces
- Provides in-memory storage for market data
- External concern implementation

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from ...domain.entities.market_data import MarketData
from ...domain.repositories.market_data_repository import IMarketDataRepository


logger = logging.getLogger(__name__)


class MemoryMarketDataRepository(IMarketDataRepository):
    """
    Memory-based Market Data Repository Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of repository interface
    IN-MEMORY STORAGE: Simple storage for development and testing
    THREAD-SAFE: Uses asyncio locks for concurrent access
    """
    
    def __init__(self):
        self._data: Dict[str, MarketData] = {}
        self._lock = asyncio.Lock()
        self._initialized_at = datetime.now()
        self._operations_count = 0
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Retrieve market data for a symbol
        
        Args:
            symbol: Stock symbol to retrieve data for
            
        Returns:
            MarketData entity or None if not found
        """
        async with self._lock:
            self._operations_count += 1
            symbol = symbol.upper().strip()
            
            logger.debug(f"Retrieving market data for symbol: {symbol}")
            market_data = self._data.get(symbol)
            
            if market_data:
                logger.debug(f"Found market data for symbol: {symbol}")
            else:
                logger.debug(f"No market data found for symbol: {symbol}")
            
            return market_data
    
    async def save_market_data(self, market_data: MarketData) -> bool:
        """
        Save market data
        
        Args:
            market_data: MarketData entity to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with self._lock:
                self._operations_count += 1
                symbol = market_data.symbol.upper().strip()
                
                logger.debug(f"Saving market data for symbol: {symbol}")
                self._data[symbol] = market_data
                
                logger.info(f"Successfully saved market data for symbol: {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save market data for symbol {market_data.symbol}: {e}")
            return False
    
    async def get_all_symbols(self) -> List[str]:
        """
        Get all available symbols
        
        Returns:
            List of available stock symbols
        """
        async with self._lock:
            self._operations_count += 1
            symbols = list(self._data.keys())
            logger.debug(f"Retrieved {len(symbols)} symbols from repository")
            return symbols
    
    async def get_market_data_by_cap_size(self, cap_classification: str) -> List[MarketData]:
        """
        Get market data filtered by cap size
        
        Args:
            cap_classification: "Large Cap", "Mid Cap", or "Small Cap"
            
        Returns:
            List of MarketData entities matching cap classification
        """
        async with self._lock:
            self._operations_count += 1
            
            logger.debug(f"Filtering market data by cap classification: {cap_classification}")
            
            filtered_data = []
            for market_data in self._data.values():
                if market_data.get_cap_classification() == cap_classification:
                    filtered_data.append(market_data)
            
            logger.debug(f"Found {len(filtered_data)} records for cap classification: {cap_classification}")
            return filtered_data
    
    async def get_fresh_market_data(self, max_age_minutes: int = 15) -> List[MarketData]:
        """
        Get fresh market data within age limit
        
        Args:
            max_age_minutes: Maximum age of data in minutes
            
        Returns:
            List of fresh MarketData entities
        """
        async with self._lock:
            self._operations_count += 1
            
            logger.debug(f"Retrieving fresh market data (max age: {max_age_minutes} minutes)")
            
            fresh_data = []
            for market_data in self._data.values():
                if market_data.is_data_fresh(max_age_minutes):
                    fresh_data.append(market_data)
            
            logger.debug(f"Found {len(fresh_data)} fresh records")
            return fresh_data
    
    async def delete_stale_data(self, max_age_hours: int = 24) -> int:
        """
        Delete stale market data
        
        Args:
            max_age_hours: Maximum age of data to keep in hours
            
        Returns:
            Number of records deleted
        """
        async with self._lock:
            self._operations_count += 1
            
            logger.debug(f"Deleting stale market data (max age: {max_age_hours} hours)")
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            symbols_to_delete = []
            
            for symbol, market_data in self._data.items():
                if market_data.timestamp < cutoff_time:
                    symbols_to_delete.append(symbol)
            
            # Delete stale records
            deleted_count = 0
            for symbol in symbols_to_delete:
                del self._data[symbol]
                deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} stale records")
            return deleted_count
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get repository health status
        
        Returns:
            Health status dictionary
        """
        async with self._lock:
            uptime = datetime.now() - self._initialized_at
            total_records = len(self._data)
            fresh_records = len(await self.get_fresh_market_data())
            
            return {
                'status': 'healthy',
                'repository_type': 'memory',
                'total_records': total_records,
                'fresh_records': fresh_records,
                'stale_records': total_records - fresh_records,
                'operations_count': self._operations_count,
                'uptime_seconds': int(uptime.total_seconds()),
                'initialized_at': self._initialized_at.isoformat(),
                'last_check': datetime.now().isoformat()
            }
    
    async def clear_all_data(self) -> int:
        """
        Clear all data (utility method)
        
        Returns:
            Number of records cleared
        """
        async with self._lock:
            count = len(self._data)
            self._data.clear()
            logger.info(f"Cleared {count} records from repository")
            return count
    
    async def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get detailed repository statistics
        
        Returns:
            Repository statistics dictionary
        """
        async with self._lock:
            symbols = list(self._data.keys())
            
            # Calculate cap distribution
            cap_distribution = {"Large Cap": 0, "Mid Cap": 0, "Small Cap": 0}
            positive_performance_count = 0
            
            for market_data in self._data.values():
                cap_classification = market_data.get_cap_classification()
                cap_distribution[cap_classification] += 1
                
                if market_data.is_positive_performance():
                    positive_performance_count += 1
            
            return {
                'total_symbols': len(symbols),
                'symbols': symbols,
                'cap_distribution': cap_distribution,
                'positive_performance_count': positive_performance_count,
                'negative_performance_count': len(symbols) - positive_performance_count,
                'operations_count': self._operations_count,
                'memory_usage_estimate': len(str(self._data))  # Rough estimate
            }