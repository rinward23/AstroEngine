"""Registry metadata for the transit detector suite."""

from __future__ import annotations

from ..registry import AstroRegistry

__all__ = ["register_event_detectors_module"]


def _payload(
    *,
    resolver: str,
    event_type: str,
    datasets: list[str],
    tests: list[str] | None = None,
    notes: str | None = None,
    schema: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "resolver": resolver,
        "event_type": event_type,
        "datasets": datasets,
    }
    if tests:
        payload["tests"] = tests
    if notes:
        payload["notes"] = notes
    if schema:
        payload["schema"] = schema
    if extra:
        payload.update(extra)
    return payload


def register_event_detectors_module(registry: AstroRegistry) -> None:
    """Register the live detector hierarchy with provenance metadata."""

    module = registry.register_module(
        "event_detectors",
        metadata={
            "description": "Swiss Ephemeris driven transit detectors with Solar Fire parity checks.",
            "status": "active",
            "datasets": [
                "profiles/base_profile.yaml",
                "profiles/fixed_stars.csv",
                "rulesets/transit/stations.ruleset.md",
                "rulesets/transit/ingresses.ruleset.md",
                "rulesets/transit/lunations.ruleset.md",
                "rulesets/transit/scan.ruleset.md",
            ],
            "tests": [
                "tests/test_stations_impl.py",
                "tests/test_ingress_features.py",
                "tests/test_ingresses_mundane.py",
                "tests/test_lunations_impl.py",
                "tests/test_out_of_bounds_impl.py",
                "tests/test_detectors_aspects.py",
                "tests/test_event_detectors_module_registry.py",
            ],
            "notes": "See docs/module/event-detectors/overview.md for Solar Fire verification reports.",
        },
    )

    stations = module.register_submodule(
        "stations",
        metadata={
            "description": "Retrograde/direct station detection including shadow windows.",
            "datasets": [
                "profiles/base_profile.yaml",
                "rulesets/transit/stations.ruleset.md",
            ],
            "tests": ["tests/test_stations_impl.py"],
        },
    )
    station_channel = stations.register_channel(
        "stations",
        metadata={"profile_toggle": "feature_flags.stations"},
    )
    station_channel.register_subchannel(
        "direct",
        metadata={"description": "Zero-speed stations (retrograde ↔ direct)."},
        payload=_payload(
            resolver="astroengine.detectors.stations.find_stations",
            event_type="astroengine.events.StationEvent",
            datasets=[
                "Swiss Ephemeris",
                "profiles/base_profile.yaml",
                "rulesets/transit/stations.ruleset.md",
            ],
            tests=["tests/test_stations_impl.py"],
            notes="Station points refined via longitudinal speed root finding.",
        ),
    )
    station_channel.register_subchannel(
        "shadow",
        metadata={"description": "Pre- and post-retrograde shadow periods."},
        payload=_payload(
            resolver="astroengine.detectors.stations.find_shadow_periods",
            event_type="astroengine.events.ShadowPeriod",
            datasets=[
                "Swiss Ephemeris",
                "profiles/base_profile.yaml",
                "rulesets/transit/stations.ruleset.md",
            ],
            tests=["tests/test_stations_impl.py"],
            notes="Shadow intervals locate the longitude crossings of the paired station longitudes.",
        ),
    )

    ingresses = module.register_submodule(
        "ingresses",
        metadata={
            "description": "Sign and house ingress detection from Swiss Ephemeris sampling.",
            "datasets": ["rulesets/transit/ingresses.ruleset.md"],
            "tests": [
                "tests/test_ingress_features.py",
                "tests/test_ingresses_mundane.py",
            ],
        },
    )
    ingress_sign = ingresses.register_channel(
        "sign",
        metadata={"profile_toggle": "feature_flags.ingresses.enabled"},
    )
    ingress_sign.register_subchannel(
        "transits",
        metadata={"description": "Transiting bodies crossing zodiac sign boundaries."},
        payload=_payload(
            resolver="astroengine.detectors.ingresses.find_sign_ingresses",
            event_type="astroengine.events.IngressEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/ingresses.ruleset.md",
            ],
            tests=["tests/test_ingress_features.py"],
            notes="Boundaries derived from tropical sign divisions; honours feature flag gating for fast movers.",
        ),
    )
    ingress_house = ingresses.register_channel(
        "house",
        metadata={"profile_toggle": "feature_flags.ingresses.enabled"},
    )
    ingress_house.register_subchannel(
        "transits",
        metadata={"description": "Ingresses against natal house cusps supplied by providers."},
        payload=_payload(
            resolver="astroengine.detectors.ingresses.find_house_ingresses",
            event_type="astroengine.events.IngressEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/ingresses.ruleset.md",
                "docs/module/providers_and_frames.md",
            ],
            tests=["tests/test_ingresses_mundane.py"],
            notes="Requires house cusp arrays from astroengine.chart.natal.compute_natal_chart.",
        ),
    )

    lunations = module.register_submodule(
        "lunations",
        metadata={
            "description": "Solar and lunar phase detection with eclipse visibility checks.",
            "datasets": ["rulesets/transit/lunations.ruleset.md"],
            "tests": ["tests/test_lunations_impl.py", "tests/test_eclipses_impl.py"],
        },
    )
    lunations.register_channel(
        "solar",
        metadata={"profile_toggle": "feature_flags.lunations"},
    ).register_subchannel(
        "new_and_full",
        metadata={"description": "New and full Moon exactitudes."},
        payload=_payload(
            resolver="astroengine.detectors.lunations.find_lunations",
            event_type="astroengine.events.LunationEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/lunations.ruleset.md",
            ],
            tests=["tests/test_lunations_impl.py"],
            notes="Phase detection samples the Sun/Moon phase angle and refines with root finding.",
        ),
    )
    lunations.register_channel(
        "lunar",
        metadata={"profile_toggle": "feature_flags.eclipses"},
    ).register_subchannel(
        "eclipses",
        metadata={"description": "Solar and lunar eclipses with optional visibility filtering."},
        payload=_payload(
            resolver="astroengine.detectors.eclipses.find_eclipses",
            event_type="astroengine.events.EclipseEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/lunations.ruleset.md",
            ],
            tests=["tests/test_eclipses_impl.py"],
            notes="Visibility flags honour Solar Fire parity checks recorded in docs/module/event-detectors/overview.md.",
        ),
    )

    declination = module.register_submodule(
        "declination",
        metadata={
            "description": "Declination aspects and out-of-bounds monitoring.",
            "datasets": ["rulesets/transit/scan.ruleset.md"],
            "tests": [
                "tests/test_out_of_bounds_impl.py",
                "tests/test_detectors_aspects.py",
                "tests/test_fixedstars_and_decl.py",
            ],
        },
    )
    declination_channel = declination.register_channel(
        "declination",
        metadata={"profile_toggle": "feature_flags.declination_aspects"},
    )
    declination_channel.register_subchannel(
        "oob",
        metadata={"description": "Declination out-of-bounds entries and exits."},
        payload=_payload(
            resolver="astroengine.detectors.out_of_bounds.find_out_of_bounds",
            event_type="astroengine.events.OutOfBoundsEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_out_of_bounds_impl.py"],
            notes="Calculates instantaneous declination relative to the solar tropic limit.",
        ),
    )
    declination_channel.register_subchannel(
        "parallel",
        metadata={"description": "Declination parallels and contraparallels."},
        payload=_payload(
            resolver="astroengine.detectors.detect_decl_contacts",
            event_type="astroengine.detectors.CoarseHit",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_detectors_aspects.py"],
            notes="Declination corridor widths respect profile orb policies and antiscia axes.",
        ),
    )

    overlays = module.register_submodule(
        "overlays",
        metadata={
            "description": "Secondary overlays: midpoints, fixed stars, returns, profections.",
            "datasets": ["rulesets/transit/scan.ruleset.md", "profiles/fixed_stars.csv"],
            "tests": [
                "tests/test_progressions_directions_impl.py",
                "tests/test_timelords.py",
                "tests/test_star_names_dataset.py",
            ],
        },
    )
    overlays.register_channel(
        "midpoints",
        metadata={"profile_toggle": "feature_flags.midpoints"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Transit hits against midpoint trees."},
        payload=_payload(
            resolver="astroengine.chart.composite.compute_midpoint_tree",
            event_type="astroengine.chart.composite.MidpointEntry",
            datasets=[
                "profiles/base_profile.yaml",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_progressions_directions_impl.py"],
            notes="Midpoint trees feed detector corridors via astroengine.engine.frames.FrameAwareProvider.",
        ),
    )
    overlays.register_channel(
        "fixed_stars",
        metadata={"profile_toggle": "feature_flags.fixed_stars"},
    ).register_subchannel(
        "contacts",
        metadata={"description": "Fixed-star contacts sourced from FK6-aligned catalogues."},
        payload=_payload(
            resolver="astroengine.plugins.examples.fixed_star_hits._detect_fixed_star_hits",
            event_type="astroengine.exporters.LegacyTransitEvent",
            datasets=[
                "profiles/fixed_stars.csv",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_star_names_dataset.py"],
            notes="Plugins may override the resolver; default implementation mirrors the documented FK6 catalogue checksums.",
        ),
    )
    overlays.register_channel(
        "returns",
        metadata={"profile_toggle": "feature_flags.returns"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Solar and lunar return overlays."},
        payload=_payload(
            resolver="astroengine.detectors.returns.solar_lunar_returns",
            event_type="astroengine.events.ReturnEvent",
            datasets=[
                "Swiss Ephemeris",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_progressions_directions_impl.py"],
            notes="Return tables share provenance with Solar Fire exports referenced in docs/module/event-detectors/overview.md.",
        ),
    )
    overlays.register_channel(
        "profections",
        metadata={"profile_toggle": "feature_flags.profections"},
    ).register_subchannel(
        "transits",
        metadata={"description": "Annual profection rulers exposed as timelord overlays."},
        payload=_payload(
            resolver="astroengine.timelords.profections.generate_profection_periods",
            event_type="astroengine.events.ProfectionEvent",
            datasets=[
                "profiles/base_profile.yaml",
                "rulesets/transit/scan.ruleset.md",
            ],
            tests=["tests/test_timelords.py", "tests/test_timelords_systems.py"],
            notes="Resolvers emit structured ProfectionEvent payloads consumed by narrative and UX layers.",
        ),
    )
