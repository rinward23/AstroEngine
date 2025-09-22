"""Registry wiring for ritual and electional timing assets."""

from __future__ import annotations

from ...ritual import (
    CHALDEAN_ORDER,
    ELECTIONAL_WINDOWS,
    PLANETARY_DAYS,
    PLANETARY_HOUR_TABLE,
    VOID_OF_COURSE_RULES,
)
from ..registry import AstroRegistry

__all__ = ["register_ritual_module"]


def register_ritual_module(registry: AstroRegistry) -> None:
    """Register planetary day/hour tables and electional guides."""

    module = registry.register_module(
        "ritual",
        metadata={
            "description": "Planetary day/hour correspondences and electional filters.",
            "datasets": [
                "planetary_days",
                "planetary_hours",
                "void_of_course_rules",
                "electional_windows",
            ],
        },
    )

    timing = module.register_submodule(
        "timing",
        metadata={"description": "Day and hour rulers used in ritual scheduling."},
    )

    days_channel = timing.register_channel(
        "planetary_days",
        metadata={
            "description": "Seven-day cycle using Chaldean order.",
            "sources": [
                "Heinrich Cornelius Agrippa — Three Books of Occult Philosophy (1533)",
                "Picatrix (Ghayat al-Hakim) Book II",
            ],
            "count": len(PLANETARY_DAYS),
        },
    )
    days_channel.register_subchannel(
        "day_rulers",
        metadata={"description": "Day rulers with ritual themes."},
        payload={"days": [day.to_payload() for day in PLANETARY_DAYS]},
    )

    hours_channel = timing.register_channel(
        "planetary_hours",
        metadata={
            "description": "Twenty-four planetary hours derived from the Chaldean sequence.",
            "sources": [
                "Picatrix (Ghayat al-Hakim) Book II",
                "William Lilly — Christian Astrology (1647)",
            ],
        },
    )
    hours_channel.register_subchannel(
        "hour_table",
        metadata={"order": list(CHALDEAN_ORDER)},
        payload={
            "hours": {weekday: list(sequence) for weekday, sequence in PLANETARY_HOUR_TABLE.items()},
        },
    )

    filters = module.register_submodule(
        "filters",
        metadata={"description": "Lunar void-of-course and quality screens."},
    )
    filters.register_channel(
        "void_of_course",
        metadata={"count": len(VOID_OF_COURSE_RULES)},
    ).register_subchannel(
        "lunar_filters",
        metadata={"description": "Void-of-course definitions with traditional sources."},
        payload={"rules": [rule.to_payload() for rule in VOID_OF_COURSE_RULES]},
    )

    elections = module.register_submodule(
        "elections",
        metadata={"description": "Electional windows for talismanic and mundane timing."},
    )
    elections.register_channel(
        "windows",
        metadata={
            "description": "Documented timing windows and their criteria.",
            "count": len(ELECTIONAL_WINDOWS),
            "sources": [
                "Dorotheus of Sidon — Carmen Astrologicum (1st century)",
                "Picatrix (Ghayat al-Hakim)",
            ],
        },
    ).register_subchannel(
        "guidelines",
        metadata={"description": "Electional sequences emphasising benefic configurations."},
        payload={"windows": [window.to_payload() for window in ELECTIONAL_WINDOWS]},
    )
