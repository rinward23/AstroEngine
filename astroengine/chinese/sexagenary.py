"""Utilities for working with the sixty Jia-Zi combinations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, tzinfo
from typing import Final

from .constants import EARTHLY_BRANCHES, HEAVENLY_STEMS

SEXAGENARY_CYCLE_LENGTH: Final[int] = 60

# Reference day: 1984-02-02 (Jia Zi) widely used in almanacs.
_DAY_ZERO = date(1984, 2, 2)
_DAY_ZERO_INDEX: Final[int] = 0


@dataclass(frozen=True)
class SexagenaryCycleEntry:
    """Pairing of a Heavenly Stem and Earthly Branch."""

    index: int
    stem_index: int
    branch_index: int

    @property
    def stem(self):  # type: ignore[override]
        return HEAVENLY_STEMS[self.stem_index]

    @property
    def branch(self):  # type: ignore[override]
        return EARTHLY_BRANCHES[self.branch_index]

    def label(self) -> str:
        """Return a human-readable stem-branch label (e.g., ``Jia-Zi``)."""

        return f"{self.stem.name}-{self.branch.name}"


_FIRST_MONTH_STEM_INDEX: Final[dict[int, int]] = {
    0: 2,  # Jia -> Bing Yin
    5: 2,  # Ji -> Bing Yin
    1: 4,  # Yi -> Wu Yin
    6: 4,  # Geng -> Wu Yin
    2: 6,  # Bing -> Geng Yin
    7: 6,  # Xin -> Geng Yin
    3: 8,  # Ding -> Ren Yin
    8: 8,  # Ren -> Ren Yin
    4: 0,  # Wu -> Jia Yin
    9: 0,  # Gui -> Jia Yin
}

_FIRST_HOUR_STEM_INDEX: Final[dict[int, int]] = {
    0: 0,  # Jia day -> Jia Zi hour
    5: 0,
    1: 2,  # Yi/Geng day -> Bing Zi hour
    6: 2,
    2: 4,  # Bing/Xin -> Wu Zi hour
    7: 4,
    3: 6,  # Ding/Ren -> Geng Zi hour
    8: 6,
    4: 8,  # Wu/Gui -> Ren Zi hour
    9: 8,
}


_MONTH_BRANCH_OFFSET: Final[int] = 1  # Tiger (Yin) is the first solar month.


def sexagenary_entry_for_index(index: int) -> SexagenaryCycleEntry:
    """Return the cycle entry for ``index`` (0-59)."""

    idx = index % SEXAGENARY_CYCLE_LENGTH
    return SexagenaryCycleEntry(index=idx, stem_index=idx % 10, branch_index=idx % 12)


def sexagenary_index(stem_index: int, branch_index: int) -> int:
    """Return the 0-59 index for the provided stem/branch combination."""

    target_stem = stem_index % 10
    target_branch = branch_index % 12
    for idx in range(SEXAGENARY_CYCLE_LENGTH):
        if idx % 10 == target_stem and idx % 12 == target_branch:
            return idx
    msg = f"Invalid stem/branch pairing: stem={stem_index}, branch={branch_index}"
    raise ValueError(msg)


def _normalize_datetime(moment: datetime, tz: tzinfo | None) -> datetime:
    if moment.tzinfo is None:
        if tz is not None:
            return moment.replace(tzinfo=tz)
        return moment.replace(tzinfo=UTC)
    if tz is not None:
        return moment.astimezone(tz)
    return moment


def _solar_year(moment: datetime) -> int:
    """Return the stem/branch solar year (using Start of Spring on Feb 4)."""

    if moment.month < 2:
        return moment.year - 1
    if moment.month > 2:
        return moment.year
    # February: use Feb 4 00:00 local as the boundary.
    if moment.day > 4:
        return moment.year
    if moment.day < 4:
        return moment.year - 1
    # Day == 4: treat midnight and later as the new year.
    if moment.hour >= 0:
        return moment.year
    return moment.year - 1


def year_cycle_index(moment: datetime, tz: tzinfo | None = None) -> int:
    """Return the sexagenary index for the solar year containing ``moment``."""

    local_moment = _normalize_datetime(moment, tz)
    year = _solar_year(local_moment)
    return ((year - 4) % SEXAGENARY_CYCLE_LENGTH)


def month_cycle_index(moment: datetime, tz: tzinfo | None = None) -> int:
    """Return the sexagenary index for the solar month containing ``moment``."""

    local_moment = _normalize_datetime(moment, tz)
    year_index = year_cycle_index(local_moment, tz=None)
    stem_index = sexagenary_entry_for_index(year_index).stem_index

    if local_moment.month == 1:
        month_number = 12
    elif local_moment.month == 2 and local_moment.day < 4:
        month_number = 12
    else:
        month_number = local_moment.month - 1

    first_stem = _FIRST_MONTH_STEM_INDEX[stem_index]
    stem = (first_stem + (month_number - 1)) % 10
    branch = (month_number + _MONTH_BRANCH_OFFSET) % 12
    return sexagenary_index(stem, branch)


def day_cycle_index(moment: datetime, tz: tzinfo | None = None) -> int:
    """Return the sexagenary index for the civil day containing ``moment``."""

    local_moment = _normalize_datetime(moment, tz)
    utc_day = local_moment.astimezone(UTC).date()
    delta_days = (utc_day - _DAY_ZERO).days
    return (_DAY_ZERO_INDEX + delta_days) % SEXAGENARY_CYCLE_LENGTH


def hour_cycle_index(moment: datetime, tz: tzinfo | None = None) -> int:
    """Return the sexagenary index for the double-hour (時辰) containing ``moment``."""

    local_moment = _normalize_datetime(moment, tz)
    day_index = day_cycle_index(local_moment, tz=None)
    day_entry = sexagenary_entry_for_index(day_index)
    hour_branch = ((local_moment.hour + 1) // 2) % 12
    first_hour_stem = _FIRST_HOUR_STEM_INDEX[day_entry.stem_index]
    hour_stem = (first_hour_stem + hour_branch) % 10
    return sexagenary_index(hour_stem, hour_branch)


__all__ = [
    "SexagenaryCycleEntry",
    "SEXAGENARY_CYCLE_LENGTH",
    "sexagenary_entry_for_index",
    "sexagenary_index",
    "year_cycle_index",
    "month_cycle_index",
    "day_cycle_index",
    "hour_cycle_index",
]
