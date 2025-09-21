# >>> AUTO-GEN BEGIN: AE Exporters v1.1
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import sqlite3
except Exception:  # pragma: no cover
    sqlite3 = None

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover
    pa = None
    pq = None


@dataclass
class TransitEvent:
    kind: str
    when_iso: str
    moving: str
    target: str
    orb_abs: float
    applying_or_separating: str
    score: float                 # base score (0..1)
    valence: str                 # positive|neutral|negative
    valence_factor: float        # >= 0
    signed_score: float          # can be negative


class SQLiteExporter:
    def __init__(self, path: str | Path) -> None:
        if sqlite3 is None:
            raise ImportError("sqlite3 unavailable")
        self.path = str(path)
        self._init()

    def _init(self) -> None:
        con = sqlite3.connect(self.path)
        con.execute(
            "CREATE TABLE IF NOT EXISTS transits_events (\n"
            "  kind TEXT, when_iso TEXT, moving TEXT, target TEXT, orb_abs REAL, applying TEXT,\n"
            "  score REAL, valence TEXT, valence_factor REAL, signed_score REAL\n"
            ")"
        )
        con.commit()
        con.close()

    def write(self, events: Iterable[TransitEvent]) -> None:
        con = sqlite3.connect(self.path)
        con.executemany(
            "INSERT INTO transits_events VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(
                e.kind, e.when_iso, e.moving, e.target, e.orb_abs, e.applying_or_separating,
                e.score, e.valence, e.valence_factor, e.signed_score
            ) for e in events],
        )
        con.commit()
        con.close()


class ParquetExporter:
    def __init__(self, path: str | Path) -> None:
        if pa is None or pq is None:
            raise ImportError("pyarrow not installed")
        self.path = str(path)

    def write(self, events: Iterable[TransitEvent]) -> None:
        rows = [asdict(e) for e in events]
        table = pa.Table.from_pylist(rows)
        pq.write_table(table, self.path)
# >>> AUTO-GEN END: AE Exporters v1.1
