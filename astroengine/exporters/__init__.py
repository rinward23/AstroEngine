"""Export utilities for persisting transit events."""

from __future__ import annotations

import json
import itertools
from collections.abc import Iterable, Iterator
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

_PARQUET_WRITE_BATCH_SIZE = 512

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
        con.executemany(
            """
            INSERT INTO transit_events
            (kind, timestamp, moving, target, orb_abs, orb_allow, applying, score,
             lon_moving, lon_target, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
            ),
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
        iterator = iter(events)
        try:
            first_event = next(iterator)
        except StopIteration:
            empty_table = pa_module.Table.from_pylist([])
            pq_module.write_table(empty_table, self.path)
            return

        chained_events = itertools.chain([first_event], iterator)
        writer = None
        try:
            for batch_dicts in _batched_event_dicts(
                chained_events, _PARQUET_WRITE_BATCH_SIZE
            ):
                record_batch = pa_module.RecordBatch.from_pylist(batch_dicts)
                if writer is None:
                    writer = pq_module.ParquetWriter(self.path, record_batch.schema)
                writer.write_batch(record_batch)
        finally:
            if writer is not None:
                writer.close()


def _batched_event_dicts(
    events: Iterable[LegacyTransitEvent], batch_size: int
) -> Iterator[list[dict[str, _TypingAny]]]:
    iterator = iter(events)
    while True:
        raw_batch = list(itertools.islice(iterator, batch_size))
        if not raw_batch:
            break
        yield [event.to_dict() for event in raw_batch]


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
