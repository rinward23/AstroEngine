"""Command line interface for AstroEngine."""

from __future__ import annotations

from typing import Any, Dict, Sequence

__all__ = ["_add_domain_args", "build_runtime_context", "parse_args", "main"]


# >>> AUTO-GEN BEGIN: CLI Domain Flags v1.0
import argparse


def _add_domain_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--emit-domains", action="store_true", help="Include elements/domains on each TransitEvent.")
    p.add_argument(
        "--domain-profile", default="vca_neutral", help="Domain profile key (see VCA_DOMAIN_PROFILES)."
    )


# In main():
# parser = argparse.ArgumentParser(...)
# _add_domain_args(parser)
# args = parser.parse_args()
# pass args to engine context as ctx["domain_profile"] = args.domain_profile when args.emit_domains is True
# >>> AUTO-GEN END: CLI Domain Flags v1.0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the AstroEngine CLI."""

    parser = argparse.ArgumentParser(description="AstroEngine runtime controller")
    _add_domain_args(parser)
    return parser.parse_args(argv)


def build_runtime_context(args: argparse.Namespace) -> Dict[str, Any]:
    """Convert parsed arguments into an engine runtime context."""

    context: Dict[str, Any] = {"emit_domains": bool(args.emit_domains)}
    if args.emit_domains:
        context["domain_profile"] = args.domain_profile
    return context


def main(argv: Sequence[str] | None = None) -> Dict[str, Any]:
    """Entry point for ``python -m astroengine.cli``."""

    args = parse_args(argv)
    return build_runtime_context(args)
