"""Swiss ephemeris installation helpers."""

from __future__ import annotations

from pathlib import Path

DEFAULT_INSTALL_ROOT = Path.home() / ".astroengine" / "ephe"

__all__ = ["DEFAULT_INSTALL_ROOT"]
