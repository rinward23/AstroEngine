# >>> AUTO-GEN BEGIN: Tests Canonical Adapter v1.0
import os
import tempfile

from astroengine.canonical import (
    TransitEvent,
    event_from_legacy,
    events_from_any,
    sqlite_write_canonical,
    parquet_write_canonical,
)


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
            meta={"profile_id": "default"},
        ),
        {
            "timestamp": "2025-01-02T12:00:00Z",
            "transiting": "Sun",
            "natal": "natal_Moon",
            "kind": "Conjunction",
            "orb_abs": 0.01,
            "is_applying": False,
            "severity": 0.9,
            "meta": {},
        },
    ]


def test_event_from_legacy_roundtrip():
    evs = events_from_any(_sample_events())
    assert isinstance(evs[0], TransitEvent)
    assert evs[0].aspect == "trine"
    assert abs(evs[1].orb - 0.01) < 1e-9
    assert event_from_legacy(evs[0]) is evs[0]


def test_sqlite_and_parquet_writers_smoke():
    evs = events_from_any(_sample_events())
    with tempfile.TemporaryDirectory() as tmp:
        n = sqlite_write_canonical(os.path.join(tmp, "events.db"), evs)
        assert n == len(evs)

        try:
            import pyarrow  # noqa: F401
        except Exception:
            return

        path = os.path.join(tmp, "events.parquet")
        n2 = parquet_write_canonical(path, evs)
        assert n2 == len(evs)


# >>> AUTO-GEN END: Tests Canonical Adapter v1.0
