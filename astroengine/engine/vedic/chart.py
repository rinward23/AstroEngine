"""Helpers for building sidereal charts and contexts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from ...chart import ChartLocation, NatalChart, compute_natal_chart
from ...chart.config import ChartConfig, normalize_ayanamsha_name
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter

__all__ = ["VedicChartContext", "compute_sidereal_chart", "build_context"]


@dataclass(frozen=True)
class VedicChartContext:
    """Container linking a sidereal chart with its runtime configuration."""

    chart: NatalChart
    config: ChartConfig
    adapter: SwissEphemerisAdapter

    @property
    def moment(self) -> datetime:
        return self.chart.moment

    @property
    def location(self) -> ChartLocation:
        return self.chart.location


def _normalize_datetime(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        raise ValueError("datetime must be timezone-aware")
    return moment.astimezone(UTC)


def compute_sidereal_chart(
    moment: datetime,
    location: ChartLocation,
    *,
    ayanamsa: str = "lahiri",
    house_system: str | None = None,
    bodies: Mapping[str, int] | None = None,
    nodes_variant: str = "mean",
) -> NatalChart:
    """Compute a sidereal natal chart using the requested ayanamsa."""

    normalized = normalize_ayanamsha_name(ayanamsa)
    config = ChartConfig(
        zodiac="sidereal",
        ayanamsha=normalized,
        house_system=house_system or "whole_sign",
        nodes_variant=nodes_variant,
    )
    adapter = SwissEphemerisAdapter.from_chart_config(config)
    return compute_natal_chart(
        _normalize_datetime(moment),
        location,
        bodies=bodies,
        config=config,
        adapter=adapter,
    )


def build_context(
    moment: datetime,
    latitude: float,
    longitude: float,
    *,
    ayanamsa: str = "lahiri",
    house_system: str | None = None,
    bodies: Mapping[str, int] | None = None,
    nodes_variant: str = "mean",
) -> VedicChartContext:
    """Return a :class:`VedicChartContext` for API and dasha helpers."""

    location = ChartLocation(latitude=latitude, longitude=longitude)
    normalized = normalize_ayanamsha_name(ayanamsa)
    config = ChartConfig(
        zodiac="sidereal",
        ayanamsha=normalized,
        house_system=house_system or "whole_sign",
        nodes_variant=nodes_variant,
    )
    adapter = SwissEphemerisAdapter.from_chart_config(config)
    chart = compute_natal_chart(
        _normalize_datetime(moment),
        location,
        bodies=bodies,
        config=config,
        adapter=adapter,
    )
    return VedicChartContext(chart=chart, config=config, adapter=adapter)
