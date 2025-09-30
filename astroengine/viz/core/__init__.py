"""Core rendering primitives used by AstroEngine visualisation modules."""

from .svg import SvgDocument, SvgElement
from .theme import VizTheme, ThemeManager
from .glyphs import Glyph, GlyphCatalog
from .labeler import LabelRequest, LabelPlacement, Labeler

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
