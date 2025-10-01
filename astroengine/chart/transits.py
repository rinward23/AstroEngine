"""Transit scanning utilities."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..ephemeris import BodyPosition, SwissEphemerisAdapter
from ..scoring import DEFAULT_ASPECTS, OrbCalculator
from .config import ChartConfig
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
    orb_allow: float
    ingress: datetime | None
    ingress_jd: float | None
    egress: datetime | None
    egress_jd: float | None


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
        self.adapter = adapter or SwissEphemerisAdapter.from_chart_config(
            self.chart_config
        )

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
                        body_code = body_map.get(transiting_name)
                        ingress_dt, ingress_jd = self._refine_contact_boundary(
                            body_name=transiting_name,
                            body_code=body_code,
                            natal_longitude=natal_position.longitude,
                            angle=float(angle),
                            threshold=threshold,
                            center=moment,
                            direction=-1,
                            position_at_center=transiting_position,
                        )
                        egress_dt, egress_jd = self._refine_contact_boundary(
                            body_name=transiting_name,
                            body_code=body_code,
                            natal_longitude=natal_position.longitude,
                            angle=float(angle),
                            threshold=threshold,
                            center=moment,
                            direction=1,
                            position_at_center=transiting_position,
                        )
                        contacts.append(
                            TransitContact(
                                moment=moment,
                                julian_day=jd_ut,
                                transiting_body=transiting_name,
                                natal_body=natal_name,
                                angle=int(angle),
                                orb=orb,
                                separation=separation,
                                orb_allow=threshold,
                                ingress=ingress_dt,
                                ingress_jd=ingress_jd,
                                egress=egress_dt,
                                egress_jd=egress_jd,
                            )
                        )
                        break
        contacts.sort(
            key=lambda item: (item.orb, item.transiting_body, item.natal_body)
        )
        return tuple(contacts)

    def _refine_contact_boundary(
        self,
        *,
        body_name: str,
        body_code: int | None,
        natal_longitude: float,
        angle: float,
        threshold: float,
        center: datetime,
        direction: int,
        position_at_center: BodyPosition,
    ) -> tuple[datetime | None, float | None]:
        """Return the datetime/JD when the contact crosses the orb boundary."""

        if body_code is None:
            return None, None

        center_utc = center.astimezone(UTC)

        def separation_at(moment: datetime, *, use_center: bool = False) -> float:
            if use_center:
                pos = position_at_center
            else:
                jd = self.adapter.julian_day(moment)
                pos = self.adapter.body_position(jd, body_code, body_name=body_name)
            return _circular_delta(pos.longitude, natal_longitude)

        current_sep = separation_at(center_utc, use_center=True)

        def metric(moment: datetime) -> float:
            sep = separation_at(moment)
            return abs(sep - angle) - threshold

        current_delta = abs(current_sep - angle)
        inside_val = current_delta - threshold
        # Positive ``inside_val`` would indicate the supplied ``center`` is
        # already outside the orb. Bail out instead of producing misleading
        # boundaries.
        if inside_val > 1e-9:
            return None, None

        speed_per_hour = max(abs(position_at_center.speed_longitude) / 24.0, 1e-6)
        delta_deg = max(threshold - current_delta, threshold * 0.1, 1e-3)
        approx_hours = max(delta_deg / speed_per_hour, 0.5)
        step_hours = min(max(approx_hours / 6.0, 0.25), 12.0)
        max_span_hours = min(max(approx_hours * 6.0, 24.0), 24.0 * 365.0)

        step = timedelta(hours=step_hours * float(direction))
        prev_dt = center_utc
        initial_val = metric(prev_dt)
        if not math.isfinite(initial_val) or initial_val > 0.0:
            return None, None

        traversed = 0.0
        boundary_inside = prev_dt
        boundary_outside: datetime | None = None
        while traversed <= max_span_hours:
            candidate = prev_dt + step
            traversed += step_hours
            val = metric(candidate)
            if not math.isfinite(val):
                return None, None
            if val >= 0.0:
                boundary_inside = prev_dt
                boundary_outside = candidate
                break
            prev_dt = candidate

        if boundary_outside is None:
            return None, None

        inside_dt = boundary_inside
        outside_dt = boundary_outside
        for _ in range(48):
            delta = outside_dt - inside_dt
            if abs(delta.total_seconds()) <= 1.0:
                midpoint = inside_dt + delta / 2
                return midpoint, self.adapter.julian_day(midpoint)
            midpoint = inside_dt + delta / 2
            mid_val = metric(midpoint)
            if not math.isfinite(mid_val):
                return None, None
            if mid_val > 0.0:
                outside_dt = midpoint
            else:
                inside_dt = midpoint

        midpoint = inside_dt + (outside_dt - inside_dt) / 2
        return midpoint, self.adapter.julian_day(midpoint)
