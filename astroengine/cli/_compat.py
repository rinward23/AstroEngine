"""Compatibility utilities for the AstroEngine CLI."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Final

_CLI_LEGACY_CACHE: ModuleType | None = None
_CLI_LEGACY_ERROR: ModuleNotFoundError | None = None
_SWISSEPH_MODULE: Final[str] = "swisseph"


def try_import_cli_legacy() -> ModuleType | None:
    """Try importing :mod:`astroengine.cli_legacy` lazily.

    When the optional Swiss Ephemeris dependency (``pyswisseph``) is not
    installed, importing ``astroengine.cli_legacy`` raises a
    :class:`ModuleNotFoundError`.  In that situation this helper caches the
    failure and returns ``None`` so callers may degrade gracefully (e.g. by
    presenting a helpful message in ``--help`` output).
    """

    global _CLI_LEGACY_CACHE, _CLI_LEGACY_ERROR

    if _CLI_LEGACY_CACHE is not None:
        return _CLI_LEGACY_CACHE
    if _CLI_LEGACY_ERROR is not None:
        return None

    try:
        module = import_module("astroengine.cli_legacy")
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime deps
        if exc.name == _SWISSEPH_MODULE:
            _CLI_LEGACY_ERROR = exc
            return None
        raise

    _CLI_LEGACY_CACHE = module
    return module


def cli_legacy_missing_reason() -> str | None:
    """Return a human readable explanation for the legacy CLI being unavailable."""

    if _CLI_LEGACY_ERROR is None:
        return None
    return (
        "pyswisseph (Swiss Ephemeris) is required for AstroEngine's transit "
        "scanning commands. Install the 'astroengine[ephem]' optional "
        "dependency set or add pyswisseph to your environment."
    )


def require_cli_legacy() -> ModuleType:
    """Return the legacy CLI module or raise a descriptive :class:`RuntimeError`."""

    module = try_import_cli_legacy()
    if module is None:
        reason = cli_legacy_missing_reason() or "pyswisseph is required"
        raise RuntimeError(reason) from _CLI_LEGACY_ERROR
    return module


__all__ = ["try_import_cli_legacy", "cli_legacy_missing_reason", "require_cli_legacy"]
