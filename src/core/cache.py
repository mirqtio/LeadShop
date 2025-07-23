"""
LeadFactory Redis Cache Configuration
Implements caching layer for performance optimization
"""

import redis.asyncio as redis
import json
from typing import Any, Optional, Union
import logging
from datetime import timedelta

from src.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get Redis connection pool (singleton)"""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("Redis connection pool created")
    
    return _redis_pool


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    global _redis_client
    
    if _redis_client is None:
        pool = await get_redis_pool()
        _redis_client = redis.Redis(connection_pool=pool, decode_responses=True)
        logger.info("Redis client created")
    
    return _redis_client


class CacheManager:
    """Cache manager for LeadFactory operations"""
    
    def __init__(self):
        self.redis = None
        self.default_ttl = settings.CACHE_TTL
    
    async def _get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await self._get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with TTL"""
        try:
            client = await self._get_client()
            ttl_seconds = ttl or self.default_ttl
            
            if isinstance(ttl_seconds, timedelta):
                ttl_seconds = int(ttl_seconds.total_seconds())
            
            serialized_value = json.dumps(value, default=str)
            await client.setex(key, ttl_seconds, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = await self._get_client()
            deleted = await client.delete(key)
            return bool(deleted)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await self._get_client()
            exists = await client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment numeric value in cache"""
        try:
            client = await self._get_client()
            result = await client.incrby(key, amount)
            return result
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def set_with_lock(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value with distributed lock"""
        lock_key = f"lock:{key}"
        try:
            client = await self._get_client()
            
            # Try to acquire lock
            lock_acquired = await client.set(lock_key, "1", nx=True, ex=30)
            if not lock_acquired:
                return False
            
            # Set the actual value
            success = await self.set(key, value, ttl)
            
            # Release lock
            await client.delete(lock_key)
            
            return success
        except Exception as e:
            logger.error(f"Cache set_with_lock error for key {key}: {e}")
            return False
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            client = await self._get_client()
            keys = await client.keys(pattern)
            if keys:
                deleted = await client.delete(*keys)
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache flush_pattern error for pattern {pattern}: {e}")
            return 0


# Global cache manager instance
cache = CacheManager()


# Cache key generators for different data types
class CacheKeys:
    """Cache key generators for consistent naming"""
    
    @staticmethod
    def lead_data(lead_id: str) -> str:
        return f"lead:{lead_id}"
    
    @staticmethod
    def assessment_result(assessment_id: str) -> str:
        return f"assessment:{assessment_id}"
    
    @staticmethod
    def company_profile(domain: str) -> str:
        return f"company:{domain}"
    
    @staticmethod
    def website_metrics(url: str) -> str:
        return f"metrics:{url}"
    
    @staticmethod
    def pagespeed_data(url: str) -> str:
        return f"pagespeed:{url}"
    
    @staticmethod
    def cost_tracking(date: str) -> str:
        return f"costs:{date}"
    
    @staticmethod
    def rate_limit(service: str, identifier: str) -> str:
        return f"ratelimit:{service}:{identifier}"