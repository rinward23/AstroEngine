"""Entry point for the modular AstroEngine CLI."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ..boot.logging import configure_logging
from . import codex, diagnose, export, scan
from ._compat import cli_legacy_missing_reason, try_import_cli_legacy


def _add_legacy_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    legacy_parser = sub.add_parser(
        "legacy",
        help="Access the historical monolithic CLI (for backward compatibility)",
        description=(
            "Invoke the previous CLI implementation. All arguments after 'legacy' "
            "are forwarded verbatim to the legacy parser."
        ),
    )
    module = try_import_cli_legacy()
    if module is None:
        reason = cli_legacy_missing_reason()
        legacy_parser.description += f"\n\nUnavailable: {reason}"
        legacy_parser.set_defaults(func=_legacy_unavailable, _cli_error=reason)
    else:
        legacy_parser.add_argument(
            "legacy_args",
            nargs=argparse.REMAINDER,
            metavar="legacy-args",
            help="Arguments passed directly to the legacy CLI",
        )
        legacy_parser.set_defaults(func=_run_legacy)


def _run_legacy(parsed: argparse.Namespace) -> int:
    argv = list(parsed.legacy_args or [])
    if argv and argv[0] == "--":
        argv = argv[1:]
    from .. import cli_legacy

    return cli_legacy.main(argv if argv else None)


def _legacy_unavailable(parsed: argparse.Namespace) -> int:
    reason = getattr(parsed, "_cli_error", cli_legacy_missing_reason())
    message = reason or "Legacy CLI unavailable"
    print(message, file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    codex.add_subparser(sub)
    scan.add_subparser(sub)
    export.add_subparser(sub)
    diagnose.add_subparser(sub)
    _add_legacy_subparser(sub)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
