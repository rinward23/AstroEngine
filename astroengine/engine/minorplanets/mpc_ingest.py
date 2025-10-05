"""Utilities for downloading, parsing, and storing MPCORB elements."""

from __future__ import annotations

import datetime as _dt
import gzip
import hashlib
import math
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import numpy as np
import requests
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, func, select
from sqlalchemy.orm import DeclarativeBase, Session

from astroengine.core.time import julian_day
from astroengine.core.dependencies import require_dependency

__all__ = [
    "Counts",
    "MinorPlanet",
    "MinorPlanetBase",
    "MpcRow",
    "download_mpcorb",
    "export_parquet",
    "export_zarr_angles",
    "filter_rows",
    "parse_mpcorb",
    "upsert_rows",
]


_DEFAULT_MPC_URL = "https://minorplanetcenter.net/Extended_Files/MPCORB.DAT.gz"

# See https://en.wikipedia.org/wiki/Gaussian_gravitational_constant. The MPCORB
# catalogue expresses mean motion in degrees per day; the Gaussian constant is
# defined in astronomical units^(3/2) per day, so we convert to and from
# radians/degrees as needed.
_GAUSSIAN_GRAVITATIONAL_CONSTANT = 0.01720209895


@lru_cache(maxsize=1)
def _pyarrow_modules():
    """Return the :mod:`pyarrow` modules required for MPC exports."""

    pa_module = require_dependency(
        "pyarrow",
        extras=("exporters", "all"),
        purpose="process Minor Planet Center catalogues",
    )
    pq_module = require_dependency(
        "pyarrow.parquet",
        package="pyarrow",
        extras=("exporters", "all"),
        purpose="write Minor Planet Center catalogues to Parquet",
    )
    return pa_module, pq_module


class MinorPlanetBase(DeclarativeBase):
    """Dedicated SQLAlchemy base for minor planet tables."""

    pass


class MinorPlanet(MinorPlanetBase):
    """ORM model storing MPC-derived orbital elements."""

    __tablename__ = "mpc_bodies"

    body_id = Column(Integer, primary_key=True, autoincrement=True)
    mpc_number = Column(Integer, nullable=True, index=True)
    provisional_designation = Column(String(32), nullable=True, index=True)
    name = Column(String(128), nullable=True, index=True)
    kind = Column(String(16), nullable=False, default="asteroid")
    family = Column(String(64), nullable=True)
    absolute_magnitude = Column(Float, nullable=True)
    slope = Column(Float, nullable=True)
    uncertainty = Column(Integer, nullable=True)
    epoch_jd = Column(Float, nullable=False)
    mean_anomaly_deg = Column(Float, nullable=False)
    argument_perihelion_deg = Column(Float, nullable=False)
    ascending_node_deg = Column(Float, nullable=False)
    inclination_deg = Column(Float, nullable=False)
    eccentricity = Column(Float, nullable=False)
    mean_motion_deg_per_day = Column(Float, nullable=False)
    semi_major_axis_au = Column(Float, nullable=False)
    perihelion_distance_au = Column(Float, nullable=False)
    data_source = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def update_from_row(self, row: "MpcRow") -> None:
        """Update the ORM instance with the latest parsed values."""

        self.mpc_number = row.mpc_number
        self.provisional_designation = row.provisional_designation
        self.name = row.name or self.name
        self.kind = row.kind
        self.family = row.family
        self.absolute_magnitude = row.absolute_magnitude
        self.slope = row.slope
        self.uncertainty = row.uncertainty
        self.epoch_jd = row.epoch_jd
        self.mean_anomaly_deg = row.mean_anomaly_deg
        self.argument_perihelion_deg = row.argument_perihelion_deg
        self.ascending_node_deg = row.ascending_node_deg
        self.inclination_deg = row.inclination_deg
        self.eccentricity = row.eccentricity
        self.mean_motion_deg_per_day = row.mean_motion_deg_per_day
        self.semi_major_axis_au = row.semi_major_axis_au
        self.perihelion_distance_au = row.perihelion_distance_au
        self.data_source = row.source

    @classmethod
    def from_row(cls, row: "MpcRow") -> "MinorPlanet":
        instance = cls()
        instance.update_from_row(row)
        return instance


@dataclass(slots=True)
class MpcRow:
    """Parsed Minor Planet Center row."""

    mpc_number: int | None
    provisional_designation: str | None
    name: str | None
    kind: str
    family: str | None
    absolute_magnitude: float | None
    slope: float | None
    uncertainty: int | None
    epoch_jd: float
    mean_anomaly_deg: float
    argument_perihelion_deg: float
    ascending_node_deg: float
    inclination_deg: float
    eccentricity: float
    mean_motion_deg_per_day: float
    semi_major_axis_au: float
    perihelion_distance_au: float
    source: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "mpc_number": self.mpc_number,
            "provisional_designation": self.provisional_designation,
            "name": self.name,
            "kind": self.kind,
            "family": self.family,
            "absolute_magnitude": self.absolute_magnitude,
            "slope": self.slope,
            "uncertainty": self.uncertainty,
            "epoch_jd": self.epoch_jd,
            "mean_anomaly_deg": self.mean_anomaly_deg,
            "argument_perihelion_deg": self.argument_perihelion_deg,
            "ascending_node_deg": self.ascending_node_deg,
            "inclination_deg": self.inclination_deg,
            "eccentricity": self.eccentricity,
            "mean_motion_deg_per_day": self.mean_motion_deg_per_day,
            "semi_major_axis_au": self.semi_major_axis_au,
            "perihelion_distance_au": self.perihelion_distance_au,
            "source": self.source,
        }


@dataclass(slots=True)
class Counts:
    """Summary of insert and update activity."""

    inserted: int = 0
    updated: int = 0


def download_mpcorb(cache_dir: str | os.PathLike[str]) -> Path:
    """Download the MPCORB catalogue into ``cache_dir`` with checksums."""

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    url = os.environ.get("ASTROENGINE_MPCORB_URL", _DEFAULT_MPC_URL)
    target = cache_path / "MPCORB.dat.gz"
    checksum_path = target.with_suffix(".sha256")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    sha256 = hashlib.sha256()
    with tempfile_path(target) as tmp_path:
        with open(tmp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                handle.write(chunk)
                sha256.update(chunk)
    checksum = sha256.hexdigest()
    checksum_path.write_text(checksum)
    return target


class tempfile_path:
    """Context manager ensuring atomic downloads."""

    def __init__(self, target: Path) -> None:
        self.target = target
        self.tmp = target.with_suffix(target.suffix + ".tmp")

    def __enter__(self) -> Path:
        if self.tmp.exists():
            self.tmp.unlink()
        return self.tmp

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if exc_type is None:
            self.tmp.replace(self.target)
        elif self.tmp.exists():
            self.tmp.unlink()


def parse_mpcorb(path: str | os.PathLike[str]) -> list[MpcRow]:
    """Parse MPCORB data into :class:`MpcRow` structures."""

    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[MpcRow] = []
    with opener(path, "rt", encoding="utf8", errors="ignore") as handle:
        for raw_line in handle:
            if not raw_line or raw_line.startswith("#"):
                continue
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            try:
                row = _parse_line(line)
            except ValueError:
                continue
            rows.append(row)
    return rows


def _parse_line(line: str) -> MpcRow:
    number = _parse_int(line[0:7])
    absolute_magnitude = _parse_float(line[8:14])
    slope = _parse_float(line[14:20])
    epoch_field = line[20:32].strip() or line[19:32].strip()
    epoch_jd = _parse_epoch(epoch_field)
    mean_anomaly = _parse_float(line[32:44])
    arg_peri = _parse_float(line[44:56])
    ascending_node = _parse_float(line[56:68])
    inclination = _parse_float(line[68:80])
    eccentricity = _parse_float(line[80:92])
    mean_motion = _parse_float(line[92:105])
    semi_major = _parse_float(line[105:118])
    uncertainty = _parse_int(line[118:120])
    provisional = line[120:136].strip() or None
    name = line[166:].strip() or None
    if semi_major is None and mean_motion is not None:
        semi_major = _semi_major_from_mean_motion(mean_motion)
    if mean_motion is None and semi_major is not None:
        mean_motion = _mean_motion_from_semi_major(semi_major)

    perihelion = semi_major * (1.0 - eccentricity) if semi_major is not None else None

    if None in (
        epoch_jd,
        mean_anomaly,
        arg_peri,
        ascending_node,
        inclination,
        eccentricity,
        mean_motion,
        semi_major,
        perihelion,
    ):
        raise ValueError("Incomplete MPC row")

    kind = _classify_minor_planet(semi_major)
    source = {"line": line.strip()}
    return MpcRow(
        mpc_number=number,
        provisional_designation=provisional,
        name=name,
        kind=kind,
        family=None,
        absolute_magnitude=absolute_magnitude,
        slope=slope,
        uncertainty=uncertainty,
        epoch_jd=epoch_jd,
        mean_anomaly_deg=mean_anomaly,
        argument_perihelion_deg=arg_peri,
        ascending_node_deg=ascending_node,
        inclination_deg=inclination,
        eccentricity=eccentricity,
        mean_motion_deg_per_day=mean_motion,
        semi_major_axis_au=semi_major,
        perihelion_distance_au=perihelion,
        source=source,
    )


def _classify_minor_planet(semi_major_axis: float) -> str:
    if semi_major_axis >= 30.0:
        return "tno"
    if semi_major_axis >= 5.5:
        return "centaur"
    return "asteroid"


def _parse_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    return int(value)


def _parse_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def _mean_motion_from_semi_major(semi_major: float) -> float:
    if semi_major <= 0.0:
        raise ValueError("semi-major axis must be positive")
    n_rad = _GAUSSIAN_GRAVITATIONAL_CONSTANT / math.pow(semi_major, 1.5)
    return math.degrees(n_rad)


def _semi_major_from_mean_motion(mean_motion: float) -> float:
    if mean_motion <= 0.0:
        raise ValueError("mean motion must be positive")
    n_rad = math.radians(mean_motion)
    return math.pow(_GAUSSIAN_GRAVITATIONAL_CONSTANT / n_rad, 2.0 / 3.0)


def _parse_epoch(token: str) -> float:
    if not token:
        raise ValueError("missing epoch")
    token = token.strip()
    if token.replace(".", "", 1).isdigit():
        return float(token)
    return _julian_day_from_packed(token)


_PACKED_YEAR_OFFSET = {
    **{str(d): d for d in range(10)},
    **{chr(ord("A") + i): 10 + i for i in range(26)},
}
_PACKED_DAY_OFFSET = {**_PACKED_YEAR_OFFSET, **{chr(ord("a") + i): 36 + i for i in range(26)}}


def _julian_day_from_packed(token: str) -> float:
    if len(token) != 5:
        raise ValueError(f"Unexpected packed epoch '{token}'")
    century = _PACKED_YEAR_OFFSET[token[0]]
    year_suffix = int(token[1:3])
    year = century * 100 + year_suffix
    month = _PACKED_YEAR_OFFSET[token[3]]
    day = _PACKED_DAY_OFFSET[token[4]]
    moment = _dt.datetime(year, month, day, tzinfo=_dt.UTC)
    return julian_day(moment)


def filter_rows(rows: Sequence[MpcRow], H_max: float = 12.0, U_max: int = 5) -> list[MpcRow]:
    """Filter rows based on absolute magnitude and uncertainty."""

    filtered: list[MpcRow] = []
    for row in rows:
        if row.absolute_magnitude is not None and row.absolute_magnitude > H_max:
            continue
        if row.uncertainty is not None and row.uncertainty > U_max:
            continue
        filtered.append(row)
    return filtered


def upsert_rows(session: Session, rows: Sequence[MpcRow]) -> Counts:
    """Insert or update :class:`MpcRow` entries into the database."""

    counts = Counts()
    for row in rows:
        statement = None
        if row.mpc_number is not None:
            statement = select(MinorPlanet).where(MinorPlanet.mpc_number == row.mpc_number)
        elif row.provisional_designation:
            statement = select(MinorPlanet).where(
                MinorPlanet.provisional_designation == row.provisional_designation
            )
        elif row.name:
            statement = select(MinorPlanet).where(MinorPlanet.name == row.name)

        existing = session.scalar(statement) if statement is not None else None
        if existing is None:
            session.add(MinorPlanet.from_row(row))
            counts.inserted += 1
        else:
            existing.update_from_row(row)
            counts.updated += 1
    return counts


def export_parquet(rows: Sequence[MpcRow], path: str | os.PathLike[str]) -> Path:
    """Export rows to a Parquet file for analytics workflows."""

    path = Path(path)
    data = [row.as_dict() for row in rows]
    pa_module, pq_module = _pyarrow_modules()
    table = pa_module.Table.from_pylist(data)
    pq_module.write_table(table, path)
    return path


def export_zarr_angles(
    ephem,
    rows: Sequence[MpcRow],
    start: _dt.datetime,
    end: _dt.datetime,
    step: _dt.timedelta,
    out_dir: str | os.PathLike[str],
    *,
    scale: int = 100,
) -> Path:
    """Export quantised longitudes to a Zarr array on disk."""

    try:
        import zarr
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise ModuleNotFoundError(
            "The 'zarr' package is required for export_zarr_angles"  # noqa: TRY003
        ) from exc

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    timestamps = _build_time_grid(start, end, step)
    data = np.empty((len(rows), len(timestamps)), dtype=np.uint16)

    for i, row in enumerate(rows):
        for j, moment in enumerate(timestamps):
            lon = float(ephem.longitude(row, moment)) % 360.0
            if lon < 0.0:
                lon += 360.0
            data[i, j] = int(round(lon * scale)) % (360 * scale)

    store_path = out_path / "angles.zarr"
    zarr.save_array(store_path, data, compressor=zarr.Blosc())
    return store_path


def _build_time_grid(start: _dt.datetime, end: _dt.datetime, step: _dt.timedelta) -> list[_dt.datetime]:
    moments: list[_dt.datetime] = []
    current = start
    while current <= end:
        moments.append(current)
        current = current + step
    return moments
