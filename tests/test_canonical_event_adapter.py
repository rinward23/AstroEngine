# >>> AUTO-GEN BEGIN: Tests Canonical Adapter v1.0
import os
import sqlite3
import tempfile

import pytest

from astroengine.canonical import (
    TransitEvent,
    event_from_legacy,
    events_from_any,
    parquet_write_canonical,
    sqlite_read_canonical,
    sqlite_write_canonical,
)
from astroengine.infrastructure.storage.sqlite import SQLiteMigrator
from astroengine.infrastructure.storage.sqlite.query import top_events_by_score


def _sample_events():
    return [
        TransitEvent(
            ts="2025-01-01T00:00:00Z",
            moving="Mars",
            target="natal_Venus",
            aspect="trine",
            orb=-0.12,
            applying=True,
            score=1.5,
            meta={
                "profile_id": "default",
                "natal_id": "n001",
                "event_type": "ingress",
                "ingress_sign": "Leo",
            },
        ),
        {
            "timestamp": "2026-03-21T12:00:00Z",
            "transiting": "Sun",
            "natal": "natal_Moon",
            "kind": "Conjunction",
            "orb_abs": 0.01,
            "is_applying": False,
            "severity": 0.9,
            "meta": {"natal": {"id": "n002"}, "profile": {"id": "secondary"}},
        },
        {
            "timestamp": "2025-06-15T05:30:00Z",
            "transiting": "Venus",
            "natal": "natal_Sun",
            "kind": "Square",
            "orb_abs": 1.2,
            "is_applying": True,
            "severity": 2.4,
            "meta": {"profile_id": "default", "natal_id": "n001"},
        },
    ]


def test_event_from_legacy_roundtrip():
    evs = events_from_any(_sample_events())
    assert isinstance(evs[0], TransitEvent)
    assert evs[0].aspect == "trine"
    assert abs(evs[1].orb - 0.01) < 1e-9
    assert event_from_legacy(evs[0]) is evs[0]


def test_sqlite_round_trip_preserves_meta():
    evs = events_from_any(_sample_events())
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "events.db")
        sqlite_write_canonical(db_path, evs)
        loaded = sqlite_read_canonical(db_path)
        assert sorted(e.ts for e in loaded) == sorted(e.ts for e in evs)
        assert loaded[0].meta["natal_id"] == "n001"
        secondary = next(e for e in loaded if e.meta.get("profile_id") == "secondary")
        assert secondary.meta["natal_id"] == "n002"


def test_alembic_migration_cycle(tmp_path):
    db_path = tmp_path / "events.db"
    migrator = SQLiteMigrator(db_path)
    migrator.upgrade()
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transits_events'"
        )
        assert cur.fetchone() is not None
    migrator.downgrade("base")
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transits_events'"
        )
        assert cur.fetchone() is None


def test_query_top_events(tmp_path):
    db_path = tmp_path / "events.db"
    evs = events_from_any(_sample_events())
    sqlite_write_canonical(db_path, evs)
    results = top_events_by_score(str(db_path), limit=2, natal_id="n001")
    assert len(results) == 2
    assert all(r["natal_id"] == "n001" for r in results)
    assert results[0]["score"] >= results[1]["score"]


def test_parquet_dataset_partition_filters(tmp_path):
    try:
        import pyarrow.dataset as ds
    except Exception:
        pytest.skip("pyarrow.dataset unavailable")

    evs = events_from_any(_sample_events())
    root = tmp_path / "events_ds"
    parquet_write_canonical(str(root), evs, compression="gzip")

    dataset = ds.dataset(str(root), partitioning="hive")
    filtered = dataset.to_table(filter=ds.field("natal_id") == "n001")
    assert filtered.num_rows == 2
    assert set(filtered.column("event_year").to_pylist()) == {2025}


# >>> AUTO-GEN END: Tests Canonical Adapter v1.0
