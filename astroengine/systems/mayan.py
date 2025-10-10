"""Mayan calendrical helpers following the GMT correlation (584283).

The algorithms implement the transformations documented in the
Smithsonian Institution's *Handbook of Maya Glyphs* and in
Dershowitz & Reingold's *Calendrical Calculations* (4th ed.).  The
calendar-round symbolism references Ralph L. Roys' translation of the
*Book of Chilam Balam of Chumayel* (1933).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

__all__ = [
    "TZOLKIN_NAMES",
    "HAAB_MONTHS",
    "LORDS_OF_NIGHT",
    "GMT_CORRELATION",
    "MayanLongCount",
    "MayanCalendarRound",
    "long_count_from_gregorian",
    "gregorian_from_long_count",
    "calendar_round_from_gregorian",
]

TZOLKIN_NAMES: tuple[str, ...] = (
    "Imix",
    "Ik'",
    "Ak'b'al",
    "K'an",
    "Chikchan",
    "Kimi",
    "Manik'",
    "Lamat",
    "Muluk",
    "Ok",
    "Chuwen",
    "Eb",
    "B'en",
    "Ix",
    "Men",
    "K'ib",
    "Kab'an",
    "Etz'nab",
    "Kawak",
    "Ajaw",
)

HAAB_MONTHS: tuple[str, ...] = (
    "Pop",
    "Wo",
    "Sip",
    "Sotz'",
    "Sek",
    "Xul",
    "Yaxk'in",
    "Mol",
    "Ch'en",
    "Yax",
    "Sak",
    "Keh",
    "Mak",
    "K'ank'in",
    "Muwan",
    "Pax",
    "K'ayab",
    "Kumk'u",
    "Wayeb",
)

LORDS_OF_NIGHT: tuple[str, ...] = (
    "G1 (Itzamna)",
    "G2",
    "G3",
    "G4",
    "G5",
    "G6",
    "G7",
    "G8",
    "G9 (Bolon Yokte')",
)

GMT_CORRELATION = 584283  # Goodman–Martínez–Thompson


@dataclass(frozen=True)
class MayanLongCount:
    """Long Count representation (baktun.katun.tun.uinal.kin)."""

    baktun: int
    katun: int
    tun: int
    uinal: int
    kin: int

    def total_days(self) -> int:
        return (
            self.baktun * 144000
            + self.katun * 7200
            + self.tun * 360
            + self.uinal * 20
            + self.kin
        )


@dataclass(frozen=True)
class MayanCalendarRound:
    """Calendar Round pair combining Tzolk'in and Haab designations."""

    tzolkin_number: int
    tzolkin_name: str
    haab_day: int
    haab_month: str
    lord_of_night: str


def _to_julian_day(gregorian: date) -> int:
    ordinal = gregorian.toordinal()
    return ordinal + 1721425


def _from_julian_day(jdn: int) -> date:
    ordinal = jdn - 1721425
    return date.fromordinal(ordinal)


def _validate_long_count(long_count: MayanLongCount) -> None:
    if not (0 <= long_count.katun < 20):
        raise ValueError("Katun must be between 0 and 19")
    if not (0 <= long_count.tun < 20):
        raise ValueError("Tun must be between 0 and 19")
    if not (0 <= long_count.uinal < 18):
        raise ValueError("Uinal must be between 0 and 17")
    if not (0 <= long_count.kin < 20):
        raise ValueError("Kin must be between 0 and 19")


def long_count_from_gregorian(moment: date | datetime) -> MayanLongCount:
    """Return the Mayan Long Count for a Gregorian calendar date."""

    if isinstance(moment, datetime):
        target_date = moment.date()
    elif isinstance(moment, date):
        target_date = moment
    else:
        raise TypeError("moment must be a date or datetime instance")

    jdn = _to_julian_day(target_date)
    elapsed = jdn - GMT_CORRELATION
    if elapsed < 0:
        raise ValueError("Date precedes the Mayan Long Count epoch")

    baktun, remainder = divmod(elapsed, 144000)
    katun, remainder = divmod(remainder, 7200)
    tun, remainder = divmod(remainder, 360)
    uinal, kin = divmod(remainder, 20)
    return MayanLongCount(baktun, katun, tun, uinal, kin)


def gregorian_from_long_count(long_count: MayanLongCount) -> date:
    """Convert a Mayan Long Count designation to the Gregorian calendar."""

    _validate_long_count(long_count)
    total = long_count.total_days()
    jdn = total + GMT_CORRELATION
    if jdn <= 0:
        raise ValueError("Long Count yields non-positive Julian day")
    return _from_julian_day(jdn)


def calendar_round_from_gregorian(moment: date | datetime) -> MayanCalendarRound:
    """Return the calendar round (Tzolk'in + Haab) for a Gregorian date."""

    if isinstance(moment, datetime):
        target_date = moment.date()
    elif isinstance(moment, date):
        target_date = moment
    else:
        raise TypeError("moment must be a date or datetime instance")

    jdn = _to_julian_day(target_date)
    elapsed = jdn - GMT_CORRELATION

    tzolkin_number = (elapsed + 3) % 13 + 1
    tzolkin_name = TZOLKIN_NAMES[(elapsed + 19) % 20]

    haab_count = (elapsed + 348) % 365
    haab_month_index, haab_day = divmod(haab_count, 20)
    if haab_month_index == 18:
        haab_day = haab_day  # Wayeb' has five days (0–4)
    haab_month = HAAB_MONTHS[haab_month_index]

    lord = LORDS_OF_NIGHT[(elapsed + 8) % 9]
    return MayanCalendarRound(tzolkin_number, tzolkin_name, haab_day, haab_month, lord)

