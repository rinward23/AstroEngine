from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from astroengine.exporters import LegacyTransitEvent, ParquetExporter, SQLiteExporter

pyarrow = pytest.importorskip("pyarrow")
pq = pyarrow.parquet


class _SinglePassTransitEvents:
    def __init__(self, count: int) -> None:
        self.count = count
        self._iterated = False

    def __iter__(self):
        if self._iterated:
            raise AssertionError("events consumed multiple times")
        self._iterated = True
        for idx in range(self.count):
            yield LegacyTransitEvent(
                kind="contact",
                timestamp=f"2024-01-{idx + 1:02d}T00:00:00Z",
                moving="Sun",
                target="Moon",
                orb_abs=0.5 + idx,
                orb_allow=1.5,
                applying_or_separating="applying" if idx % 2 == 0 else "separating",
                score=25.0 + idx,
                lon_moving=120.0 + idx,
                lon_target=210.0 + idx,
                metadata={"index": idx, "label": f"event-{idx}"},
            )


def test_sqlite_exporter_accepts_generator(tmp_path: Path) -> None:
    exporter = SQLiteExporter(tmp_path / "events.db")
    source = _SinglePassTransitEvents(3)

    exporter.write(iter(source))

    con = sqlite3.connect(str(tmp_path / "events.db"))
    try:
        rows = con.execute(
            "SELECT kind, timestamp, metadata FROM transit_events ORDER BY timestamp"
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 3
    metadata_payloads = [json.loads(row[2]) for row in rows]
    assert metadata_payloads == [
        {"index": 0, "label": "event-0"},
        {"index": 1, "label": "event-1"},
        {"index": 2, "label": "event-2"},
    ]
    assert source._iterated is True


@pytest.mark.filterwarnings("ignore:Parquet file size is 0 bytes")
def test_parquet_exporter_accepts_single_pass_iterable(tmp_path: Path) -> None:
    exporter = ParquetExporter(tmp_path / "events.parquet")
    source = _SinglePassTransitEvents(4)

    exporter.write(iter(source))

    table = pq.read_table(tmp_path / "events.parquet")
    data = table.to_pylist()

    assert len(data) == 4
    assert data[0]["metadata"] == {"index": 0, "label": "event-0"}
    assert data[-1]["metadata"] == {"index": 3, "label": "event-3"}
    assert source._iterated is True
