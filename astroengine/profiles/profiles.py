"""Helpers for loading canonical profile metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

__all__ = [
    "load_base_profile",
    "load_vca_outline",
    "ResonanceWeights",
    "load_resonance_weights",
]


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


def _repository_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "profiles"
        if (candidate / "vca_outline.json").is_file():
            return parent
    raise FileNotFoundError("Unable to locate repository root containing 'profiles'.")


@lru_cache(maxsize=1)
def load_vca_outline() -> dict[str, Any]:
    """Return the canonical VCA outline JSON payload."""

    outline_path = _repository_root() / "profiles" / "vca_outline.json"
    with outline_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_base_profile() -> dict[str, Any]:
    """Load and parse the baseline AstroEngine profile definition."""

    profile_path = _repository_root() / "profiles" / "base_profile.yaml"
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
