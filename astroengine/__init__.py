"""AstroEngine package bootstrap.

This lightweight package exposes convenience
helpers for loading schema definitions used by the
validation and doctor tooling.  The actual
rulesets live under :mod:`Version Consolidation` and
are left untouched to preserve the append-only
workflow preferred by operators.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:  # pragma: no cover - package metadata not available during tests
    __version__ = version("astroengine")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
