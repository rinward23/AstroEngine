from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass(slots=True)
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[K, V]):
    def __init__(self, maxsize: int = 2048):
        self.maxsize = maxsize
        self._lock = threading.Lock()
        self._data: Dict[K, _Entry[V]] = {}

    def get(self, key: K) -> Optional[V]:
        now = time.time()
        with self._lock:
            ent = self._data.get(key)
            if not ent:
                return None
            if ent.expires_at < now:
                # expired
                self._data.pop(key, None)
                return None
            return ent.value

    def set(self, key: K, value: V, ttl_seconds: float) -> None:
        with self._lock:
            if len(self._data) >= self.maxsize:
                # naive eviction: drop an arbitrary item (FIFO/LRU not needed for MVP)
                self._data.pop(next(iter(self._data)))
            self._data[key] = _Entry(value=value, expires_at=time.time() + float(ttl_seconds))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def ttl_cache(ttl_seconds: float, key_fn: Optional[Callable[..., Hashable]] = None, maxsize: int = 2048):
    """Decorator for simple function result caching with TTL.
    key_fn maps args/kwargs → hashable key. If None, uses (args, frozenset(kwargs.items())).
    """
    cache: TTLCache[Hashable, Any] = TTLCache(maxsize=maxsize)

    def _default_key_fn(*args, **kwargs):
        return (args, frozenset(kwargs.items()))

    def decorator(fn: Callable[..., V]):
        def wrapper(*args, **kwargs):
            k = (key_fn or _default_key_fn)(*args, **kwargs)
            v = cache.get(k)
            if v is not None:
                return v
            res = fn(*args, **kwargs)
            cache.set(k, res, ttl_seconds)
            return res

        wrapper._ttl_cache = cache  # expose for tests
        return wrapper

    return decorator
