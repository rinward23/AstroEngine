"""AstroEngine command line interface package."""

from __future__ import annotations

import json as _json

from .app import app
from ._compat import build_parser, console_main, main

json = _json

__all__ = ["app", "main", "build_parser", "console_main", "json"]
