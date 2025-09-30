"""Cross-engine validation harness for AstroEngine ephemeris providers.

The :func:`run_matrix` entry point evaluates a matrix of timestamps,
bodies, and (optional) observer metadata against multiple ephemeris
providers.  The resulting :class:`MatrixResult` captures per-body deltas
in arcseconds together with aggregate statistics and tolerance breaches.

The harness is deterministic by construction: iteration order is sorted,
randomness is avoided, and callers are expected to supply explicit ISO
8601 timestamps.  The harness does not fabricate ephemeris values; it
relies entirely on the provided adapters which must source their data
from real ephemeris kernels installed in the runtime environment.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
import math
from pathlib import Path
import statistics
from typing import Protocol, runtime_checkable

LOG = logging.getLogger(__name__)


@runtime_checkable
class EphemerisAdapter(Protocol):
    """Adapter contract required by :func:`run_matrix`."""

    def positions_ecliptic(
        self, iso_utc: str, bodies: Iterable[str]
    ) -> Mapping[str, Mapping[str, float]]:
        """Return ecliptic positions for ``bodies`` at ``iso_utc``.

        Implementations must express longitudes in degrees (0–360) and
        declinations/latitudes in degrees.  Optional keys such as
        ``speed_lon`` will be processed when available.
        """


@dataclass(frozen=True)
class ToleranceBand:
    """Tolerance expressed in arcseconds for longitude/declination."""

    lon_arcsec: float
    decl_arcsec: float | None = None


@dataclass(frozen=True)
class MatrixConfig:
    """Configuration describing the validation matrix."""

    timestamps: Sequence[str]
    bodies: Sequence[str]
    tolerances: Mapping[str, ToleranceBand] = field(default_factory=dict)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def sorted_timestamps(self) -> list[str]:
        return sorted(self.timestamps)

    def sorted_bodies(self) -> list[str]:
        return sorted({body.lower(): body for body in self.bodies}.values())

    def tolerance_for(self, body: str) -> ToleranceBand | None:
        key = body.lower()
        if key in self.tolerances:
            return self.tolerances[key]
        return self.tolerances.get("default")


@dataclass(frozen=True)
class AdapterMatrix:
    """Mapping of adapter names to instances with optional reference."""

    adapters: Mapping[str, EphemerisAdapter]
    reference: str | None = None

    def reference_name(self) -> str:
        if not self.adapters:
            raise ValueError("at least one adapter is required")
        if self.reference is not None:
            if self.reference not in self.adapters:
                raise KeyError(f"reference adapter '{self.reference}' missing")
            return self.reference
        return sorted(self.adapters)[0]

    def ordered_names(self) -> list[str]:
        return sorted(self.adapters)


@dataclass
class DeltaSample:
    """Single body/timestamp comparison against the reference adapter."""

    timestamp: str
    body: str
    adapter: str
    lon_arcsec: float | None
    decl_arcsec: float | None
    speed_lon_arcsec_per_hour: float | None
    tolerance_lon_arcsec: float | None
    tolerance_decl_arcsec: float | None
    lon_violation: bool
    decl_violation: bool


@dataclass
class AdapterReport:
    """Aggregated statistics for a non-reference adapter."""

    adapter: str
    sample_count: int
    lon_stats: Mapping[str, float]
    decl_stats: Mapping[str, float]
    breaches: list[DeltaSample]


@dataclass
class MatrixResult:
    """Outcome of :func:`run_matrix`."""

    reference: str
    matrix: MatrixConfig
    metadata: Mapping[str, object]
    adapters: list[AdapterReport]
    samples: list[DeltaSample]


def _wrap_angle_diff_deg(deg_a: float, deg_b: float) -> float:
    """Return signed difference in degrees within [-180, 180)."""

    diff = (deg_a - deg_b + 180.0) % 360.0 - 180.0
    return diff


def _deg_to_arcsec(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 3600.0


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires non-empty values")
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    k = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return ordered[int(k)]
    weight = k - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _stats(values: Sequence[float]) -> Mapping[str, float]:
    if not values:
        return {}
    absolute = [abs(v) for v in values]
    return {
        "mean": statistics.fmean(absolute),
        "median": statistics.median(absolute),
        "p95": _percentile(absolute, 95.0),
        "p99": _percentile(absolute, 99.0),
        "max": max(absolute),
    }


def _detect_violation(sample: DeltaSample) -> bool:
    lon_exceeds = (
        sample.lon_arcsec is not None
        and sample.tolerance_lon_arcsec is not None
        and abs(sample.lon_arcsec) > sample.tolerance_lon_arcsec
    )
    decl_exceeds = (
        sample.decl_arcsec is not None
        and sample.tolerance_decl_arcsec is not None
        and abs(sample.decl_arcsec) > sample.tolerance_decl_arcsec
    )
    object.__setattr__(sample, "lon_violation", lon_exceeds)
    object.__setattr__(sample, "decl_violation", decl_exceeds)
    return lon_exceeds or decl_exceeds


def run_matrix(matrix: AdapterMatrix, config: MatrixConfig) -> MatrixResult:
    """Execute the comparison matrix and return aggregated results."""

    if len(matrix.adapters) < 2:
        raise ValueError("at least two adapters are required for comparison")

    reference_name = matrix.reference_name()
    ref_adapter = matrix.adapters[reference_name]
    comparisons = [name for name in matrix.ordered_names() if name != reference_name]

    timestamps = config.sorted_timestamps()
    bodies = config.sorted_bodies()

    LOG.info(
        "running_cross_engine_matrix",
        extra={
            "event": "qa_cross_engine_start",
            "reference": reference_name,
            "adapters": comparisons,
            "timestamp_count": len(timestamps),
            "body_count": len(bodies),
        },
    )

    reference_positions: dict[str, Mapping[str, Mapping[str, float]]] = {}
    for ts in timestamps:
        reference_positions[ts] = ref_adapter.positions_ecliptic(ts, bodies)

    samples: list[DeltaSample] = []
    breaches: dict[str, list[DeltaSample]] = defaultdict(list)

    for adapter_name in comparisons:
        adapter = matrix.adapters[adapter_name]
        for ts in timestamps:
            subject_positions = adapter.positions_ecliptic(ts, bodies)
            ref_positions = reference_positions[ts]
            for body in bodies:
                reference_data = ref_positions.get(body)
                subject_data = subject_positions.get(body)
                if not reference_data or not subject_data:
                    LOG.warning(
                        "body_missing_from_provider",
                        extra={
                            "event": "qa_cross_engine_missing_body",
                            "adapter": adapter_name,
                            "body": body,
                            "timestamp": ts,
                        },
                    )
                    continue

                lon_diff_arcsec = _deg_to_arcsec(
                    _wrap_angle_diff_deg(subject_data.get("lon", 0.0), reference_data.get("lon", 0.0))
                )
                decl_diff_arcsec = None
                if "decl" in subject_data and "decl" in reference_data:
                    decl_diff_arcsec = _deg_to_arcsec(
                        subject_data["decl"] - reference_data["decl"]
                    )

                speed_diff_arcsec_per_hour = None
                if "speed_lon" in subject_data and "speed_lon" in reference_data:
                    speed_diff_arcsec_per_hour = _deg_to_arcsec(
                        subject_data["speed_lon"] - reference_data["speed_lon"]
                    )

                tolerance = config.tolerance_for(body)
                sample = DeltaSample(
                    timestamp=ts,
                    body=body,
                    adapter=adapter_name,
                    lon_arcsec=lon_diff_arcsec,
                    decl_arcsec=decl_diff_arcsec,
                    speed_lon_arcsec_per_hour=speed_diff_arcsec_per_hour,
                    tolerance_lon_arcsec=tolerance.lon_arcsec if tolerance else None,
                    tolerance_decl_arcsec=tolerance.decl_arcsec if tolerance else None,
                    lon_violation=False,
                    decl_violation=False,
                )
                if _detect_violation(sample):
                    breaches[adapter_name].append(sample)
                samples.append(sample)

    adapter_reports: list[AdapterReport] = []
    metadata = {
        "run_started": datetime.now(tz=UTC).isoformat(),
        **config.metadata,
    }

    for adapter_name in comparisons:
        adapter_samples = [s for s in samples if s.adapter == adapter_name]
        lon_values = [s.lon_arcsec for s in adapter_samples if s.lon_arcsec is not None]
        decl_values = [s.decl_arcsec for s in adapter_samples if s.decl_arcsec is not None]
        adapter_reports.append(
            AdapterReport(
                adapter=adapter_name,
                sample_count=len(adapter_samples),
                lon_stats=_stats(lon_values),
                decl_stats=_stats(decl_values),
                breaches=breaches.get(adapter_name, []),
            )
        )

    LOG.info(
        "completed_cross_engine_matrix",
        extra={
            "event": "qa_cross_engine_complete",
            "reference": reference_name,
            "adapters": comparisons,
        },
    )

    return MatrixResult(
        reference=reference_name,
        matrix=config,
        metadata=metadata,
        adapters=adapter_reports,
        samples=samples,
    )


def write_report_json(result: MatrixResult, path: Path) -> None:
    """Persist a :class:`MatrixResult` as JSON for CI artifacts."""

    def serialize_sample(sample: DeltaSample) -> dict[str, object]:
        return {
            "timestamp": sample.timestamp,
            "body": sample.body,
            "adapter": sample.adapter,
            "lon_arcsec": sample.lon_arcsec,
            "decl_arcsec": sample.decl_arcsec,
            "speed_lon_arcsec_per_hour": sample.speed_lon_arcsec_per_hour,
            "tolerance_lon_arcsec": sample.tolerance_lon_arcsec,
            "tolerance_decl_arcsec": sample.tolerance_decl_arcsec,
            "lon_violation": sample.lon_violation,
            "decl_violation": sample.decl_violation,
        }

    payload = {
        "reference": result.reference,
        "metadata": result.metadata,
        "matrix": {
            "timestamps": list(result.matrix.timestamps),
            "bodies": list(result.matrix.bodies),
            "tolerances": {
                key: {
                    "lon_arcsec": band.lon_arcsec,
                    "decl_arcsec": band.decl_arcsec,
                }
                for key, band in result.matrix.tolerances.items()
            },
            "metadata": dict(result.matrix.metadata),
        },
        "adapters": [
            {
                "adapter": report.adapter,
                "sample_count": report.sample_count,
                "lon_stats": dict(report.lon_stats),
                "decl_stats": dict(report.decl_stats),
                "breaches": [serialize_sample(sample) for sample in report.breaches],
            }
            for report in result.adapters
        ],
        "samples": [serialize_sample(sample) for sample in result.samples],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def render_markdown(result: MatrixResult, path: Path) -> None:
    """Render a summary Markdown report for human inspection."""

    lines = [
        f"# Cross-Engine Validation Report",
        "",
        f"Reference adapter: `{result.reference}`",
        "",
        "## Configuration",
        "",
    ]
    lines.append("| Timestamp | Bodies |")
    lines.append("| --- | --- |")
    for ts in result.matrix.sorted_timestamps():
        lines.append(f"| {ts} | {', '.join(result.matrix.sorted_bodies())} |")
    lines.append("")

    lines.append("## Adapter Statistics")
    lines.append("")
    lines.append("| Adapter | Samples | lon mean (\") | lon p99 (\") | lon max (\") | decl p99 (\") | Breaches |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for report in result.adapters:
        lon_mean = report.lon_stats.get("mean", float("nan"))
        lon_p99 = report.lon_stats.get("p99", float("nan"))
        lon_max = report.lon_stats.get("max", float("nan"))
        decl_p99 = report.decl_stats.get("p99", float("nan"))
        breach_count = len(report.breaches)
        lines.append(
            "| {adapter} | {samples} | {lon_mean:.3f} | {lon_p99:.3f} | {lon_max:.3f} | {decl_p99:.3f} | {breach_count} |".format(
                adapter=report.adapter,
                samples=report.sample_count,
                lon_mean=lon_mean,
                lon_p99=lon_p99,
                lon_max=lon_max,
                decl_p99=decl_p99,
                breach_count=breach_count,
            )
        )
    lines.append("")

    if result.samples:
        lines.append("## Violations")
        lines.append("")
        lines.append("| Adapter | Body | Timestamp | Δλ (\") | Δβ (\") | lon tol (\") | decl tol (\") |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: |")
        for report in result.adapters:
            for sample in report.breaches:
                lines.append(
                    "| {adapter} | {body} | {ts} | {lon:.3f} | {decl:.3f} | {lon_tol:.3f} | {decl_tol:.3f} |".format(
                        adapter=report.adapter,
                        body=sample.body,
                        ts=sample.timestamp,
                        lon=sample.lon_arcsec or 0.0,
                        decl=sample.decl_arcsec or 0.0,
                        lon_tol=sample.tolerance_lon_arcsec or 0.0,
                        decl_tol=sample.tolerance_decl_arcsec or 0.0,
                    )
                )
        lines.append("")

    path.write_text("\n".join(lines))


def load_default_adapters(names: Sequence[str]) -> AdapterMatrix:
    """Attempt to instantiate well-known providers by name."""

    adapters: dict[str, EphemerisAdapter] = {}
    for name in names:
        if name.lower() == "skyfield":
            try:
                from astroengine.providers.skyfield_provider import SkyfieldProvider

                adapters[name] = SkyfieldProvider()
            except Exception as exc:  # pragma: no cover - depends on environment
                LOG.warning(
                    "skyfield_adapter_unavailable",
                    exc_info=exc,
                    extra={"event": "qa_cross_engine_adapter_unavailable", "adapter": name},
                )
        elif name.lower() in {"swiss", "swisseph"}:
            try:
                from astroengine.providers.swiss_provider import SwissProvider

                adapters[name] = SwissProvider()
            except Exception as exc:  # pragma: no cover - depends on environment
                LOG.warning(
                    "swiss_adapter_unavailable",
                    exc_info=exc,
                    extra={"event": "qa_cross_engine_adapter_unavailable", "adapter": name},
                )
        else:
            LOG.warning(
                "unknown_adapter_requested",
                extra={"event": "qa_cross_engine_unknown_adapter", "adapter": name},
            )
    return AdapterMatrix(adapters=adapters)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by CI scripts."""

    import argparse

    parser = argparse.ArgumentParser(description="Run cross-engine QA matrix")
    parser.add_argument(
        "--adapter",
        dest="adapters",
        action="append",
        default=["skyfield", "swiss"],
        help="Adapter names to compare (default: skyfield, swiss)",
    )
    parser.add_argument(
        "--timestamp",
        dest="timestamps",
        action="append",
        default=["2000-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
        help="UTC timestamp in ISO 8601 format (repeatable)",
    )
    parser.add_argument(
        "--body",
        dest="bodies",
        action="append",
        default=["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"],
        help="Body name to include (repeatable)",
    )
    parser.add_argument(
        "--report-dir",
        dest="report_dir",
        default="qa/artifacts",
        help="Directory to store generated reports",
    )
    args = parser.parse_args(argv)

    adapter_matrix = load_default_adapters(args.adapters)
    if len(adapter_matrix.adapters) < 2:
        parser.error("At least two adapters must be available to run the matrix")

    tolerances: dict[str, ToleranceBand] = {
        "sun": ToleranceBand(lon_arcsec=2.0),
        "moon": ToleranceBand(lon_arcsec=5.0, decl_arcsec=5.0),
        "mercury": ToleranceBand(lon_arcsec=2.0),
        "venus": ToleranceBand(lon_arcsec=2.0),
        "mars": ToleranceBand(lon_arcsec=5.0),
        "jupiter": ToleranceBand(lon_arcsec=5.0),
        "saturn": ToleranceBand(lon_arcsec=5.0),
        "default": ToleranceBand(lon_arcsec=5.0),
    }
    config = MatrixConfig(
        timestamps=args.timestamps,
        bodies=args.bodies,
        tolerances=tolerances,
        metadata={"source": "cli"},
    )

    result = run_matrix(adapter_matrix, config)

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    write_report_json(result, report_dir / "cross_engine.json")
    render_markdown(result, report_dir / "cross_engine.md")

    if any(report.breaches for report in result.adapters):
        LOG.error("cross_engine_validation_failed")
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
