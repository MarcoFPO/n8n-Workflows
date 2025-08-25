#!/usr/bin/env python3
"""
MarketCap Service - Memory Cache Implementation
Infrastructure Layer Cache Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Implements domain cache interface
- In-memory caching for development/testing
- Thread-safe operations

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

from ...domain.entities.market_data import MarketData
from ...domain.repositories.market_data_repository import IMarketDataCache


logger = logging.getLogger(__name__)


class MemoryMarketDataCache(IMarketDataCache):
    """
    Memory-based Market Data Cache Implementation
    
    INFRASTRUCTURE LAYER: Concrete implementation of cache interface
    IN-MEMORY STORAGE: Simple LRU-like caching for development
    THREAD-SAFE: Uses asyncio locks for concurrent access
    """
    
    def __init__(self, max_size: int = 1000, default_ttl_minutes: int = 15):
        """
        Initialize memory cache
        
        Args:
            max_size: Maximum number of cached items
            default_ttl_minutes: Default TTL in minutes
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self._default_ttl_minutes = default_ttl_minutes
        self._initialized_at = datetime.now()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(f"Memory cache initialized (max_size: {max_size}, ttl: {default_ttl_minutes}min)")
    
    async def get_cached_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get cached market data
        
        Args:
            symbol: Stock symbol to retrieve
            
        Returns:
            MarketData entity or None if not cached or expired
        """
        async with self._lock:
            symbol = symbol.upper().strip()
            
            if symbol not in self._cache:
                self._misses += 1
                logger.debug(f"Cache miss for symbol: {symbol}")
                return None
            
            cached_item = self._cache[symbol]
            
            # Check TTL
            if datetime.now() > cached_item['expires_at']:
                del self._cache[symbol]
                if symbol in self._access_times:
                    del self._access_times[symbol]
                self._misses += 1
                logger.debug(f"Cache expired for symbol: {symbol}")
                return None
            
            # Update access time for LRU
            self._access_times[symbol] = datetime.now()
            self._hits += 1
            
            # Reconstruct MarketData from cached data
            data = cached_item['data']
            market_data = MarketData.from_dict(data)
            
            logger.debug(f"Cache hit for symbol: {symbol}")
            return market_data
    
    async def cache_data(self, market_data: MarketData, ttl_minutes: Optional[int] = None) -> bool:
        """
        Cache market data
        
        Args:
            market_data: MarketData entity to cache
            ttl_minutes: Custom TTL in minutes
            
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            async with self._lock:
                symbol = market_data.symbol.upper().strip()
                
                # Check if we need to evict items (LRU)
                if len(self._cache) >= self._max_size and symbol not in self._cache:
                    await self._evict_lru_item()
                
                # Calculate expiration time
                ttl = ttl_minutes or self._default_ttl_minutes
                expires_at = datetime.now() + timedelta(minutes=ttl)
                
                # Cache the item
                self._cache[symbol] = {
                    'data': market_data.to_dict(),
                    'cached_at': datetime.now(),
                    'expires_at': expires_at
                }
                self._access_times[symbol] = datetime.now()
                
                logger.debug(f"Cached data for symbol: {symbol} (TTL: {ttl}min)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache data for symbol {market_data.symbol}: {e}")
            return False
    
    async def invalidate(self, symbol: str) -> bool:
        """
        Invalidate cached data for symbol
        
        Args:
            symbol: Stock symbol to invalidate
            
        Returns:
            True if invalidated, False if not found
        """
        async with self._lock:
            symbol = symbol.upper().strip()
            
            if symbol in self._cache:
                del self._cache[symbol]
                if symbol in self._access_times:
                    del self._access_times[symbol]
                logger.debug(f"Invalidated cache for symbol: {symbol}")
                return True
            
            return False
    
    async def clear_cache(self) -> int:
        """
        Clear all cached data
        
        Returns:
            Number of items cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._access_times.clear()
            logger.info(f"Cache cleared - removed {count} items")
            return count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics dictionary
        """
        async with self._lock:
            uptime = datetime.now() - self._initialized_at
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_type': 'memory',
                'max_size': self._max_size,
                'current_size': len(self._cache),
                'default_ttl_minutes': self._default_ttl_minutes,
                'hit_rate_percentage': round(hit_rate, 2),
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'total_requests': total_requests,
                'uptime_seconds': int(uptime.total_seconds()),
                'memory_efficiency': round(len(self._cache) / self._max_size * 100, 2)
            }
    
    async def _evict_lru_item(self) -> None:
        """
        Evict least recently used item (internal method)
        """
        if not self._access_times:
            return
        
        # Find LRU item
        lru_symbol = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        # Remove from cache
        if lru_symbol in self._cache:
            del self._cache[lru_symbol]
        del self._access_times[lru_symbol]
        
        self._evictions += 1
        logger.debug(f"Evicted LRU item: {lru_symbol}")
    
    async def get_cached_symbols(self) -> list[str]:
        """
        Get list of currently cached symbols
        
        Returns:
            List of cached symbols
        """
        async with self._lock:
            return list(self._cache.keys())
    
    async def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries
        
        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            now = datetime.now()
            expired_symbols = []
            
            for symbol, cached_item in self._cache.items():
                if now > cached_item['expires_at']:
                    expired_symbols.append(symbol)
            
            # Remove expired items
            for symbol in expired_symbols:
                del self._cache[symbol]
                if symbol in self._access_times:
                    del self._access_times[symbol]
            
            if expired_symbols:
                logger.info(f"Cleaned up {len(expired_symbols)} expired cache entries")
            
            return len(expired_symbols)