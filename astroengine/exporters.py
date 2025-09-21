"""Export helpers for AstroEngine transit events."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - optional dependency
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

    def _ensure_schema(self) -> None:
        assert sqlite3 is not None
        con = sqlite3.connect(self.path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS transit_events (
                    timestamp TEXT,
                    kind TEXT,
                    moving TEXT,
                    target TEXT,
                    orb_abs REAL,
                    orb_allow REAL,
                    applying_or_separating TEXT,
                    score REAL,
                    lon_moving REAL,
                    lon_target REAL
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def write(self, events: Iterable[TransitEvent]) -> None:
        assert sqlite3 is not None
        con = sqlite3.connect(self.path)
        try:
            rows = [
                (
                    event.timestamp,
                    event.kind,
                    event.moving,
                    event.target,
                    float(event.orb_abs),
                    float(event.orb_allow),
                    event.applying_or_separating,
                    float(event.score),
                    None if event.lon_moving is None else float(event.lon_moving),
                    None if event.lon_target is None else float(event.lon_target),
                )
                for event in events
            ]
            con.executemany(
                """
                INSERT INTO transit_events (
                    timestamp,
                    kind,
                    moving,
                    target,
                    orb_abs,
                    orb_allow,
                    applying_or_separating,
                    score,
                    lon_moving,
                    lon_target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            con.commit()
        finally:
            con.close()


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


def serialize_events_to_json(events: Iterable[TransitEvent]) -> str:
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "events": [event.to_dict() for event in events],
    }
    return json.dumps(payload, indent=2)
