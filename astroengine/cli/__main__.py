"""Entry point for the modular AstroEngine CLI."""

from __future__ import annotations

import argparse
from typing import Sequence

from . import diagnose, export, scan
from .. import cli_legacy


def _add_legacy_subparser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    legacy_parser = sub.add_parser(
        "legacy",
        help="Access the historical monolithic CLI (for backward compatibility)",
        description=(
            "Invoke the previous CLI implementation. All arguments after 'legacy' "
            "are forwarded verbatim to the legacy parser."
        ),
    )
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
    return cli_legacy.main(argv if argv else None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    scan.add_subparser(sub)
    export.add_subparser(sub)
    diagnose.add_subparser(sub)
    _add_legacy_subparser(sub)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
