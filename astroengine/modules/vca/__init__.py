"""VCA module definitions and registry bootstrap helpers."""

from __future__ import annotations

from typing import Dict

from ..registry import AstroModule, AstroRegistry
from .catalogs import (
    VCA_CENTAURS,
    VCA_CORE_BODIES,
    VCA_EXT_ASTEROIDS,
    VCA_SENSITIVE_POINTS,
    VCA_TNOS,
)
from .profiles import VCA_DOMAIN_PROFILES
from .rulesets import VCA_RULESET

__all__ = ["register_vca_module", "serialize_vca_ruleset"]


def serialize_vca_ruleset() -> Dict[str, object]:
    """Return a serialisable representation of the bundled VCA ruleset."""

    aspects = {
        name: {
            "angle": aspect.angle,
            "class": aspect.klass,
            "default_orb_deg": aspect.default_orb_deg,
        }
        for name, aspect in VCA_RULESET.aspects.items()
    }
    orb_defaults = dict(VCA_RULESET.orb_class_defaults)
    return {
        "id": VCA_RULESET.id,
        "expand_luminaries": VCA_RULESET.expand_luminaries,
        "aspects": aspects,
        "orb_class_defaults": orb_defaults,
    }


def register_vca_module(registry: AstroRegistry) -> AstroModule:
    """Register the bundled VCA assets into ``registry``."""

    module = registry.register_module(
        "vca",
        metadata={
            "description": "Venus Cycle Analytics baseline assets",
            "source": "SolarFire/Vanessa Cycle Astrology",
        },
    )

    # Catalogs
    catalogs = module.register_submodule(
        "catalogs",
        metadata={"description": "Planetary and point catalogs"},
    )
    bodies = catalogs.register_channel("bodies", metadata={"default_profile": "core"})
    bodies.register_subchannel(
        "core",
        metadata={"description": "Core planets and luminaries"},
        payload={"bodies": VCA_CORE_BODIES},
    )
    bodies.register_subchannel(
        "extended",
        metadata={"description": "Extended asteroid catalog"},
        payload={"bodies": VCA_EXT_ASTEROIDS},
    )
    bodies.register_subchannel(
        "centaurs",
        metadata={"description": "Centaurs"},
        payload={"bodies": VCA_CENTAURS},
    )
    bodies.register_subchannel(
        "tnos",
        metadata={"description": "Trans-Neptunian objects"},
        payload={"bodies": VCA_TNOS},
    )
    bodies.register_subchannel(
        "sensitive_points",
        metadata={"description": "Sensitive chart points"},
        payload={"bodies": VCA_SENSITIVE_POINTS},
    )

    # Profiles
    profiles = module.register_submodule(
        "profiles",
        metadata={"description": "Domain scoring profiles"},
    )
    domain_profiles = profiles.register_channel(
        "domain",
        metadata={"default": "vca_neutral"},
    )
    for name, profile in VCA_DOMAIN_PROFILES.items():
        domain_profiles.register_subchannel(
            name,
            metadata={"label": profile.name},
            payload={"multipliers": dict(profile.domain_multipliers)},
        )

    # Rulesets
    rulesets = module.register_submodule(
        "rulesets",
        metadata={"description": "Aspect rule definitions"},
    )
    aspects = rulesets.register_channel(
        "aspects",
        metadata={"ruleset_id": VCA_RULESET.id},
    )
    aspects.register_subchannel(
        "definitions",
        metadata={"expand_luminaries": VCA_RULESET.expand_luminaries},
        payload=serialize_vca_ruleset(),
    )

    return module
