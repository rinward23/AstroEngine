"""Jinja2 utilities for rendering markdown snippets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - optional dependency path
    from jinja2 import Environment, StrictUndefined
except ImportError:  # pragma: no cover - fallback when jinja2 unavailable
    Environment = None  # type: ignore[assignment]
    StrictUndefined = None  # type: ignore[assignment]


@dataclass(slots=True)
class TemplateRenderer:
    """Lightweight renderer that only activates when Jinja2 is installed."""

    environment_factory: Callable[[], Environment | None]

    def render(self, template: str, context: dict[str, Any]) -> str:
        env = self.environment_factory()
        if env is None:
            raise RuntimeError("Jinja2 is required to render rulepack templates.")
        return env.from_string(template).render(**context)


def _create_environment() -> Environment | None:
    if Environment is None:
        return None

    env = Environment(undefined=StrictUndefined, autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env.filters.update(
        {
            "round": lambda value, digits=0: round(float(value), int(digits)),
            "deg": lambda value: f"{float(value):.2f}°",
        }
    )
    return env


def get_renderer() -> TemplateRenderer:
    """Return a singleton renderer for markdown templates."""

    return TemplateRenderer(environment_factory=_create_environment)


__all__ = ["TemplateRenderer", "get_renderer"]
