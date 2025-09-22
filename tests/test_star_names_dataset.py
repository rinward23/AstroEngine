"""Validation tests for the official IAU star names dataset."""

from __future__ import annotations

import csv
from pathlib import Path


DATASET = Path(__file__).resolve().parent.parent / "datasets" / "star_names_iau.csv"


def test_dataset_contains_regulus() -> None:
    assert DATASET.is_file(), "star name dataset missing"
    with DATASET.open(encoding="utf-8") as handle:
        reader = csv.DictReader(filter(lambda line: not line.startswith("#"), handle))
        rows = list(reader)
    assert len(rows) > 400
    names = {row["name"] for row in rows}
    assert "Regulus" in names
    assert all(not name.endswith(" B") for name in names)
    regulus = next(row for row in rows if row["name"] == "Regulus")
    assert abs(float(regulus["ra_deg"]) - 152.092962) < 1e-4
    assert abs(float(regulus["dec_deg"]) - 11.967208) < 1e-4
