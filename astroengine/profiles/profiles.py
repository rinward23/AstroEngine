"""Helpers for loading canonical profile metadata."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..infrastructure.paths import profiles_dir
from ..scoring.policy import load_orb_policy, load_severity_policy, load_visibility_policy
from ..utils import deep_merge

__all__ = [
    "load_base_profile",
    "load_profile",
    "load_vca_outline",
    "ResonanceWeights",
    "load_resonance_weights",
]


_USER_OVERRIDES_PATH = profiles_dir() / "user_overrides.yaml"


@dataclass(frozen=True)
class ResonanceWeights:
    """Mind/Body/Spirit emphasis factors sourced from profile metadata."""

    mind: float = 1.0
    body: float = 1.0
    spirit: float = 1.0

    def normalized(self) -> "ResonanceWeights":
        total = max(self.mind, 0.0) + max(self.body, 0.0) + max(self.spirit, 0.0)
        if total <= 0.0:
            return ResonanceWeights(1.0, 1.0, 1.0)
        return ResonanceWeights(
            mind=max(self.mind, 0.0) / total,
            body=max(self.body, 0.0) / total,
            spirit=max(self.spirit, 0.0) / total,
        )

    def as_mapping(self) -> dict[str, float]:
        weights = self.normalized()
        return {"mind": weights.mind, "body": weights.body, "spirit": weights.spirit}

@lru_cache(maxsize=1)
def load_vca_outline() -> dict[str, Any]:
    """Return the canonical VCA outline JSON payload."""

    outline_path = profiles_dir() / "vca_outline.json"
    with outline_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_base_profile() -> dict[str, Any]:
    """Load and parse the baseline AstroEngine profile definition."""

    profile_path = profiles_dir() / "base_profile.yaml"
    with profile_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resonance_from_payload(payload: Mapping[str, Any] | None) -> ResonanceWeights:
    if not payload:
        return ResonanceWeights()
    if "weights" in payload:
        data = payload["weights"]
    else:
        data = payload
    return ResonanceWeights(
        mind=float(data.get("mind", 1.0)),
        body=float(data.get("body", 1.0)),
        spirit=float(data.get("spirit", 1.0)),
    )


@lru_cache(maxsize=1)
def _load_default_resonance() -> ResonanceWeights:
    profile = load_base_profile()
    resonance_section = profile.get("resonance") if isinstance(profile, Mapping) else None
    return _resonance_from_payload(resonance_section)


def load_resonance_weights(profile: Mapping[str, Any] | None = None) -> ResonanceWeights:
    """Load the resonance weighting triple from a parsed profile mapping."""

    if profile is None:
        return _load_default_resonance()
    resonance_section = profile.get("resonance") if isinstance(profile, Mapping) else None
    return _resonance_from_payload(resonance_section)


def _load_user_overrides_table(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, Mapping):
        return {}
    users_section = payload.get("users") if isinstance(payload, Mapping) else None
    if isinstance(users_section, Mapping):
        return users_section
    return payload


def load_profile(
    profile_id: str = "base",
    *,
    user: str | None = None,
    overrides: Mapping[str, Any] | None = None,
    overrides_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a merged profile including policy payloads and overrides."""

    if profile_id != "base":
        raise ValueError(f"Unknown profile_id: {profile_id}")

    base = load_base_profile()
    if not isinstance(base, Mapping):
        raise ValueError("Base profile must be a mapping")

    merged: Mapping[str, Any] = base

    if user:
        overrides_file = Path(overrides_path) if overrides_path else _USER_OVERRIDES_PATH
        table = _load_user_overrides_table(overrides_file)
        user_payload = table.get(user)
        if isinstance(user_payload, Mapping):
            merged = deep_merge(merged, user_payload)

    if overrides:
        merged = deep_merge(merged, overrides)

    profile_dict: dict[str, Any] = deepcopy(dict(merged))

    policy_overrides = profile_dict.get("policies") if isinstance(profile_dict.get("policies"), Mapping) else {}
    orb_overrides = None
    severity_overrides = None
    visibility_overrides = None
    if isinstance(policy_overrides, Mapping):
        orb_candidate = policy_overrides.get("orb")
        if isinstance(orb_candidate, Mapping):
            orb_overrides = orb_candidate
        severity_candidate = policy_overrides.get("severity")
        if isinstance(severity_candidate, Mapping):
            severity_overrides = severity_candidate
        visibility_candidate = policy_overrides.get("visibility")
        if isinstance(visibility_candidate, Mapping):
            visibility_overrides = visibility_candidate

    orb_policy = load_orb_policy(overrides=orb_overrides)
    severity_policy = load_severity_policy(overrides=severity_overrides)
    visibility_policy = load_visibility_policy(overrides=visibility_overrides)

    profile_dict["policies"] = {
        "orb": orb_policy.to_mapping(),
        "severity": severity_policy.to_mapping(),
        "visibility": visibility_policy.to_mapping(),
    }
    profile_dict.setdefault("profile_id", profile_dict.get("id", profile_id))
    return profile_dict
