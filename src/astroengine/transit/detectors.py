"""Angular helpers and contact detection routines."""

from __future__ import annotations

from datetime import datetime
from math import fmod
from typing import Any, TYPE_CHECKING, Dict, List, Mapping, Sequence, cast

if TYPE_CHECKING:
    from .api import TransitEvent
    from .profiles import OrbPolicy

ASPECT_ANGLES: Dict[str, float] = {
    "conjunction": 0.0,
    "semisextile": 30.0,
    "semisquare": 45.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "sesquisquare": 135.0,
    "quincunx": 150.0,
    "opposition": 180.0,
}

MINOR_ASPECTS = {"semisextile", "semisquare", "sesquisquare", "quincunx"}
MAJOR_ASPECTS = {
    "conjunction",
    "opposition",
    "square",
    "trine",
    "sextile",
}


def normalize_degrees(value: float) -> float:
    """Return an angle in the range [0, 360)."""

    return fmod(fmod(value, 360.0) + 360.0, 360.0)


def normalize_signed(value: float) -> float:
    """Return an angle in the range (-180, 180]."""

    value = fmod(value + 180.0, 360.0)
    if value < 0:
        value += 360.0
    return value - 180.0


def compute_orb(transit_lon: float, natal_lon: float, aspect: str) -> float:
    """Compute the signed orb from the exact aspect."""

    aspect_key = aspect.lower()
    if aspect_key not in ASPECT_ANGLES:
        raise ValueError(f"Unknown aspect '{aspect}'")
    delta = normalize_degrees(transit_lon - natal_lon)
    target = ASPECT_ANGLES[aspect_key]
    return normalize_signed(delta - target)


def detect_ecliptic_contacts(
    state: Mapping[str, Mapping[str, float] | Any],
    natal: Mapping[str, float | str],
    aspects: Sequence[str],
    orb_policy: OrbPolicy,
) -> List[TransitEvent]:
    """Detect contacts within the allowed orb at the provided timestamp."""

    from .api import TransitEvent

    timestamp = cast(datetime | None, state.get("__timestamp__"))
    if timestamp is None:
        raise ValueError("State mapping must include a '__timestamp__' entry")

    results: List[TransitEvent] = []
    for aspect in aspects:
        aspect_key = aspect.lower()
        if aspect_key not in ASPECT_ANGLES:
            continue
        natal_name = cast(str, natal["name"])
        natal_lon = cast(float, natal["lon_deg"])
        for body, payload in state.items():
            if body == "__timestamp__":
                continue
            payload_map = cast(Mapping[str, float], payload)
            orb_allow = orb_policy(body, natal_name, aspect_key)
            diff = compute_orb(payload_map["lon_deg"], natal_lon, aspect_key)
            if abs(diff) <= orb_allow:
                family = "minor" if aspect_key in MINOR_ASPECTS else "major"
                metadata = {"signed_orb": diff}
                results.append(
                    TransitEvent(
                        timestamp=timestamp,
                        aspect=aspect_key,
                        transiting_body=body,
                        natal_point=natal_name,
                        orb_deg=abs(diff),
                        family=family,
                        metadata=metadata,
                    )
                )
    return results


__all__ = [
    "ASPECT_ANGLES",
    "MINOR_ASPECTS",
    "MAJOR_ASPECTS",
    "normalize_degrees",
    "normalize_signed",
    "compute_orb",
    "detect_ecliptic_contacts",
]
