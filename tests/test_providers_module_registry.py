from astroengine.modules.providers import register_providers_module
from astroengine.modules.registry import AstroRegistry


def test_providers_registry_exposes_skyfield_metadata():
    registry = AstroRegistry()
    register_providers_module(registry)

    snapshot = registry.as_dict()["providers"]["submodules"]["ephemeris"]["channels"]["plugins"][
        "subchannels"
    ]
    skyfield = snapshot["skyfield"]

    metadata = skyfield["metadata"]
    payload = skyfield["payload"]

    assert metadata.get("status") == "active"
    assert "tests/test_providers_module_registry.py" in metadata.get("tests", [])
    assert payload.get("module") == "astroengine.providers.skyfield_provider"
    assert payload.get("design_notes") == "astroengine/providers/skyfield_provider.md"
    datasets = payload.get("datasets", [])
    assert "astroengine/providers/skyfield_kernels.py" in datasets
    assert "docs/module/providers_and_frames.md" in datasets
