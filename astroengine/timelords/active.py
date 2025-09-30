"""Helpers to expose active timelord stacks for arbitrary timestamps."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .context import TimelordContext, build_context
from .models import TimelordPeriod, TimelordStack
from .profections import generate_profection_periods
from .utils import parse_iso
from .vimshottari import generate_vimshottari_periods
from .zodiacal import generate_zodiacal_releasing

__all__ = ["TimelordCalculator", "active_timelords"]

_SYSTEM_ORDER = {
    "profections": 0,
    "vimshottari": 1,
    "zodiacal_releasing": 2,
}

_LEVEL_ORDER = {
    "annual": 0,
    "monthly": 1,
    "daily": 2,
    "maha": 0,
    "antar": 1,
    "pratyantar": 2,
    "sookshma": 3,
    "praan": 4,
    "l1": 0,
    "l2": 1,
    "l3": 2,
    "l4": 3,
}

_SYSTEM_ALIASES = {
    "profections": {"profections"},
    "vimshottari": {"vimshottari"},
    "zodiacal_releasing": {"zodiacal_releasing_spirit", "zodiacal_releasing_fortune"},
    "zr_spirit": {"zodiacal_releasing_spirit"},
    "zr_fortune": {"zodiacal_releasing_fortune"},
    "zodiacal_releasing_spirit": {"zodiacal_releasing_spirit"},
    "zodiacal_releasing_fortune": {"zodiacal_releasing_fortune"},
}

_DEFAULT_SYSTEMS = ("profections", "vimshottari", "zodiacal_releasing_spirit")


def _resolve_systems(
    systems: tuple[str, ...] | None,
    include_fortune: bool,
) -> set[str]:
    if systems is None:
        selected = {name for alias in _DEFAULT_SYSTEMS for name in _SYSTEM_ALIASES[alias]}
        if include_fortune:
            selected.add("zodiacal_releasing_fortune")
        return selected

    resolved: set[str] = set()
    for system in systems:
        key = system.lower()
        aliases = _SYSTEM_ALIASES.get(key)
        if not aliases:
            raise ValueError(f"unknown timelord system '{system}'")
        resolved.update(aliases)

    if "zodiacal_releasing_fortune" in resolved and not include_fortune:
        raise ValueError(
            "include_fortune must be True to compute zodiacal releasing for fortune"
        )
    if not resolved:
        raise ValueError("at least one timelord system must be selected")
    return resolved


@dataclass
class TimelordCalculator:
    """Precomputes timelord periods for repeated lookups."""

    context: TimelordContext
    until: datetime
    include_fortune: bool = False
    systems: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        selected = _resolve_systems(self.systems, self.include_fortune)

        self.profections = (
            generate_profection_periods(self.context, self.until)
            if "profections" in selected
            else []
        )
        self.vimshottari = (
            generate_vimshottari_periods(self.context, self.until)
            if "vimshottari" in selected
            else []
        )
        self.zr_spirit = (
            generate_zodiacal_releasing(self.context, self.until, lot="spirit")
            if "zodiacal_releasing_spirit" in selected
            else []
        )
        self.zr_fortune = (
            generate_zodiacal_releasing(self.context, self.until, lot="fortune")
            if "zodiacal_releasing_fortune" in selected
            else []
        )

    def iter_periods(self) -> Iterable[TimelordPeriod]:
        yield from self.profections
        yield from self.vimshottari
        yield from self.zr_spirit
        yield from self.zr_fortune

    def active_stack(self, moment: datetime) -> TimelordStack:
        reference = moment.astimezone(UTC)
        active: list[TimelordPeriod] = []
        for period in self.iter_periods():
            if period.contains(reference):
                active.append(period)
        active.sort(key=_period_sort_key)
        return TimelordStack(moment=reference, periods=tuple(active))


def _period_sort_key(period: TimelordPeriod) -> tuple[int, int]:
    system_rank = _SYSTEM_ORDER.get(period.system, 99)
    level_rank = _LEVEL_ORDER.get(period.level, 99)
    return (system_rank, level_rank)


def active_timelords(
    natal_ts: str,
    lat: float,
    lon: float,
    target_ts: str,
    *,
    include_fortune: bool = False,
    horizon_ts: str | None = None,
) -> TimelordStack:
    """Return the timelord stack active at ``target_ts``."""

    natal_moment = parse_iso(natal_ts)
    target = parse_iso(target_ts)
    horizon = parse_iso(horizon_ts) if horizon_ts else target + timedelta(days=1)
    if horizon <= target:
        horizon = target + timedelta(days=1)
    context = build_context(natal_moment, lat, lon)
    calculator = TimelordCalculator(
        context=context,
        until=horizon,
        include_fortune=include_fortune,
    )
    return calculator.active_stack(target)
