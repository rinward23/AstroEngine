from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import dataclass
from math import floor
from typing import Any, Hashable, Optional, Tuple

# Quantization size in seconds (default 1s). Tune via env if needed.
DEFAULT_QSEC = float(os.getenv("AE_QCACHE_SEC", "1.0"))


def qbin(jd_tt: float, qsec: float = DEFAULT_QSEC) -> int:
    """Quantize a Julian Day (TT) into ``qsec``-sized bins."""

    # 1 day = 86400 s
    return int(floor((jd_tt * 86400.0) / qsec))


@dataclass(slots=True)
class _Entry:
    key: Tuple[Hashable, ...]
    value: Any


class QCache:
    """Simple process-local LRU cache with maxsize bound."""

    __slots__ = ("maxsize", "_data")

    def __init__(self, maxsize: int = 16384) -> None:
        self.maxsize = maxsize
        self._data: "OrderedDict[Tuple[Hashable, ...], _Entry]" = OrderedDict()

    def get(self, key: Tuple[Hashable, ...]) -> Optional[Any]:
        val = self._data.get(key)
        if val is None:
            return None
        # move to end (most recently used)
        self._data.move_to_end(key)
        return val.value

    def put(self, key: Tuple[Hashable, ...], value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
            self._data[key].value = value
        else:
            self._data[key] = _Entry(key, value)
            if len(self._data) > self.maxsize:
                self._data.popitem(last=False)


# Module-global cache (per process)
qcache = QCache(maxsize=int(os.getenv("AE_QCACHE_SIZE", "4096")))
