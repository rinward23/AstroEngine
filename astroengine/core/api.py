"""Public API dataclasses used by AstroEngine helpers."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field


@dataclass
class TransitEvent:
    """Container for a resolved transit event.

    Attributes
    ----------
    timestamp:
        Timestamp in UTC. ``None`` is used for detectors that only emit
        positional metadata.
    body:
        Moving body symbol (``"mars"``, ``"moon"``…).
    target:
        Static body or chart point symbol (e.g. ``"natal_sun"``).
    aspect:
        Canonical aspect name such as ``"conjunction"`` or ``"square"``.
    orb:
        Signed separation in **degrees** relative to the aspect angle.
        Negative values represent applying contacts. Values are expected
        to fall inside the configured orb policy.
    motion:
        ``"applying"``, ``"separating"``, or ``"stationary"`` depending on
        relative speed calculations.
    elements:
        Optional elemental tags derived from domain scoring.
    element_domains:
        Mapping of element name → weight reflecting the Mind/Body/Spirit bridge.
    domains:
        Mapping of domain name → weight (each weight in ``[0, 1]``).
    domain_profile:
        Identifier of the profile that produced ``domains``.
    severity:
        Composite severity score in ``[0, 1]`` when profiles supply a
        weighting model.
    metadata:
        Free-form provenance dictionary recorded by detectors.
    """

    timestamp: _dt.datetime | None = None
    body: str | None = None
    target: str | None = None
    aspect: str | None = None
    orb: float | None = None
    motion: str | None = None
    elements: list[str] = field(default_factory=list)
    element_domains: dict[str, float] = field(default_factory=dict)
    domains: dict[str, float] = field(default_factory=dict)
    domain_profile: str | None = None
    severity: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class TransitScanConfig:
    """Configuration options for a transit scan.

    Parameters
    ----------
    ruleset_id:
        Identifier of the ruleset to load from the registry.
    enable_declination:
        Toggle declination parallels/contraparallels.
    enable_mirrors:
        Toggle antiscia/contra-antiscia detection.
    enable_harmonics:
        Toggle harmonic aspect families defined in the selected profile.
    """

    ruleset_id: str = "vca_core"
    enable_declination: bool = True
    enable_mirrors: bool = True
    enable_harmonics: bool = True


__all__ = ["TransitEvent", "TransitScanConfig"]
