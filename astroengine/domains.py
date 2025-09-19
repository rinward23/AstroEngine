"""Compatibility layer for :mod:`astroengine.core.domains`."""

from __future__ import annotations

from .core.domains import (
    DEFAULT_HOUSE_DOMAIN_WEIGHTS,
    DEFAULT_PLANET_DOMAIN_WEIGHTS,
    DOMAINS,
    ELEMENTS,
    ZODIAC_ELEMENT_MAP,
    DomainResolution,
    DomainResolver,
    natal_domain_factor,
)

__all__ = [
    "ELEMENTS",
    "DOMAINS",
    "ZODIAC_ELEMENT_MAP",
    "DEFAULT_PLANET_DOMAIN_WEIGHTS",
    "DEFAULT_HOUSE_DOMAIN_WEIGHTS",
    "DomainResolver",
    "DomainResolution",
    "natal_domain_factor",
]
