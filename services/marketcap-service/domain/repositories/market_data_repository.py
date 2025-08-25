#!/usr/bin/env python3
"""
MarketCap Service - Domain Repository Interface
Repository Pattern for Market Data Access

CLEAN ARCHITECTURE - DOMAIN LAYER:
- Defines interfaces for data access
- Independent of implementation details
- Repository Pattern compliance

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..entities.market_data import MarketData, MarketDataRequest


class IMarketDataRepository(ABC):
    """
    Market Data Repository Interface
    
    REPOSITORY PATTERN: Abstract interface for market data persistence
    DEPENDENCY INVERSION: High-level modules depend on this abstraction
    """
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Retrieve market data for a symbol
        
        Args:
            symbol: Stock symbol to retrieve data for
            
        Returns:
            MarketData entity or None if not found
        """
        pass
    
    @abstractmethod
    async def save_market_data(self, market_data: MarketData) -> bool:
        """
        Save market data
        
        Args:
            market_data: MarketData entity to save
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_all_symbols(self) -> List[str]:
        """
        Get all available symbols
        
        Returns:
            List of available stock symbols
        """
        pass
    
    @abstractmethod
    async def get_market_data_by_cap_size(self, cap_classification: str) -> List[MarketData]:
        """
        Get market data filtered by cap size
        
        Args:
            cap_classification: "Large Cap", "Mid Cap", or "Small Cap"
            
        Returns:
            List of MarketData entities matching cap classification
        """
        pass
    
    @abstractmethod
    async def get_fresh_market_data(self, max_age_minutes: int = 15) -> List[MarketData]:
        """
        Get fresh market data within age limit
        
        Args:
            max_age_minutes: Maximum age of data in minutes
            
        Returns:
            List of fresh MarketData entities
        """
        pass
    
    @abstractmethod
    async def delete_stale_data(self, max_age_hours: int = 24) -> int:
        """
        Delete stale market data
        
        Args:
            max_age_hours: Maximum age of data to keep in hours
            
        Returns:
            Number of records deleted
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get repository health status
        
        Returns:
            Health status dictionary
        """
        pass


class IMarketDataCache(ABC):
    """
    Market Data Cache Interface
    
    CACHING PATTERN: Abstract interface for caching layer
    PERFORMANCE: Provides fast access to frequently requested data
    """
    
    @abstractmethod
    async def get_cached_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get cached market data
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Cached MarketData entity or None
        """
        pass
    
    @abstractmethod
    async def cache_data(self, market_data: MarketData, ttl_seconds: int = 900) -> bool:
        """
        Cache market data
        
        Args:
            market_data: MarketData entity to cache
            ttl_seconds: Time to live in seconds (default 15 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def invalidate_cache(self, symbol: str) -> bool:
        """
        Invalidate cached data for symbol
        
        Args:
            symbol: Stock symbol to invalidate
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def clear_all_cache(self) -> bool:
        """
        Clear all cached data
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics dictionary
        """
        pass


class IMarketDataProvider(ABC):
    """
    Market Data Provider Interface
    
    EXTERNAL SERVICE INTEGRATION: Abstract interface for data providers
    ADAPTER PATTERN: Allows different data source implementations
    """
    
    @abstractmethod
    async def fetch_market_data(self, symbol: str) -> Optional[MarketData]:
        """
        Fetch market data from external source
        
        Args:
            symbol: Stock symbol to fetch
            
        Returns:
            MarketData entity or None if not available
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if data provider is available
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_supported_symbols(self) -> List[str]:
        """
        Get list of supported symbols
        
        Returns:
            List of supported stock symbols
        """
        pass
    
    @abstractmethod
    async def get_provider_info(self) -> Dict[str, Any]:
        """
        Get provider information
        
        Returns:
            Provider information dictionary
        """
        pass