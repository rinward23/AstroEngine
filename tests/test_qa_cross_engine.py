from __future__ import annotations

from dataclasses import dataclass

import json

from qa.validation import (
    AdapterMatrix,
    MatrixConfig,
    ToleranceBand,
    run_matrix,
)
from qa.validation.report import write_artifacts


@dataclass
class DummyAdapter:
    config: MatrixConfig
    lon_offset_deg: float = 0.0
    decl_offset_deg: float = 0.0
    speed_offset_deg_per_hour: float = 0.0

    def positions_ecliptic(self, iso_utc: str, bodies):  # pragma: no cover - exercised via tests
        try:
            ts_index = self.config.timestamps.index(iso_utc)
        except ValueError as exc:  # pragma: no cover - defensive
            raise KeyError(f"timestamp {iso_utc} not configured") from exc
        result = {}
        for idx, body in enumerate(bodies):
            try:
                base_idx = self.config.bodies.index(body)
            except ValueError as exc:  # pragma: no cover - defensive
                raise KeyError(f"body {body} not configured") from exc
            base_lon = (base_idx * 30.0 + ts_index * 5.0) % 360.0
            base_decl = -10.0 + base_idx + ts_index
            base_speed = (base_idx + 1) * 0.1
            result[body] = {
                "lon": base_lon + self.lon_offset_deg,
                "decl": base_decl + self.decl_offset_deg,
                "speed_lon": base_speed + self.speed_offset_deg_per_hour,
            }
        return result


def test_run_matrix_detects_breaches(tmp_path):
    timestamps = ["2000-01-01T00:00:00Z", "2000-01-02T00:00:00Z"]
    bodies = ["sun", "mercury", "mars"]
    tolerances = {body: ToleranceBand(lon_arcsec=2.0, decl_arcsec=3.0) for body in bodies}
    config = MatrixConfig(timestamps=timestamps, bodies=bodies, tolerances=tolerances)

    reference = DummyAdapter(config)
    near_match = DummyAdapter(config, lon_offset_deg=0.0001)
    drifting = DummyAdapter(config, lon_offset_deg=0.0025, decl_offset_deg=0.001)

    matrix = AdapterMatrix(
        adapters={
            "reference": reference,
            "near": near_match,
            "drift": drifting,
        },
        reference="reference",
    )

    result = run_matrix(matrix, config)

    assert result.reference == "reference"
    assert len(result.samples) == len(timestamps) * len(bodies) * 2

    near_report = next(report for report in result.adapters if report.adapter == "near")
    drift_report = next(report for report in result.adapters if report.adapter == "drift")

    assert near_report.breaches == []
    assert drift_report.breaches, "drift adapter should violate tolerances"

    # Ensure statistics capture the maximum absolute longitude delta (~9")
    assert drift_report.lon_stats["max"] == max(
        abs(sample.lon_arcsec) for sample in drift_report.breaches
    )

    write_artifacts(result, tmp_path)
    report_json = json.loads((tmp_path / "cross_engine.json").read_text())
    assert report_json["reference"] == "reference"
    assert (tmp_path / "cross_engine.md").exists()
