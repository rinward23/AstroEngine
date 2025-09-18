"""Command line helpers for AstroEngine."""

from __future__ import annotations

import argparse
import json
from typing import Any, Mapping, Sequence

from .engine import assemble_transit_event, event_to_mapping


# >>> AUTO-GEN BEGIN: CLI Domain Scorer Flags v1.1


def _add_domain_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--emit-domains",
        action="store_true",
        help="Include elements/domains on each TransitEvent.",
    )
    parser.add_argument(
        "--domain-profile",
        default="vca_neutral",
        help="Domain profile key (see VCA_DOMAIN_PROFILES).",
    )
    parser.add_argument(
        "--domain-scorer",
        default="weighted",
        choices=["weighted", "top", "softmax"],
        help="Method to transform domains into a severity multiplier.",
    )
    parser.add_argument(
        "--domain-temperature",
        type=float,
        default=8.0,
        help="Softmax temperature (only used when --domain-scorer=softmax).",
    )


# >>> AUTO-GEN END: CLI Domain Scorer Flags v1.1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assemble AstroEngine transit events")
    parser.add_argument("--sign-index", type=int, help="Zodiac index (0=Aries)")
    parser.add_argument("--planet-key", help="Canonical planet identifier")
    parser.add_argument("--house-index", type=int, help="House index (1-12)")
    parser.add_argument("--severity", type=float, default=None, help="Base severity value")
    _add_domain_args(parser)
    return parser


def _ctx_from_args(namespace: argparse.Namespace) -> Mapping[str, Any]:
    ctx: dict[str, Any] = {
        "sign_index": namespace.sign_index,
        "planet_key": namespace.planet_key,
        "house_index": namespace.house_index,
        "severity": namespace.severity,
        "emit_domains": namespace.emit_domains,
    }
    if namespace.emit_domains:
        ctx["domain_profile"] = namespace.domain_profile
        ctx["domain_scorer"] = namespace.domain_scorer
        ctx["domain_temperature"] = namespace.domain_temperature
    return ctx


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ctx = _ctx_from_args(args)
    event = assemble_transit_event(ctx)
    payload = event_to_mapping(event)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


__all__ = ["build_parser", "main", "_add_domain_args"]

