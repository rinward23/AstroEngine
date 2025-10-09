"""Compatibility shim for legacy imports expecting :mod:`astroengine.api_server`."""

from __future__ import annotations

from warnings import warn

from astroengine.api.app import app, create_app, get_app, run

warn(
    "Importing from 'astroengine.api_server' is deprecated; use 'astroengine.api.app' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["app", "create_app", "get_app", "run"]

