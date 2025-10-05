"""AstroEngine command line interface package."""

from __future__ import annotations

import json as _json

json = _json


def build_parser():
    """Lazily import the CLI parser builder to avoid early heavy dependencies."""

    from .__main__ import build_parser as _build

    return _build()


def main(argv=None):
    """Lazily import the CLI entrypoint to defer optional dependency loading."""

    from .__main__ import main as _main

    return _main(argv)


def console_main() -> None:
    """Invoke :func:`main` and terminate with its return code."""

    raise SystemExit(main())


__all__ = ["main", "build_parser", "console_main", "json"]
