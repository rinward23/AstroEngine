from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

pytest.importorskip(
    "pyarrow",
    reason="pyarrow not installed; install extras with `pip install -e .[exporters,providers]`.",
)
pq = pytest.importorskip(
    "pyarrow.parquet",
    reason="pyarrow not installed; install extras with `pip install -e .[exporters,providers]`.",
)

from astroengine.engine.minorplanets import mpc_ingest


class DummyEphem:
    def longitude(self, row: mpc_ingest.MpcRow, moment: dt.datetime) -> float:
        base = (row.mpc_number or 0) * 1.0
        return (base + moment.timetuple().tm_yday) % 360.0


def _row(number: int) -> mpc_ingest.MpcRow:
    return mpc_ingest.MpcRow(
        mpc_number=number,
        provisional_designation=f"X{number:04d}",
        name=f"Asteroid {number}",
        kind="asteroid",
        family=None,
        absolute_magnitude=10.0,
        slope=0.15,
        uncertainty=1,
        epoch_jd=2459200.5,
        mean_anomaly_deg=0.0,
        argument_perihelion_deg=0.0,
        ascending_node_deg=0.0,
        inclination_deg=0.0,
        eccentricity=0.1,
        mean_motion_deg_per_day=0.1,
        semi_major_axis_au=2.7,
        perihelion_distance_au=2.4,
        source={"line": ""},
    )


def test_export_parquet_round_trip(tmp_path: Path) -> None:
    rows = [_row(1), _row(2)]
    path = tmp_path / "rows.parquet"
    mpc_ingest.export_parquet(rows, path)
    table = pq.read_table(path)
    assert table.num_rows == 2
    assert table.column("mpc_number")[0].as_py() == 1


def test_export_zarr_angles(tmp_path: Path) -> None:
    zarr = pytest.importorskip("zarr")
    rows = [_row(1), _row(2)]
    start = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    end = dt.datetime(2024, 1, 2, tzinfo=dt.timezone.utc)
    step = dt.timedelta(days=1)
    ephem = DummyEphem()
    store_path = mpc_ingest.export_zarr_angles(ephem, rows, start, end, step, tmp_path)
    arr = zarr.open(store_path, mode="r")
    assert arr.shape == (2, 2)
    assert arr[0, 0] != arr[0, 1]
