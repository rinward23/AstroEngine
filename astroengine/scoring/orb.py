"""Aspect orb policy helpers backed by :mod:`astroengine` JSON profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources as importlib_resources
from math import isclose
from typing import Mapping, Sequence

# Prefer the project-level body classification but fall back to a minimal map.
try:  # pragma: no cover - import guard for editable installs
    from ..core.bodies import body_class  # type: ignore
except Exception:  # pragma: no cover
    def body_class(name: str) -> str:
        lowered = (name or "").lower()
        if lowered in {"sun", "moon"}:
            return "luminary"
        if lowered in {"mercury", "venus", "mars"}:
            return "personal"
        if lowered in {"jupiter", "saturn"}:
            return "social"
        return "outer"


def _normalize_name(name: str) -> str:
    return str(name).strip().lower()


def _policy_text() -> str:
    """Return the raw aspects policy JSON, tolerating comment lines."""

    # First attempt to load from the installed package resources.
    try:
        resource = importlib_resources.files("astroengine.profiles").joinpath(
            "aspects_policy.json"
        )
        with resource.open("r", encoding="utf-8") as handle:
            text = handle.read()
    except (FileNotFoundError, ModuleNotFoundError):  # pragma: no cover - fallback path
        # Fallback to the repository profiles directory (editable installs).
        try:
            from ..infrastructure.paths import profiles_dir
        except Exception as exc:  # pragma: no cover - defensive guard
            raise FileNotFoundError("Unable to locate aspects_policy.json") from exc
        fallback_path = profiles_dir() / "aspects_policy.json"
        with fallback_path.open("r", encoding="utf-8") as handle:
            text = handle.read()
    # Remove comment lines starting with '#'
    filtered = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )
    return filtered


@lru_cache(maxsize=1)
def _load_aspects_policy() -> dict:
    return json.loads(_policy_text())


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
        for entry in policy.get(key, []) or []:
            normalized = _normalize_name(str(entry))
            if normalized:
                enabled.add(normalized)
    return tuple(
        sorted({name_to_angle[name] for name in enabled if name in name_to_angle})
    )


DEFAULT_ASPECTS: tuple[float, ...] = tuple(_enabled_angle_values())


@dataclass(frozen=True)
class OrbCalculator:
    """Compute orb allowances for aspect detections based on JSON policy."""

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
        name = _aspect_name_for_angle(float(angle_deg)) or ""

        per_aspect = policy.get("orbs_deg", {})  # type: ignore[assignment]
        if name and name in per_aspect:
            spec = per_aspect[name]  # type: ignore[index]
            if isinstance(spec, Mapping):
                class_a = body_class(body_a)
                class_b = body_class(body_b)
                allow_a = float(spec.get(class_a, spec.get("outer", 2.0)))
                allow_b = float(spec.get(class_b, spec.get("outer", 2.0)))
                return min(allow_a, allow_b)
            if isinstance(spec, (int, float)):
                return float(spec)

        family = _family_for_name(name)
        family_defaults: Mapping[str, float] | None = policy.get("orb_defaults", {}).get(  # type: ignore[index]
            family
        )
        if isinstance(family_defaults, Mapping):
            class_a = body_class(body_a)
            class_b = body_class(body_b)
            default = float(family_defaults.get("default", policy.get("default_orb_deg", 2.0)))
            allow_a = float(family_defaults.get(class_a, default))
            allow_b = float(family_defaults.get(class_b, default))
            return min(allow_a, allow_b)

        return float(policy.get("default_orb_deg", 2.0))


__all__ = ["DEFAULT_ASPECTS", "OrbCalculator"]
