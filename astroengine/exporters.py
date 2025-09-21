

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


    import sqlite3
except Exception:  # pragma: no cover
    sqlite3 = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover
    pa = None  # type: ignore[assignment]
    pq = None  # type: ignore[assignment]


@dataclass
class TransitEvent:
    """Canonical representation of a detected transit contact."""

    kind: str
    timestamp: str
    moving: str
    target: str
    orb_abs: float
    orb_allow: float
    applying_or_separating: str
    score: float
    lon_moving: float | None = None
    lon_target: float | None = None
    metadata: dict[str, float] = field(default_factory=dict)

    @property
    def when_iso(self) -> str:
        return self.timestamp

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload.setdefault("when_iso", self.timestamp)
        return payload


class SQLiteExporter:
    """Persist transit events into a lightweight SQLite file."""

    def __init__(self, path: str | Path) -> None:
        if sqlite3 is None:
            raise ImportError("sqlite3 unavailable")
        self.path = str(path)
        self._ensure_schema()



class ParquetExporter:
    """Write transit events as a Parquet dataset."""

    def __init__(self, path: str | Path) -> None:
        if pa is None or pq is None:
            raise ImportError("pyarrow not installed")
        self.path = str(path)

    def write(self, events: Iterable[TransitEvent]) -> None:
        assert pa is not None and pq is not None
        table = pa.Table.from_pylist([event.to_dict() for event in events])
        pq.write_table(table, self.path)

