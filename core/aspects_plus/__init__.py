"""Compatibility layer exposing ``astroengine.core.aspects_plus`` under the ``core`` namespace."""

from __future__ import annotations

import sys
from importlib import import_module

_base = import_module("astroengine.core.aspects_plus")

for name in getattr(_base, "__all__", []):
    if hasattr(_base, name):
        globals()[name] = getattr(_base, name)

for sub in [
    "harmonics",
    "matcher",
    "orb_policy",
    "scan",
    "search",
    "aggregate",
    "provider_wrappers",
]:
    module = import_module(f"astroengine.core.aspects_plus.{sub}")
    sys.modules[f"{__name__}.{sub}"] = module
    globals().setdefault(sub, module)

__all__ = getattr(_base, "__all__", [])
