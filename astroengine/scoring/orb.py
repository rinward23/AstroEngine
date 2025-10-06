
"""Aspect angle defaults and orb calculations sourced from policy JSON."""


from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources as importlib_resources
from math import isclose
from pathlib import Path

# Optional: integrate with project body classification if available
try:  # pragma: no cover - fallback for minimal installs
    from astroengine.core.bodies import body_class as _body_class
except Exception:  # pragma: no cover

    def _body_class(name: str) -> str:
        n = (name or "").lower()
        luminaries = {"sun", "moon"}
        personals = {"mercury", "venus", "mars"}
        socials = {"jupiter", "saturn"}
        if n in luminaries:
            return "luminary"
        if n in personals:
            return "personal"
        if n in socials:

            return "social"
        return "outer"


def body_class(name: str) -> str:
    """Return the configured classification for ``name``."""

    return _body_class(name)


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()


@lru_cache(maxsize=1)
def _load_aspects_policy() -> dict:
    """Load the packaged aspect policy with an editable-install fallback."""

    text: str | None = None

    try:
        resource = importlib_resources.files("astroengine.profiles").joinpath(
            "aspects_policy.json"
        )

        # ``read_text`` works for regular and zip-based installations alike.
        text = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):  # pragma: no cover - packaging issues
        text = None
    if text is None:
        repo_path = Path(__file__).resolve().parents[2] / "profiles" / "aspects_policy.json"
        text = repo_path.read_text(encoding="utf-8")

    filtered = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )
    return json.loads(filtered)



@lru_cache(maxsize=1)
def _angles_index() -> tuple[dict[str, float], dict[float, str]]:
    policy = _load_aspects_policy()
    name_to_angle: dict[str, float] = {
        _normalize_name(k): float(v) for k, v in policy.get("angles_deg", {}).items()
    }
    angle_to_name: dict[float, str] = {round(v, 4): k for k, v in name_to_angle.items()}
    return name_to_angle, angle_to_name


def _aspect_name_for_angle(angle_deg: float, *, tol: float = 1e-3) -> str | None:
    name_to_angle, _ = _angles_index()
    for name, base in name_to_angle.items():
        if isclose(float(angle_deg), float(base), abs_tol=tol):
            return name
    return None


def _family_for_name(name: str) -> str:
    policy = _load_aspects_policy()
    normalized = _normalize_name(name)
    majors = {_normalize_name(n) for n in policy.get("enabled", [])}
    minors = {_normalize_name(n) for n in policy.get("enabled_minors", [])}
    if normalized in majors:
        return "major"
    if normalized in minors:
        return "minor"
    return "harmonic"


def _enabled_angle_values() -> Sequence[float]:
    policy = _load_aspects_policy()
    name_to_angle, _ = _angles_index()
    enabled: set[str] = set()
    for key in ("enabled", "enabled_minors", "enabled_harmonics"):

        values = policy.get(key) or []
        for name in values:
            normalized = _normalize_name(str(name))

            if normalized:
                enabled.add(normalized)
    return tuple(
        sorted({name_to_angle[name] for name in enabled if name in name_to_angle})
    )


DEFAULT_ASPECTS: tuple[float, ...] = tuple(_enabled_angle_values())


@dataclass(frozen=True)
class OrbCalculator:

    """Compute orb allowances using the repository's aspect policy."""


    _policy: Mapping[str, object] | None = None

    def __init__(self, policy: Mapping[str, object] | None = None) -> None:
        object.__setattr__(self, "_policy", policy or _load_aspects_policy())

    def orb_for(
        self,
        body_a: str,
        body_b: str,
        angle_deg: float,
        *,
        profile: str = "standard",
    ) -> float:
        policy = self._policy or {}

        aspect_name = _aspect_name_for_angle(float(angle_deg))
        per_aspect: Mapping[str, Mapping[str, float]] = policy.get("orbs_deg", {})  # type: ignore[assignment]
        if aspect_name and aspect_name in per_aspect:
            classification_a = body_class(body_a)
            classification_b = body_class(body_b)
            spec = per_aspect[aspect_name]  # type: ignore[index]
            allow_a = float(spec.get(classification_a, spec.get("outer", 2.0)))
            allow_b = float(spec.get(classification_b, spec.get("outer", 2.0)))
            return min(allow_a, allow_b)

        family = _family_for_name(aspect_name or "")
        orb_defaults = policy.get("orb_defaults", {})  # type: ignore[assignment]
        family_defaults = (
            orb_defaults.get(family, {}) if isinstance(orb_defaults, Mapping) else {}
        )
        if isinstance(family_defaults, Mapping):
            classification_a = body_class(body_a)
            classification_b = body_class(body_b)
            default_value = float(family_defaults.get("default", 2.0))
            allow_a = float(family_defaults.get(classification_a, default_value))
            allow_b = float(family_defaults.get(classification_b, default_value))

            return min(allow_a, allow_b)

        return float(policy.get("default_orb_deg", 2.0))


__all__ = ["DEFAULT_ASPECTS", "OrbCalculator"]
