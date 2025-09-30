"""Horary significator selection and reception mapping."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ...chart.natal import NatalChart
from ...ephemeris.swisseph_adapter import HousePositions
from .models import Significator, SignificatorSet
from .profiles import HoraryProfile
from .rulers import (
    dignities_at,
    house_ruler,
    sign_from_longitude,
)

__all__ = ["choose_significators"]


@dataclass(frozen=True)
class _BodyPosition:
    longitude: float
    latitude: float
    speed: float


_DEF_QUESTED_ROLES = {
    "domicile": "quesited_dispositor",
    "exaltation": "quesited_exaltation_ruler",
    "triplicity": "quesited_triplicity_ruler",
}


def _house_for(longitude: float, houses: HousePositions) -> int:
    cusps = [c % 360.0 for c in houses.cusps[:12]]
    lon = float(longitude) % 360.0
    for idx in range(12):
        start = cusps[idx]
        end = cusps[(idx + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return idx + 1
        else:
            if lon >= start or lon < end:
                return idx + 1
    return 12


def _collect_receptions(body: str, status) -> dict[str, tuple[str, ...]]:
    mapping: dict[str, list[str]] = {}
    for key in ("domicile", "exaltation", "triplicity", "term", "face"):
        ruler = getattr(status, key)
        if ruler and ruler != body:
            mapping.setdefault(ruler, []).append(key)
    return {target: tuple(values) for target, values in mapping.items()}


def _make_significator(
    body: str,
    role: str,
    positions: Mapping[str, _BodyPosition],
    houses: HousePositions,
    profile: HoraryProfile,
    *,
    is_day_chart: bool,
) -> Significator:
    pos = positions[body]
    dignity = dignities_at(body, pos.longitude, profile=profile, is_day_chart=is_day_chart)
    receptions = _collect_receptions(body, dignity)
    return Significator(
        body=body,
        longitude=pos.longitude % 360.0,
        latitude=pos.latitude,
        speed=pos.speed,
        house=_house_for(pos.longitude, houses),
        dignities=dignity,
        receptions=receptions,
        role=role,
    )


def _cast_positions(chart: NatalChart) -> Mapping[str, _BodyPosition]:
    positions: dict[str, _BodyPosition] = {}
    for name, pos in chart.positions.items():
        positions[name] = _BodyPosition(
            longitude=pos.longitude,
            latitude=pos.latitude,
            speed=pos.speed_longitude,
        )
    return positions


def choose_significators(
    chart: NatalChart,
    quesited_house: int,
    profile: HoraryProfile,
    *,
    is_day_chart: bool,
) -> SignificatorSet:
    """Return horary significators based on the chart and question context."""

    if not 1 <= int(quesited_house) <= 12:
        raise ValueError("quesited_house must be between 1 and 12")

    houses = chart.houses
    positions = _cast_positions(chart)

    asc_sign = sign_from_longitude(houses.ascendant)
    asc_ruler = house_ruler(asc_sign)

    quesited_cusp = houses.cusps[quesited_house - 1]
    quesited_sign = sign_from_longitude(quesited_cusp)
    quesited_ruler = house_ruler(quesited_sign)

    if asc_ruler not in positions:
        raise KeyError(f"Ascendant ruler '{asc_ruler}' not present in chart positions")
    if quesited_ruler not in positions:
        raise KeyError(f"Quesited ruler '{quesited_ruler}' not present in chart positions")
    if "Moon" not in positions:
        raise KeyError("Moon position missing from chart data")

    querent = _make_significator(
        asc_ruler,
        role="querent_ruler",
        positions=positions,
        houses=houses,
        profile=profile,
        is_day_chart=is_day_chart,
    )
    quesited = _make_significator(
        quesited_ruler,
        role="quesited_ruler",
        positions=positions,
        houses=houses,
        profile=profile,
        is_day_chart=is_day_chart,
    )
    moon = _make_significator(
        "Moon",
        role="querent_co_ruler",
        positions=positions,
        houses=houses,
        profile=profile,
        is_day_chart=is_day_chart,
    )

    co_significators: list[Significator] = []
    for name, pos in positions.items():
        if name in {querent.body, quesited.body, moon.body}:
            continue
        house = _house_for(pos.longitude, houses)
        if house == quesited_house:
            co_significators.append(
                _make_significator(
                    name,
                    role=f"quesited_house_body_{name.lower()}",
                    positions=positions,
                    houses=houses,
                    profile=profile,
                    is_day_chart=is_day_chart,
                )
            )

    return SignificatorSet(
        querent=querent,
        quesited=quesited,
        moon=moon,
        co_significators=tuple(co_significators),
        is_day_chart=is_day_chart,
    )

