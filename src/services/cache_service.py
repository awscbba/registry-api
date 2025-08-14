"""
Cache Service - Centralized caching management for performance optimization.
Implements multi-level caching with TTL support and intelligent invalidation.
"""

import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from functools import wraps

from ..core.base_service import BaseService
from ..utils.logging_config import get_handler_logger


class CacheService(BaseService):
    """Centralized caching service with TTL support and performance optimization."""

    def __init__(self):
        super().__init__("cache_service")
        self.logger = get_handler_logger("cache_service")

        # In-memory cache storage (in production, this would be Redis)
        self.cache_store: Dict[str, Dict[str, Any]] = {}
        self.ttl_store: Dict[str, datetime] = {}

        # Cache statistics
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "evictions": 0}

        # Cache configuration
        self.default_ttl = 3600  # 1 hour
        self.max_cache_size = 10000  # Maximum number of cache entries

        self.logger.info("Cache service initialized with in-memory storage")

    async def initialize(self):
        """Initialize the cache service."""
        try:
            # Start cache cleanup task
            asyncio.create_task(self._cleanup_expired_entries())
            self.logger.info("Cache service initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize cache service: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the cache service."""
        try:
            cache_size = len(self.cache_store)
            hit_rate = (
                self.stats["hits"] / (self.stats["hits"] + self.stats["misses"])
                if (self.stats["hits"] + self.stats["misses"]) > 0
                else 0
            )

            return {
                "service": "cache_service",
                "status": "healthy",
                "cache_size": cache_size,
                "hit_rate": round(hit_rate * 100, 2),
                "statistics": self.stats.copy(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Cache service health check failed: {str(e)}")
            return {
                "service": "cache_service",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from prefix and parameters."""
        # Create a consistent string representation
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (dict, list)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments
        if kwargs:
            sorted_kwargs = json.dumps(kwargs, sort_keys=True)
            key_parts.append(sorted_kwargs)

        # Create hash of the combined key
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Check if key exists and is not expired
            if key not in self.cache_store:
                self.stats["misses"] += 1
                return None

            # Check TTL
            if key in self.ttl_store:
                if datetime.utcnow() > self.ttl_store[key]:
                    # Expired, remove from cache
                    await self.delete(key)
                    self.stats["misses"] += 1
                    self.stats["evictions"] += 1
                    return None

            self.stats["hits"] += 1
            cached_data = self.cache_store[key]

            self.logger.debug(f"Cache hit for key: {key[:20]}...")
            return cached_data["value"]

        except Exception as e:
            self.logger.error(f"Error getting cache key {key}: {str(e)}")
            self.stats["misses"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Check cache size limit
            if len(self.cache_store) >= self.max_cache_size:
                await self._evict_oldest_entries(int(self.max_cache_size * 0.1))

            # Store the value with metadata
            self.cache_store[key] = {
                "value": value,
                "created_at": datetime.utcnow(),
                "access_count": 0,
            }

            # Set TTL if specified
            if ttl > 0:
                self.ttl_store[key] = datetime.utcnow() + timedelta(seconds=ttl)

            self.stats["sets"] += 1
            self.logger.debug(f"Cache set for key: {key[:20]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            self.logger.error(f"Error setting cache key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if key in self.cache_store:
                del self.cache_store[key]
                self.stats["deletes"] += 1

            if key in self.ttl_store:
                del self.ttl_store[key]

            self.logger.debug(f"Cache deleted for key: {key[:20]}...")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False

    async def clear_prefix(self, prefix: str) -> int:
        """Clear all cache entries with a specific prefix."""
        try:
            keys_to_delete = [
                key for key in self.cache_store.keys() if key.startswith(prefix)
            ]

            for key in keys_to_delete:
                await self.delete(key)

            self.logger.info(
                f"Cleared {len(keys_to_delete)} cache entries with prefix: {prefix}"
            )
            return len(keys_to_delete)

        except Exception as e:
            self.logger.error(f"Error clearing cache prefix {prefix}: {str(e)}")
            return 0

    async def clear_all(self) -> bool:
        """Clear all cache entries."""
        try:
            cache_size = len(self.cache_store)
            self.cache_store.clear()
            self.ttl_store.clear()

            self.logger.info(f"Cleared all cache entries ({cache_size} items)")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing all cache: {str(e)}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

            # Calculate cache size and memory usage estimate
            cache_size = len(self.cache_store)
            memory_estimate = sum(
                len(json.dumps(entry["value"])) for entry in self.cache_store.values()
            )

            return {
                "cache_size": cache_size,
                "max_cache_size": self.max_cache_size,
                "hit_rate": round(hit_rate * 100, 2),
                "total_requests": total_requests,
                "memory_estimate_bytes": memory_estimate,
                "statistics": self.stats.copy(),
                "ttl_entries": len(self.ttl_store),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}

    def cache_result(
        self, ttl: int = None, key_prefix: str = "", include_user_context: bool = False
    ):
        """Decorator for caching function results."""

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key_parts = [key_prefix or func.__name__]

                # Include user context if requested
                if include_user_context and "current_user" in kwargs:
                    user_id = kwargs.get("current_user", {}).get("id", "anonymous")
                    cache_key_parts.append(f"user:{user_id}")

                cache_key = self.generate_cache_key(*cache_key_parts, *args, **kwargs)

                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for function: {func.__name__}")
                    return cached_result

                # Execute function and cache result
                result = await func(*args, **kwargs)

                # Only cache successful results
                if isinstance(result, dict) and result.get("success", True):
                    await self.set(cache_key, result, ttl or self.default_ttl)
                    self.logger.debug(f"Cached result for function: {func.__name__}")

                return result

            return wrapper

        return decorator

    async def _cleanup_expired_entries(self):
        """Background task to clean up expired cache entries."""
        while True:
            try:
                current_time = datetime.utcnow()
                expired_keys = [
                    key
                    for key, expiry_time in self.ttl_store.items()
                    if current_time > expiry_time
                ]

                for key in expired_keys:
                    await self.delete(key)
                    self.stats["evictions"] += 1

                if expired_keys:
                    self.logger.debug(
                        f"Cleaned up {len(expired_keys)} expired cache entries"
                    )

                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)

            except Exception as e:
                self.logger.error(f"Error in cache cleanup task: {str(e)}")
                await asyncio.sleep(60)  # Shorter sleep on error

    async def _evict_oldest_entries(self, count: int):
        """Evict oldest cache entries to make room for new ones."""
        try:
            # Sort by creation time and evict oldest
            sorted_entries = sorted(
                self.cache_store.items(), key=lambda x: x[1]["created_at"]
            )

            for i in range(min(count, len(sorted_entries))):
                key = sorted_entries[i][0]
                await self.delete(key)
                self.stats["evictions"] += 1

            self.logger.debug(f"Evicted {count} oldest cache entries")

        except Exception as e:
            self.logger.error(f"Error evicting cache entries: {str(e)}")

    # Cache warming methods
    async def warm_cache(self, warming_functions: List[callable]):
        """Warm cache with frequently accessed data."""
        try:
            self.logger.info("Starting cache warming process")

            for func in warming_functions:
                try:
                    await func()
                    self.logger.debug(f"Cache warmed by function: {func.__name__}")
                except Exception as e:
                    self.logger.error(
                        f"Error warming cache with {func.__name__}: {str(e)}"
                    )

            self.logger.info("Cache warming process completed")

        except Exception as e:
            self.logger.error(f"Error in cache warming process: {str(e)}")

    async def get_cache_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get all cache keys matching a pattern."""
        try:
            matching_keys = [key for key in self.cache_store.keys() if pattern in key]
            return matching_keys
        except Exception as e:
            self.logger.error(f"Error getting cache keys by pattern: {str(e)}")
            return []
