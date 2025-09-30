"""Theme management for AstroEngine visualisations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Optional


@dataclass(frozen=True)
class VizTheme:
    """A lightweight collection of tokens used when rendering SVG scenes."""

    identifier: str
    name: str
    colors: Mapping[str, str] = field(default_factory=dict)
    fonts: Mapping[str, str] = field(default_factory=dict)
    sizes: Mapping[str, float] = field(default_factory=dict)
    strokes: Mapping[str, float] = field(default_factory=dict)
    extras: Mapping[str, object] = field(default_factory=dict)

    def color(self, role: str, default: Optional[str] = None) -> Optional[str]:
        return self.colors.get(role, default)

    def font(self, role: str, default: Optional[str] = None) -> Optional[str]:
        return self.fonts.get(role, default)

    def size(self, token: str, default: Optional[float] = None) -> Optional[float]:
        return self.sizes.get(token, default)

    def stroke(self, token: str, default: Optional[float] = None) -> Optional[float]:
        return self.strokes.get(token, default)

    def to_payload(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "name": self.name,
            "colors": dict(self.colors),
            "fonts": dict(self.fonts),
            "sizes": dict(self.sizes),
            "strokes": dict(self.strokes),
            "extras": dict(self.extras),
        }


class ThemeManager:
    """Registry and loader for :class:`VizTheme` instances."""

    def __init__(self, themes: Optional[Iterable[VizTheme]] = None) -> None:
        self._themes: MutableMapping[str, VizTheme] = {}
        if themes:
            for theme in themes:
                self.register(theme)

    def register(self, theme: VizTheme) -> None:
        if theme.identifier in self._themes:
            raise ValueError(f"Theme '{theme.identifier}' already registered")
        self._themes[theme.identifier] = theme

    def replace(self, theme: VizTheme) -> None:
        """Insert or update a theme without raising."""

        self._themes[theme.identifier] = theme

    def get(self, identifier: str) -> VizTheme:
        try:
            return self._themes[identifier]
        except KeyError as exc:
            raise KeyError(f"Unknown theme '{identifier}'") from exc

    def load_from_payload(self, payload: Mapping[str, object]) -> VizTheme:
        identifier = str(payload.get("identifier"))
        name = str(payload.get("name", identifier))
        colors = _as_mapping(payload.get("colors"))
        fonts = _as_mapping(payload.get("fonts"))
        sizes = {k: float(v) for k, v in _as_mapping(payload.get("sizes")).items()}
        strokes = {k: float(v) for k, v in _as_mapping(payload.get("strokes")).items()}
        extras = _as_mapping(payload.get("extras"))
        theme = VizTheme(identifier, name, colors, fonts, sizes, strokes, extras)
        self.replace(theme)
        return theme

    def default_theme(self) -> VizTheme:
        if not self._themes:
            self.register(DEFAULT_THEME)
        # ``next(iter(...))`` is safe because a default is always present
        # after the above guard.
        return next(iter(self._themes.values()))

    def list_themes(self) -> Mapping[str, VizTheme]:
        return dict(self._themes)


def _as_mapping(source: object) -> Dict[str, object]:
    if source is None:
        return {}
    if isinstance(source, Mapping):
        return dict(source)
    raise TypeError("Theme payload sections must be mappings")


DEFAULT_THEME = VizTheme(
    identifier="astroengine-default",
    name="AstroEngine Default",
    colors={
        "background": "#0d1117",
        "foreground": "#f0f6fc",
        "accent": "#58a6ff",
        "secondary": "#8b949e",
        "warning": "#f85149",
    },
    fonts={
        "label": "Inter, 'Helvetica Neue', Arial, sans-serif",
        "mono": "'JetBrains Mono', 'Fira Code', monospace",
    },
    sizes={
        "label": 12.0,
        "title": 18.0,
        "glyph": 16.0,
    },
    strokes={
        "default": 1.0,
        "accent": 1.5,
        "emphasis": 2.0,
    },
)
