"""AstroEngine command line interface package."""

from __future__ import annotations

import json as _json

from .__main__ import build_parser, main

json = _json


def console_main() -> None:
    """Invoke :func:`main` and terminate with its return code."""

    raise SystemExit(main())


__all__ = ["main", "build_parser", "console_main", "json"]
