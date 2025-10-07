from __future__ import annotations

import importlib
import importlib.util
from typing import Any

__all__ = ["swe", "reset_swe", "has_swe"]

_swe_mod: Any | None = None


def _load_swe() -> Any:
    global _swe_mod
    if _swe_mod is None:
        try:
            _swe_mod = importlib.import_module("swisseph")
        except Exception as exc:  # pragma: no cover - import errors depend on env
            raise RuntimeError(
                "Swiss Ephemeris not available. Install pyswisseph (package: 'pyswisseph') "
                "and set SE_EPHE_PATH to your ephemeris data directory."
            ) from exc
    return _swe_mod


class _SweProxy:
    """Proxy object exposing Swiss Ephemeris attributes lazily."""

    def __call__(self) -> Any:
        return _load_swe()

    def __getattr__(self, item: str) -> Any:
        return getattr(_load_swe(), item)


swe = _SweProxy()


def reset_swe():
    """For tests: force reload of swisseph on next swe() call."""
    global _swe_mod
    _swe_mod = None


def has_swe() -> bool:
    """Return ``True`` if pyswisseph is importable."""

    if _swe_mod is not None:
        return True
    return importlib.util.find_spec("swisseph") is not None
