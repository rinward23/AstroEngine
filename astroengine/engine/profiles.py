"""Profile loading helpers for the transit scanning engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml

from ..infrastructure.paths import profiles_dir
from ..profiles import load_base_profile

__all__ = [
    "load_profile_by_id",
    "resolve_profile",
]


def load_profile_by_id(profile_id: str) -> Mapping[str, Any]:
    """Return the profile payload resolved from the on-disk registry."""

    base = load_base_profile()
    profiles_path = profiles_dir()
    for suffix in (".yaml", ".yml", ".json"):
        candidate = profiles_path / f"{profile_id}{suffix}"
        if not candidate.exists():
            continue
        try:
            data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except (
            Exception
        ):  # pragma: no cover - file parse errors bubble to callers later
            break
        if isinstance(data, Mapping):
            return data
        break
    return base


def resolve_profile(
    profile: Mapping[str, Any] | None,
    profile_id: str | None,
) -> Mapping[str, Any]:
    """Return the effective profile payload."""

    if profile is not None:
        return profile
    if profile_id:
        if profile_id == "base":
            return load_base_profile()
        return load_profile_by_id(profile_id)
    return load_base_profile()
