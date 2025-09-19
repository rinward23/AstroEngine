"""Helpers for loading canonical profile metadata."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

__all__ = ["load_base_profile", "load_vca_outline"]


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
