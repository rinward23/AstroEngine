"""Built-in interpretation profiles."""

from __future__ import annotations

DEFAULT_PROFILES = {
    "balanced": {"tags": {"chemistry": 1.0, "stability": 1.0, "growth": 1.0, "friction": 1.0}},
}

__all__ = ["DEFAULT_PROFILES"]
