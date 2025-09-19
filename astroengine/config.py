"""Compatibility layer that re-exports :mod:`astroengine.core.config`."""

from __future__ import annotations

from .core.config import load_profile_json, profile_into_ctx

__all__ = ["load_profile_json", "profile_into_ctx"]
