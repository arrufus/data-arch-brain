"""Tests for the caching module."""

import pytest
from unittest.mock import AsyncMock, patch

from src.cache import (
    CacheClient,
    get_cache_client,
    make_cache_key,
    CacheInvalidator,
)


class TestCacheKey:
    """Tests for cache key generation."""

    def test_make_cache_key_simple(self):
        """Test simple cache key generation."""
        key = make_cache_key("test", "value")
        assert key.startswith("dab:")
        assert len(key) > 4  # prefix + hash

    def test_make_cache_key_consistent(self):
        """Test that same inputs produce same key."""
        key1 = make_cache_key("test", "value", prefix="test")
        key2 = make_cache_key("test", "value", prefix="test")
        assert key1 == key2

    def test_make_cache_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = make_cache_key("test", "value1")
        key2 = make_cache_key("test", "value2")
        assert key1 != key2

    def test_make_cache_key_custom_prefix(self):
        """Test custom prefix in cache key."""
        key = make_cache_key("test", prefix="custom")
        assert key.startswith("custom:")


class TestCacheClient:
    """Tests for the CacheClient class."""

    @pytest.mark.asyncio
    async def test_memory_cache_connect(self):
        """Test connecting with memory cache (no Redis)."""
        client = CacheClient()
        with patch.object(client, '_redis', None):
            result = await client.connect()
            assert result is True
            assert client.is_connected is True
            assert client.is_redis is False

    @pytest.mark.asyncio
    async def test_memory_cache_set_get(self):
        """Test set and get with memory cache."""
        client = CacheClient()
        await client.connect()
        
        await client.set("test_key", "test_value")
        result = await client.get("test_key")
        
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_memory_cache_set_with_ttl(self):
        """Test set with TTL."""
        client = CacheClient()
        await client.connect()
        
        await client.set("test_key", "test_value", ttl=60)
        result = await client.get("test_key")
        
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_memory_cache_delete(self):
        """Test delete from memory cache."""
        client = CacheClient()
        await client.connect()
        
        await client.set("test_key", "test_value")
        await client.delete("test_key")
        result = await client.get("test_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_memory_cache_delete_pattern(self):
        """Test delete pattern from memory cache."""
        client = CacheClient()
        await client.connect()
        
        await client.set("prefix:key1", "value1")
        await client.set("prefix:key2", "value2")
        await client.set("other:key3", "value3")
        
        count = await client.delete_pattern("prefix:*")
        
        assert count == 2
        assert await client.get("prefix:key1") is None
        assert await client.get("prefix:key2") is None
        assert await client.get("other:key3") == "value3"

    @pytest.mark.asyncio
    async def test_memory_cache_clear_all(self):
        """Test clearing all cache entries."""
        client = CacheClient()
        await client.connect()
        
        await client.set("key1", "value1")
        await client.set("key2", "value2")
        
        result = await client.clear_all()
        
        assert result is True
        assert await client.get("key1") is None
        assert await client.get("key2") is None

    @pytest.mark.asyncio
    async def test_memory_cache_stats(self):
        """Test getting cache stats."""
        client = CacheClient()
        await client.connect()
        
        await client.set("key1", "value1")
        await client.set("key2", "value2")
        
        stats = await client.get_stats()
        
        assert stats["backend"] == "memory"
        assert stats["keys"] == 2
        assert stats["connected"] is True

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting cache."""
        client = CacheClient()
        await client.connect()
        await client.disconnect()
        
        assert client.is_connected is False


class TestCacheInvalidator:
    """Tests for the CacheInvalidator class."""

    @pytest.mark.asyncio
    async def test_invalidate_capsules(self):
        """Test invalidating capsule cache."""
        client = CacheClient()
        await client.connect()
        
        await client.set("dab:capsule:1", "value1")
        await client.set("dab:capsule:2", "value2")
        await client.set("dab:other:1", "value3")
        
        invalidator = CacheInvalidator(client)
        count = await invalidator.invalidate_capsules()
        
        assert count == 2

    @pytest.mark.asyncio
    async def test_on_ingestion_complete(self):
        """Test full cache invalidation after ingestion."""
        client = CacheClient()
        await client.connect()
        
        await client.set("dab:capsule:1", "value1")
        await client.set("dab:conformance:1", "value2")
        await client.set("dab:compliance:1", "value3")
        await client.set("dab:lineage:1", "value4")
        
        invalidator = CacheInvalidator(client)
        result = await invalidator.on_ingestion_complete()
        
        assert "capsules" in result
        assert "conformance" in result
        assert "compliance" in result
        assert "lineage" in result
