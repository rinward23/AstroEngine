"""Entry point discovery utilities for AstroEngine plugins and providers."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import EntryPoint, entry_points
import importlib
import sys
from typing import Callable


class Registry:
    """In-memory registry populated by plugin and provider entry points."""

    def __init__(self) -> None:
        self.rulesets: dict[str, object] = {}
        self.providers: dict[str, object] = {}

    def register_ruleset(self, name: str, obj: object) -> None:
        """Record a ruleset supplied by a plugin."""

        self.rulesets[name] = obj

    def register_provider(self, name: str, obj: object) -> None:
        """Record an external provider implementation."""

        self.providers[name] = obj


def _ensure_entry_point_importable(ep: EntryPoint) -> Callable[..., object]:
    """Load an entry point, retrying after fixing sys.path for editable installs."""

    try:
        return ep.load()
    except ModuleNotFoundError:
        module_name = getattr(ep, "module", "") or ""
        dist = getattr(ep, "dist", None)
        if dist:
            location = dist.locate_file("")
            if location:
                location_str = str(location)
                if location_str not in sys.path:
                    sys.path.append(location_str)
                    importlib.invalidate_caches()
        if module_name:
            import_module(module_name)
        return ep.load()


def load_plugins(registry: Registry) -> list[str]:
    """Load plugin entry points and allow them to self-register."""

    names: list[str] = []
    for ep in entry_points(group="astroengine.plugins"):
        fn = _ensure_entry_point_importable(ep)
        fn(registry)
        names.append(ep.name)
    return sorted(names)


def load_providers(registry: Registry) -> list[str]:
    """Load provider entry points and register them with the runtime."""

    names: list[str] = []
    for ep in entry_points(group="astroengine.providers"):
        fn = _ensure_entry_point_importable(ep)
        prov_name, prov_obj = fn()
        registry.register_provider(prov_name, prov_obj)
        names.append(ep.name)
    return sorted(names)

