"""Registry wiring for the AstroEngine knowledge base."""

from __future__ import annotations

from ..registry import AstroRegistry, AstroChannel
from .catalog import (
    CHART_TYPES,
    FRAMEWORKS,
    GLOSSARY,
    INDICATORS,
    ReferenceEntry,
)

__all__ = ["register_reference_module"]


def _register_entries(channel: AstroChannel, entries: dict[str, ReferenceEntry]) -> None:
    for slug, entry in sorted(entries.items()):
        metadata: dict[str, object] = {"term": entry.term}
        if entry.tags:
            metadata["tags"] = list(entry.tags)
        if entry.related:
            metadata["related"] = list(entry.related)
        channel.register_subchannel(
            slug,
            metadata=metadata,
            payload={
                "summary": entry.summary,
                "sources": [source.as_payload() for source in entry.sources],
            },
        )


def register_reference_module(registry: AstroRegistry) -> None:
    """Attach the documentation knowledge base to the shared registry."""

    module = registry.register_module(
        "reference",
        metadata={
            "description": "Knowledge base describing charts, terminology, and esoteric frameworks.",
            "documentation": "docs/reference/knowledge_base.md",
            "datasets": [
                "docs/reference/knowledge_base.md",
                "docs/reference/astrological_indicators.md",
                "docs/module/core-transit-math.md",
                "docs/module/esoteric_overlays.md",
            ],
        },
    )

    glossary = module.register_submodule(
        "glossary",
        metadata={
            "description": "Definitions for core charting terminology used across the engine.",
            "datasets": ["docs/reference/knowledge_base.md"],
            "tests": ["tests/test_module_registry.py"],
        },
    )
    definitions = glossary.register_channel(
        "definitions",
        metadata={
            "description": "Terminology index backed by source modules and parity datasets.",
            "format": "markdown",
        },
    )
    _register_entries(definitions, dict(GLOSSARY))

    charts = module.register_submodule(
        "charts",
        metadata={
            "description": "Reference guide for natal, progressed, return, and synastry charts.",
            "datasets": ["docs/reference/knowledge_base.md"],
        },
    )
    chart_types = charts.register_channel(
        "types",
        metadata={
            "description": "Chart categories linked to their generating modules and datasets.",
        },
    )
    _register_entries(chart_types, dict(CHART_TYPES))

    frameworks = module.register_submodule(
        "frameworks",
        metadata={
            "description": "Psychological, tarot, and esoteric systems mapped to runtime payloads.",
            "datasets": [
                "docs/reference/knowledge_base.md",
                "docs/module/core-transit-math.md",
                "docs/module/esoteric_overlays.md",
            ],
        },
    )
    systems = frameworks.register_channel(
        "systems",
        metadata={
            "description": "Cross-tradition overlays sourced from published correspondences.",
        },
    )
    _register_entries(systems, dict(FRAMEWORKS))

    indicators = module.register_submodule(
        "indicators",
        metadata={
            "description": "Astrological indicator outline spanning celestial bodies, timing, and overlays.",
            "datasets": ["docs/reference/astrological_indicators.md"],
        },
    )
    catalog = indicators.register_channel(
        "catalog",
        metadata={
            "description": "Indicator categories linked to source modules, datasets, and provenance notes.",
        },
    )
    _register_entries(catalog, dict(INDICATORS))
