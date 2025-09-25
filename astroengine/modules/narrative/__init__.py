"""Registry metadata for narrative bundle generation."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_narrative_module"]


def register_narrative_module(registry: AstroRegistry) -> None:
    """Expose the narrative bundle structure with provenance metadata."""

    module = registry.register_module(
        "narrative",
        metadata={

            "description": "Narrative bundle and profile composition (placeholder).",
            "status": "planned",
            "notes": (
                "Runtime implementation lives in astroengine.narrative and "
                "relies on Solar Fire backed scores."
            ),

        },
    )

    bundles = module.register_submodule(
        "bundles",
        metadata={
            "description": "Bundle and export narrative summaries from scored transits.",
            "datasets": ["docs/recipes/narrative_profiles.md"],
            "tests": [
                "tests/test_narrative_summaries.py",
                "tests/test_narrative_templates.py",
            ],
        },
    )
    summary_channel = bundles.register_channel(
        "summaries",
        metadata={
            "composer": "astroengine.narrative.compose_narrative",
            "renderers": [
                "astroengine.narrative.markdown_to_html",
                "astroengine.narrative.markdown_to_plaintext",
            ],
        },
    )
    summary_channel.register_subchannel(
        "markdown",
        metadata={"description": "Markdown narrative export"},
        payload={
            "resolver": "astroengine.narrative.compose_narrative",
            "renderer": "astroengine.narrative.markdown_to_plaintext",
            "event_type": "astroengine.narrative.NarrativeBundle",
            "datasets": ["docs/recipes/narrative_profiles.md"],
            "tests": ["tests/test_narrative_summaries.py"],
            "notes": "Uses offline template profiles when GPT services are unavailable.",
        },
    )
    summary_channel.register_subchannel(
        "html",
        metadata={"description": "HTML rendering using jinja2 fallback"},
        payload={
            "resolver": "astroengine.narrative.compose_narrative",
            "renderer": "astroengine.narrative.markdown_to_html",
            "event_type": "astroengine.narrative.NarrativeBundle",
            "datasets": ["docs/recipes/narrative_profiles.md"],
            "tests": ["tests/test_narrative_templates.py"],
            "notes": "HTML output sanitises markdown via jinja2 templates with provenance recorded in docs/recipes/narrative_profiles.md.",
        },
    )

    profiles = module.register_submodule(
        "profiles",
        metadata={
            "description": "Narrative persona and resonance overlays.",
            "datasets": ["docs/recipes/narrative_profiles.md"],
            "tests": ["tests/test_narrative_templates.py"],
        },
    )
    profiles.register_channel(
        "persona",
        metadata={"renderer": "astroengine.narrative.profiles.render_profile"},
    ).register_subchannel(
        "templates",
        metadata={"description": "Profile template rendering placeholders."},
        payload={
            "resolver": "astroengine.narrative.profiles.render_profile",
            "event_type": "str",
            "datasets": ["docs/recipes/narrative_profiles.md"],
            "tests": ["tests/test_narrative_templates.py"],
            "notes": "Profiles render persona templates from PROFILE_SPECS with Solar Fire aligned resonance metadata.",
        },
    )

    timelords = module.register_submodule(
        "timelords",
        metadata={
            "description": "Integration points for time-lord sequences.",
            "datasets": ["docs/module/predictive_charts.md"],
            "tests": ["tests/test_narrative_overlay.py", "tests/test_timelords.py"],
        },
    )
    timelords.register_channel(
        "systems",
        metadata={"outline": "astroengine.narrative.profiles.timelord_outline"},
    ).register_subchannel(
        "dashas",
        metadata={"description": "Placeholder for dashas and profection overlays."},
        payload={
            "resolver": "astroengine.narrative.profiles.timelord_outline",
            "event_type": "dict",
            "datasets": ["docs/module/predictive_charts.md"],
            "tests": ["tests/test_narrative_overlay.py"],
            "notes": "Timelord overlays summarise active periods from astroengine.timelords stacks.",
        },
    )
