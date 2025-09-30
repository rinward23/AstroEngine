"""Layered cache wrapper with in-process + Redis storage and dogpile protection."""
from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from cachetools import TTLCache
from prometheus_client import Counter

from astroengine.utils import json as json_utils

try:  # pragma: no cover - optional compression
    import zstandard as zstd
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    zstd = None  # type: ignore

try:  # pragma: no cover - optional redis runtime
    from redis import Redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    Redis = None  # type: ignore
    RedisError = Exception  # type: ignore

_LOGGER = logging.getLogger(__name__)

_CACHE_HITS = Counter("cache_hits_total", "Cache hit counts", ["layer", "namespace"])
_CACHE_MISSES = Counter("cache_misses_total", "Cache miss counts", ["namespace"])


@dataclass
class CacheEntry:
    body: Any
    status_code: int
    headers: Dict[str, str]
    created_at: float


@dataclass
class CacheOutcome:
    entry: Optional[CacheEntry]
    key: str
    etag: str
    source: str
    waited: bool = False


class RelationshipResponseCache:
    """Layered caching facade for relationship endpoints."""

    def __init__(
        self,
        namespace: str,
        ttl_seconds: int,
        *,
        lru_maxsize: int = 512,
        redis_client: Optional[Redis] = None,
        compression: bool | None = None,
    ) -> None:
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds
        self._lru = TTLCache(maxsize=lru_maxsize, ttl=ttl_seconds)
        self._redis = redis_client
        self._compression = bool(compression if compression is not None else os.getenv("CACHE_ZSTD", "false").lower() in {"1", "true", "yes"})
        if self._compression and zstd is None:
            _LOGGER.warning("zstandard unavailable; disabling compression")
            self._compression = False
        self._compressor = zstd.ZstdCompressor(level=3) if self._compression and zstd else None
        self._decompressor = zstd.ZstdDecompressor() if self._compression and zstd else None
        self._compression_floor = int(os.getenv("CACHE_COMPRESSION_FLOOR", "512"))
        self._lock_timeout_ms = int(os.getenv("CACHE_LOCK_TIMEOUT_MS", "30000"))
        self._wait_attempts = int(os.getenv("CACHE_WAIT_ATTEMPTS", "30"))
        self._wait_interval = float(os.getenv("CACHE_WAIT_INTERVAL", "0.05"))

    def get(self, key: str) -> CacheOutcome:
        etag = key.split(":")[-1]
        entry = self._lru.get(key)
        if entry:
            _CACHE_HITS.labels(layer="process", namespace=self.namespace).inc()
            return CacheOutcome(entry=entry, key=key, etag=etag, source="lru")
        payload = self._get_from_redis(key)
        if payload:
            _CACHE_HITS.labels(layer="redis", namespace=self.namespace).inc()
            self._lru[key] = payload
            return CacheOutcome(entry=payload, key=key, etag=etag, source="redis")
        _CACHE_MISSES.labels(namespace=self.namespace).inc()
        return CacheOutcome(entry=None, key=key, etag=etag, source="miss")

    def set(self, key: str, entry: CacheEntry) -> None:
        self._lru[key] = entry
        if not self._redis:
            return
        try:
            packed = json_utils.dumps(
                {
                    "body": entry.body,
                    "status": entry.status_code,
                    "headers": entry.headers,
                    "created": entry.created_at,
                }
            )
            payload: bytes
            if self._compression and len(packed) >= self._compression_floor and self._compressor:
                payload = b"Z" + self._compressor.compress(packed)
            else:
                payload = b"J" + packed
            self._redis.set(key, payload, ex=self.ttl_seconds)
        except RedisError as exc:  # pragma: no cover - network failure
            _LOGGER.error("Failed to write response cache to Redis", exc_info=exc)

    def with_singleflight(
        self,
        key: str,
        compute: Callable[[], CacheEntry],
    ) -> CacheOutcome:
        if not self._redis:
            entry = compute()
            self.set(key, entry)
            return CacheOutcome(entry=entry, key=key, etag=key.split(":")[-1], source="compute")
        token = uuid.uuid4().hex
        lock_key = f"lock:{key}"
        acquired = False
        try:
            try:
                acquired = bool(self._redis.set(lock_key, token, nx=True, px=self._lock_timeout_ms))
            except RedisError as exc:  # pragma: no cover - redis down
                _LOGGER.warning("Redis unavailable for singleflight; computing directly", exc_info=exc)
                entry = compute()
                self.set(key, entry)
                return CacheOutcome(entry=entry, key=key, etag=key.split(":")[-1], source="compute")
            if acquired:
                entry = compute()
                self.set(key, entry)
                return CacheOutcome(entry=entry, key=key, etag=key.split(":")[-1], source="compute")
            # follower path
            for _ in range(self._wait_attempts):
                time.sleep(self._wait_interval)
                payload = self._get_from_redis(key)
                if payload:
                    self._lru[key] = payload
                    return CacheOutcome(entry=payload, key=key, etag=key.split(":")[-1], source="redis", waited=True)
            entry = compute()
            self.set(key, entry)
            return CacheOutcome(entry=entry, key=key, etag=key.split(":")[-1], source="fallback", waited=True)
        finally:
            if acquired:
                try:
                    current = self._redis.get(lock_key)
                    if current and current.decode() == token:
                        self._redis.delete(lock_key)
                except RedisError:  # pragma: no cover - cleanup best effort
                    _LOGGER.debug("Failed releasing redis lock", exc_info=True)

    def _get_from_redis(self, key: str) -> Optional[CacheEntry]:
        if not self._redis:
            return None
        try:
            raw = self._redis.get(key)
        except RedisError as exc:  # pragma: no cover - redis down
            _LOGGER.warning("Redis unavailable during get", exc_info=exc)
            return None
        if not raw:
            return None
        marker, payload = raw[:1], raw[1:]
        if marker == b"Z" and self._decompressor:
            payload = self._decompressor.decompress(payload)
        try:
            data = json_utils.loads(payload)
        except json_utils.JSONDecodeError:
            _LOGGER.error("Corrupted cache payload for key %s", key)
            return None
        return CacheEntry(
            body=data.get("body"),
            status_code=int(data.get("status", 200)),
            headers={str(k): str(v) for k, v in (data.get("headers") or {}).items()},
            created_at=float(data.get("created", time.time())),
        )


def _redis_from_env() -> Optional[Redis]:
    url = os.getenv("REDIS_URL")
    if not url or Redis is None:
        return None
    try:
        client = Redis.from_url(url)
        client.ping()
        return client
    except Exception as exc:  # pragma: no cover - runtime configuration issue
        _LOGGER.warning("Unable to initialize Redis cache", exc_info=exc)
        return None


def build_default_relationship_cache(namespace: str, ttl_seconds: int) -> RelationshipResponseCache:
    redis_client = _redis_from_env()
    maxsize = int(os.getenv("CACHE_MAX_LRU", "512"))
    return RelationshipResponseCache(
        namespace=namespace,
        ttl_seconds=ttl_seconds,
        lru_maxsize=maxsize,
        redis_client=redis_client,
    )
