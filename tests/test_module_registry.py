from astroengine import DEFAULT_REGISTRY, serialize_vca_ruleset


def test_vca_module_registered():
    module = DEFAULT_REGISTRY.get_module("vca")
    assert module.metadata["description"].startswith("Venus Cycle")
    catalogs = module.get_submodule("catalogs")
    bodies = catalogs.get_channel("bodies")
    assert "core" in bodies.subchannels
    profiles = module.get_submodule("profiles")
    domain_channel = profiles.get_channel("domain")
    assert "vca_neutral" in domain_channel.subchannels
    rulesets = module.get_submodule("rulesets")
    aspects = rulesets.get_channel("aspects")
    assert "definitions" in aspects.subchannels


def test_serialize_vca_ruleset_matches_registry():
    payload = serialize_vca_ruleset()
    module = DEFAULT_REGISTRY.get_module("vca")
    rulesets = module.get_submodule("rulesets")
    aspects = rulesets.get_channel("aspects")
    definitions = aspects.get_subchannel("definitions").describe()
    assert payload["id"] == definitions["payload"]["id"]
