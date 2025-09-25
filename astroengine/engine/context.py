"""Profile-derived runtime context helpers for the scanning engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..astro.declination import DEFAULT_ANTISCIA_AXIS
from ..profiles import load_resonance_weights

__all__ = [
    "ScanFeaturePlan",
    "ScanFeatureToggles",
    "ScanProfileContext",
    "build_scan_profile_context",
]


def _normalize_body(name: str | None) -> str:
    return str(name or "").lower()


def _has_moon(*names: str) -> bool:
    return any(_normalize_body(name) == "moon" for name in names)


def _has_angle(*names: str) -> bool:
    return any(_normalize_body(name) in {"asc", "mc", "ic", "dsc"} for name in names)


def _orb_from_policy(
    policy: Any,
    *,
    moving: str,
    target: str,
    default: float,
    include_moon: bool = True,
    include_angles: bool = False,
    angle_key: str = "angular",
) -> float:
    if isinstance(policy, Mapping):
        value: Any = policy.get("default", default)
        if include_moon and _has_moon(moving, target):
            value = policy.get("moon", value)
        if include_angles and _has_angle(moving, target):
            value = policy.get(angle_key, value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)
    if policy is None:
        return float(default)
    try:
        return float(policy)
    except (TypeError, ValueError):
        return float(default)


def _resolve_declination_orb(
    profile: Mapping[str, Any],
    *,
    kind: str,
    moving: str,
    target: str,
    override: float | None,
) -> float:
    if override is not None:
        return float(override)
    policies = profile.get("orb_policies")
    policy: Any = None
    if isinstance(policies, Mapping):
        policy = policies.get("declination_aspect_orb_deg")
        if isinstance(policy, Mapping):
            kind_policy = policy.get(kind)
            if kind_policy is not None:
                policy = kind_policy
    return _orb_from_policy(
        policy,
        moving=moving,
        target=target,
        default=0.5,
    )


def _resolve_mirror_orb(
    profile: Mapping[str, Any],
    *,
    kind: str,
    moving: str,
    target: str,
    override: float | None,
) -> float:
    if override is not None:
        return float(override)
    policies = profile.get("orb_policies")
    policy: Any = None
    if isinstance(policies, Mapping):
        policy = policies.get("antiscia_orb_deg")
        if isinstance(policy, Mapping):
            kind_policy = policy.get(kind)
            if kind_policy is not None:
                policy = kind_policy
    return _orb_from_policy(
        policy,
        moving=moving,
        target=target,
        default=2.0,
        include_angles=True,
    )


def _resolve_tradition(profile: Mapping[str, Any], override: str | None) -> str | None:
    if override:
        return override
    tradition_section = (
        profile.get("tradition") if isinstance(profile, Mapping) else None
    )
    if isinstance(tradition_section, Mapping):
        default_trad = tradition_section.get("default")
        if isinstance(default_trad, str):
            return default_trad
    return None


def _resolve_chart_sect(profile: Mapping[str, Any], override: str | None) -> str | None:
    if override:
        return override
    natal_section = profile.get("natal") if isinstance(profile, Mapping) else None
    if isinstance(natal_section, Mapping):
        candidate = natal_section.get("chart_sect")
        if isinstance(candidate, str):
            return candidate
    return None


def _resolve_antiscia_axis(
    profile: Mapping[str, Any], axis_override: str | None
) -> str:
    if axis_override:
        return axis_override
    feature_flags = profile.get("feature_flags")
    axis: Any = None
    if isinstance(feature_flags, Mapping):
        antiscia_flags = feature_flags.get("antiscia")
        if isinstance(antiscia_flags, Mapping):
            axis = antiscia_flags.get("axis")
    if axis is None:
        legacy = profile.get("antiscia")
        if isinstance(legacy, Mapping):
            axis = legacy.get("axis")
    if isinstance(axis, str) and axis.strip():
        return axis
    return DEFAULT_ANTISCIA_AXIS


@dataclass(frozen=True, slots=True)
class ScanFeatureToggles:
    """Boolean switches that control which detector families execute."""

    do_declination: bool
    do_parallels: bool
    do_contras: bool
    do_mirrors: bool
    do_aspects: bool

    @property
    def declination_executed(self) -> bool:
        """Return ``True`` when any declination detector will emit events."""

        return self.do_declination and (self.do_parallels or self.do_contras)

    @property
    def parallels_executed(self) -> bool:
        """Return ``True`` when parallel declination passes are active."""

        return self.do_declination and self.do_parallels

    @property
    def contras_executed(self) -> bool:
        """Return ``True`` when contraparallel declination passes are active."""

        return self.do_declination and self.do_contras

    def feature_toggle_map(self) -> dict[str, bool]:
        """Return a mapping mirroring the plugin ``feature_toggles`` contract."""

        return {
            "declination": self.do_declination,
            "declination_parallels": self.do_parallels,
            "declination_contras": self.do_contras,
            "antiscia": self.do_mirrors,
            "aspects": self.do_aspects,
        }

    def executed_feature_map(self) -> dict[str, bool]:
        """Return a mapping mirroring the plugin ``executed_features`` contract."""

        return {
            "declination": self.declination_executed,
            "declination_parallels": self.parallels_executed,
            "declination_contras": self.contras_executed,
            "antiscia": self.do_mirrors,
            "aspects": self.do_aspects,
        }


@dataclass(frozen=True, slots=True)
class ScanFeaturePlan:
    """Computed execution metadata derived from feature toggle inputs."""

    toggles: ScanFeatureToggles
    feature_toggles: Mapping[str, bool]
    executed_features: Mapping[str, bool]
    requested_features: Mapping[str, bool]

    @property
    def declination_executed(self) -> bool:
        """Return whether any declination detector branch will emit events."""

        return bool(self.executed_features.get("declination", False))

    def plugin_metadata(self) -> dict[str, Any]:
        """Return feature toggle payload tailored for detector plugins."""

        feature_toggles = dict(self.feature_toggles)
        executed_features = dict(self.executed_features)
        requested_features = dict(self.requested_features)
        return {
            "feature_toggles": feature_toggles,
            "executed_features": executed_features,
            "requested_features": requested_features,
            "include_declination": executed_features.get("declination", False),
            "include_mirrors": feature_toggles.get("antiscia", False),
            "include_aspects": feature_toggles.get("aspects", False),
        }


@dataclass(frozen=True, slots=True)
class ScanProfileContext:
    """Profile-derived runtime configuration for :func:`scan_contacts`."""

    resonance_weights: Mapping[str, float]
    uncertainty_bias: Mapping[str, str] | None
    tradition: str | None
    chart_sect: str | None
    decl_parallel_orb: float
    decl_contra_orb: float
    antiscia_orb: float
    contra_antiscia_orb: float
    antiscia_axis: str
    declination_flags: Mapping[str, Any]
    antiscia_flags: Mapping[str, Any]

    def feature_toggles(
        self,
        *,
        include_declination: bool,
        include_mirrors: bool,
        include_aspects: bool,
    ) -> ScanFeatureToggles:
        """Derive feature toggles from profile flags and caller overrides."""

        decl_flags = self.declination_flags
        mirror_flags = self.antiscia_flags

        decl_enabled = bool(decl_flags.get("enabled", True)) if decl_flags else True
        parallels_enabled = (
            bool(decl_flags.get("parallels", True)) if decl_flags else True
        )
        contras_enabled = (
            bool(decl_flags.get("contraparallels", True)) if decl_flags else True
        )
        antiscia_enabled = (
            bool(mirror_flags.get("enabled", True)) if mirror_flags else True
        )

        do_declination = include_declination and decl_enabled
        return ScanFeatureToggles(
            do_declination=do_declination,
            do_parallels=do_declination and parallels_enabled,
            do_contras=do_declination and contras_enabled,
            do_mirrors=include_mirrors and antiscia_enabled,
            do_aspects=bool(include_aspects),
        )

    def plan_features(
        self,
        *,
        include_declination: bool,
        include_mirrors: bool,
        include_aspects: bool,
    ) -> ScanFeaturePlan:
        """Return the executed/requested feature plan for the scan."""

        toggles = self.feature_toggles(
            include_declination=include_declination,
            include_mirrors=include_mirrors,
            include_aspects=include_aspects,
        )
        feature_map = toggles.feature_toggle_map()
        executed_map = toggles.executed_feature_map()
        requested_map = {
            "declination": bool(include_declination),
            "mirrors": bool(include_mirrors),
            "aspects": bool(include_aspects),
        }
        return ScanFeaturePlan(
            toggles=toggles,
            feature_toggles=feature_map,
            executed_features=executed_map,
            requested_features=requested_map,
        )


def build_scan_profile_context(
    profile_data: Mapping[str, Any],
    *,
    moving: str,
    target: str,
    decl_parallel_orb: float | None,
    decl_contra_orb: float | None,
    antiscia_orb: float | None,
    contra_antiscia_orb: float | None,
    antiscia_axis: str | None,
    tradition_profile: str | None,
    chart_sect: str | None,
) -> ScanProfileContext:
    """Return the resolved runtime configuration for :func:`scan_contacts`."""

    resonance_weights = dict(load_resonance_weights(profile_data).as_mapping())

    uncertainty_bias: Mapping[str, str] | None = None
    resonance_section = (
        profile_data.get("resonance") if isinstance(profile_data, Mapping) else None
    )
    if isinstance(resonance_section, Mapping):
        bias_section = resonance_section.get("uncertainty_bias")
        if isinstance(bias_section, Mapping):
            uncertainty_bias = {
                str(key): str(value) for key, value in bias_section.items()
            }

    tradition = _resolve_tradition(profile_data, tradition_profile)
    chart_sect_value = _resolve_chart_sect(profile_data, chart_sect)

    decl_parallel_allow = _resolve_declination_orb(
        profile_data,
        kind="parallel",
        moving=moving,
        target=target,
        override=decl_parallel_orb,
    )
    decl_contra_allow = _resolve_declination_orb(
        profile_data,
        kind="contraparallel",
        moving=moving,
        target=target,
        override=decl_contra_orb,
    )
    antiscia_allow = _resolve_mirror_orb(
        profile_data,
        kind="antiscia",
        moving=moving,
        target=target,
        override=antiscia_orb,
    )
    contra_antiscia_allow = _resolve_mirror_orb(
        profile_data,
        kind="contra_antiscia",
        moving=moving,
        target=target,
        override=contra_antiscia_orb,
    )
    axis = _resolve_antiscia_axis(profile_data, antiscia_axis)

    feature_flags = (
        profile_data.get("feature_flags") if isinstance(profile_data, Mapping) else None
    )
    decl_flags: Mapping[str, Any] = {}
    antiscia_flags: Mapping[str, Any] = {}
    if isinstance(feature_flags, Mapping):
        candidate = feature_flags.get("declination_aspects")
        if isinstance(candidate, Mapping):
            decl_flags = dict(candidate)
        candidate = feature_flags.get("antiscia")
        if isinstance(candidate, Mapping):
            antiscia_flags = dict(candidate)

    return ScanProfileContext(
        resonance_weights=resonance_weights,
        uncertainty_bias=uncertainty_bias,
        tradition=tradition,
        chart_sect=chart_sect_value,
        decl_parallel_orb=decl_parallel_allow,
        decl_contra_orb=decl_contra_allow,
        antiscia_orb=antiscia_allow,
        contra_antiscia_orb=contra_antiscia_allow,
        antiscia_axis=axis,
        declination_flags=dict(decl_flags),
        antiscia_flags=dict(antiscia_flags),
    )


# Backwards compatibility hook for unit tests importing the private helper.
_build_scan_profile_context = build_scan_profile_context
