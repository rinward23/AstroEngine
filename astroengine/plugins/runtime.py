"""Entry point discovery utilities for AstroEngine plugins and providers."""

from __future__ import annotations

import site
import sys
from importlib.metadata import entry_points


def _prepare_entrypoints(group: str) -> list:
    """Return entry points for *group* ensuring newly installed dists are importable."""

    eps = list(entry_points(group=group))
    for ep in eps:
        dist = getattr(ep, "dist", None)
        if not dist:
            continue
        try:
            base = dist.locate_file(".")
        except Exception:  # pragma: no cover - defensive guard around metadata access
            continue
        if not base:
            continue
        base_str = str(base)
        if base_str not in sys.path:
            # Re-run .pth processing so editable installs become visible mid-process.
            site.addsitedir(base_str)
    return eps


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


def load_plugins(registry: Registry) -> list[str]:
    """Load plugin entry points and allow them to self-register."""

    names: list[str] = []
    for ep in _prepare_entrypoints("astroengine.plugins"):
        fn = ep.load()
        fn(registry)
        names.append(ep.name)
    return sorted(names)


def load_providers(registry: Registry) -> list[str]:
    """Load provider entry points and register them with the runtime."""

    names: list[str] = []
    for ep in _prepare_entrypoints("astroengine.providers"):
        fn = ep.load()
        prov_name, prov_obj = fn()
        registry.register_provider(prov_name, prov_obj)
        names.append(ep.name)
    return sorted(names)

