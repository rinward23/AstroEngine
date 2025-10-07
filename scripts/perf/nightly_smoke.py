"""Deterministic nightly benchmarks for electional and forecast workflows."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.config.settings import Settings
from astroengine.electional import ElectionalSearchParams, search_constraints
from astroengine.forecast.stack import (
    ForecastChart,
    ForecastWindow,
    build_forecast_stack,
)

HISTORY_DEFAULT = Path("observability/trends/nightly-metrics.json")
ELECTIONAL_SEED = 1729
FORECAST_SEED = 2718


def _ensure_ephemeris() -> Path:
    env_path = os.environ.get("SE_EPHE_PATH")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate
    repo_root = Path(__file__).resolve().parents[2]
    fallback = repo_root / "datasets" / "swisseph_stub"
    if not fallback.exists():
        raise RuntimeError("Swiss ephemeris dataset is required for nightly benchmarks.")
    os.environ["SE_EPHE_PATH"] = str(fallback)
    return fallback


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _run_electional(seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    base = datetime(2024, 3, 20, 12, tzinfo=UTC)
    start = base + timedelta(days=rng.randint(0, 30))
    end = start + timedelta(hours=48)
    latitude = rng.uniform(-45.0, 45.0)
    longitude = rng.uniform(-90.0, 90.0)
    params = ElectionalSearchParams(
        start=start,
        end=end,
        step_minutes=30,
        constraints=[
            {
                "aspect": {
                    "body": "venus",
                    "target": "asc",
                    "type": "trine",
                    "max_orb": 3.5,
                }
            },
            {"moon": {"void_of_course": False, "max_orb": 6.0}},
            {"malefic_to_angles": {"allow": False, "max_orb": 4.0}},
        ],
        latitude=latitude,
        longitude=longitude,
        limit=10,
    )
    started = time.perf_counter()
    results = search_constraints(params)
    duration = time.perf_counter() - started
    summary: dict[str, Any] = {
        "duration_seconds": round(duration, 6),
        "candidates": len(results),
        "window_start": _iso(start),
        "window_end": _iso(end),
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
    }
    if results:
        best = max(results, key=lambda item: item.score)
        summary["best"] = {
            "timestamp": _iso(best.ts),
            "score": round(float(best.score), 6),
        }
    return summary


def _run_forecast(seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    natal_moment = datetime(1993, 7, 11, 6, tzinfo=UTC) + timedelta(days=rng.randint(0, 365))
    location = ChartLocation(
        latitude=rng.uniform(-35.0, 55.0), longitude=rng.uniform(-100.0, 120.0)
    )
    natal_chart = compute_natal_chart(natal_moment, location)
    window = ForecastWindow(
        start=natal_moment,
        end=natal_moment + timedelta(days=365),
    )
    settings = Settings()
    started = time.perf_counter()
    events = build_forecast_stack(settings, ForecastChart(natal_chart=natal_chart, window=window))
    duration = time.perf_counter() - started
    summary: dict[str, Any] = {
        "duration_seconds": round(duration, 6),
        "events": len(events),
        "window_start": _iso(window.start),
        "window_end": _iso(window.end),
    }
    if events:
        first = events[0]
        summary["first_event"] = {
            "start": first["start"],
            "end": first["end"],
            "body": first["body"],
            "aspect": first["aspect"],
            "technique": first["technique"],
        }
    return summary


def _load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        records: list[dict[str, Any]] = []
        for entry in data:
            if isinstance(entry, dict):
                records.append({str(k): v for k, v in entry.items()})
        return records
    return []


def _write_history(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=HISTORY_DEFAULT,
        help="Path to the trend history JSON file.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=60,
        help="Retain the most recent N benchmark entries (default: 60).",
    )
    args = parser.parse_args()

    _ensure_ephemeris()

    electional_summary = _run_electional(ELECTIONAL_SEED)
    forecast_summary = _run_forecast(FORECAST_SEED)

    record = {
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "electional": electional_summary,
        "forecast": forecast_summary,
    }

    history = _load_history(args.output)
    history.append(record)
    if args.history_limit > 0:
        history = history[-args.history_limit :]
    _write_history(args.output, history)

    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
