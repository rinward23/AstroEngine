"""Sample aspect and lot plugin for AstroEngine.

Copy this file to ``~/.astroengine/plugins/custom_aspects.py`` (or any
``.py`` filename) and edit the registrations below. Every decorated function is
invoked at import time to register metadata; the function bodies are never
executed by AstroEngine, so ``pass`` is sufficient.
"""

from __future__ import annotations

from astroengine.plugins.registry import register_aspect, register_lot


@register_aspect(
    "Septile",
    angle=51.4286,
    description="Seventh-harmonic aspect often associated with inspiration.",
)
def septile() -> None:
    """Register a custom aspect angle.

    The function body is intentionally empty; registration happens via the
    decorator. Rename the function to keep module-level identifiers unique.
    """


@register_lot(
    "Lot of Research",
    day_formula="Asc + Mercury - Saturn",
    night_formula="Asc + Saturn - Mercury",
    description="Experimental lot blending Mercurial inquiry with Saturnine discipline.",
)
def lot_of_research() -> None:
    """Register a custom Arabic Lot.

    Use ``replace=True`` in the decorator arguments to override a built-in lot
    definition. Day and night formulas can reference other registered lots as
    needed.
    """

