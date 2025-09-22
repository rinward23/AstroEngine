"""Transit scanning utilities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from .config import ChartConfig
from ..ephemeris import SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator
from .natal import DEFAULT_BODIES, NatalChart

__all__ = ["TransitContact", "TransitScanner"]


@dataclass(frozen=True)
class TransitContact:
    """Record describing a transit aspect between a moving and natal body."""

    moment: datetime
    julian_day: float
    transiting_body: str
    natal_body: str
    angle: int
    orb: float
    separation: float


def _circular_delta(a: float, b: float) -> float:
    diff = (b - a) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


class TransitScanner:
    """Compute transit contacts against a natal chart."""

    def __init__(
        self,
        *,
        adapter: SwissEphemerisAdapter | None = None,
        orb_calculator: OrbCalculator | None = None,
        aspect_angles: Sequence[int] | None = None,
        orb_profile: str = "standard",
        chart_config: ChartConfig | None = None,
    ) -> None:
        self.chart_config = chart_config or ChartConfig()
        self.adapter = adapter or SwissEphemerisAdapter.from_chart_config(self.chart_config)
        self.orb_calculator = orb_calculator or OrbCalculator()
        self.aspect_angles = tuple(aspect_angles or DEFAULT_ASPECTS)
        self.orb_profile = orb_profile

    def scan(
        self,
        natal_chart: NatalChart,
        moment: datetime,
        *,
        bodies: Mapping[str, int] | None = None,
    ) -> tuple[TransitContact, ...]:
        """Return a tuple of transit contacts for the supplied moment."""

        jd_ut = self.adapter.julian_day(moment)
        body_map = bodies or DEFAULT_BODIES
        transiting_positions = self.adapter.body_positions(jd_ut, body_map)
        contacts: list[TransitContact] = []
        for transiting_name, transiting_position in transiting_positions.items():
            for natal_name, natal_position in natal_chart.positions.items():
                separation = _circular_delta(
                    transiting_position.longitude, natal_position.longitude
                )
                for angle in self.aspect_angles:
                    orb = abs(separation - angle)
                    threshold = self.orb_calculator.orb_for(
                        transiting_name,
                        natal_name,
                        angle,
                        profile=self.orb_profile,
                    )
                    if orb <= threshold:
                        contacts.append(
                            TransitContact(
                                moment=moment,
                                julian_day=jd_ut,
                                transiting_body=transiting_name,
                                natal_body=natal_name,
                                angle=int(angle),
                                orb=orb,
                                separation=separation,
                            )
                        )
                        break
        contacts.sort(key=lambda item: (item.orb, item.transiting_body, item.natal_body))
        return tuple(contacts)
