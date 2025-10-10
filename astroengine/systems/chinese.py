"""Chinese calendrical helpers used by AstroEngine.

The conversion routines follow the Hong Kong Observatory tabulation for
1900–2099 reproduced in *Calendrical Calculations* (Dershowitz &
Reingold, 4th ed.).  Month metadata mirrors the observatory's published
"LunarInfo" sequence.  See Helmer Aslaksen's "The Mathematics of the
Chinese Calendar" (National University of Singapore, 2010) for the
sexagenary pillar rules referenced below.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Mapping

__all__ = [
    "ChineseLunarDate",
    "ChineseFourPillars",
    "HEAVENLY_STEMS",
    "EARTHLY_BRANCHES",
    "SHENGXIAO_ANIMALS",
    "FIVE_ELEMENTS",
    "LUNAR_INFO",
    "chinese_lunar_from_gregorian",
    "gregorian_from_chinese_lunar",
    "chinese_sexagenary_cycle",
    "four_pillars_from_moment",
    "hour_branch",
]

HEAVENLY_STEMS: tuple[str, ...] = (
    "Jia",
    "Yi",
    "Bing",
    "Ding",
    "Wu",
    "Ji",
    "Geng",
    "Xin",
    "Ren",
    "Gui",
)

EARTHLY_BRANCHES: tuple[str, ...] = (
    "Zi",
    "Chou",
    "Yin",
    "Mao",
    "Chen",
    "Si",
    "Wu",
    "Wei",
    "Shen",
    "You",
    "Xu",
    "Hai",
)

SHENGXIAO_ANIMALS: tuple[str, ...] = (
    "Rat",
    "Ox",
    "Tiger",
    "Rabbit",
    "Dragon",
    "Snake",
    "Horse",
    "Goat",
    "Monkey",
    "Rooster",
    "Dog",
    "Pig",
)

FIVE_ELEMENTS: Mapping[str, str] = {
    "Wood": "growth and expansion",
    "Fire": "illumination and action",
    "Earth": "stability and nurture",
    "Metal": "refinement and structure",
    "Water": "adaptability and wisdom",
}

_HOUR_BRANCHES: tuple[str, ...] = (
    "Zi",
    "Chou",
    "Yin",
    "Mao",
    "Chen",
    "Si",
    "Wu",
    "Wei",
    "Shen",
    "You",
    "Xu",
    "Hai",
)


@dataclass(frozen=True)
class ChineseLunarDate:
    """Chinese lunisolar date covering the 1900–2099 range."""

    year: int
    month: int
    day: int
    is_leap_month: bool = False


@dataclass(frozen=True)
class ChineseFourPillars:
    """Heavenly stem and Earthly branch pairs for BaZi analysis."""

    year: tuple[str, str]
    month: tuple[str, str]
    day: tuple[str, str]
    hour: tuple[str, str]


BASE_DATE = date(1900, 1, 31)
DAY_CYCLE_BASE = date(1984, 2, 2)  # JiaZi day used for the pillar sequence.

LUNAR_INFO: tuple[int, ...] = (
    0x04BD8,
    0x04AE0,
    0x0A570,
    0x054D5,
    0x0D260,
    0x0D950,
    0x16554,
    0x056A0,
    0x09AD0,
    0x055D2,
    0x04AE0,
    0x0A5B6,
    0x0A4D0,
    0x0D250,
    0x1D255,
    0x0B540,
    0x0D6A0,
    0x0ADA2,
    0x095B0,
    0x14977,
    0x04970,
    0x0A4B0,
    0x0B4B5,
    0x06A50,
    0x06D40,
    0x1AB54,
    0x02B60,
    0x09570,
    0x052F2,
    0x04970,
    0x06566,
    0x0D4A0,
    0x0EA50,
    0x06E95,
    0x05AD0,
    0x02B60,
    0x186E3,
    0x092E0,
    0x1C8D7,
    0x0C950,
    0x0D4A0,
    0x1D8A6,
    0x0B550,
    0x056A0,
    0x1A5B4,
    0x025D0,
    0x092D0,
    0x0D2B2,
    0x0A950,
    0x0B557,
    0x06CA0,
    0x0B550,
    0x15355,
    0x04DA0,
    0x0A5D0,
    0x14573,
    0x052D0,
    0x0A9A8,
    0x0E950,
    0x06AA0,
    0x0AEA6,
    0x0AB50,
    0x04B60,
    0x0AAE4,
    0x0A570,
    0x05260,
    0x0F263,
    0x0D950,
    0x05B57,
    0x056A0,
    0x096D0,
    0x04DD5,
    0x04AD0,
    0x0A4D0,
    0x0D4D4,
    0x0D250,
    0x0D558,
    0x0B540,
    0x0B5A0,
    0x195A6,
    0x095B0,
    0x049B0,
    0x0A974,
    0x0A4B0,
    0x0B27A,
    0x06A50,
    0x06D40,
    0x0AF46,
    0x0AB60,
    0x09570,
    0x04AF5,
    0x04970,
    0x064B0,
    0x074A3,
    0x0EA50,
    0x06B58,
    0x05AC0,
    0x0AB60,
    0x096D5,
    0x092E0,
    0x0C960,
    0x0D954,
    0x0D4A0,
    0x0DA50,
    0x07552,
    0x056A0,
    0x0ABB7,
    0x025D0,
    0x092D0,
    0x0CAB5,
    0x0A950,
    0x0B4A0,
    0x0BAA4,
    0x0AD50,
    0x055D9,
    0x04BA0,
    0x0A5B0,
    0x15176,
    0x052B0,
    0x0A930,
    0x07954,
    0x06AA0,
    0x0AD50,
    0x05B52,
    0x04B60,
    0x0A6E6,
    0x0A4E0,
    0x0D260,
    0x0EA65,
    0x0D530,
    0x05AA0,
    0x076A3,
    0x096D0,
    0x04AFB,
    0x04AD0,
    0x0A4D0,
    0x1D0B6,
    0x0D250,
    0x0D520,
    0x0DD45,
    0x0B5A0,
    0x056D0,
    0x055B2,
    0x049B0,
    0x0A577,
    0x0A4B0,
    0x0AA50,
    0x1B255,
    0x06D20,
    0x0ADA0,
    0x14B63,
    0x09370,
    0x049F8,
    0x04970,
    0x064B0,
    0x168A6,
    0x0EA50,
    0x06AA0,
    0x1A6C4,
    0x0AAE0,
    0x092E0,
    0x0D2E3,
    0x0C960,
    0x0D557,
    0x0D4A0,
    0x0DA50,
    0x05D55,
    0x056A0,
    0x0A6D0,
    0x055D4,
    0x052D0,
    0x0A9B8,
    0x0A950,
    0x0B4A0,
    0x0B6A6,
    0x0AD50,
    0x055A0,
    0x0ABA4,
    0x0A5B0,
    0x052B0,
    0x0B273,
    0x06930,
    0x07337,
    0x06AA0,
    0x0AD50,
    0x14B55,
    0x04B60,
    0x0A570,
    0x054E4,
    0x0D160,
    0x0E968,
    0x0D520,
    0x0DAA0,
    0x16AA6,
    0x056D0,
    0x04AE0,
    0x0A9D4,
    0x0A2D0,
    0x0D150,
    0x0F252,
)

_MONTH_STEM_START: dict[int, int] = {
    0: 2,  # Jia year → Bing month stem
    5: 2,
    1: 4,  # Yi/Geng → Wu
    6: 4,
    2: 6,  # Bing/Xin → Geng
    7: 6,
    3: 8,  # Ding/Ren → Ren
    8: 8,
    4: 0,  # Wu/Gui → Jia
    9: 0,
}


def _year_index(year: int) -> int:
    if 1900 <= year <= 2099:
        return year - 1900
    raise ValueError("Supported years span 1900–2099")


def _year_info(year: int) -> int:
    return LUNAR_INFO[_year_index(year)]


def _leap_month(year: int) -> int:
    return _year_info(year) & 0xF


def _month_days(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError("Lunar month must be between 1 and 12")
    info = _year_info(year)
    mask = 0x8000 >> (month - 1)
    return 30 if info & mask else 29


def _leap_days(year: int) -> int:
    leap = _leap_month(year)
    if leap == 0:
        return 0
    info = _year_info(year)
    return 30 if info & 0x10000 else 29


def _year_days(year: int) -> int:
    info = _year_info(year)
    days = 348
    mask = 0x8000
    for _ in range(12):
        if info & mask:
            days += 1
        mask >>= 1
    return days + _leap_days(year)


def _enumerate_months(year: int):
    info = _year_info(year)
    leap = info & 0xF
    months = [(m, False) for m in range(1, 13)]
    if leap:
        months.insert(leap, (leap, True))
    for month, is_leap in months:
        if is_leap:
            days = ((info >> 16) & 1) + 29
        else:
            days = ((info >> (16 - month)) & 1) + 29
        yield month, bool(is_leap), days


def chinese_lunar_from_gregorian(gregorian: date | datetime) -> ChineseLunarDate:
    """Convert a Gregorian date to its Chinese lunisolar representation."""

    if isinstance(gregorian, datetime):
        target_date = gregorian.date()
    elif isinstance(gregorian, date):
        target_date = gregorian
    else:
        raise TypeError("gregorian must be a date or datetime instance")

    if target_date < BASE_DATE or target_date >= date(2100, 1, 1):
        raise ValueError("Date outside supported 1900–2099 range")

    offset = (target_date - BASE_DATE).days
    year = 1900
    while year <= 2099 and offset >= _year_days(year):
        offset -= _year_days(year)
        year += 1

    for month, is_leap, days in _enumerate_months(year):
        if offset < days:
            return ChineseLunarDate(year, month, offset + 1, is_leap)
        offset -= days

    raise RuntimeError("Failed to resolve Chinese lunar date")


def gregorian_from_chinese_lunar(lunar: ChineseLunarDate) -> date:
    """Convert a Chinese lunar date to the Gregorian calendar."""

    year = lunar.year
    month = lunar.month
    day = lunar.day
    is_leap = bool(lunar.is_leap_month)

    _ = _year_index(year)  # validates range
    leap_month = _leap_month(year)

    if not 1 <= month <= 12:
        raise ValueError("Lunar month must be between 1 and 12")
    if is_leap and leap_month == 0:
        raise ValueError(f"Year {year} has no leap month")
    if is_leap and month != leap_month:
        raise ValueError(f"Leap month for {year} is {leap_month}")

    offset = 0
    for yr in range(1900, year):
        offset += _year_days(yr)

    month_found = False
    for current_month, current_is_leap, days in _enumerate_months(year):
        if current_month == month and current_is_leap == is_leap:
            if not 1 <= day <= days:
                raise ValueError("Day out of range for lunar month")
            offset += day - 1
            month_found = True
            break
        offset += days

    if not month_found:
        raise ValueError("Requested lunar month configuration not present in year")

    result = BASE_DATE + timedelta(days=offset)
    if result >= date(2100, 1, 1):
        raise ValueError("Resulting date exceeds supported range")
    return result


def chinese_sexagenary_cycle(year: int) -> tuple[str, str]:
    """Return the Heavenly stem and Earthly branch for ``year``."""

    _ = _year_index(year)
    stem = HEAVENLY_STEMS[(year - 4) % 10]
    branch_index = (year - 4) % 12
    branch = EARTHLY_BRANCHES[branch_index]
    return stem, branch


def hour_branch(moment: datetime | date | int) -> str:
    """Return the Earthly Branch assigned to a given civil hour."""

    if isinstance(moment, datetime):
        hour = moment.hour
    elif isinstance(moment, date):
        hour = 12
    elif isinstance(moment, int):
        hour = moment
    else:
        raise TypeError("moment must supply an hour")

    hour = int(hour) % 24
    index = ((hour + 1) // 2) % 12
    return _HOUR_BRANCHES[index]


def four_pillars_from_moment(moment: datetime) -> ChineseFourPillars:
    """Return the BaZi pillars for a Gregorian moment."""

    if not isinstance(moment, datetime):
        raise TypeError("moment must be a datetime instance")

    lunar = chinese_lunar_from_gregorian(moment)
    year_pillar = chinese_sexagenary_cycle(lunar.year)

    year_stem_index = (lunar.year - 4) % 10
    month_branch_index = (lunar.month + 1) % 12
    month_branch = EARTHLY_BRANCHES[month_branch_index]
    month_stem_start = _MONTH_STEM_START[year_stem_index]
    month_stem = HEAVENLY_STEMS[(month_stem_start + lunar.month - 1) % 10]

    day_offset = (moment.date() - DAY_CYCLE_BASE).days
    day_stem_index = day_offset % 10
    day_branch_index = day_offset % 12
    day_pillar = (
        HEAVENLY_STEMS[day_stem_index],
        EARTHLY_BRANCHES[day_branch_index],
    )

    hour_branch_name = hour_branch(moment)
    hour_branch_index = EARTHLY_BRANCHES.index(hour_branch_name)
    hour_stem_index = (day_stem_index * 2 + hour_branch_index) % 10
    hour_pillar = (HEAVENLY_STEMS[hour_stem_index], hour_branch_name)

    return ChineseFourPillars(
        year=year_pillar,
        month=(month_stem, month_branch),
        day=day_pillar,
        hour=hour_pillar,
    )

