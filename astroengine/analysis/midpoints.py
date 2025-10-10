"""Midpoint helpers used by AstroEngine analysis surfaces."""

from __future__ import annotations

import math
from collections.abc import Mapping
from functools import lru_cache

from astroengine.config import MidpointsCfg, default_settings
from astroengine.runtime_config import runtime_settings
from astroengine.utils.angles import delta_angle, norm360

__all__ = [
    "compute_midpoints",
    "get_midpoint_settings",
    "midpoint_longitude",
]


def midpoint_longitude(lon_a: float, lon_b: float) -> float:
    """Return the circular midpoint between ``lon_a`` and ``lon_b`` in degrees."""

    a = norm360(float(lon_a))
    b = norm360(float(lon_b))
    return norm360(a + delta_angle(a, b) / 2.0)


@lru_cache(maxsize=1)
def _cached_midpoint_settings() -> MidpointsCfg:
    """Load midpoint settings from disk with caching."""

    try:
        settings = runtime_settings.persisted()
    except Exception:  # pragma: no cover - defensive fallback when settings missing
        settings = default_settings()
    cfg = getattr(settings, "midpoints", None)
    if isinstance(cfg, MidpointsCfg):
        return cfg
    # Accept plain dictionaries when legacy configs are loaded.
    return MidpointsCfg.model_validate(cfg or {})


def get_midpoint_settings(*, force_reload: bool = False) -> MidpointsCfg:
    """Return the configured midpoint settings.

    Parameters
    ----------
    force_reload:
        When ``True`` the settings cache is cleared before reloading.
    """

    if force_reload:
        _cached_midpoint_settings.cache_clear()
    return _cached_midpoint_settings()


def _canonical_pair(name_a: str, name_b: str) -> tuple[str, str]:
    return tuple(sorted((name_a, name_b), key=str.casefold))


def _pair_depth(pair: tuple[str, str]) -> int:
    return max(segment.count("/") for segment in pair) + 1


def _should_include(name: str, include_nodes: bool) -> bool:
    if include_nodes:
        return True
    lowered = name.lower()
    return "node" not in lowered


def _normalize_longitudes(
    chart_longitudes: Mapping[str, float], include_nodes: bool
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for raw_name, raw_value in chart_longitudes.items():
        if raw_value is None:
            continue
        name = str(raw_name)
        if not name:
            continue
        if not _should_include(name, include_nodes):
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isnan(value):
            continue
        normalized[name] = norm360(value)
    return normalized


def compute_midpoints(
    chart_longitudes: Mapping[str, float],
    include_nodes: bool = True,
) -> dict[tuple[str, str], float]:
    """Return midpoint degrees for every unique pair in ``chart_longitudes``.

    Midpoints are only calculated when the feature is enabled in settings. When
    midpoint tree expansion is enabled the function will cascade midpoint
    calculations for midpoint pairs up to ``max_depth`` levels.
    """

    cfg = get_midpoint_settings()
    if not cfg.enabled:
        return {}

    include_nodes = bool(include_nodes and cfg.include_nodes)
    base_positions = _normalize_longitudes(chart_longitudes, include_nodes)
    if len(base_positions) < 2:
        return {}

    names = sorted(base_positions.keys(), key=str.casefold)
    pairs: dict[tuple[str, str], float] = {}
    seen_pairs: set[tuple[str, str]] = set()
    current_level: list[tuple[str, float]] = [(name, base_positions[name]) for name in names]
    max_depth = 1
    if cfg.tree.enabled:
        max_depth = max(1, int(cfg.tree.max_depth))

    for depth in range(1, max_depth + 1):
        next_level: list[tuple[str, float]] = []
        level_labels: set[str] = set()
        for index, (name_a, lon_a) in enumerate(current_level):
            for name_b, lon_b in current_level[index + 1 :]:
                pair = _canonical_pair(name_a, name_b)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                midpoint = midpoint_longitude(lon_a, lon_b)
                pairs[pair] = midpoint
                if depth < max_depth:
                    label = f"{pair[0]}/{pair[1]}"
                    if label not in level_labels:
                        level_labels.add(label)
                        next_level.append((label, midpoint))
        if not next_level:
            break
        current_level = next_level
        if len(current_level) < 2:
            break

    ordered = sorted(
        pairs.items(),
        key=lambda item: (_pair_depth(item[0]), item[0][0].casefold(), item[0][1].casefold()),
    )
    return dict(ordered)
