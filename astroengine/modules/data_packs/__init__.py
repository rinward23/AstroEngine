"""Registry wiring for bundled data packs and static profiles.

This module captures the CSV/YAML/JSON datasets that ship with the
repository and power runtime scoring. Documenting them inside the
registry keeps provenance attached to each dataset reference so the
engine never emits values that cannot be traced back to a Solar Fire or
Swiss Ephemeris export.
"""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_data_packs_module"]


DATA_PACKS_DOC = "docs/module/data-packs.md"


def register_data_packs_module(registry: AstroRegistry) -> None:
    """Attach the bundled CSV/YAML/JSON packs to the shared registry."""

    module = registry.register_module(
        "data_packs",
        metadata={
            "description": "Bundled Solar Fire aligned datasets and scoring profiles.",
            "documentation": DATA_PACKS_DOC,
            "datasets": [
                "profiles/base_profile.yaml",
                "profiles/dignities.csv",
                "profiles/fixed_stars.csv",
                "profiles/vca_outline.json",
                "schemas/orbs_policy.json",
                "datasets/star_names_iau.csv",
            ],
        },
    )

    profiles = module.register_submodule(
        "profiles",
        metadata={
            "description": "Runtime scoring profiles derived from Solar Fire exports.",
            "docs": [DATA_PACKS_DOC],
        },
    )
    catalogue = profiles.register_channel(
        "catalogue",
        metadata={"description": "Profile documents consumed by detectors and scoring helpers."},
    )
    catalogue.register_subchannel(
        "base_profile",
        metadata={
            "description": "Swiss Ephemeris calibrated base profile and feature toggles.",
            "tests": [
                "tests/test_vca_profile.py",
                "tests/test_domain_scoring.py",
            ],
        },
        payload={
            "path": "profiles/base_profile.yaml",
            "provenance": "Solar Fire 9 base profile parity checks recorded in docs/governance/data_revision_policy.md",
        },
    )
    catalogue.register_subchannel(
        "vca_outline",
        metadata={
            "description": "Venus Cycle Analytics module outline driving registry bootstrapping.",
            "tests": ["tests/test_vca_profile.py"],
        },
        payload={
            "path": "profiles/vca_outline.json",
            "registry_path_key": "modules",
        },
    )

    atlases = module.register_submodule(
        "catalogs",
        metadata={
            "description": "CSV datasets that extend natal and transit scoring capabilities.",
            "docs": [DATA_PACKS_DOC],
        },
    )
    atlases_channel = atlases.register_channel(
        "csv",
        metadata={"description": "Static CSV packs bundled for deterministic lookups."},
    )
    atlases_channel.register_subchannel(
        "dignities",
        metadata={
            "description": "Essential dignities and modifiers mirrored from Solar Fire tables.",
            "tests": ["tests/test_domain_scoring.py"],
        },
        payload={
            "path": "profiles/dignities.csv",
            "provenance": "Solar Fire ESSENTIAL.DAT export cross-referenced with traditional sources.",
        },
    )
    atlases_channel.register_subchannel(
        "fixed_stars",
        metadata={
            "description": "FK6 aligned bright star catalogue consumed by fixed-star overlays.",
            "tests": [
                "tests/test_star_names_dataset.py",
                "tests/test_fixed_stars.py",
            ],
        },
        payload={
            "path": "profiles/fixed_stars.csv",
            "provenance": "Solar Fire Bright Stars export with documented checksum column.",
        },
    )
    atlases_channel.register_subchannel(
        "star_names",
        metadata={
            "description": "IAU Working Group star names derived from the HYG database.",
            "tests": ["tests/test_star_names_dataset.py"],
        },
        payload={
            "path": "datasets/star_names_iau.csv",
            "provenance": "HYG Database v4.1 filtered to official WGSN designations.",
        },
    )

    schemas = module.register_submodule(
        "schemas",
        metadata={
            "description": "JSON datasets that keep client orb policies aligned with runtime defaults.",
        },
    )
    schema_channel = schemas.register_channel(
        "orbs",
        metadata={"description": "Aspect orb definitions distributed for interoperability."},
    )
    schema_channel.register_subchannel(
        "policy",
        metadata={
            "description": "Aspect families and multipliers for client configuration UIs.",
            "tests": ["tests/test_orbs_policy.py"],
        },
        payload={
            "path": "schemas/orbs_policy.json",
            "provenance": "Matches Solar Fire default orb policy with documented profile multipliers.",
        },
    )
