"""Helper utilities for loading traditional dignity tables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from ...scoring.dignity import DignityRecord, load_dignities

__all__ = [
    "DignitySpan",
    "SignDignities",
    "bounds_ruler",
    "face_ruler",
    "sign_dignities",
]


@dataclass(frozen=True)
class DignitySpan:
    ruler: str
    start_deg: float | None
    end_deg: float | None

    def contains(self, degree: float) -> bool:
        if self.start_deg is None or self.end_deg is None:
            return False
        return float(self.start_deg) <= degree < float(self.end_deg)


@dataclass(frozen=True)
class SignDignities:
    sign: str
    exaltation: str | None
    triplicity_day: str | None
    triplicity_night: str | None
    triplicity_participating: str | None
    bounds: tuple[DignitySpan, ...]
    decans: tuple[DignitySpan, ...]

    def bounds_ruler(self, degree: float) -> str | None:
        for span in self.bounds:
            if span.contains(degree):
                return span.ruler
        return None

    def face_ruler(self, degree: float) -> str | None:
        for span in self.decans:
            if span.contains(degree):
                return span.ruler
        return None

    def triplicity_for_sect(self, sect: str) -> str | None:
        sect_lower = sect.lower()
        if sect_lower == "day":
            return self.triplicity_day or self.triplicity_participating
        if sect_lower == "night":
            return self.triplicity_night or self.triplicity_participating
        return self.triplicity_participating


def _iter_records(sign: str) -> Iterable[DignityRecord]:
    for record in load_dignities():
        if record.sign == sign:
            yield record


@lru_cache(maxsize=32)
def sign_dignities(sign: str) -> SignDignities:
    sign_lower = sign.lower()
    exaltation: str | None = None
    triplicity_day: str | None = None
    triplicity_night: str | None = None
    triplicity_participating: str | None = None
    bounds: list[DignitySpan] = []
    decans: list[DignitySpan] = []
    for record in _iter_records(sign_lower):
        if record.dignity_type == "exaltation":
            exaltation = record.planet
        elif record.dignity_type == "triplicity_day":
            triplicity_day = record.planet
        elif record.dignity_type == "triplicity_night":
            triplicity_night = record.planet
        elif record.dignity_type == "triplicity_participating":
            triplicity_participating = record.planet
        elif record.dignity_type == "bounds_egyptian":
            bounds.append(
                DignitySpan(
                    ruler=record.planet,
                    start_deg=record.start_deg,
                    end_deg=record.end_deg,
                )
            )
        elif record.dignity_type == "decans_chaldean":
            decans.append(
                DignitySpan(
                    ruler=record.planet,
                    start_deg=record.start_deg,
                    end_deg=record.end_deg,
                )
            )
    bounds_sorted = tuple(sorted(bounds, key=lambda span: span.start_deg or 0.0))
    decans_sorted = tuple(sorted(decans, key=lambda span: span.start_deg or 0.0))
    return SignDignities(
        sign=sign_lower,
        exaltation=exaltation,
        triplicity_day=triplicity_day,
        triplicity_night=triplicity_night,
        triplicity_participating=triplicity_participating,
        bounds=bounds_sorted,
        decans=decans_sorted,
    )


def bounds_ruler(sign: str, degree: float) -> str | None:
    return sign_dignities(sign).bounds_ruler(degree)


def face_ruler(sign: str, degree: float) -> str | None:
    return sign_dignities(sign).face_ruler(degree)
