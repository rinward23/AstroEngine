"""Module namespace wiring for AstroEngine."""

from __future__ import annotations

from .registry import AstroChannel, AstroModule, AstroRegistry, AstroSubchannel, AstroSubmodule
from .cycles import register_cycles_module
from .esoteric import register_esoteric_module
from .predictive import register_predictive_module
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
    register_esoteric_module(registry)
    register_predictive_module(registry)
    register_cycles_module(registry)
    return registry


DEFAULT_REGISTRY = bootstrap_default_registry()
