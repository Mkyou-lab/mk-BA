# ================================================================
#  SMART CACHE MANAGER
# ================================================================

import time
import asyncio
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class SmartCache:
    """
    Thread-safe in-memory cache with TTL and size limits.
    """

    def __init__(self, max_size: int = 500, default_ttl: int = 30):
        self._cache: Dict[str, dict] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() > entry["expires"]:
            del self._cache[key]
            return None
        entry["hits"] = entry.get("hits", 0) + 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        if len(self._cache) >= self._max_size:
            self._evict()
        self._cache[key] = {
            "value": value,
            "expires": time.time() + (ttl or self._default_ttl),
            "created": time.time(),
            "hits": 0,
        }

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def _evict(self) -> None:
        now = time.time()
        # Remove expired
        expired = [k for k, v in self._cache.items() if now > v["expires"]]
        for k in expired:
            del self._cache[k]
        # Remove least used if still over limit
        if len(self._cache) >= self._max_size:
            lru = sorted(self._cache.items(), key=lambda x: x[1].get("hits", 0))
            for k, _ in lru[:len(self._cache) // 4]:
                del self._cache[k]

    def stats(self) -> Dict:
        now = time.time()
        active = sum(1 for v in self._cache.values() if now <= v["expires"])
        return {
            "total": len(self._cache),
            "active": active,
            "max_size": self._max_size,
        }

    async def cleanup_loop(self, interval: int = 60) -> None:
        while True:
            await asyncio.sleep(interval)
            self._evict()
            stats = self.stats()
            logger.debug(f"Cache stats: {stats}")


# Global cache instances
signal_cache = SmartCache(max_size=200, default_ttl=15)
indicator_cache = SmartCache(max_size=300, default_ttl=30)
user_cache = SmartCache(max_size=1000, default_ttl=300)