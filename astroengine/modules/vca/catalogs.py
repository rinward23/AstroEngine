"""Catalog definitions for VCA Outline bodies and points."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from ...profiles import load_vca_outline

__all__ = [
    "load_vca_body_catalog",
    "load_vca_sensitive_points",
    "VCA_CORE_BODIES",
    "VCA_EXT_ASTEROIDS",
    "VCA_CENTAURS",
    "VCA_TNOS",
    "VCA_SENSITIVE_POINTS",
]


def _ensure_str_list(values: Any) -> list[str]:
    if isinstance(values, list):
        return [str(item) for item in values]
    return []


def _ensure_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


@lru_cache(maxsize=1)
def load_vca_body_catalog() -> dict[str, Any]:
    """Return the VCA body catalog as defined in ``vca_outline.json``."""

    outline = load_vca_outline()
    bodies_section = _ensure_mapping(outline.get("bodies"))

    include = _ensure_str_list(bodies_section.get("include"))

    raw_groups = _ensure_mapping(bodies_section.get("optional_groups"))
    optional_groups: dict[str, list[str]] = {}
    for name, payload in raw_groups.items():
        optional_groups[str(name)] = _ensure_str_list(payload)

    raw_fixed_stars = _ensure_mapping(bodies_section.get("fixed_stars"))
    fixed_stars = {
        "enabled": bool(raw_fixed_stars.get("enabled", False)),
        "list": _ensure_str_list(raw_fixed_stars.get("list")),
    }

    return {
        "include": include,
        "optional_groups": optional_groups,
        "fixed_stars": fixed_stars,
    }


@lru_cache(maxsize=1)
def load_vca_sensitive_points() -> list[str]:
    """Return the sensitive point catalog from ``vca_outline.json``."""

    outline = load_vca_outline()
    return _ensure_str_list(outline.get("sensitive_points"))


def _copy(values: list[str]) -> list[str]:
    return list(values)


def _optional_group(name: str) -> list[str]:
    catalog = load_vca_body_catalog()
    optional_groups = _ensure_mapping(catalog.get("optional_groups"))
    payload = optional_groups.get(name)
    return _copy(payload) if isinstance(payload, list) else []


_BODY_CATALOG = load_vca_body_catalog()

VCA_CORE_BODIES = _copy(_BODY_CATALOG["include"])
VCA_EXT_ASTEROIDS = _optional_group("asteroids_main")
VCA_CENTAURS = _optional_group("centaurs")
VCA_TNOS = _optional_group("tno")
VCA_SENSITIVE_POINTS = _copy(load_vca_sensitive_points())
