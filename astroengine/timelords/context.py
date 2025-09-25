"""Natal context helpers shared by timelord calculators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..chart import ChartLocation, compute_natal_chart
from ..ephemeris import SwissEphemerisAdapter

__all__ = ["TimelordContext", "build_context"]


@dataclass(frozen=True)
class TimelordContext:
    """Shared natal chart inputs used by timelord calculators."""

    moment: datetime
    location: ChartLocation
    chart: object
    adapter: SwissEphemerisAdapter


def build_context(
    natal_moment: datetime,
    latitude: float,
    longitude: float,
    *,
    adapter: SwissEphemerisAdapter | None = None,
) -> TimelordContext:
    """Create a :class:`TimelordContext` from natal inputs."""

    adapter = adapter or SwissEphemerisAdapter()
    location = ChartLocation(latitude=latitude, longitude=longitude)
    chart = compute_natal_chart(natal_moment.astimezone(UTC), location, adapter=adapter)
    return TimelordContext(
        moment=natal_moment.astimezone(UTC),
        location=location,
        chart=chart,
        adapter=adapter,
    )
