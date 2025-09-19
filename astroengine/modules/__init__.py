"""Module namespace wiring for AstroEngine."""

from __future__ import annotations

from .registry import AstroChannel, AstroModule, AstroRegistry, AstroSubchannel, AstroSubmodule
from .vca import register_vca_module

__all__ = [
    "AstroRegistry",
    "AstroModule",
    "AstroSubmodule",
    "AstroChannel",
    "AstroSubchannel",
    "bootstrap_default_registry",
    "DEFAULT_REGISTRY",
]


def bootstrap_default_registry() -> AstroRegistry:
    """Return a registry populated with the built-in modules."""

    registry = AstroRegistry()
    register_vca_module(registry)
    return registry


DEFAULT_REGISTRY = bootstrap_default_registry()
