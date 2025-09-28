"""Execute cookbook notebooks and optionally refresh fixtures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import nbformat
from nbclient import NotebookClient

SCRIPT_PATH = Path(__file__).resolve()
DOCS_SITE_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.ephemeris.swisseph_adapter import SwissEphemerisAdapter
from astroengine.synastry.orchestrator import compute_synastry
from astroengine.core.transit_engine import scan_transits
from core.interpret_plus.engine import interpret, load_rules
from astroengine.core.rel_plus.composite import (
    composite_midpoint_positions,
    davison_positions as rel_davison_positions,
)

FIXTURE_EVENTS = [
    {
        "id": "subject",
        "name": "Alex",
        "ts": "1990-07-11T08:00:00Z",
        "lat": 40.7128,
        "lon": -74.0060,
        "tz": "America/New_York",
        "place": "New York, NY",
    },
    {
        "id": "partner",
        "name": "Riley",
        "ts": "1992-03-15T20:15:00Z",
        "lat": 34.0522,
        "lon": -118.2437,
        "tz": "America/Los_Angeles",
        "place": "Los Angeles, CA",
    },
]

SE_PATH = (REPO_ROOT / "datasets" / "swisseph_stub").resolve()


def _as_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_fixtures(fixtures_dir: Path) -> None:
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SE_EPHE_PATH", str(SE_PATH))

    adapter = SwissEphemerisAdapter()

    # Birth events CSV
    csv_path = fixtures_dir / "birth_events.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "name", "ts", "lat", "lon", "tz", "place"],
        )
        writer.writeheader()
        for event in FIXTURE_EVENTS:
            writer.writerow(event)

    position_payloads: dict[str, dict[str, dict[str, float]]] = {}
    for event in FIXTURE_EVENTS:
        moment = _as_dt(event["ts"])
        loc = ChartLocation(latitude=event["lat"], longitude=event["lon"])
        chart = compute_natal_chart(moment, loc, adapter=adapter)
        positions = {
            name: {
                "longitude": data.longitude,
                "latitude": data.latitude,
                "distance_au": data.distance_au,
            }
            for name, data in chart.positions.items()
        }
        path = fixtures_dir / f"positions_{event['id']}.json"
        _write_json(path, positions)
        position_payloads[event["id"]] = positions

    comp = composite_midpoint_positions(
        {k: v["longitude"] for k, v in position_payloads["subject"].items()},
        {k: v["longitude"] for k, v in position_payloads["partner"].items()},
        ["Sun", "Moon", "Mercury", "Venus", "Mars"],
    )
    _write_json(fixtures_dir / "composite_midpoints.json", comp)

    def _provider(when: datetime) -> dict[str, float]:
        chart = compute_natal_chart(
            when,
            ChartLocation(latitude=0.0, longitude=0.0),
            adapter=adapter,
        )
        return {name: pos.longitude for name, pos in chart.positions.items()}

    davison = rel_davison_positions(
        ["Sun", "Moon", "Mercury", "Venus", "Mars"],
        _as_dt(FIXTURE_EVENTS[0]["ts"]),
        _as_dt(FIXTURE_EVENTS[1]["ts"]),
        _provider,
        lat_a=FIXTURE_EVENTS[0]["lat"],
        lon_a=FIXTURE_EVENTS[0]["lon"],
        lat_b=FIXTURE_EVENTS[1]["lat"],
        lon_b=FIXTURE_EVENTS[1]["lon"],
    )
    _write_json(fixtures_dir / "davison_positions.json", davison)

    syn_hits = compute_synastry(
        subject={"ts": FIXTURE_EVENTS[0]["ts"], "lat": FIXTURE_EVENTS[0]["lat"], "lon": FIXTURE_EVENTS[0]["lon"]},
        partner={"ts": FIXTURE_EVENTS[1]["ts"], "lat": FIXTURE_EVENTS[1]["lat"], "lon": FIXTURE_EVENTS[1]["lon"]},
        aspects=[0, 60, 90, 120, 180],
        orb_deg=2.0,
    )
    syn_serialized = [
        {
            "direction": hit.direction,
            "moving": hit.moving,
            "target": hit.target,
            "angle_deg": hit.angle_deg,
            "orb_abs": hit.orb_abs,
            "score": hit.score,
            "domains": hit.domains,
        }
        for hit in syn_hits
    ]
    syn_path = fixtures_dir / "synastry_hits.json"
    _write_json(syn_path, syn_serialized)

    rules_path = DOCS_SITE_ROOT / "docs" / "rulepacks" / "examples" / "basic.yaml"
    rules = load_rules(str(rules_path))
    interpret_payload = {
        "scope": "synastry",
        "hits": [
            {
                "a": item["moving"],
                "b": item["target"],
                "aspect": "conjunction" if item["angle_deg"] == 0 else str(int(item["angle_deg"])),
                "severity": float(item["score"] or 0),
            }
            for item in syn_serialized[:6]
        ],
    }
    findings = interpret(interpret_payload, rules)
    findings_payload = [
        {
            "id": f.id,
            "scope": f.scope,
            "title": f.title,
            "text": f.text,
            "score": f.score,
            "tags": f.tags,
        }
        for f in findings
    ]
    _write_json(fixtures_dir / "interpretations.json", findings_payload)

    # Markdown summary for report
    summary_lines = ["# Relationship Snapshot", "", "## Synastry Overview"]
    summary_lines.append(f"Total hits: {len(syn_serialized)}")
    top = findings_payload[:3]
    if top:
        summary_lines.append("")
        summary_lines.append("### Top Findings")
        for item in top:
            summary_lines.append(f"- **{item['title']}** — {item['text']}")
    (fixtures_dir / "report_markdown.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    # PDF bundle using reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError("reportlab is required for PDF generation") from exc

    pdf_path = fixtures_dir / "report_bundle.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, y, "Relationship Snapshot")
    y -= 36
    c.setFont("Helvetica", 12)
    c.drawString(72, y, f"Generated: {datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()}")
    y -= 24
    c.drawString(72, y, f"Synastry hits: {len(syn_serialized)}")
    y -= 24
    for item in top:
        c.drawString(72, y, f"• {item['title']} — {item['text']}")
        y -= 18
    c.showPage()
    c.save()

    # Timeline events via transit scan
    timeline_hits = scan_transits(
        natal_ts=FIXTURE_EVENTS[0]["ts"],
        start_ts="2024-01-01T00:00:00Z",
        end_ts="2024-03-01T00:00:00Z",
        bodies=["Mars", "Jupiter"],
        targets=["Sun", "Saturn"],
        aspects=["conjunction", "opposition"],
        orb_deg=1.0,
        step_days=2.0,
    )
    timeline_payload = [
        {
            "ts": getattr(hit, "when_iso", None),
            "moving": getattr(hit, "moving", None),
            "target": getattr(hit, "target", None),
            "angle_deg": getattr(hit, "angle_deg", None),
            "orb_abs": getattr(hit, "orb_abs", None),
            "family": getattr(hit, "family", None),
            "kind": getattr(hit, "kind", None),
        }
        for hit in timeline_hits
    ]
    _write_json(fixtures_dir / "timeline_events.json", timeline_payload)

    # Cache timing comparison
    start = time.perf_counter()
    scan_transits(
        natal_ts=FIXTURE_EVENTS[0]["ts"],
        start_ts="2024-01-01T00:00:00Z",
        end_ts="2024-02-01T00:00:00Z",
        bodies=["Mars"],
        targets=["Sun"],
        aspects=["conjunction"],
        orb_deg=1.5,
        step_days=1.0,
    )
    cold_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    scan_transits(
        natal_ts=FIXTURE_EVENTS[0]["ts"],
        start_ts="2024-01-01T00:00:00Z",
        end_ts="2024-02-01T00:00:00Z",
        bodies=["Mars"],
        targets=["Sun"],
        aspects=["conjunction"],
        orb_deg=1.5,
        step_days=1.0,
    )
    warm_ms = (time.perf_counter() - start) * 1000
    _write_json(
        fixtures_dir / "caching_metrics.json",
        {"cold_call_ms": round(cold_ms, 3), "warm_call_ms": round(warm_ms, 3)},
    )

    # Record checksums for transparency
    checksums = {
        path.name: _sha256_bytes(path)
        for path in fixtures_dir.iterdir()
        if path.is_file() and path.suffix in {".json", ".txt", ".pdf", ".csv"}
    }
    _write_json(fixtures_dir / "checksums.json", checksums)


def execute_notebook(path: Path, env: dict[str, str]) -> None:
    nb = nbformat.read(path.open(), as_version=4)
    client = NotebookClient(nb, timeout=600, kernel_name="python3")
    previous = os.environ.copy()
    try:
        os.environ.update(env)
        client.execute(cwd=str(path.parent))
    finally:
        os.environ.clear()
        os.environ.update(previous)
    nbformat.write(nb, path.open("w", encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-fixtures",
        action="store_true",
        help="Regenerate docs/fixtures before executing notebooks.",
    )
    parser.add_argument(
        "--notebooks",
        nargs="*",
        default=sorted((DOCS_SITE_ROOT / "docs" / "cookbook").glob("*.ipynb")),
        help="Specific notebooks to run (default: all in docs/cookbook).",
    )
    args = parser.parse_args()

    fixtures_dir = DOCS_SITE_ROOT / "docs" / "fixtures"
    if args.refresh_fixtures:
        refresh_fixtures(fixtures_dir)

    env = os.environ.copy()
    env.setdefault("ASTROENGINE_ROOT", str(REPO_ROOT))
    env.setdefault("DOCS_SITE_ROOT", str(DOCS_SITE_ROOT))
    env.setdefault("SE_EPHE_PATH", str(SE_PATH))

    notebooks: Iterable[Path]
    if args.notebooks and all(isinstance(item, Path) for item in args.notebooks):
        notebooks = [Path(item) for item in args.notebooks]
    else:
        notebooks = [Path(item) if isinstance(item, Path) else Path(item) for item in args.notebooks]

    for nb_path in notebooks:
        nb_path = nb_path if isinstance(nb_path, Path) else Path(nb_path)
        if not nb_path.exists():
            raise FileNotFoundError(nb_path)
        print(f"[exec] {nb_path}")
        execute_notebook(nb_path, env)


if __name__ == "__main__":
    main()
