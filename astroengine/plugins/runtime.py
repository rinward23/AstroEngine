"""Entry point discovery utilities for AstroEngine plugins and providers."""

from __future__ import annotations

from importlib.metadata import entry_points


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
    for ep in entry_points(group="astroengine.plugins"):
        fn = ep.load()
        fn(registry)
        names.append(ep.name)
    return sorted(names)


def load_providers(registry: Registry) -> list[str]:
    """Load provider entry points and register them with the runtime."""

    names: list[str] = []
    for ep in entry_points(group="astroengine.providers"):
        fn = ep.load()
        prov_name, prov_obj = fn()
        registry.register_provider(prov_name, prov_obj)
        names.append(ep.name)
    return sorted(names)

