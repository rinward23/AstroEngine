"""Swiss ephemeris installation helpers."""

from __future__ import annotations

from pathlib import Path

from .pull import PullError, PullResult, available_sets, pull_set

DEFAULT_INSTALL_ROOT = Path.home() / ".astroengine" / "ephe"

__all__ = [
    "DEFAULT_INSTALL_ROOT",
    "available_sets",
    "pull_set",
    "PullError",
    "PullResult",
]
