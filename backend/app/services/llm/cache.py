"""LLM response caching service."""
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMCache:
    """Cache LLM responses based on (topic_id, gap_type, reference_hash)."""

    def __init__(self):
        """Initialize LLM cache."""
        self._redis: Optional[Redis] = None
        self._enabled = False
        self._cache_ttl = 86400  # 24 hours default

    async def initialize(self):
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, LLM cache disabled")
            return

        try:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            self._enabled = True
            logger.info("LLM cache initialized with Redis")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}, cache disabled")
            self._enabled = False

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._enabled = False

    def _make_key(
        self,
        topic_id: str,
        gap_type: str,
        reference_hash: str,
    ) -> str:
        """
        Generate cache key.

        Args:
            topic_id: Topic identifier
            gap_type: Gap type enum value
            reference_hash: Hash of reference content

        Returns:
            Cache key string
        """
        key_parts = [
            "llm_cache",
            topic_id,
            gap_type,
            reference_hash[:16],  # Use first 16 chars of hash
        ]
        return ":".join(key_parts)

    async def get(
        self,
        topic_id: str,
        gap_type: str,
        reference_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached LLM response.

        Args:
            topic_id: Topic identifier
            gap_type: Gap type enum value
            reference_hash: Hash of reference content

        Returns:
            Cached response dict or None
        """
        if not self._enabled:
            return None

        try:
            key = self._make_key(topic_id, gap_type, reference_hash)
            cached = await self._redis.get(key)

            if cached:
                logger.debug(f"LLM cache hit: {key}")
                return json.loads(cached)

            logger.debug(f"LLM cache miss: {key}")
            return None

        except Exception as e:
            logger.warning(f"Failed to get from LLM cache: {e}")
            return None

    async def set(
        self,
        topic_id: str,
        gap_type: str,
        reference_hash: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ):
        """
        Cache LLM response.

        Args:
            topic_id: Topic identifier
            gap_type: Gap type enum value
            reference_hash: Hash of reference content
            value: Response to cache
            ttl: Time-to-live in seconds (default from settings)
        """
        if not self._enabled:
            return

        try:
            key = self._make_key(topic_id, gap_type, reference_hash)
            ttl = ttl or self._cache_ttl

            await self._redis.setex(
                key,
                ttl,
                json.dumps(value, ensure_ascii=False),
            )
            logger.debug(f"LLM cached: {key}, ttl={ttl}")

        except Exception as e:
            logger.warning(f"Failed to set LLM cache: {e}")

    async def invalidate(self, topic_id: str):
        """
        Invalidate all cache entries for a topic.

        Args:
            topic_id: Topic identifier
        """
        if not self._enabled:
            return

        try:
            pattern = f"llm_cache:{topic_id}:*"
            keys = []

            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for topic: {topic_id}")

        except Exception as e:
            logger.warning(f"Failed to invalidate LLM cache: {e}")

    async def clear_all(self):
        """Clear all LLM cache entries."""
        if not self._enabled:
            return

        try:
            pattern = "llm_cache:*"
            keys = []

            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self._redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} LLM cache entries")

        except Exception as e:
            logger.warning(f"Failed to clear LLM cache: {e}")

    @property
    def enabled(self) -> bool:
        """Check if cache is enabled."""
        return self._enabled


# Global cache instance
_llm_cache: Optional[LLMCache] = None


async def get_llm_cache() -> LLMCache:
    """
    Get or create global LLM cache instance.

    Returns:
        LLMCache instance
    """
    global _llm_cache

    if _llm_cache is None:
        _llm_cache = LLMCache()
        await _llm_cache.initialize()

    return _llm_cache
