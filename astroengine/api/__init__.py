"""FastAPI application factory and legacy transit helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .app import app, create_app, get_app

if TYPE_CHECKING:  # pragma: no cover - runtime side effects avoided during typing
    from astroengine.core.api import TransitEvent, TransitScanConfig
    from astroengine.core.transit_engine import TransitEngine, TransitEngineConfig

def _load_transit_engine() -> tuple[type["TransitEngine"], type["TransitEngineConfig"]]:
    """Import transit engine helpers lazily to avoid heavy dependencies."""

    from astroengine.core.transit_engine import TransitEngine, TransitEngineConfig

    return TransitEngine, TransitEngineConfig


def _load_transit_api() -> tuple[type["TransitEvent"], type["TransitScanConfig"]]:
    """Import public dataclasses exposed for backwards compatibility."""

    from astroengine.core.api import TransitEvent, TransitScanConfig

    return TransitEvent, TransitScanConfig


def __getattr__(name: str) -> Any:  # pragma: no cover - invoked via diagnostics
    """Preserve legacy re-exports from :mod:`astroengine.api`.

    Older integrations imported :class:`TransitEngine` and its related
    dataclasses directly from :mod:`astroengine.api`.  The FastAPI module was
    recently split out and those aliases were lost, breaking diagnostics and
    downstream tooling.  We restore the symbols here while keeping imports
    lazy so environments without Swiss Ephemeris support do not fail at import
    time.
    """

    if name in {"TransitEngine", "TransitEngineConfig"}:
        TransitEngine, TransitEngineConfig = _load_transit_engine()
        globals().update(
            {
                "TransitEngine": TransitEngine,
                "TransitEngineConfig": TransitEngineConfig,
            }
        )
        return globals()[name]
    if name in {"TransitEvent", "TransitScanConfig"}:
        TransitEvent, TransitScanConfig = _load_transit_api()
        globals().update(
            {
                "TransitEvent": TransitEvent,
                "TransitScanConfig": TransitScanConfig,
            }
        )
        return globals()[name]
    raise AttributeError(name)


def __dir__() -> list[str]:  # pragma: no cover - used for tooling hints only
    return sorted(
        set(globals())
        | {"TransitEngine", "TransitEngineConfig", "TransitEvent", "TransitScanConfig"}
    )
__all__ = [
    "app",
    "create_app",
    "get_app",
    "TransitEngine",
    "TransitEngineConfig",
    "TransitEvent",
    "TransitScanConfig",
]


