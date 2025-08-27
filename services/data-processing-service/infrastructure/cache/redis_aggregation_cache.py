"""
Data Processing Service - Redis Aggregation Cache Implementation
Timeframe-Specific Aggregation v7.1 - Clean Architecture Infrastructure Layer

Redis Implementation für High-Performance Aggregation Caching
SOLID Principles: Single Responsibility, Dependency Inversion, Interface Implementation
"""
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging
from decimal import Decimal

# Application Interface
from ...application.interfaces.cache_service_interface import CacheServiceInterface

# Infrastructure Exceptions
class CacheException(Exception):
    """Exception für Cache Layer Errors"""
    pass


class RedisAggregationCacheService(CacheServiceInterface):
    """
    Redis Implementation für High-Performance Aggregation Caching
    
    PERFORMANCE REQUIREMENTS:
    - Cache Hit Rate: >85% target
    - Cache Access Time: <10ms average
    - Memory Efficiency: Optimized JSON serialization
    - TTL Management: Automatic expiration handling
    
    REDIS OPTIMIZATIONS:
    - Pipeline operations für batch requests
    - Connection pooling für concurrent access
    - Memory-efficient data structures
    - Intelligent key naming conventions
    """
    
    def __init__(self, 
                 redis_pool: redis.ConnectionPool,
                 key_prefix: str = "aggregation",
                 logger: Optional[logging.Logger] = None):
        """
        Initialize Redis Cache Service
        
        Args:
            redis_pool: Redis connection pool
            key_prefix: Prefix für all cache keys
            logger: Optional logger instance
        """
        self._pool = redis_pool
        self._key_prefix = key_prefix
        self._logger = logger or logging.getLogger(__name__)
        
        # Performance Monitoring
        self._hit_count = 0
        self._miss_count = 0
        self._error_count = 0
        self._total_requests = 0
        self._response_times = []
        
        # Configuration
        self._default_ttl = 300  # 5 minutes
        self._max_response_times_tracked = 1000
        self._serialization_version = "v7.1"
    
    def _build_key(self, key: str) -> str:
        """Build full cache key mit prefix"""
        return f"{self._key_prefix}:{key}"
    
    def _serialize_value(self, value: Dict[str, Any]) -> str:
        """Serialize value für Redis storage mit optimization"""
        try:
            # Add metadata für version control
            serialized_data = {
                'data': value,
                'version': self._serialization_version,
                'cached_at': datetime.now().isoformat(),
                'cache_type': 'aggregation_prediction'
            }
            
            # Custom JSON encoder für Decimal values
            def decimal_encoder(obj):
                if isinstance(obj, Decimal):
                    return str(obj)
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            return json.dumps(serialized_data, default=decimal_encoder, separators=(',', ':'))
            
        except Exception as e:
            self._logger.error(f"Serialization error: {e}")
            raise CacheException(f"Failed to serialize data: {e}")
    
    def _deserialize_value(self, value: str) -> Optional[Dict[str, Any]]:
        """Deserialize value from Redis storage"""
        try:
            parsed_data = json.loads(value)
            
            # Version check für backward compatibility
            if parsed_data.get('version') != self._serialization_version:
                self._logger.warning(f"Cache version mismatch: {parsed_data.get('version')} != {self._serialization_version}")
                return None
            
            return parsed_data.get('data')
            
        except Exception as e:
            self._logger.error(f"Deserialization error: {e}")
            return None
    
    def _track_response_time(self, duration_ms: float):
        """Track response time für performance monitoring"""
        self._response_times.append(duration_ms)
        if len(self._response_times) > self._max_response_times_tracked:
            self._response_times.pop(0)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get Value from Cache
        
        PERFORMANCE TARGET: <10ms response time
        """
        start_time = time.time()
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                value = await client.get(full_key)
                
                self._total_requests += 1
                
                if value:
                    self._hit_count += 1
                    deserialized = self._deserialize_value(value)
                    
                    response_time = (time.time() - start_time) * 1000
                    self._track_response_time(response_time)
                    
                    if response_time > 10:  # Log slow cache hits
                        self._logger.warning(f"Slow cache hit: {response_time:.2f}ms for key {key}")
                    
                    return deserialized
                else:
                    self._miss_count += 1
                    return None
                    
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, 
                 key: str, 
                 value: Dict[str, Any], 
                 ttl_seconds: int = 300) -> bool:
        """
        Set Value in Cache mit TTL
        
        PERFORMANCE TARGET: <20ms set time
        """
        start_time = time.time()
        full_key = self._build_key(key)
        
        try:
            serialized_value = self._serialize_value(value)
            
            async with redis.Redis(connection_pool=self._pool) as client:
                await client.setex(full_key, ttl_seconds, serialized_value)
                
                response_time = (time.time() - start_time) * 1000
                self._track_response_time(response_time)
                
                if response_time > 20:  # Log slow cache sets
                    self._logger.warning(f"Slow cache set: {response_time:.2f}ms for key {key}")
                
                self._logger.debug(f"Cached key {key} with TTL {ttl_seconds}s")
                return True
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete Value from Cache"""
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                deleted = await client.delete(full_key)
                return deleted > 0
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if Key Exists in Cache"""
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                exists = await client.exists(full_key)
                return exists > 0
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache exists check error for key {key}: {e}")
            return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get Remaining TTL für Key"""
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                ttl = await client.ttl(full_key)
                return ttl if ttl > 0 else None
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache TTL check error for key {key}: {e}")
            return None
    
    async def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """Extend TTL für Existing Key"""
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                current_ttl = await client.ttl(full_key)
                if current_ttl > 0:
                    new_ttl = current_ttl + additional_seconds
                    success = await client.expire(full_key, new_ttl)
                    return success
                return False
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache TTL extension error for key {key}: {e}")
            return False
    
    async def get_multiple(self, keys: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get Multiple Values from Cache (Batch Operation)
        
        PERFORMANCE TARGET: <50ms für batch of 10 keys
        """
        start_time = time.time()
        full_keys = [self._build_key(key) for key in keys]
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                # Use pipeline für batch operation
                pipe = client.pipeline()
                for full_key in full_keys:
                    pipe.get(full_key)
                
                values = await pipe.execute()
                
                # Process results
                result = {}
                for i, key in enumerate(keys):
                    if i < len(values) and values[i]:
                        self._hit_count += 1
                        result[key] = self._deserialize_value(values[i])
                    else:
                        self._miss_count += 1
                        result[key] = None
                
                self._total_requests += len(keys)
                response_time = (time.time() - start_time) * 1000
                self._track_response_time(response_time)
                
                return result
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache batch get error: {e}")
            return {key: None for key in keys}
    
    async def set_multiple(self, 
                          items: Dict[str, Dict[str, Any]], 
                          ttl_seconds: int = 300) -> Dict[str, bool]:
        """
        Set Multiple Values in Cache (Batch Operation)
        
        PERFORMANCE TARGET: <100ms für batch of 10 items
        """
        start_time = time.time()
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                # Use pipeline für batch operation
                pipe = client.pipeline()
                
                serialized_items = {}
                for key, value in items.items():
                    try:
                        serialized_value = self._serialize_value(value)
                        full_key = self._build_key(key)
                        pipe.setex(full_key, ttl_seconds, serialized_value)
                        serialized_items[key] = True
                    except Exception as e:
                        self._logger.error(f"Failed to serialize item {key}: {e}")
                        serialized_items[key] = False
                
                # Execute batch
                results = await pipe.execute()
                
                # Build result dictionary
                result = {}
                for i, key in enumerate(serialized_items.keys()):
                    if i < len(results):
                        result[key] = results[i] is not None
                    else:
                        result[key] = False
                
                response_time = (time.time() - start_time) * 1000
                self._track_response_time(response_time)
                
                return result
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache batch set error: {e}")
            return {key: False for key in items.keys()}
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete All Keys Matching Pattern"""
        try:
            full_pattern = self._build_key(pattern)
            
            async with redis.Redis(connection_pool=self._pool) as client:
                # Get matching keys
                keys = []
                async for key in client.scan_iter(match=full_pattern):
                    keys.append(key)
                
                if keys:
                    deleted = await client.delete(*keys)
                    self._logger.info(f"Deleted {deleted} keys matching pattern {pattern}")
                    return deleted
                return 0
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Cache pattern delete error for pattern {pattern}: {e}")
            return 0
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get Cache Performance Statistics"""
        total_requests = max(1, self._total_requests)  # Avoid division by zero
        hit_ratio = self._hit_count / total_requests
        
        avg_response_time = (sum(self._response_times) / len(self._response_times) 
                           if self._response_times else 0.0)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                info = await client.info('memory')
                used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
                
                # Get key count for our prefix
                key_count = 0
                pattern = self._build_key("*")
                async for _ in client.scan_iter(match=pattern):
                    key_count += 1
                
                return {
                    'hit_ratio': hit_ratio,
                    'total_requests': self._total_requests,
                    'hit_count': self._hit_count,
                    'miss_count': self._miss_count,
                    'error_count': self._error_count,
                    'total_keys': key_count,
                    'memory_usage_mb': used_memory_mb,
                    'average_response_time_ms': avg_response_time,
                    'error_rate': self._error_count / total_requests,
                    'performance_target_met': avg_response_time <= 10.0
                }
                
        except Exception as e:
            self._logger.error(f"Failed to get cache statistics: {e}")
            return {
                'hit_ratio': hit_ratio,
                'total_requests': self._total_requests,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'error_count': self._error_count,
                'average_response_time_ms': avg_response_time
            }
    
    async def warm_cache(self, 
                        key_value_pairs: Dict[str, Dict[str, Any]], 
                        ttl_seconds: int = 600) -> Dict[str, bool]:
        """Warm Cache mit Predicted Hot Data"""
        try:
            # Use batch set für performance
            result = await self.set_multiple(key_value_pairs, ttl_seconds)
            
            successful_warms = sum(1 for success in result.values() if success)
            self._logger.info(f"Successfully warmed {successful_warms}/{len(key_value_pairs)} cache entries")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Cache warming failed: {e}")
            return {key: False for key in key_value_pairs.keys()}
    
    async def get_key_size(self, key: str) -> Optional[int]:
        """Get Memory Size of Cached Value"""
        full_key = self._build_key(key)
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                size = await client.memory_usage(full_key)
                return size
                
        except Exception as e:
            self._logger.error(f"Failed to get key size for {key}: {e}")
            return None
    
    async def cleanup_expired_keys(self) -> int:
        """Manually Trigger Cleanup of Expired Keys"""
        try:
            # Redis automatically handles expired keys, but we can scan für manual cleanup
            deleted_count = 0
            
            async with redis.Redis(connection_pool=self._pool) as client:
                pattern = self._build_key("*")
                async for key in client.scan_iter(match=pattern):
                    ttl = await client.ttl(key)
                    if ttl == -2:  # Key expired but not yet cleaned up
                        deleted = await client.delete(key)
                        deleted_count += deleted
                
                return deleted_count
                
        except Exception as e:
            self._logger.error(f"Manual cleanup failed: {e}")
            return 0
    
    async def get_keys_by_pattern(self, pattern: str, limit: int = 100) -> List[str]:
        """Get Keys Matching Pattern"""
        try:
            full_pattern = self._build_key(pattern)
            keys = []
            
            async with redis.Redis(connection_pool=self._pool) as client:
                async for key in client.scan_iter(match=full_pattern):
                    # Strip prefix für return
                    clean_key = key.decode() if isinstance(key, bytes) else key
                    if clean_key.startswith(f"{self._key_prefix}:"):
                        clean_key = clean_key[len(f"{self._key_prefix}:"):]
                    keys.append(clean_key)
                    
                    if len(keys) >= limit:
                        break
                
                return keys
                
        except Exception as e:
            self._logger.error(f"Failed to get keys by pattern {pattern}: {e}")
            return []
    
    async def set_with_custom_expiry(self, 
                                   key: str, 
                                   value: Dict[str, Any], 
                                   expires_at: float) -> bool:
        """Set Value mit Custom Expiration Timestamp"""
        current_time = time.time()
        ttl_seconds = max(0, int(expires_at - current_time))
        
        if ttl_seconds <= 0:
            self._logger.warning(f"Custom expiry time {expires_at} is in the past")
            return False
        
        return await self.set(key, value, ttl_seconds)
    
    async def increment_counter(self, key: str, increment: int = 1, ttl_seconds: int = 3600) -> int:
        """Increment Counter Value in Cache"""
        full_key = self._build_key(f"counter:{key}")
        
        try:
            async with redis.Redis(connection_pool=self._pool) as client:
                # Use pipeline für atomic increment and expire
                pipe = client.pipeline()
                pipe.incr(full_key, increment)
                pipe.expire(full_key, ttl_seconds)
                
                results = await pipe.execute()
                return results[0] if results else 0
                
        except Exception as e:
            self._error_count += 1
            self._logger.error(f"Counter increment error for key {key}: {e}")
            return 0
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get Cache Health Status"""
        try:
            start_time = time.time()
            
            async with redis.Redis(connection_pool=self._pool) as client:
                # Test connectivity mit simple operation
                await client.ping()
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Get Redis info
                info = await client.info()
                memory_info = await client.info('memory')
                
                # Calculate memory pressure
                used_memory = memory_info.get('used_memory', 0)
                max_memory = memory_info.get('maxmemory', 0)
                memory_pressure = (used_memory / max_memory) if max_memory > 0 else 0.0
                
                # Determine health status
                status = 'healthy'
                if latency_ms > 50:
                    status = 'degraded'
                if latency_ms > 200 or memory_pressure > 0.9:
                    status = 'unhealthy'
                
                return {
                    'status': status,
                    'connectivity': True,
                    'latency_ms': latency_ms,
                    'memory_pressure': memory_pressure,
                    'error_rate': self._error_count / max(1, self._total_requests),
                    'uptime_seconds': info.get('uptime_in_seconds', 0),
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_mb': used_memory / (1024 * 1024)
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connectivity': False,
                'latency_ms': float('inf'),
                'memory_pressure': 1.0,
                'error_rate': 1.0,
                'uptime_seconds': 0,
                'error': str(e)
            }