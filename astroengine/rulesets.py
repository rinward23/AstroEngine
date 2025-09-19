"""Compatibility layer for :mod:`astroengine.modules.vca.rulesets`."""

from __future__ import annotations

from .modules.vca.rulesets import VCA_RULESET, AspectDef, Ruleset, get_vca_aspect, vca_orb_for

__all__ = ["AspectDef", "Ruleset", "VCA_RULESET", "get_vca_aspect", "vca_orb_for"]
