"""Module namespace wiring for AstroEngine."""

from __future__ import annotations

from .registry import AstroChannel, AstroModule, AstroRegistry, AstroSubchannel, AstroSubmodule
from .esoteric import register_esoteric_module
from .event_detectors import register_event_detectors_module
from .mundane import register_mundane_module
from .narrative import register_narrative_module
from .predictive import register_predictive_module
from .ritual import register_ritual_module
from .ux import register_ux_module
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
    register_event_detectors_module(registry)
    register_esoteric_module(registry)
    register_mundane_module(registry)
    register_narrative_module(registry)
    register_ritual_module(registry)
    register_predictive_module(registry)
    register_ux_module(registry)
    return registry


DEFAULT_REGISTRY = bootstrap_default_registry()
