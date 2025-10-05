"""Transit scanning command plumbing for the modular CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Dict

from ._compat import cli_legacy_missing_reason, try_import_cli_legacy
from ..utils import DETECTOR_NAMES, available_frames

_ACCURACY_TO_STEP: Dict[str, int] = {"fast": 120, "default": 60, "high": 15}


def add_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``scan`` subcommand."""

    parser = sub.add_parser(
        "scan",
        help="Scan transits/events over a time range",
        description="Run the canonical AstroEngine transit scanner.",
    )
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
    parser.add_argument("--export-parquet", help="Write canonical events to a Parquet dataset")
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

    legacy_module = try_import_cli_legacy()
    if legacy_module is None:
        reason = cli_legacy_missing_reason()
        parser.description += "\n\nUnavailable: {reason}".format(reason=reason)
        parser.set_defaults(func=_legacy_scan_unavailable, _cli_error=reason)
        return

    legacy_module.add_canonical_export_args(parser)
    parser.set_defaults(func=run, profile=None, _cli_legacy=legacy_module)


def run(args: argparse.Namespace) -> int:
    """Execute the scan subcommand via the legacy implementation."""

    legacy_module = getattr(args, "_cli_legacy")

    accuracy = getattr(args, "accuracy_budget", None)
    if accuracy:
        args.step_minutes = _ACCURACY_TO_STEP[accuracy]

    if getattr(args, "moving", None) is None:
        args.moving = list(legacy_module.DEFAULT_MOVING_BODIES)

    if not hasattr(args, "profile"):
        args.profile = None

    return legacy_module.cmd_scan(args)


def _legacy_scan_unavailable(args: argparse.Namespace) -> int:
    reason = getattr(args, "_cli_error", cli_legacy_missing_reason())
    message = reason or "Transit scanning requires pyswisseph"
    print(message, file=sys.stderr)
    return 2
