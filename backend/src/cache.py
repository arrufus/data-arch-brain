"""Redis caching module for Data Architecture Brain.

Provides caching decorators and utilities for improving query performance.
Supports both Redis (for distributed deployments) and in-memory fallback (for development).
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional, Union
import asyncio

from src.config import get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Global cache client
_cache_client: Optional["CacheClient"] = None


class CacheClient:
    """Abstract cache client supporting Redis and in-memory fallback."""

    def __init__(self):
        self._redis: Optional[Any] = None
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis if configured, otherwise use memory cache."""
        if settings.cache_redis_url:
            try:
                import redis.asyncio as redis
                
                self._redis = redis.from_url(
                    settings.cache_redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                # Test connection
                await self._redis.ping()
                self._connected = True
                logger.info("Redis cache connected", url=settings.cache_redis_url)
                return True
            except ImportError:
                logger.warning("redis package not installed, using memory cache")
            except Exception as e:
                logger.warning("Redis connection failed, using memory cache", error=str(e))
        
        # Fall back to memory cache
        self._connected = True
        logger.info("Using in-memory cache (development mode)")
        return True

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._memory_cache.clear()
        self._connected = False
        logger.info("Cache disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if cache is connected."""
        return self._connected

    @property
    def is_redis(self) -> bool:
        """Check if using Redis (vs memory cache)."""
        return self._redis is not None

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._connected:
            return None
            
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception as e:
                logger.warning("Cache get failed", key=key, error=str(e))
                return None
        else:
            # Memory cache with TTL check
            import time
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if expiry == 0 or time.time() < expiry:
                    return value
                else:
                    del self._memory_cache[key]
            return None

    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        if not self._connected:
            return False
            
        if self._redis:
            try:
                if ttl:
                    await self._redis.setex(key, ttl, value)
                else:
                    await self._redis.set(key, value)
                return True
            except Exception as e:
                logger.warning("Cache set failed", key=key, error=str(e))
                return False
        else:
            # Memory cache
            import time
            expiry = time.time() + ttl if ttl else 0
            self._memory_cache[key] = (value, expiry)
            return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected:
            return False
            
        if self._redis:
            try:
                await self._redis.delete(key)
                return True
            except Exception as e:
                logger.warning("Cache delete failed", key=key, error=str(e))
                return False
        else:
            self._memory_cache.pop(key, None)
            return True

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern. Returns count deleted."""
        if not self._connected:
            return 0
            
        if self._redis:
            try:
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._redis.delete(*keys)
                return len(keys)
            except Exception as e:
                logger.warning("Cache delete_pattern failed", pattern=pattern, error=str(e))
                return 0
        else:
            # Memory cache pattern matching (simple glob-style)
            import fnmatch
            keys_to_delete = [
                k for k in self._memory_cache.keys() 
                if fnmatch.fnmatch(k, pattern)
            ]
            for k in keys_to_delete:
                del self._memory_cache[k]
            return len(keys_to_delete)

    async def clear_all(self) -> bool:
        """Clear all cached data. Use with caution!"""
        if not self._connected:
            return False
            
        if self._redis:
            try:
                await self._redis.flushdb()
                return True
            except Exception as e:
                logger.warning("Cache clear failed", error=str(e))
                return False
        else:
            self._memory_cache.clear()
            return True

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if self._redis:
            try:
                info = await self._redis.info("stats")
                return {
                    "backend": "redis",
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "connected": True,
                }
            except Exception:
                return {"backend": "redis", "connected": False}
        else:
            return {
                "backend": "memory",
                "keys": len(self._memory_cache),
                "connected": True,
            }


def get_cache_client() -> CacheClient:
    """Get the global cache client instance."""
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client


async def init_cache() -> None:
    """Initialize the cache connection."""
    client = get_cache_client()
    await client.connect()


async def close_cache() -> None:
    """Close the cache connection."""
    global _cache_client
    if _cache_client:
        await _cache_client.disconnect()
        _cache_client = None


def make_cache_key(*args: Any, prefix: str = "dab") -> str:
    """Create a deterministic cache key from arguments."""
    # Serialize arguments to JSON and hash
    key_data = json.dumps(args, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
    return f"{prefix}:{key_hash}"


def cached(
    ttl: int = 300,
    prefix: str = "dab",
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator to cache async function results.
    
    Args:
        ttl: Time-to-live in seconds (default: 5 minutes)
        prefix: Cache key prefix
        key_builder: Optional custom function to build cache key
    
    Usage:
        @cached(ttl=600, prefix="capsules")
        async def get_capsules(layer: str) -> list[Capsule]:
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = get_cache_client()
            
            if not client.is_connected or not settings.cache_enabled:
                # Cache disabled or not connected, execute directly
                return await func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder: function name + args hash
                cache_key = make_cache_key(
                    func.__module__,
                    func.__name__,
                    args[1:] if args else (),  # Skip 'self' for methods
                    kwargs,
                    prefix=prefix,
                )
            
            # Try to get from cache
            try:
                cached_value = await client.get(cache_key)
                if cached_value is not None:
                    logger.debug("Cache hit", key=cache_key)
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning("Cache read error", key=cache_key, error=str(e))
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            try:
                # Serialize result (handles Pydantic models and dataclasses)
                if hasattr(result, "model_dump"):
                    serialized = json.dumps(result.model_dump())
                elif hasattr(result, "__dict__"):
                    serialized = json.dumps(result.__dict__, default=str)
                else:
                    serialized = json.dumps(result, default=str)
                
                await client.set(cache_key, serialized, ttl=ttl)
                logger.debug("Cache set", key=cache_key, ttl=ttl)
            except Exception as e:
                logger.warning("Cache write error", key=cache_key, error=str(e))
            
            return result
        
        return wrapper
    return decorator


class CacheInvalidator:
    """Helper class for invalidating cache entries."""
    
    def __init__(self, client: Optional[CacheClient] = None):
        self.client = client or get_cache_client()
    
    async def invalidate_capsules(self) -> int:
        """Invalidate all capsule-related cache entries."""
        return await self.client.delete_pattern("dab:capsule*")
    
    async def invalidate_conformance(self) -> int:
        """Invalidate all conformance-related cache entries."""
        return await self.client.delete_pattern("dab:conformance*")
    
    async def invalidate_compliance(self) -> int:
        """Invalidate all compliance/PII-related cache entries."""
        return await self.client.delete_pattern("dab:compliance*")
    
    async def invalidate_lineage(self) -> int:
        """Invalidate all lineage-related cache entries."""
        return await self.client.delete_pattern("dab:lineage*")
    
    async def invalidate_all(self) -> bool:
        """Invalidate all cache entries."""
        return await self.client.clear_all()
    
    async def on_ingestion_complete(self) -> dict[str, int]:
        """Invalidate caches that should be cleared after ingestion."""
        return {
            "capsules": await self.invalidate_capsules(),
            "conformance": await self.invalidate_conformance(),
            "compliance": await self.invalidate_compliance(),
            "lineage": await self.invalidate_lineage(),
        }
