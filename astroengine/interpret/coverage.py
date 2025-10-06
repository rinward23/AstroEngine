"""Coverage helpers for sign, house, and luminary aspect interpretations."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from astroengine.utils.i18n import translate

MAJOR_BODIES: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
)

ZODIAC_SIGNS: tuple[str, ...] = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

HOUSES: tuple[int, ...] = tuple(range(1, 13))

LUMINARY_ASPECTS: tuple[int, ...] = (0, 60, 90, 120, 180)

_HOUSE_SIGNS = ZODIAC_SIGNS


def _body_trait(body: str, *, locale: str | None = None) -> str:
    return translate(
        f"interpretation.body_trait.{body}",
        locale=locale,
        default=translate("interpretation.no_content", subject=body, locale=locale),
    )


def _sign_trait(sign: str, *, locale: str | None = None) -> str:
    return translate(
        f"interpretation.sign_trait.{sign}",
        locale=locale,
        default=sign,
    )


def _house_trait(house: int, *, locale: str | None = None) -> str:
    return translate(
        f"interpretation.house_trait.{house}",
        locale=locale,
        default=str(house),
    )


def _luminary_trait(luminary: str, *, locale: str | None = None) -> str:
    return translate(
        f"interpretation.luminary_trait.{luminary}",
        locale=locale,
        default=luminary,
    )


def _aspect_term(aspect: int, *, locale: str | None = None) -> str:
    mapping = {
        0: "conjunction",
        60: "sextile",
        90: "square",
        120: "trine",
        180: "opposition",
    }
    key = mapping.get(aspect)
    if not key:
        return translate(
            "interpretation.no_content",
            locale=locale,
            subject=str(aspect),
        )
    return translate(f"interpretation.aspect.term.{key}", locale=locale, default=key)


def _aspect_trait(aspect: int, *, locale: str | None = None) -> str:
    mapping = {
        0: "conjunction",
        60: "sextile",
        90: "square",
        120: "trine",
        180: "opposition",
    }
    key = mapping.get(aspect)
    if not key:
        return translate(
            "interpretation.no_content",
            locale=locale,
            subject=str(aspect),
        )
    return translate(f"interpretation.aspect_trait.{key}", locale=locale, default=key)


def sign_block(body: str, sign: str, *, locale: str | None = None) -> str:
    """Return sign-based interpretation text or a fallback."""

    if body not in MAJOR_BODIES or sign not in ZODIAC_SIGNS:
        return translate(
            "interpretation.no_content",
            locale=locale,
            subject=f"{body} in {sign}",
        )
    return translate(
        "interpretation.sign.block",
        locale=locale,
        body_name=body,
        sign_name=sign,
        body_trait=_body_trait(body, locale=locale),
        sign_trait=_sign_trait(sign, locale=locale),
    )


def house_block(body: str, house: int, *, locale: str | None = None) -> str:
    """Return house-based interpretation text or a fallback."""

    if body not in MAJOR_BODIES or house not in HOUSES:
        return translate(
            "interpretation.no_content",
            locale=locale,
            subject=f"{body} in house {house}",
        )
    house_name = str(house)
    return translate(
        "interpretation.house.block",
        locale=locale,
        body_name=body,
        house_name=house_name,
        body_trait=_body_trait(body, locale=locale),
        house_trait=_house_trait(house, locale=locale),
    )


def luminary_aspect_block(
    body: str,
    luminary: str,
    aspect: int,
    *,
    locale: str | None = None,
) -> str:
    """Return aspect interpretation text between *body* and luminary."""

    if body not in MAJOR_BODIES or luminary not in ("Sun", "Moon") or aspect not in LUMINARY_ASPECTS:
        return translate(
            "interpretation.no_content",
            locale=locale,
            subject=f"{body} {aspect} {luminary}",
        )
    return translate(
        "interpretation.aspect.template",
        locale=locale,
        body_name=body,
        luminary_name=luminary,
        body_trait=_body_trait(body, locale=locale),
        luminary_trait=_luminary_trait(luminary, locale=locale),
        aspect_term=_aspect_term(aspect, locale=locale),
        aspect_trait=_aspect_trait(aspect, locale=locale),
    )


@dataclass(frozen=True)
class InterpretationBlock:
    subject: str
    text: str

    def to_payload(self) -> dict[str, Any]:
        return {"subject": self.subject, "text": self.text}


def _iter_sign_blocks(*, locale: str | None = None) -> Iterable[InterpretationBlock]:
    for body in MAJOR_BODIES:
        for sign in ZODIAC_SIGNS:
            yield InterpretationBlock(
                subject=f"{body}:{sign}",
                text=sign_block(body, sign, locale=locale),
            )


def _iter_house_blocks(*, locale: str | None = None) -> Iterable[InterpretationBlock]:
    for body in MAJOR_BODIES:
        for index, house in enumerate(HOUSES):
            yield InterpretationBlock(
                subject=f"{body}:House{house}",
                text=house_block(body, house, locale=locale),
            )


def _iter_luminary_aspects(*, locale: str | None = None) -> Iterable[InterpretationBlock]:
    for body in MAJOR_BODIES:
        for luminary in ("Sun", "Moon"):
            for aspect in LUMINARY_ASPECTS:
                yield InterpretationBlock(
                    subject=f"{body}:{aspect}:{luminary}",
                    text=luminary_aspect_block(body, luminary, aspect, locale=locale),
                )


def build_interpretation_blocks(*, locale: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """Return coverage payload for sign, house, and luminary aspect interpretations."""

    return {
        "signs": [block.to_payload() for block in _iter_sign_blocks(locale=locale)],
        "houses": [block.to_payload() for block in _iter_house_blocks(locale=locale)],
        "luminary_aspects": [
            block.to_payload() for block in _iter_luminary_aspects(locale=locale)
        ],
    }


__all__ = [
    "MAJOR_BODIES",
    "ZODIAC_SIGNS",
    "HOUSES",
    "LUMINARY_ASPECTS",
    "sign_block",
    "house_block",
    "luminary_aspect_block",
    "build_interpretation_blocks",
]

