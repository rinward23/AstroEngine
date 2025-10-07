from __future__ import annotations

from collections.abc import Iterable

from core.viz_plus.wheel_svg import build_aspect_hits

ASPECT_SYMBOLS = {
    "conjunction": "☌",
    "opposition": "☍",
    "trine": "△",
    "square": "□",
    "sextile": "✶",
    "quincunx": "⚻",
}


def render_aspect_grid(hits: list[dict]) -> dict[str, dict[str, str]]:
    """Return an aspect grid keyed by object with mirrored pairs."""

    grid: dict[str, dict[str, str]] = {}
    for hit in hits:
        a = hit["a"]
        b = hit["b"]
        aspect = hit["aspect"]
        grid.setdefault(a, {})[b] = aspect
        grid.setdefault(b, {})[a] = aspect
    return grid


def aspect_grid_symbols(
    positions: dict[str, float] | None = None,
    aspects: Iterable[str] | None = None,
    policy: dict | None = None,
    hits: list[dict] | None = None,
) -> dict[str, dict[str, str]]:
    """Return a mirrored aspect grid populated with glyphs.

    When ``hits`` are provided they take precedence, ensuring that symbol grids
    rendered alongside tabular hits reuse the exact same matches.
    """

    if hits is None:
        if positions is None or aspects is None or policy is None:
            raise ValueError("positions, aspects, and policy are required when hits are not provided")
        hits = build_aspect_hits(positions, aspects, policy)

    grid: dict[str, dict[str, str]] = {}
    for hit in hits:
        a, b, asp = hit["a"], hit["b"], hit["aspect"]
        symbol = ASPECT_SYMBOLS.get(asp, asp)
        grid.setdefault(a, {})[b] = symbol
        grid.setdefault(b, {})[a] = symbol
    return grid
