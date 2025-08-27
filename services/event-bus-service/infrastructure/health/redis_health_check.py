import logging

logger = logging.getLogger(__name__)

"""
Redis Health Check Implementation
Clean Architecture - Infrastructure Layer
"""

import redis.asyncio as aioredis
from typing import Dict, Any, Optional
from datetime import datetime


class RedisHealthCheck:
    """Health Check für Redis Event Bus"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis_client: Optional[aioredis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self._redis_client = await aioredis.from_url(self.redis_url)
        except Exception as e:
            logger.info(f"Redis connection failed: {e}")
            
    async def check_health(self) -> Dict[str, Any]:
        """Check Redis health status"""
        try:
            if not self._redis_client:
                await self.initialize()
                
            # Ping Redis
            ping_response = await self._redis_client.ping()
            
            # Get memory info
            info = await self._redis_client.info("memory")
            memory_mb = info.get("used_memory", 0) / 1024 / 1024 if info else 0
            
            # Get key count
            key_count = await self._redis_client.dbsize()
            
            # Test pub/sub
            test_channel = "health_check_test"
            pubsub = self._redis_client.pubsub()
            await pubsub.subscribe(test_channel)
            await self._redis_client.publish(test_channel, "test")
            await pubsub.unsubscribe(test_channel)
            await pubsub.close()
            
            return {
                "connected": True,
                "responsive": ping_response,
                "memory_usage_mb": round(memory_mb, 2),
                "key_count": key_count,
                "pub_sub_functional": True,
                "last_check": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "connected": False,
                "responsive": False,
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
            
    async def cleanup(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()