"""Diagnostics command integration for the modular CLI."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from typing import Any

from .. import diagnostics as diag


def add_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``diagnose`` subcommand."""

    parser = sub.add_parser(
        "diagnose",
        help="Environment & ephemeris diagnostics",
        description=(
            "Inspect local environment configuration, verify optional dependencies, "
            "and optionally run a Swiss Ephemeris smoketest."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures when computing the exit status",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include environment metadata in the diagnostic report",
    )
    parser.add_argument(
        "--smoketest",
        metavar="ISO_UTC",
        nargs="?",
        const="now",
        help="Run a Sun..Saturn Swiss Ephemeris smoketest for the given timestamp",
    )
    parser.set_defaults(func=run)


def _append_environment(payload: dict[str, Any]) -> None:
    payload["environment"] = {
        "SE_EPHE_PATH": os.getenv("SE_EPHE_PATH"),
        "ENV": os.getenv("ENV"),
        "PWD": os.getcwd(),
    }


def run(args: argparse.Namespace) -> int:
    """Execute the diagnose subcommand."""

    payload = diag.collect_diagnostics(strict=args.strict)

    if args.verbose:
        _append_environment(payload)

    smoketest_rows = None
    smoketest_iso = None
    if args.smoketest is not None:
        smoketest_iso = args.smoketest
        if smoketest_iso == "now":
            smoketest_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        smoketest_rows = diag.smoketest_positions(smoketest_iso)
        payload["smoketest"] = {"timestamp": smoketest_iso, "rows": smoketest_rows}

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(diag._format_text_report(payload))
        if args.verbose:
            env = payload.get("environment", {})
            if env:
                print("\nEnvironment:")
                for key, value in env.items():
                    resolved = value if value is not None else "<unset>"
                    print(f"  {key}={resolved}")
        if smoketest_rows is not None:
            print(f"\nSmoketest — {smoketest_iso}")
            for row in smoketest_rows:
                if {"body", "lon_deg", "lat_deg", "dist_au"}.issubset(row):
                    print(
                        "  {body:8} λ={lon_deg:9.5f}°  β={lat_deg:8.5f}°  Δ={dist_au:.6f} au".format(
                            **row
                        )
                    )
                else:
                    detail = row.get("detail") or row
                    print(f"  {row.get('body', 'INFO')}: {detail}")

    return int(payload.get("summary", {}).get("exit_code", 0))
