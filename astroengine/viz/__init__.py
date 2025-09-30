"""Visualization primitives for AstroEngine.

This package hosts SVG-first rendering utilities shared across
visualization modules (wheel, aspectarian, midpoints, stars, alt/az).
The implementation focuses on deterministic outputs suitable for
streaming to export pipelines.  Each module is organised using the
module → submodule → channel → subchannel hierarchy mandated by the
project's contribution guide.

Only real ephemeris or catalog data should be plotted with these
utilities.  The components defined here provide the plumbing needed to
represent that data faithfully; they never fabricate celestial
positions or magnitudes.
"""

from .core.svg import SvgDocument, SvgElement
from .core.theme import VizTheme, ThemeManager
from .core.glyphs import Glyph, GlyphCatalog
from .core.labeler import LabelRequest, LabelPlacement, Labeler

__all__ = [
    "SvgDocument",
    "SvgElement",
    "VizTheme",
    "ThemeManager",
    "Glyph",
    "GlyphCatalog",
    "LabelRequest",
    "LabelPlacement",
    "Labeler",
]
