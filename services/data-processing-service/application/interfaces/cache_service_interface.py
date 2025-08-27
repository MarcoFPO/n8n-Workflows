"""
Data Processing Service - Cache Service Interface
Timeframe-Specific Aggregation v7.1 - Clean Architecture Application Layer

Cache Service Interface für Performance Optimization (Dependency Inversion Principle)
SOLID Principles: Interface Segregation, Dependency Inversion, Single Responsibility
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import timedelta


class CacheServiceInterface(ABC):
    """
    Cache Service Interface für High-Performance Aggregation Caching
    
    SOLID PRINCIPLES:
    - Interface Segregation: Spezifische Methods für Cache Operations
    - Dependency Inversion: Application Layer hängt von Interface ab, nicht Implementation
    - Single Responsibility: Ausschließlich Caching Operations
    
    PERFORMANCE REQUIREMENTS:
    - Cache Hit Rate: >85%
    - Cache Access Time: <10ms
    - TTL Management: Automatic expiration
    - Memory Efficiency: Optimized serialization
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get Value from Cache
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Dict[str, Any]]: Cached value oder None if not found/expired
            
        Performance Target: <10ms response time
        """
        pass
    
    @abstractmethod
    async def set(self, 
                 key: str, 
                 value: Dict[str, Any], 
                 ttl_seconds: int = 300) -> bool:
        """
        Set Value in Cache mit TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (default 5 minutes)
            
        Returns:
            bool: Success status
            
        Performance Target: <20ms set time
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete Value from Cache
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: Success status (True even if key didn't exist)
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if Key Exists in Cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if key exists and not expired
        """
        pass
    
    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get Remaining TTL für Key
        
        Args:
            key: Cache key
            
        Returns:
            Optional[int]: Remaining seconds until expiration, None if key doesn't exist
        """
        pass
    
    @abstractmethod
    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        Extend TTL für Existing Key
        
        Args:
            key: Cache key
            additional_seconds: Seconds to add to current TTL
            
        Returns:
            bool: Success status
        """
        pass
    
    @abstractmethod
    async def get_multiple(self, keys: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get Multiple Values from Cache (Batch Operation)
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dict[str, Optional[Dict[str, Any]]]: Dictionary mapping keys to values
            
        Performance Target: <50ms für batch of 10 keys
        """
        pass
    
    @abstractmethod
    async def set_multiple(self, 
                          items: Dict[str, Dict[str, Any]], 
                          ttl_seconds: int = 300) -> Dict[str, bool]:
        """
        Set Multiple Values in Cache (Batch Operation)
        
        Args:
            items: Dictionary mapping keys to values
            ttl_seconds: TTL für all items
            
        Returns:
            Dict[str, bool]: Success status für each key
            
        Performance Target: <100ms für batch of 10 items
        """
        pass
    
    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete All Keys Matching Pattern
        
        Args:
            pattern: Pattern to match (supports wildcards wie 'aggregation:*')
            
        Returns:
            int: Number of deleted keys
            
        Use Case: Cache invalidation für timeframe updates
        """
        pass
    
    @abstractmethod
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get Cache Performance Statistics
        
        Returns:
            Dict[str, Any]: Statistics containing:
                - hit_ratio: float
                - total_requests: int
                - hit_count: int  
                - miss_count: int
                - total_keys: int
                - memory_usage_mb: float
                - average_response_time_ms: float
        """
        pass
    
    @abstractmethod
    async def warm_cache(self, 
                        key_value_pairs: Dict[str, Dict[str, Any]], 
                        ttl_seconds: int = 600) -> Dict[str, bool]:
        """
        Warm Cache mit Predicted Hot Data
        
        Args:
            key_value_pairs: Dictionary of key-value pairs to pre-load
            ttl_seconds: TTL für warmed data (default 10 minutes)
            
        Returns:
            Dict[str, bool]: Success status für each key
            
        Use Case: Pre-populate cache mit likely-to-be-requested aggregations
        """
        pass
    
    @abstractmethod
    async def get_key_size(self, key: str) -> Optional[int]:
        """
        Get Memory Size of Cached Value
        
        Args:
            key: Cache key
            
        Returns:
            Optional[int]: Size in bytes, None if key doesn't exist
            
        Use Case: Memory optimization und monitoring
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_keys(self) -> int:
        """
        Manually Trigger Cleanup of Expired Keys
        
        Returns:
            int: Number of cleaned up keys
            
        Use Case: Memory management und maintenance
        """
        pass
    
    @abstractmethod
    async def get_keys_by_pattern(self, pattern: str, limit: int = 100) -> List[str]:
        """
        Get Keys Matching Pattern
        
        Args:
            pattern: Pattern to match
            limit: Maximum number of keys to return
            
        Returns:
            List[str]: Matching cache keys
            
        Use Case: Cache inspection und debugging
        """
        pass
    
    @abstractmethod
    async def set_with_custom_expiry(self, 
                                   key: str, 
                                   value: Dict[str, Any], 
                                   expires_at: float) -> bool:
        """
        Set Value mit Custom Expiration Timestamp
        
        Args:
            key: Cache key
            value: Value to cache
            expires_at: Unix timestamp when key should expire
            
        Returns:
            bool: Success status
            
        Use Case: Sync expiry mit business logic (e.g., market hours)
        """
        pass
    
    @abstractmethod
    async def increment_counter(self, key: str, increment: int = 1, ttl_seconds: int = 3600) -> int:
        """
        Increment Counter Value in Cache
        
        Args:
            key: Counter key
            increment: Value to increment by
            ttl_seconds: TTL für counter if creating new
            
        Returns:
            int: New counter value
            
        Use Case: Request counting, rate limiting
        """
        pass
    
    @abstractmethod
    async def get_cache_health(self) -> Dict[str, Any]:
        """
        Get Cache Health Status
        
        Returns:
            Dict[str, Any]: Health status containing:
                - status: str ('healthy', 'degraded', 'unhealthy')
                - connectivity: bool
                - latency_ms: float
                - memory_pressure: float (0.0-1.0)
                - error_rate: float
                - uptime_seconds: int
        """
        pass