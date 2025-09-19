"""Lookup helpers for classical dignity tables."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

__all__ = ["DignityRecord", "load_dignities", "lookup_dignities"]


@dataclass(frozen=True)
class DignityRecord:
    """Structured row pulled from :mod:`profiles/dignities.csv`."""

    planet: str
    sign: str
    dignity_type: str
    sect: str | None
    start_deg: float | None
    end_deg: float | None
    modifier: float | None
    source: str


def _repository_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "profiles"
        if (candidate / "dignities.csv").is_file():
            return parent
    raise FileNotFoundError("Unable to locate repository root containing 'profiles'.")


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


@lru_cache(maxsize=1)
def load_dignities() -> tuple[DignityRecord, ...]:
    """Load the entire dignity table into memory."""

    path = _repository_root() / "profiles" / "dignities.csv"
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records = []
        for row in reader:
            records.append(
                DignityRecord(
                    planet=row["planet"].strip().lower(),
                    sign=row["sign"].strip().lower(),
                    dignity_type=row["dignity_type"].strip().lower(),
                    sect=row.get("sect", "").strip().lower() or None,
                    start_deg=_parse_float(row.get("start_deg")),
                    end_deg=_parse_float(row.get("end_deg")),
                    modifier=_parse_float(row.get("modifier")),
                    source=row.get("source", "").strip(),
                )
            )
    return tuple(records)


def lookup_dignities(
    planet: str,
    *,
    sign: str | None = None,
    degree: float | None = None,
) -> tuple[DignityRecord, ...]:
    """Return dignity rows matching the supplied filters."""

    planet_key = planet.strip().lower()
    sign_key = sign.strip().lower() if sign else None
    matches: list[DignityRecord] = []
    for record in load_dignities():
        if record.planet != planet_key:
            continue
        if sign_key and record.sign != sign_key:
            continue
        if degree is not None and record.start_deg is not None and record.end_deg is not None:
            if not (record.start_deg <= degree < record.end_deg):
                continue
        matches.append(record)
    return tuple(matches)
