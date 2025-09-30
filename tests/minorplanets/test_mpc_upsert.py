from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from astroengine.engine.minorplanets import mpc_ingest


def _row(number: int, name: str, semi_major: float) -> mpc_ingest.MpcRow:
    return mpc_ingest.MpcRow(
        mpc_number=number,
        provisional_designation=None,
        name=name,
        kind="asteroid",
        family=None,
        absolute_magnitude=3.0,
        slope=0.15,
        uncertainty=1,
        epoch_jd=2459200.5,
        mean_anomaly_deg=0.0,
        argument_perihelion_deg=0.0,
        ascending_node_deg=0.0,
        inclination_deg=0.0,
        eccentricity=0.1,
        mean_motion_deg_per_day=0.1,
        semi_major_axis_au=semi_major,
        perihelion_distance_au=semi_major * (1.0 - 0.1),
        source={"line": ""},
    )


def test_upsert_inserts_and_updates(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    mpc_ingest.MinorPlanetBase.metadata.create_all(engine)

    rows = [_row(1, "Ceres", 2.77), _row(2, "Pallas", 2.72)]
    with Session(engine) as session:
        counts = mpc_ingest.upsert_rows(session, rows)
        session.commit()
        assert counts.inserted == 2
        assert counts.updated == 0

        updated = [_row(1, "Ceres", 2.80)]
        counts = mpc_ingest.upsert_rows(session, updated)
        session.commit()
        assert counts.inserted == 0
        assert counts.updated == 1

        stored = session.query(mpc_ingest.MinorPlanet).filter_by(mpc_number=1).one()
        assert stored.semi_major_axis_au == 2.80
