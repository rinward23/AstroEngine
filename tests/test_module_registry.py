from astroengine import DEFAULT_REGISTRY, serialize_vca_ruleset
from astroengine.modules.orchestration import load_multi_agent_plan
from astroengine.modules.reference.catalog import (
    CHART_TYPES,
    FRAMEWORKS,
    GLOSSARY,
    INDICATORS,
)


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


def test_integrations_module_catalogues_external_tooling():
    module = DEFAULT_REGISTRY.get_module("integrations")
    ephemeris = module.get_submodule("ephemeris_tooling")
    swiss = ephemeris.get_channel("swiss_ephemeris")
    sweph = swiss.get_subchannel("sweph")
    assert sweph.metadata["project_url"] == "https://www.astro.com/swisseph/"
    assert sweph.payload == {"ephemeris_path": "datasets/swisseph_stub"}

    python_toolkits = module.get_submodule("python_toolkits")
    libraries = python_toolkits.get_channel("libraries")
    assert "flatlib" in libraries.subchannels

    vedic = module.get_submodule("vedic_workflows")
    desktop = vedic.get_channel("desktop_suites")
    assert "maitreya" in desktop.subchannels


def test_reference_module_exposes_catalogued_entries():
    module = DEFAULT_REGISTRY.get_module("reference")
    assert module.metadata["description"].startswith("Knowledge base")

    glossary = module.get_submodule("glossary")
    definitions = glossary.get_channel("definitions")
    for key, entry in GLOSSARY.items():
        payload = definitions.get_subchannel(key).describe()["payload"]
        assert payload["summary"] == entry.summary
        assert payload["sources"] == [source.as_payload() for source in entry.sources]

    charts = module.get_submodule("charts")
    types_channel = charts.get_channel("types")
    for key, entry in CHART_TYPES.items():
        data = types_channel.get_subchannel(key).describe()
        assert data["metadata"]["term"] == entry.term

    frameworks = module.get_submodule("frameworks")
    systems = frameworks.get_channel("systems")
    for key, entry in FRAMEWORKS.items():
        assert systems.get_subchannel(key).metadata["term"] == entry.term

    indicators = module.get_submodule("indicators")
    catalog = indicators.get_channel("catalog")
    for key, entry in INDICATORS.items():
        node = catalog.get_subchannel(key).describe()
        assert node["metadata"]["term"] == entry.term
        assert node["payload"]["summary"] == entry.summary
        assert node["payload"]["sources"] == [source.as_payload() for source in entry.sources]


def test_orchestration_module_registers_multi_agent_workflow():
    module = DEFAULT_REGISTRY.get_module("orchestration")
    submodule = module.get_submodule("multi_agent")
    workflows = submodule.get_channel("workflows")
    node = workflows.get_subchannel("solar_fire_tracking_v1").describe()
    plan = load_multi_agent_plan()

    assert node["version"] == plan["version"]
    assert node["payload"]["observability"]["metrics_dashboard"] == "observability/dashboards/engine_scans.json"
    assert [agent["name"] for agent in plan["agents"]]
    assert node["payload"]["agents"][0]["name"] == plan["agents"][0]["name"]
