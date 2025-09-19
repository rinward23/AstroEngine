"""Command line interface helpers for AstroEngine."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from .api import TransitEvent, TransitScanConfig
from .config import load_profile_json
from .engine import apply_profile_if_any, maybe_attach_domain_fields


def _add_domain_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--emit-domains", action="store_true", help="Include elements/domains on each TransitEvent.")
    p.add_argument("--domain-profile", default="vca_neutral", help="Domain profile key (see VCA_DOMAIN_PROFILES).")
    p.add_argument(
        "--domain-scorer",
        default="weighted",
        choices=["weighted", "top", "softmax"],
        help="Method to transform domains into a severity multiplier.",
    )
    p.add_argument(
        "--domain-temperature",
        type=float,
        default=8.0,
        help="Softmax temperature (only used when --domain-scorer=softmax).",
    )


def _add_profile_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--profile-file", help="Path to profile JSON (e.g., profiles/vca_outline.json)")


def _add_ruleset_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--ruleset", default="vca_core", help="Aspect ruleset id (default: vca_core)")
    p.add_argument("--no-declination", action="store_true", help="Disable declination aspects (parallel/contra-parallel)")
    p.add_argument("--no-mirrors", action="store_true", help="Disable antiscia/contra-antiscia")
    p.add_argument("--no-harmonics", action="store_true", help="Disable harmonic-derived aspects")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine command line interface")
    _add_profile_args(parser)
    _add_domain_args(parser)
    _add_ruleset_args(parser)
    return parser


def _initial_context_from_args(args: argparse.Namespace) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "emit_domains": args.emit_domains,
    }
    if args.emit_domains:
        ctx["domain_profile"] = args.domain_profile
        ctx["domain_scorer"] = args.domain_scorer
        ctx["domain_temperature"] = args.domain_temperature
    return ctx


def main(argv: Sequence[str] | None = None) -> tuple[TransitScanConfig, dict[str, Any]]:
    parser = build_parser()
    args = parser.parse_args(argv)

    scan_config = TransitScanConfig(
        ruleset_id=args.ruleset,
        enable_declination=not args.no_declination,
        enable_mirrors=not args.no_mirrors,
        enable_harmonics=not args.no_harmonics,
    )

    ctx = _initial_context_from_args(args)

    profile = load_profile_json(args.profile_file) if args.profile_file else None
    ctx = apply_profile_if_any(ctx, profile)

    sample_event = maybe_attach_domain_fields(TransitEvent(), ctx)
    _ = sample_event  # placeholder to show integration; real engine would persist or stream events

    return scan_config, ctx


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
