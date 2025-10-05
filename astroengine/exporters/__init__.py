"""Export utilities for persisting transit events."""

from __future__ import annotations

import json
from collections.abc import Iterable
from collections.abc import Iterable as _TypingIterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any as _TypingAny

from ..canonical import parquet_write_canonical, sqlite_write_canonical
from ..infrastructure.storage.sqlite import apply_default_pragmas

try:  # pragma: no cover - optional dependency
    import sqlite3
except Exception:  # pragma: no cover
    sqlite3 = None  # type: ignore[assignment]

_PYARROW_MODULES: tuple[_TypingAny, _TypingAny] | None = None
_PARQUET_OK: bool | None = None

__all__ = [
    "LegacyTransitEvent",
    "SQLiteExporter",
    "ParquetExporter",
    "write_sqlite_canonical",
    "write_parquet_canonical",
    "parquet_available",
]


def _load_pyarrow(*, required: bool) -> tuple[_TypingAny, _TypingAny] | None:
    """Import :mod:`pyarrow` lazily to avoid CLI cold-start penalties."""

    global _PYARROW_MODULES, _PARQUET_OK

    if _PYARROW_MODULES is not None:
        _PARQUET_OK = True
        return _PYARROW_MODULES

    try:  # pragma: no cover - optional dependency
        import pyarrow as pa_module
        import pyarrow.parquet as pq_module
    except Exception as exc:  # pragma: no cover - optional dependency
        _PARQUET_OK = False
        if required:
            raise ImportError("pyarrow not installed") from exc
        return None

    _PYARROW_MODULES = (pa_module, pq_module)
    _PARQUET_OK = True
    return _PYARROW_MODULES


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

    metadata: dict[str, object] = field(default_factory=dict)

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
        connection = sqlite3.connect(self.path)
        apply_default_pragmas(connection)
        return connection

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
        if _load_pyarrow(required=False) is None:
            _load_pyarrow(required=True)
        self.path = str(path)

    def write(self, events: Iterable[LegacyTransitEvent]) -> None:
        modules = _load_pyarrow(required=True)
        assert modules is not None  # for type-checkers
        pa_module, pq_module = modules
        table = pa_module.Table.from_pylist([event.to_dict() for event in events])
        pq_module.write_table(table, self.path)


# >>> AUTO-GEN BEGIN: Canonical Export Adapters v1.0

def write_sqlite_canonical(db_path: str, events: _TypingIterable[_TypingAny]) -> int:
    """Canonical SQLite writer accepting legacy or canonical events."""

    return sqlite_write_canonical(db_path, events)


def write_parquet_canonical(path: str, events: _TypingIterable[_TypingAny]) -> int:
    """Canonical Parquet writer accepting legacy or canonical events."""

    return parquet_write_canonical(path, events)


# >>> AUTO-GEN END: Canonical Export Adapters v1.0


def parquet_available() -> bool:
    if _PARQUET_OK is None:
        _load_pyarrow(required=False)
    return bool(_PARQUET_OK)
