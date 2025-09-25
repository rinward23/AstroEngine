"""Registry scaffolding for narrative bundle generation."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_narrative_module"]


def register_narrative_module(registry: AstroRegistry) -> None:
    """Expose the narrative bundle structure with explicit TODO markers."""

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
            "todo": [
                "Persist narrative bundles to durable storage with provenance hashes",
                "Ensure markdown/html outputs embed only data-backed summaries",
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
            "implementation": "pending",
            "todo": [
                "Finalize template catalog referencing docs/recipes/narrative_profiles.md",
                "Add regression tests verifying Solar Fire alignment for highlights",
            ],
        },
    )
    summary_channel.register_subchannel(
        "html",
        metadata={"description": "HTML rendering using jinja2 fallback"},
        payload={
            "implementation": "pending",
            "todo": [
                "Record template provenance and version hashes",
                "Document sanitization flow for HTML export",
            ],
        },
    )

    profiles = module.register_submodule(
        "profiles",
        metadata={
            "description": "Narrative persona and resonance overlays.",
            "todo": [
                "Backfill Solar Fire derived persona datasets",
                "Track profile versioning in docs/recipes/narrative_profiles.md",
            ],
        },
    )
    profiles.register_channel(
        "persona",
        metadata={"renderer": "astroengine.narrative.profiles.render_profile"},
    ).register_subchannel(
        "templates",
        metadata={"description": "Profile template rendering placeholders."},
        payload={
            "implementation": "pending",
            "todo": [
                "Index YAML templates under profiles/ with provenance checksums",
                "Expose CLI command to list available narrative personas",
            ],
        },
    )

    timelords = module.register_submodule(
        "timelords",
        metadata={
            "description": "Integration points for time-lord sequences.",
            "todo": [
                "Map Solar Fire dashas/profections to internal time-lord API",
                "Attach acceptance tests referencing docs/module/predictive_charts.md",
            ],
        },
    )
    timelords.register_channel(
        "systems",
        metadata={"outline": "astroengine.narrative.profiles.timelord_outline"},
    ).register_subchannel(
        "dashas",
        metadata={"description": "Placeholder for dashas and profection overlays."},
        payload={
            "implementation": "pending",
            "todo": [
                "Surface active time-lords in narrative exports once predictive data is indexed",
            ],
        },
    )
