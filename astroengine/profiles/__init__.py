"""Profiles and profile loading utilities."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .profiles import (
    ResonanceWeights,
    load_base_profile,
    load_profile,
    load_resonance_weights,
    load_vca_outline,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..modules.vca.profiles import DomainScoringProfile, VCA_DOMAIN_PROFILES

__all__ = [
    "DomainScoringProfile",
    "VCA_DOMAIN_PROFILES",
    "ResonanceWeights",
    "load_base_profile",
    "load_profile",
    "load_resonance_weights",
    "load_vca_outline",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "DomainScoringProfile": ("..modules.vca.profiles", "DomainScoringProfile"),
    "VCA_DOMAIN_PROFILES": ("..modules.vca.profiles", "VCA_DOMAIN_PROFILES"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(name)
    module = import_module(target[0], package=__name__)
    value = getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals().keys()))
