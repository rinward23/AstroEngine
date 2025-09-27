"""Compatibility shim exposing :mod:`astroengine.core.electional_plus`."""

from __future__ import annotations

import sys
from importlib import import_module

_base = import_module("astroengine.core.electional_plus")

for name in getattr(_base, "__all__", []):
    if hasattr(_base, name):
        globals()[name] = getattr(_base, name)

sys.modules[f"{__name__}.engine"] = import_module("astroengine.core.electional_plus.engine")

__all__ = getattr(_base, "__all__", [])
