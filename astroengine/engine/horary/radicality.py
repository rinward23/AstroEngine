"""Policy-driven radicality checks for horary cases."""

from __future__ import annotations

from datetime import timedelta

from ...chart.natal import NatalChart
from ...utils.angles import delta_angle
from .aspects_logic import aspect_between
from .hour_ruler import PlanetaryHourResult
from .models import RadicalityCheck, SignificatorSet
from .profiles import HoraryProfile
from .rulers import degree_in_sign

__all__ = ["run_checks"]


def _house_for(longitude: float, cusps: tuple[float, ...]) -> int:
    lon = float(longitude) % 360.0
    values = [c % 360.0 for c in cusps[:12]]
    for idx in range(12):
        start = values[idx]
        end = values[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def _moon_exit_time(chart: NatalChart) -> timedelta | None:
    moon = chart.positions.get("Moon")
    if moon is None:
        return None
    lon = moon.longitude % 360.0
    remaining = ((int(lon // 30) + 1) * 30.0) - lon
    speed = abs(moon.speed_longitude)
    if speed <= 0:
        return None
    return timedelta(days=remaining / speed)


def run_checks(
    chart: NatalChart,
    profile: HoraryProfile,
    significators: SignificatorSet,
    hour: PlanetaryHourResult,
) -> list[RadicalityCheck]:
    """Return radicality cautions for the supplied horary case."""

    policy = profile.radicality_policy()
    checks: list[RadicalityCheck] = []

    asc_deg = degree_in_sign(chart.houses.ascendant)
    if asc_deg < policy.asc_early_deg:
        checks.append(
            RadicalityCheck(
                code="asc_early",
                flag=True,
                reason=f"Ascendant at {asc_deg:.2f}° is earlier than {policy.asc_early_deg:.1f}°",
                data={"ascendant_degree": asc_deg},
                caution_weight=-5.0,
            )
        )
    if asc_deg > policy.asc_late_deg:
        checks.append(
            RadicalityCheck(
                code="asc_late",
                flag=True,
                reason=f"Ascendant at {asc_deg:.2f}° is later than {policy.asc_late_deg:.1f}°",
                data={"ascendant_degree": asc_deg},
                caution_weight=-5.0,
            )
        )

    hour_ruler = hour.ruler
    asc_ruler = significators.querent.body
    dignities = significators.querent.dignities
    agreement = hour_ruler == asc_ruler or hour_ruler in {
        dignities.triplicity,
        dignities.exaltation,
    }
    checks.append(
        RadicalityCheck(
            code="hour_agreement",
            flag=not agreement,
            reason=(
                "Planetary hour ruler agrees with the Ascendant ruler"
                if agreement
                else "Planetary hour ruler does not agree with the Ascendant ruler"
            ),
            data={"hour_ruler": hour_ruler, "asc_ruler": asc_ruler},
            caution_weight=0.0 if agreement else -4.0,
        )
    )

    # Void of course Moon
    moon = chart.positions.get("Moon")
    if moon is not None:
        exit_delta = _moon_exit_time(chart)
        exit_deadline = chart.moment + exit_delta if exit_delta else None
        will_perfect = False
        for other in chart.positions:
            if other == "Moon":
                continue
            contact = aspect_between(chart, "Moon", other, profile)
            if not contact or not contact.applying:
                continue
            if contact.perfection_time is None:
                will_perfect = True
                break
            if exit_deadline is None or contact.perfection_time <= exit_deadline:
                will_perfect = True
                break
        checks.append(
            RadicalityCheck(
                code="moon_voc",
                flag=not will_perfect,
                reason=(
                    "Moon applies to an aspect before leaving its sign"
                    if will_perfect
                    else "Moon is void of course before changing sign"
                ),
                data={"moon_longitude": moon.longitude % 360.0},
                caution_weight=0.0 if will_perfect else -8.0,
            )
        )

    saturn = chart.positions.get("Saturn")
    if saturn is not None:
        house = _house_for(saturn.longitude, chart.houses.cusps)
        if house == 7:
            checks.append(
                RadicalityCheck(
                    code="saturn_in_7th",
                    flag=True,
                    reason="Saturn is in the 7th house, cautioning the astrologer's judgement",
                    data={"saturn_longitude": saturn.longitude % 360.0},
                    caution_weight=-6.0,
                )
            )

    node = chart.positions.get("True Node") or chart.positions.get("Mean Node")
    if node is not None:
        south_lon = (node.longitude + 180.0) % 360.0
        asc_lon = chart.houses.ascendant % 360.0
        distance = abs(delta_angle(asc_lon, south_lon))
        if distance <= policy.south_node_on_asc_orb:
            checks.append(
                RadicalityCheck(
                    code="south_node_asc",
                    flag=True,
                    reason="South Node closely conjoins the Ascendant",
                    data={"distance": distance},
                    caution_weight=-4.0,
                )
            )

    sun = chart.positions.get("Sun")
    if sun is not None:
        for role in ("querent", "quesited"):
            sig = getattr(significators, role)
            distance = abs(delta_angle(sun.longitude, sig.longitude))
            if distance <= 0.17:
                checks.append(
                    RadicalityCheck(
                        code=f"{role}_cazimi",
                        flag=False,
                        reason=f"{sig.body} is in Cazimi (within 0.17° of the Sun)",
                        data={"distance": distance},
                        caution_weight=3.0,
                    )
                )
            elif distance <= 8.0:
                checks.append(
                    RadicalityCheck(
                        code=f"{role}_combust",
                        flag=True,
                        reason=f"{sig.body} is combust the Sun (within 8°)",
                        data={"distance": distance},
                        caution_weight=-6.0,
                    )
                )
            elif distance <= 17.0:
                checks.append(
                    RadicalityCheck(
                        code=f"{role}_under_beams",
                        flag=True,
                        reason=f"{sig.body} is under the Sun's beams (within 17°)",
                        data={"distance": distance},
                        caution_weight=-3.0,
                    )
                )

    return checks

