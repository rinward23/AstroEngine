from astroengine.modules.registry import AstroRegistry


def test_registry_resolve_path() -> None:
    registry = AstroRegistry()
    module = registry.register_module("natal")
    submodule = module.register_submodule("charts")
    channel = submodule.register_channel("core")
    subchannel = channel.register_subchannel("radix")

    assert registry.resolve("natal") is module
    assert registry.resolve("natal", submodule="charts") is submodule
    assert registry.resolve("natal", submodule="charts", channel="core") is channel
    assert (
        registry.resolve(
            "natal", submodule="charts", channel="core", subchannel="radix"
        )
        is subchannel
    )
