"""Ephemeris provider resolution for Davison composites."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Callable, Iterable

from .telemetry import get_logger

PositionProvider = Callable[[datetime], dict[str, float]]


@lru_cache(maxsize=8)
def _provider_instance(name: str, node_policy: str):
    name = name.lower()
    if name == "swiss":
        try:
            from astroengine.providers.swiss_provider import SwissProvider
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Swiss ephemeris unavailable") from exc
        provider = SwissProvider()
        if hasattr(provider, "configure"):
            try:
                provider.configure(nodes_variant=node_policy)
            except Exception as exc:  # pragma: no cover - configuration failure
                get_logger().warning(
                    "swiss.configure.failed",
                    extra={"error": str(exc), "request_id": "-"},
                )
        return provider
    if name == "skyfield":
        try:
            from astroengine.providers.skyfield_provider import SkyfieldProvider
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Skyfield ephemeris unavailable") from exc
        return SkyfieldProvider()
    raise ValueError(f"Unsupported ephemeris '{name}'")


def make_position_provider(name: str, node_policy: str, bodies: Iterable[str]) -> PositionProvider:
    bodies_tuple = tuple(sorted(set(bodies)))
    provider = _provider_instance(name, node_policy)

    def _inner(ts: datetime) -> dict[str, float]:
        iso = ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        data = provider.positions_ecliptic(iso, bodies_tuple)
        if not isinstance(data, dict):
            raise TypeError("Ephemeris provider returned unexpected payload")
        out: dict[str, float] = {}
        for body in bodies_tuple:
            entry = data.get(body)
            if entry is None:
                continue
            lon = entry.get("lon")
            if lon is None:
                continue
            out[body] = float(lon) % 360.0
        return out

    return _inner


__all__ = ["make_position_provider", "PositionProvider"]
