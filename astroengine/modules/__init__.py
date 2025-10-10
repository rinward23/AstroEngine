"""Module namespace wiring for AstroEngine."""

from __future__ import annotations

from .chinese import register_chinese_module
from .data_packs import register_data_packs_module
from .developer_platform import register_developer_platform_module
from .esoteric import register_esoteric_module
from .event_detectors import register_event_detectors_module
from .integrations import register_integrations_module
from .jyotish import register_jyotish_module
from .mayan import register_mayan_module
from .mundane import register_mundane_module
from .narrative import register_narrative_module
from .interop import register_interop_module
from .predictive import register_predictive_module
from .reference import register_reference_module
from .registry import (
    AstroChannel,
    AstroModule,
    AstroRegistry,
    AstroSubchannel,
    AstroSubmodule,
)
from .providers import register_providers_module
from .orchestration import register_orchestration_module
from .ritual import register_ritual_module
from .tibetan import register_tibetan_module
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
    register_chinese_module(registry)
    register_jyotish_module(registry)
    register_narrative_module(registry)
    register_mayan_module(registry)
    register_tibetan_module(registry)

    register_ritual_module(registry)
    register_predictive_module(registry)
    register_ux_module(registry)
    register_integrations_module(registry)
    register_data_packs_module(registry)
    register_reference_module(registry)
    register_providers_module(registry)
    register_interop_module(registry)
    register_developer_platform_module(registry)
    register_orchestration_module(registry)
    return registry


DEFAULT_REGISTRY = bootstrap_default_registry()
