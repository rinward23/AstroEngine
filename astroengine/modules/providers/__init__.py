"""Registry wiring for ephemeris providers and frame preferences."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_providers_module"]

PROVIDERS_DOC = "docs/module/providers_and_frames.md"


def register_providers_module(registry: AstroRegistry) -> None:
    """Expose provider contracts and bundled plugin metadata."""

    module = registry.register_module(
        "providers",
        metadata={
            "description": "Ephemeris provider protocol and bundled plugin configurations.",
            "documentation": PROVIDERS_DOC,
            "sources": [
                "astroengine/providers/__init__.py",
                "astroengine/providers/skyfield_provider.md",
                "astroengine/providers/swe_provider.md",
            ],
        },
    )

    ephemeris = module.register_submodule(
        "ephemeris",
        metadata={
            "description": "Provider implementations supplying Swiss Ephemeris and Skyfield data.",
            "protocol": "astroengine.providers.EphemerisProvider",
        },
    )
    plugins = ephemeris.register_channel(
        "plugins",
        metadata={
            "description": "Built-in provider registry backed by astroengine.providers.",
            "registry_module": "astroengine.providers",
        },
    )
    plugins.register_subchannel(
        "swiss_ephemeris",
        metadata={
            "description": "Swiss Ephemeris bridge with pyswisseph dependency management.",
            "tests": [
                "tests/test_swisseph_adapter.py",
                "tests/test_swisseph_sidereal.py",
            ],
        },
        payload={
            "module": "astroengine.providers.swiss_provider",
            "design_notes": "astroengine/providers/swe_provider.md",
            "datasets": ["datasets/swisseph_stub"],
        },
    )
    plugins.register_subchannel(
        "skyfield",
        metadata={
            "description": "Skyfield DE ephemeris provider plan (implementation pending).",
            "status": "planned",
        },
        payload={
            "design_notes": "astroengine/providers/skyfield_provider.md",
            "datasets": ["astroengine/providers/skyfield_kernels.py"],
        },
    )

    cadence = module.register_submodule(
        "cadence",
        metadata={
            "description": "Recommended sampling cadences and cache layout referenced by profiles.",
        },
    )
    cadence_channel = cadence.register_channel(
        "profiles",
        metadata={
            "description": "Cadence values sourced from profiles/base_profile.yaml.",
        },
    )
    cadence_channel.register_subchannel(
        "default",
        metadata={
            "description": "Default provider selection and cadence configuration.",
            "tests": ["tests/test_vca_profile.py"],
        },
        payload={
            "path": "profiles/base_profile.yaml",
            "keys": [
                "providers.default",
                "providers.skyfield.cache_path",
                "providers.swe().enabled",
                "providers.*.cadence_hours",
            ],
        },
    )

    frames = module.register_submodule(
        "frames",
        metadata={
            "description": "House systems and ayanamsha preferences tied to provider outputs.",
        },
    )
    frames.register_channel(
        "preferences",
        metadata={
            "description": "Frame toggles referenced by detectors and narrative overlays.",
        },
    ).register_subchannel(
        "profile_flags",
        metadata={
            "description": "Feature flags controlling house system and sidereal settings.",
            "tests": [
                "tests/test_result_schema.py",
                "tests/test_contact_gate_schema.py",
            ],
        },
        payload={
            "path": "profiles/base_profile.yaml",
            "keys": [
                "feature_flags.house_system",
                "feature_flags.sidereal",
            ],
        },
    )
