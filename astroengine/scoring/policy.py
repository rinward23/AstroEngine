"""Load and merge scoring policy documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..infrastructure.paths import profiles_dir
from ..utils import deep_merge

__all__ = [
    "OrbPolicy",
    "SeverityPolicy",
    "VisibilityPolicy",
    "load_orb_policy",
    "load_severity_policy",
    "load_visibility_policy",
]

_DEF_ORB_POLICY = profiles_dir() / "orb_policy.json"
_DEF_SEVERITY_POLICY = profiles_dir() / "scoring_policy.json"
_DEF_VISIBILITY_POLICY = profiles_dir() / "visibility_policy.json"


def _load_json(path: Path) -> dict[str, Any]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    payload = "\n".join(line for line in raw_lines if not line.strip().startswith("#"))
    return json.loads(payload)


@lru_cache(maxsize=1)
def _base_orb_policy() -> dict[str, Any]:
    return _load_json(_DEF_ORB_POLICY)


@lru_cache(maxsize=1)
def _base_severity_policy() -> dict[str, Any]:
    return _load_json(_DEF_SEVERITY_POLICY)


@lru_cache(maxsize=1)
def _base_visibility_policy() -> dict[str, Any]:
    return _load_json(_DEF_VISIBILITY_POLICY)


@dataclass(frozen=True)
class OrbPolicy:
    """Wrapper for the orb policy mapping."""

    data: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {key: value for key, value in self.data.items()}


@dataclass(frozen=True)
class SeverityPolicy:
    """Wrapper for severity policy data with helper accessors."""

    data: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {key: value for key, value in self.data.items()}

    @property
    def condition_modifiers(self) -> Mapping[str, float]:
        base = self.data.get("condition_modifiers", {})
        if isinstance(base, Mapping):
            return {str(key): float(value) for key, value in base.items()}
        return {}


@dataclass(frozen=True)
class VisibilityPolicy:
    """Visibility thresholds expressed as minimum score gates."""

    data: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {key: value for key, value in self.data.items()}

    @property
    def default_min_score(self) -> float:
        return float(self.data.get("default_min_score", 0.0))

    def threshold_for(self, kind: str) -> float:
        entries = self.data.get("per_kind", {})
        if isinstance(entries, Mapping) and kind in entries:
            try:
                return float(entries[kind])
            except (TypeError, ValueError):
                return self.default_min_score
        return self.default_min_score


def load_orb_policy(*, overrides: Mapping[str, Any] | None = None) -> OrbPolicy:
    base = _base_orb_policy()
    if overrides:
        data = deep_merge(base, overrides)
    else:
        data = deepcopy(base)
    return OrbPolicy(data)


def load_severity_policy(*, overrides: Mapping[str, Any] | None = None) -> SeverityPolicy:
    base = _base_severity_policy()
    if overrides:
        data = deep_merge(base, overrides)
    else:
        data = deepcopy(base)
    return SeverityPolicy(data)


def load_visibility_policy(*, overrides: Mapping[str, Any] | None = None) -> VisibilityPolicy:
    base = _base_visibility_policy()
    if overrides:
        data = deep_merge(base, overrides)
    else:
        data = deepcopy(base)
    return VisibilityPolicy(data)
