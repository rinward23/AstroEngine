from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest

from astroengine import canonical
from astroengine.canonical import TransitEvent
from astroengine.exporters import write_parquet_canonical

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
settings = hypothesis.settings
st = hypothesis.strategies

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

ASPECTS = (
    "conjunction",
    "sextile",
    "square",
    "trine",
    "opposition",
    "semi-sextile",
    "semi-square",
    "sesquiquadrate",
    "quincunx",
)
BODIES = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")

ISO_TIMESTAMPS = st.datetimes(
    min_value=datetime(1950, 1, 1),
    max_value=datetime(2050, 12, 31),
).map(lambda dt: dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"))

META_VALUES = st.one_of(
    st.none(),
    st.integers(-10, 10),
    st.from_regex(r"[A-Za-z0-9 _]{0,16}", fullmatch=True),
)
META_DICT = st.dictionaries(
    keys=st.sampled_from(["profile_id", "natal_id", "source", "notes"]),
    values=META_VALUES,
    max_size=3,
)

TRANSIT_EVENTS = st.builds(
    TransitEvent,
    ts=ISO_TIMESTAMPS,
    moving=st.sampled_from(BODIES),
    target=st.sampled_from(tuple(f"natal_{body}" for body in BODIES)),
    aspect=st.sampled_from(ASPECTS),
    orb=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    applying=st.booleans(),
    score=st.one_of(
        st.none(),
        st.floats(min_value=-25.0, max_value=25.0, allow_nan=False, allow_infinity=False),
    ),
    meta=META_DICT,
)


def _expected_rows(events: Sequence[TransitEvent]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for event in events:
        row = canonical._event_row(event)
        row.pop("meta", None)
        row["natal_id"] = row.get("natal_id") or "unknown"
        rows.append(row)
    return rows


@settings(deadline=None)
@given(events=st.lists(TRANSIT_EVENTS, min_size=1, max_size=20))
def test_parquet_export_round_trip(events: Sequence[TransitEvent]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        parquet_path = Path(tmpdir) / "hits.parquet"
        count = write_parquet_canonical(str(parquet_path), events)
        assert count == len(events)

        df = pd.read_parquet(parquet_path)
        canonical_events = canonical.events_from_any(events)
        expected = _expected_rows(canonical_events)
        expected_df = pd.DataFrame(expected)

        sort_columns = ["ts", "moving", "target", "aspect", "orb"]
        df_sorted = df.sort_values(sort_columns).reset_index(drop=True)
        expected_sorted = expected_df.sort_values(sort_columns).reset_index(drop=True)
        expected_sorted = expected_sorted[df_sorted.columns]

        assert len(df_sorted) == len(expected_sorted)
        pd.testing.assert_frame_equal(
            df_sorted,
            expected_sorted,
            check_dtype=False,
            check_like=False,
        )
