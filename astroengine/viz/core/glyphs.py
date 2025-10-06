"""Embedded SVG glyphs used across visualisation modules."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Glyph:
    """A reusable glyph defined by an SVG path."""

    name: str
    path: str
    viewbox: Sequence[float] = (0.0, 0.0, 24.0, 24.0)
    advance: float = 24.0

    def normalised_path(self) -> str:
        return " ".join(self.path.split())


class GlyphCatalog:
    """Container for glyph definitions.

    Glyphs are stored in-memory and made available without relying on
    system fonts.  The default catalogue includes the core planets and
    zodiac signs so the wheel renderer can generate charts without extra
    assets.
    """

    def __init__(self, glyphs: Iterable[Glyph] | None = None) -> None:
        self._glyphs: MutableMapping[str, Glyph] = {}
        if glyphs:
            for glyph in glyphs:
                self.register(glyph)

    def register(self, glyph: Glyph) -> None:
        key = glyph.name.lower()
        if key in self._glyphs:
            raise ValueError(f"Glyph '{glyph.name}' already registered")
        self._glyphs[key] = glyph

    def replace(self, glyph: Glyph) -> None:
        self._glyphs[glyph.name.lower()] = glyph

    def get(self, name: str) -> Glyph:
        try:
            return self._glyphs[name.lower()]
        except KeyError as exc:
            raise KeyError(f"Unknown glyph '{name}'") from exc

    def load_from_payload(self, payload: Mapping[str, Mapping[str, object]]) -> None:
        for name, meta in payload.items():
            path = str(meta["path"])
            viewbox = tuple(float(v) for v in meta.get("viewbox", (0.0, 0.0, 24.0, 24.0)))
            advance = float(meta.get("advance", viewbox[2]))
            glyph = Glyph(name=name, path=path, viewbox=viewbox, advance=advance)
            self.replace(glyph)

    def as_payload(self) -> dict[str, dict[str, object]]:
        return {
            glyph.name: {
                "path": glyph.path,
                "viewbox": list(glyph.viewbox),
                "advance": glyph.advance,
            }
            for glyph in self._glyphs.values()
        }


@lru_cache(maxsize=1)
def default_catalog() -> GlyphCatalog:
    catalog = GlyphCatalog()
    for glyph in DEFAULT_GLYPHS:
        catalog.replace(glyph)
    return catalog


DEFAULT_GLYPHS = (
    Glyph(
        name="Sun",
        path="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20z",
    ),
    Glyph(
        name="Moon",
        path="M17 3a9 9 0 0 1-7 19 9 9 0 1 0 7-19z",
    ),
    Glyph(
        name="Mercury",
        path="M12 2a4 4 0 1 1-4 4v2h2v3.268A5 5 0 1 0 12 18a5 5 0 0 0 2-9.732V8h2V6a4 4 0 0 1-4-4z",
    ),
    Glyph(
        name="Venus",
        path="M12 2a5 5 0 0 0-2 9.623V14H7v2h3v3h2v-3h3v-2h-3v-2.377A5 5 0 0 0 12 2z",
    ),
    Glyph(
        name="Mars",
        path="M14 2v2h1.586L13 6.586l1.414 1.414L17 5.414V7h2V2zM10 4a6 6 0 1 0 4.472 10.028l-1.414-1.414A4 4 0 1 1 12 8a3.98 3.98 0 0 1 2.614.964l1.414-1.414A5.98 5.98 0 0 0 10 4z",
    ),
    Glyph(
        name="Jupiter",
        path="M7 4v2h3v4.268A4 4 0 1 0 12 18a3.99 3.99 0 0 0 3.523-2H17a6 6 0 1 1-7-8V4z",
    ),
    Glyph(
        name="Saturn",
        path="M12 2a4 4 0 0 0-4 4h2a2 2 0 0 1 4 0v3h-3a4 4 0 1 0 0 8h3v5h2V4a4 4 0 0 0-4-2zm0 7h3v5h-3a2 2 0 1 1 0-5z",
    ),
    Glyph(
        name="Aries",
        path="M7 5a5 5 0 0 1 5-5 5 5 0 0 1 5 5v14h-2V5a3 3 0 0 0-3-3 3 3 0 0 0-3 3v14H7z",
    ),
    Glyph(
        name="Taurus",
        path="M8 3a4 4 0 0 1 8 0h-2a2 2 0 0 0-4 0H8zm4 5a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z",
    ),
    Glyph(
        name="Gemini",
        path="M8 2v2h1v14H8v2h8v-2h-1V4h1V2z",
    ),
    Glyph(
        name="Cancer",
        path="M8 7a4 4 0 1 1 0 8 4 4 0 0 1 0-8zm8-4a4 4 0 1 1 0 8 4 4 0 0 1 0-8z",
    ),
    Glyph(
        name="Leo",
        path="M12 2a5 5 0 0 1 5 5c0 1.657-.672 3.157-1.757 4.243A5.5 5.5 0 1 1 11 21h2a3.5 3.5 0 1 0 2.474-6.012 6.99 6.99 0 0 0 2.526-5.388A5 5 0 0 0 12 2z",
    ),
)
