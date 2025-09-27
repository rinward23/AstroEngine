"""Compatibility layer exposing ``astroengine.core.charts_plus`` under the ``core`` namespace."""

from __future__ import annotations

import sys
from importlib import import_module

_base = import_module("astroengine.core.charts_plus")

for name in getattr(_base, "__all__", []):
    if hasattr(_base, name):
        globals()[name] = getattr(_base, name)

for sub in [
    "returns",
]:
    module = import_module(f"astroengine.core.charts_plus.{sub}")
    sys.modules[f"{__name__}.{sub}"] = module
    globals().setdefault(sub, module)

__all__ = getattr(_base, "__all__", [])
