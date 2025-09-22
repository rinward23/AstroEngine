"""Export utilities for persisting transit events."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - optional dependency
    import sqlite3
except Exception:  # pragma: no cover
    sqlite3 = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    import pyarrow as pa
    import pyarrow.parquet as pq
    _PARQUET_OK = True
except Exception:  # pragma: no cover
    pa = None  # type: ignore[assignment]
    pq = None  # type: ignore[assignment]
    _PARQUET_OK = False

__all__ = [
    "LegacyTransitEvent",
    "SQLiteExporter",
    "ParquetExporter",
    "write_sqlite_canonical",
    "write_parquet_canonical",
    "parquet_available",
]


@dataclass
class LegacyTransitEvent:
    """Legacy representation of a detected transit contact."""

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
    metadata: dict[str, float | str] = field(default_factory=dict)

    @property
    def when_iso(self) -> str:
        """Backwards-compatible alias used by older code paths."""

        return self.timestamp

    def to_dict(self) -> dict:
        """Serialise the event into a JSON-friendly mapping."""

        payload = asdict(self)
        payload.setdefault("when_iso", self.timestamp)
        return payload


class SQLiteExporter:
    """Persist transit events into a lightweight SQLite file."""

    def __init__(self, path: str | Path) -> None:
        if sqlite3 is None:  # pragma: no cover - environment dependent
            raise ImportError("sqlite3 unavailable")
        self.path = str(path)
        self._ensure_schema()

    def _connect(self):  # pragma: no cover - trivial wrapper
        assert sqlite3 is not None
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        con = self._connect()
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS transit_events (
                kind TEXT,
                timestamp TEXT,
                moving TEXT,
                target TEXT,
                orb_abs REAL,
                orb_allow REAL,
                applying TEXT,
                score REAL,
                lon_moving REAL,
                lon_target REAL,
                metadata TEXT
            )
            """
        )
        con.commit()
        con.close()

    def write(self, events: Iterable[LegacyTransitEvent]) -> None:
        con = self._connect()
        rows = [
            (
                event.kind,
                event.timestamp,
                event.moving,
                event.target,
                float(event.orb_abs),
                float(event.orb_allow),
                event.applying_or_separating,
                float(event.score),
                event.lon_moving,
                event.lon_target,
                json.dumps(event.metadata, sort_keys=True),
            )
            for event in events
        ]
        con.executemany(
            """
            INSERT INTO transit_events
            (kind, timestamp, moving, target, orb_abs, orb_allow, applying, score,
             lon_moving, lon_target, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
        con.close()


class ParquetExporter:
    """Write transit events as a Parquet dataset."""

    def __init__(self, path: str | Path) -> None:
        if pa is None or pq is None:  # pragma: no cover - optional dependency
            raise ImportError("pyarrow not installed")
        self.path = str(path)

    def write(self, events: Iterable[LegacyTransitEvent]) -> None:
        assert pa is not None and pq is not None  # for mypy/pyright
        table = pa.Table.from_pylist([event.to_dict() for event in events])
        pq.write_table(table, self.path)


# >>> AUTO-GEN BEGIN: Canonical Export Adapters v1.0
from typing import Iterable as _TypingIterable, Any as _TypingAny

from .canonical import TransitEvent, sqlite_write_canonical, parquet_write_canonical


def write_sqlite_canonical(db_path: str, events: _TypingIterable[_TypingAny]) -> int:
    """Canonical SQLite writer accepting legacy or canonical events."""

    return sqlite_write_canonical(db_path, events)


def write_parquet_canonical(path: str, events: _TypingIterable[_TypingAny]) -> int:
    """Canonical Parquet writer accepting legacy or canonical events."""

    return parquet_write_canonical(path, events)


# >>> AUTO-GEN END: Canonical Export Adapters v1.0


def parquet_available() -> bool:
    return _PARQUET_OK
