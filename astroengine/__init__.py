"""AstroEngine package bootstrap.

This lightweight package exposes convenience
helpers for loading schema definitions used by the
validation and doctor tooling.  The actual
rulesets live under :mod:`Version Consolidation` and
are left untouched to preserve the append-only
workflow preferred by operators.
"""

# ruff: noqa: E402

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

__all__ = ["__version__", "TransitEngine", "TransitScanConfig"]

_PKG_DIR = Path(__file__).resolve().parent
_SRC_TRANSIT = _PKG_DIR.parent / "src" / "astroengine"
if _SRC_TRANSIT.exists():
    __path__ = list(dict.fromkeys(list(__path__) + [str(_SRC_TRANSIT)]))

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

from .transit.api import TransitEngine, TransitScanConfig  # ENSURE-LINE
