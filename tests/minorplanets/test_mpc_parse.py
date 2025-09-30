from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from astroengine.engine.minorplanets import mpc_ingest


def _format_field(value: str, width: int) -> str:
    text = f"{value:>{width}}"
    if len(text) > width:
        return text[:width]
    return text


def _format_float(value: float, width: int, precision: int) -> str:
    text = f"{value:{width}.{precision}f}"
    if len(text) > width:
        text = text[:width]
    return text


def _mpc_line(
    number: int,
    H: float,
    G: float,
    epoch_jd: float,
    mean_anomaly: float,
    arg_peri: float,
    ascending_node: float,
    inclination: float,
    eccentricity: float,
    mean_motion: float,
    semi_major: float,
    uncertainty: int,
    provisional: str,
    name: str,
) -> str:
    line = [" "] * 194
    line[0:7] = _format_field(f"{number:d}", 7)
    line[8:14] = _format_float(H, 6, 2)
    line[14:20] = _format_float(G, 6, 2)
    line[20:32] = _format_float(epoch_jd, 12, 1)
    line[32:44] = _format_float(mean_anomaly, 12, 5)
    line[44:56] = _format_float(arg_peri, 12, 5)
    line[56:68] = _format_float(ascending_node, 12, 5)
    line[68:80] = _format_float(inclination, 12, 5)
    line[80:92] = _format_float(eccentricity, 12, 7)
    line[92:105] = _format_float(mean_motion, 13, 8)
    line[105:118] = _format_float(semi_major, 13, 7)
    line[118:120] = _format_field(str(uncertainty), 2)
    line[120:136] = _format_field(provisional, 16)
    line[166:166 + len(name)] = list(name)
    return "".join(line)


def test_parse_mpc_rows(tmp_path: Path) -> None:
    content = "\n".join(
        [
            _mpc_line(
                1,
                3.34,
                0.12,
                2459200.5,
                80.30420,
                73.59748,
                80.30563,
                10.58764,
                0.0785020,
                0.21456678,
                2.7678531,
                0,
                "A1234",
                "(1) Ceres",
            ),
            _mpc_line(
                2060,
                6.54,
                0.15,
                2459200.5,
                138.74120,
                311.12345,
                209.12345,
                6.93725,
                0.3829402,
                0.09956789,
                13.6901234,
                2,
                "1977UB",
                "(2060) Chiron",
            ),
        ]
    )
    catalog_path = tmp_path / "sample.dat"
    catalog_path.write_text(content)

    rows = mpc_ingest.parse_mpcorb(catalog_path)
    assert len(rows) == 2

    ceres, chiron = rows
    assert ceres.mpc_number == 1
    assert pytest.approx(ceres.semi_major_axis_au, rel=1e-7) == 2.7678531
    assert ceres.kind == "asteroid"
    assert ceres.name == "(1) Ceres"
    assert pytest.approx(chiron.perihelion_distance_au, rel=1e-7) == pytest.approx(
        13.6901234 * (1.0 - 0.3829402), rel=1e-7
    )
    assert chiron.kind == "centaur"


def test_filtering_limits() -> None:
    rows = [
        mpc_ingest.MpcRow(
            mpc_number=1,
            provisional_designation=None,
            name="Ceres",
            kind="asteroid",
            family=None,
            absolute_magnitude=3.3,
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
        ),
        mpc_ingest.MpcRow(
            mpc_number=2,
            provisional_designation=None,
            name="Dim",
            kind="asteroid",
            family=None,
            absolute_magnitude=15.0,
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
        ),
        mpc_ingest.MpcRow(
            mpc_number=3,
            provisional_designation=None,
            name="Fuzzy",
            kind="asteroid",
            family=None,
            absolute_magnitude=10.0,
            slope=0.15,
            uncertainty=9,
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
        ),
    ]

    filtered = mpc_ingest.filter_rows(rows, H_max=12.0, U_max=5)
    assert [row.mpc_number for row in filtered] == [1]


def test_missing_mean_motion_reconstructed(tmp_path: Path) -> None:
    line = _mpc_line(
        1,
        3.34,
        0.12,
        2459200.5,
        80.30420,
        73.59748,
        80.30563,
        10.58764,
        0.0785020,
        0.21456678,
        2.7678531,
        0,
        "A1234",
        "(1) Ceres",
    )
    line = f"{line[:92]}{' ' * 13}{line[105:]}"
    path = tmp_path / "missing_n.dat"
    path.write_text(line)

    rows = mpc_ingest.parse_mpcorb(path)
    assert len(rows) == 1
    row = rows[0]
    expected = mpc_ingest._mean_motion_from_semi_major(row.semi_major_axis_au)
    assert pytest.approx(row.mean_motion_deg_per_day, rel=1e-9) == expected


def test_missing_semi_major_reconstructed(tmp_path: Path) -> None:
    semi_major = 2.7678531
    mean_motion = mpc_ingest._mean_motion_from_semi_major(semi_major)
    line = _mpc_line(
        1,
        3.34,
        0.12,
        2459200.5,
        80.30420,
        73.59748,
        80.30563,
        10.58764,
        0.0785020,
        mean_motion,
        semi_major,
        0,
        "A1234",
        "(1) Ceres",
    )
    line = f"{line[:105]}{' ' * 13}{line[118:]}"
    path = tmp_path / "missing_a.dat"
    path.write_text(line)

    rows = mpc_ingest.parse_mpcorb(path)
    assert len(rows) == 1
    row = rows[0]
    assert row.semi_major_axis_au == pytest.approx(semi_major, rel=1e-7)
