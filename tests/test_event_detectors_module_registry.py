from astroengine.modules.event_detectors import register_event_detectors_module
from astroengine.modules.registry import AstroRegistry


EXPECTED_RESOLVERS = {
    ("stations", "stations", "direct"): "astroengine.detectors.stations.find_stations",
    ("stations", "stations", "shadow"): "astroengine.detectors.stations.find_shadow_periods",
    ("ingresses", "sign", "transits"): "astroengine.detectors.ingresses.find_sign_ingresses",
    ("ingresses", "house", "transits"): "astroengine.detectors.ingresses.find_house_ingresses",
    ("lunations", "solar", "new_and_full"): "astroengine.detectors.lunations.find_lunations",
    ("lunations", "lunar", "eclipses"): "astroengine.detectors.eclipses.find_eclipses",
    ("declination", "declination", "oob"): "astroengine.detectors.out_of_bounds.find_out_of_bounds",
    ("declination", "declination", "parallel"): "astroengine.detectors.detect_decl_contacts",
    ("overlays", "midpoints", "transits"): "astroengine.chart.composite.compute_midpoint_tree",
    ("overlays", "fixed_stars", "contacts"): "astroengine.plugins.examples.fixed_star_hits._detect_fixed_star_hits",
    ("overlays", "returns", "transits"): "astroengine.detectors.returns.solar_lunar_returns",
    ("overlays", "profections", "transits"): "astroengine.timelords.profections.generate_profection_periods",
}


def test_event_detector_registry_resolvers_match_documentation():
    registry = AstroRegistry()
    register_event_detectors_module(registry)

    snapshot = registry.as_dict()["event_detectors"]["submodules"]
    for key, resolver in EXPECTED_RESOLVERS.items():
        submodule, channel, subchannel = key
        node = snapshot[submodule]["channels"][channel]["subchannels"][subchannel]
        payload = node.get("payload", {})
        assert payload.get("resolver") == resolver
        assert payload.get("datasets"), f"datasets missing for {key}"
        assert payload.get("event_type"), f"event type missing for {key}"
