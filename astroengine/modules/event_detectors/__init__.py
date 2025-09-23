"""Placeholder registry entries for the transit event detector suite.

The detector runtime remains under active development.  These placeholders
reserve deterministic module/submodule/channel/subchannel identifiers so
future implementation packets can land without risking accidental module
loss.  Each leaf stores a TODO list that points at the concrete follow-up
work required to activate the detector against real Solar Fire–derived
datasets.
"""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_event_detectors_module"]


_BASE_TODO = [
    "wire Solar Fire derived datasets with indexed lookups",
    "document schema payloads under docs/module/interop.md",
    "add integration tests covering detector output integrity",
]


def _subchannel_payload(*extra: str) -> dict[str, object]:
    """Return a standard payload describing outstanding implementation work."""

    return {"implementation": "pending", "todo": list(_BASE_TODO + list(extra))}


def register_event_detectors_module(registry: AstroRegistry) -> None:
    """Register placeholder detector channels in the shared registry."""

    module = registry.register_module(
        "event_detectors",
        metadata={
            "description": "Transit detector placeholders reserved for upcoming implementations.",
            "status": "planned",
            "notes": "See docs/module/event-detectors/overview.md for design requirements.",
        },
    )

    stations = module.register_submodule(
        "stations",
        metadata={
            "description": "Retrograde/direct station detection awaiting runtime wiring.",
            "todo": [
                "Implement longitudinal speed tracking against indexed ephemerides",
            ],
        },
    )
    station_channel = stations.register_channel(
        "stations",
        metadata={"profile_toggle": "feature_flags.stations"},
    )
    station_channel.register_subchannel(
        "direct",
        metadata={"description": "Direct stations (retrograde → direct)."},
        payload=_subchannel_payload("validate severity falloff against Solar Fire exports"),
    )
    station_channel.register_subchannel(
        "shadow",
        metadata={"description": "Shadow periods bracketing the station moments."},
        payload=_subchannel_payload("record ingress and egress timestamps"),
    )

    ingresses = module.register_submodule(
        "ingresses",
        metadata={"description": "Sign and house ingress detection"},
    )
    ingress_sign = ingresses.register_channel(
        "sign",
        metadata={"profile_toggle": "feature_flags.ingresses.sign"},
    )
    ingress_sign.register_subchannel(
        "transits",
        metadata={"description": "Transiting bodies crossing sign boundaries."},
        payload=_subchannel_payload("include angular gate metadata in payload schemas"),
    )
    ingress_house = ingresses.register_channel(
        "house",
        metadata={"profile_toggle": "feature_flags.ingresses.house"},
    )
    ingress_house.register_subchannel(
        "transits",
        metadata={"description": "Transiting bodies crossing natal house cusps."},
        payload=_subchannel_payload("confirm house calculations honour provider contract"),
    )

    lunations = module.register_submodule(
        "lunations",
        metadata={"description": "Solar and lunar phase detection"},
    )
    lunations.register_channel(
        "solar",
        metadata={"profile_toggle": "feature_flags.lunations"},
    ).register_subchannel(
        "new_and_full",
        metadata={"description": "Solar-phase events (new/full) awaiting severity tables."},
        payload=_subchannel_payload("attach eclipse metadata sourced from real datasets"),
    )
    lunations.register_channel(
        "lunar",
        metadata={"profile_toggle": "feature_flags.eclipses"},
    ).register_subchannel(
        "eclipses",
        metadata={"description": "Placeholder for solar/lunar eclipses and saros links."},
        payload=_subchannel_payload("index saros data in rulesets/transit"),
    )

    declination = module.register_submodule(
        "declination",
        metadata={"description": "Declination overlays including out-of-bounds."},
    )
    declination_channel = declination.register_channel(
        "declination",
        metadata={"profile_toggle": "feature_flags.declination_aspects"},
    )
    declination_channel.register_subchannel(
        "oob",
        metadata={"description": "Out-of-bounds windows and antiscia parallels."},
        payload=_subchannel_payload("define declination orb schema under schemas/events"),
    )
    declination_channel.register_subchannel(
        "parallel",
        metadata={"description": "Parallel and contraparallel detections."},
        payload=_subchannel_payload("cross-check declination thresholds against Solar Fire"),
    )

    overlays = module.register_submodule(
        "overlays",
        metadata={"description": "Midpoints, returns, profections, and fixed-star contacts."},
    )
    overlays.register_channel(
        "midpoints",
        metadata={"profile_toggle": "feature_flags.midpoints"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Transit-to-midpoint triggers derived from real Solar Fire exports."},
        payload=_subchannel_payload("finalise midpoint orb matrices"),
    )
    overlays.register_channel(
        "fixed_stars",
        metadata={"profile_toggle": "feature_flags.fixed_stars"},
    ).register_subchannel(
        "contacts",
        metadata={"description": "Fixed-star contacts referencing profiles/fixed_stars.csv."},
        payload=_subchannel_payload("confirm star catalog indices and source checksums"),
    )
    overlays.register_channel(
        "returns",
        metadata={"profile_toggle": "feature_flags.returns"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Transit overlays against Solar Fire return tables."},
        payload=_subchannel_payload("index Solar Fire return tables in SQLite"),
    )
    overlays.register_channel(
        "profections",
        metadata={"profile_toggle": "feature_flags.profections"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Transit overlays referencing profection rulers."},
        payload=_subchannel_payload("document profection profiles under docs/module/event-detectors"),
    )
