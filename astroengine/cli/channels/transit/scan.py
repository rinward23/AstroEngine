"""Transit scanning command plumbing for the modular CLI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

from ....app_api import canonicalize_events, run_scan_or_raise
from ....detectors.common import enable_cache
from ....exporters_ics import write_ics_canonical
from ....utils import DEFAULT_TARGET_FRAMES, DETECTOR_NAMES, available_frames
from ..._compat import cli_legacy_missing_reason
from ..transit.common import (
    DEFAULT_MOVING_BODIES,
    canonical_events_to_dicts,
    format_event_table,
    normalize_detectors,
    resolve_targets_cli,
    serialize_events_to_json,
    set_engine_detector_flags,
)
from ..transit.exports import (
    add_canonical_export_args,
    export_canonical_datasets,
    write_parquet_canonical,
    write_sqlite_canonical,
)

_ACCURACY_TO_STEP: dict[str, int] = {"fast": 120, "default": 60, "high": 15}


def _add_base_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument(
        "--start",
        "--start-utc",
        dest="start_utc",
        required=True,
        help="Start time (ISO-8601, UTC)",
    )
    parser.add_argument(
        "--end",
        "--end-utc",
        dest="end_utc",
        required=True,
        help="End time (ISO-8601, UTC)",
    )
    parser.add_argument(
        "--bodies",
        "--moving",
        dest="moving",
        nargs="+",
        help="Transiting bodies to scan (defaults to canonical moving bodies)",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        help="Target bodies or qualified identifiers (e.g. natal:Sun)",
    )
    parser.add_argument(
        "--target-frame",
        "--frame",
        dest="target_frames",
        action="append",
        choices=available_frames(),
        help="Frame to prefix targets (repeatable)",
    )
    parser.add_argument(
        "--detector",
        "--detectors",
        dest="detectors",
        action="append",
        choices=sorted(DETECTOR_NAMES),
        help="Enable optional detectors (repeatable; use 'all' for every toggle)",
    )
    parser.add_argument(
        "--entrypoint",
        action="append",
        help="Explicit scan entrypoint module:function (repeatable)",
    )
    parser.add_argument(
        "--provider",
        default="auto",
        help="Ephemeris provider (auto, swiss, pymeeus, skyfield)",
    )
    parser.add_argument(
        "--profile",
        help="Profile identifier to annotate export metadata",
    )
    parser.add_argument(
        "--step-minutes",
        type=int,
        default=60,
        help="Sampling cadence in minutes (default: %(default)s)",
    )
    parser.add_argument(
        "--accuracy-budget",
        choices=tuple(_ACCURACY_TO_STEP),
        help="Preset cadence (fast=120m, default=60m, high=15m)",
    )
    parser.add_argument("--json", help="Write scan payload to this JSON file")
    parser.add_argument("--export-json", help="Write canonical events to a JSON file")
    parser.add_argument("--export-sqlite", help="Write canonical events to a SQLite file")
    parser.add_argument(
        "--export-parquet", help="Write canonical events to a Parquet dataset"
    )
    parser.add_argument("--export-ics", help="Write canonical events to an ICS calendar file")
    parser.add_argument(
        "--ics-title",
        default="AstroEngine Events",
        help="Calendar title when exporting ICS",
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Enable Swiss longitude caching when available",
    )
    parser.add_argument(
        "--sidereal",
        dest="sidereal",
        action="store_true",
        help="Use sidereal zodiac settings for this scan",
    )
    parser.add_argument(
        "--tropical",
        dest="sidereal",
        action="store_false",
        help="Force tropical zodiac for this scan",
    )
    parser.set_defaults(sidereal=None)
    parser.add_argument(
        "--ayanamsha",
        help="Sidereal ayanāṁśa to apply when sidereal mode is enabled",
    )


def add_subparser(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``scan`` subcommand."""

    parser = sub.add_parser(
        "scan",
        help="Scan transits/events over a time range",
        description="Run the canonical AstroEngine transit scanner.",
    )
    _add_base_arguments(parser)
    add_canonical_export_args(parser)
    parser.set_defaults(func=run)


def _accuracy_step_minutes(args: argparse.Namespace) -> int:
    if getattr(args, "accuracy_budget", None):
        return _ACCURACY_TO_STEP[args.accuracy_budget]
    return getattr(args, "step_minutes", 60)


def _collect_entrypoints(raw: Iterable[str] | None) -> list[str]:
    entrypoints: list[str] = []
    for token in raw or []:
        cleaned = str(token).strip()
        if cleaned:
            entrypoints.append(cleaned)
    return entrypoints


def run(args: argparse.Namespace) -> int:
    """Execute the scan subcommand."""

    if not getattr(args, "start_utc", None) or not getattr(args, "end_utc", None):
        print("scan: --start-utc and --end-utc are required", file=sys.stderr)
        return 1

    detectors = normalize_detectors(getattr(args, "detectors", None))
    set_engine_detector_flags(detectors)

    moving = list(dict.fromkeys(args.moving or DEFAULT_MOVING_BODIES))
    frame_selection = list(dict.fromkeys(args.target_frames or []))
    if not frame_selection:
        frame_selection = list(DEFAULT_TARGET_FRAMES)
    targets = resolve_targets_cli(args.targets, frame_selection)

    entrypoints = _collect_entrypoints(getattr(args, "entrypoint", None))

    if getattr(args, "cache", False):
        enable_cache(True)

    provider = args.provider
    if provider == "auto":
        provider = None

    step_minutes = _accuracy_step_minutes(args)

    try:
        result = run_scan_or_raise(
            start_utc=args.start_utc,
            end_utc=args.end_utc,
            moving=moving,
            targets=targets,
            provider=provider,
            profile_id=getattr(args, "profile", None),
            step_minutes=step_minutes,
            detectors=detectors,
            target_frames=frame_selection,
            sidereal=args.sidereal if args.sidereal is not None else None,
            ayanamsha=args.ayanamsha or None,
            entrypoints=entrypoints or None,
            return_used_entrypoint=True,
        )
    except RuntimeError as exc:  # pragma: no cover - surfaces in CLI usage
        reason = cli_legacy_missing_reason()
        if reason:
            print(reason, file=sys.stderr)
        print(f"Scan failed: {exc}", file=sys.stderr)
        return 1

    raw_events, used_entrypoint = result
    canonical_events = canonicalize_events(raw_events)
    records = canonical_events_to_dicts(canonical_events)

    if args.export_json:
        try:
            path = Path(args.export_json)
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"JSON export complete: {path} ({len(records)} events)")
        except Exception as exc:  # pragma: no cover - surface for CLI usage
            print(f"JSON export failed ({exc})", file=sys.stderr)

    if args.export_sqlite:
        try:
            rows = write_sqlite_canonical(args.export_sqlite, canonical_events)
            print(f"SQLite export complete: {args.export_sqlite} ({rows} rows)")
        except Exception as exc:  # pragma: no cover - dataset I/O issues
            print(f"SQLite export failed ({exc})", file=sys.stderr)

    if args.export_parquet:
        try:
            rows = write_parquet_canonical(args.export_parquet, canonical_events)
            print(f"Parquet export complete: {args.export_parquet} ({rows} rows)")
        except Exception as exc:  # pragma: no cover
            print(f"Parquet export failed ({exc})", file=sys.stderr)

    if args.export_ics:
        try:
            rows = write_ics_canonical(
                args.export_ics,
                canonical_events,
                calendar_name=args.ics_title or "AstroEngine Events",
            )
            print(f"ICS export complete: {args.export_ics} ({rows} events)")
        except Exception as exc:  # pragma: no cover - ICS I/O issues
            print(f"ICS export failed ({exc})", file=sys.stderr)

    # Canonical dataset exports (--sqlite/--parquet) share the same helper.
    canonical_written = export_canonical_datasets(args, canonical_events)
    if canonical_written.get("sqlite"):
        print(
            f"SQLite export complete: {args.sqlite} ({canonical_written['sqlite']} rows)"
        )
    if canonical_written.get("parquet"):
        print(
            f"Parquet export complete: {args.parquet} ({canonical_written['parquet']} rows)"
        )

    table = format_event_table(canonical_events)
    module_name, func_name = used_entrypoint
    print(f"Scan entrypoint: {module_name}.{func_name}")
    print(f"Detected {len(canonical_events)} events")
    if detectors:
        print("Detectors:", ", ".join(detectors))
    if table:
        print(table)
    elif not canonical_events:
        print("No events detected for the provided window.")

    if not any(
        [
            args.export_json,
            args.export_sqlite,
            args.export_parquet,
            args.export_ics,
            args.sqlite,
            args.parquet,
        ]
    ):
        print(serialize_events_to_json(canonical_events))

    return 0


__all__ = ["add_subparser", "run"]
