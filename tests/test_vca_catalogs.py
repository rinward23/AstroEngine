"""Regression tests for the bundled VCA catalog payloads."""

from __future__ import annotations

from astroengine.modules.registry import AstroRegistry
from astroengine.modules.vca import register_vca_module
from astroengine.profiles import load_vca_outline


def test_vca_registry_catalog_matches_outline() -> None:
    registry = AstroRegistry()
    register_vca_module(registry)

    outline = load_vca_outline()
    bodies_outline = outline["bodies"]
    sensitive_points_outline = outline["sensitive_points"]

    bodies_outline_subchannel = registry.resolve(
        "vca", submodule="catalogs", channel="bodies", subchannel="outline"
    )
    assert bodies_outline_subchannel.payload == bodies_outline

    fixed_stars_subchannel = registry.resolve(
        "vca", submodule="catalogs", channel="bodies", subchannel="fixed_stars"
    )
    assert fixed_stars_subchannel.payload == bodies_outline["fixed_stars"]

    sensitive_points_subchannel = registry.resolve(
        "vca", submodule="catalogs", channel="bodies", subchannel="sensitive_points"
    )
    assert sensitive_points_subchannel.payload == {"bodies": sensitive_points_outline}
