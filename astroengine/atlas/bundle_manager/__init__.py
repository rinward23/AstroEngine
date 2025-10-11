"""Atlas bundle helpers including advanced map tile caching."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import time
from typing import Callable, Mapping, MutableMapping

TileId = tuple[str, int, int, int]
TileLoader = Callable[[TileId], bytes | Mapping[str, object]]


@dataclass
class CacheStats:
    """Aggregated statistics about cache performance."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total else 0.0


@dataclass
class TileCache:
    """LRU cache for map tiles aware of atlas bundle provenance."""

    capacity: int = 256
    ttl_seconds: int = 3600
    _entries: MutableMapping[TileId, tuple[float, bytes | Mapping[str, object]]] = field(default_factory=dict)
    stats: CacheStats = field(default_factory=CacheStats)

    def fetch(self, tile_id: TileId, loader: TileLoader) -> bytes | Mapping[str, object]:
        now = time.monotonic()
        payload = self._entries.get(tile_id)
        if payload and (now - payload[0]) < self.ttl_seconds:
            self.stats.hits += 1
            return payload[1]
        if payload:
            self.stats.evictions += 1
            del self._entries[tile_id]
        self.stats.misses += 1
        value = loader(tile_id)
        self._entries[tile_id] = (now, value)
        self._trim()
        return value

    def prefetch(self, tile_ids: list[TileId], loader: TileLoader) -> None:
        for tile_id in tile_ids:
            self.fetch(tile_id, loader)

    def _trim(self) -> None:
        if len(self._entries) <= self.capacity:
            return
        sorted_items = sorted(self._entries.items(), key=lambda item: item[1][0])
        for key, _ in sorted_items[:-self.capacity]:
            del self._entries[key]
            self.stats.evictions += 1


@dataclass(frozen=True)
class AtlasBundleManager:
    """Expose bundle metadata and lazily provide a :class:`TileCache`."""

    tile_capacity: int = 512
    ttl_seconds: int = 7200

    @lru_cache(maxsize=1)
    def tile_cache(self) -> TileCache:
        return TileCache(capacity=self.tile_capacity, ttl_seconds=self.ttl_seconds)


@lru_cache(maxsize=1)
def default_bundle_manager() -> AtlasBundleManager:
    """Return the default bundle manager used by UI integrations."""

    return AtlasBundleManager()
