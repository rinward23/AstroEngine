"""Placeholder registry metadata for mundane ingress workflows."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_mundane_module"]


def register_mundane_module(registry: AstroRegistry) -> None:
    """Register the mundane astrology scaffolding with TODO markers."""

    module = registry.register_module(
        "mundane",
        metadata={
            "description": "Mundane ingress and seasonal chart calculations (placeholder).",
            "status": "planned",
            "notes": "Runtime functions live in astroengine.mundane; data indexing pending.",
        },
    )

    ingress = module.register_submodule(
        "ingress",
        metadata={
            "description": "Solar ingress charts and mundane aspect analysis.",
            "todo": [
                "Index Solar Fire ingress exports into SQLite for deterministic lookups",
                "Attach provenance hashes for each imported ingress chart",
            ],
        },
    )

    charts = ingress.register_channel(
        "solar_ingress",
        metadata={
            "description": "Ingress charts for each zodiac sign.",
            "source_functions": [
                "astroengine.mundane.ingress.compute_solar_ingress_chart",
                "astroengine.mundane.ingress.compute_solar_quartet",
            ],
        },
    )
    charts.register_subchannel(
        "sign_charts",
        metadata={"description": "Compute ingress chart for a single sign boundary."},
        payload={
            "implementation": "pending",
            "todo": [
                "Persist ingress summaries to datasets/mundane once ingestion lands",
                "Validate angles against Solar Fire reference charts",
            ],
        },
    )
    charts.register_subchannel(
        "seasonal_quartet",
        metadata={"description": "Package the Aries/Cancer/Libra/Capricorn ingress charts."},
        payload={
            "implementation": "pending",
            "todo": [
                "Expose quartet export schema under docs/module/interop.md",
                "Backfill regression tests comparing Solar Fire output",
            ],
        },
    )

    module.register_submodule(
        "aspects",
        metadata={
            "description": "Placeholder for mundane aspect scoring across nations/regions.",
            "todo": [
                "Design dataset schema linking ingress charts to regional metadata",
                "Integrate scoring rules once Solar Fire comparisons are catalogued",
            ],
        },
    )
