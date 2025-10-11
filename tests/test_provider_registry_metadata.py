import contextlib
from importlib import reload
from types import SimpleNamespace

import pytest

import astroengine.providers as providers_module
from astroengine.canonical import BodyPosition


@contextlib.contextmanager
def isolated_registry():
    providers = reload(providers_module)
    registry_snapshot = providers._REGISTRY.copy()
    metadata_snapshot = providers._METADATA_REGISTRY.copy()
    name_snapshot = providers._NAME_TO_PROVIDER_ID.copy()
    try:
        yield providers
    finally:
        providers._REGISTRY.clear()
        providers._REGISTRY.update(registry_snapshot)
        providers._METADATA_REGISTRY.clear()
        providers._METADATA_REGISTRY.update(metadata_snapshot)
        providers._NAME_TO_PROVIDER_ID.clear()
        providers._NAME_TO_PROVIDER_ID.update(name_snapshot)


class _StubProvider:
    provider_id = "stub_ephemeris"

    def positions_ecliptic(self, iso_utc, bodies):
        return {body: {"lon": 0.0, "decl": 0.0, "speed_lon": 0.0} for body in bodies}

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        return BodyPosition(lon=0.0, lat=0.0, dec=0.0, speed_lon=0.0)


def test_register_provider_with_metadata_and_aliases():
    with isolated_registry() as providers:
        metadata = providers.ProviderMetadata(
            provider_id="stub_ephemeris",
            version="1.0.0",
            supported_bodies=("sun", "moon"),
            supported_frames=("ecliptic_true_date",),
            supports_declination=True,
            supports_light_time=False,
            cache_layout={"kernels": "<memory>"},
            extras_required=(),
            description="Test stub provider",
            module="tests.test_provider_registry_metadata",
            available=True,
        )
        providers.register_provider(
            "stub",
            _StubProvider(),
            metadata=metadata,
            aliases=("stub_alias",),
        )

        assert "stub" in providers.list_providers()
        assert providers.get_provider("stub_alias") is providers.get_provider("stub")
        assert providers.get_provider_metadata("stub_ephemeris") == metadata
        assert (
            providers.get_provider_metadata_for_name("stub_alias")
            == providers.get_provider_metadata("stub_ephemeris")
        )

        with pytest.raises(ValueError):
            providers.register_provider("stub", _StubProvider(), metadata=metadata)

        with pytest.raises(KeyError):
            providers.get_provider_metadata("missing")


def test_register_provider_metadata_only_records_unavailable_provider():
    with isolated_registry() as providers:
        metadata = providers.ProviderMetadata(
            provider_id="unavailable_ephemeris",
            version=None,
            supported_bodies=(),
            supported_frames=(),
            supports_declination=False,
            supports_light_time=False,
            cache_layout={},
            extras_required=("skyfield",),
            description="Unavailable provider placeholder",
            module="tests.test_provider_registry_metadata",
            available=False,
        )
        providers.register_provider_metadata(metadata, overwrite=True)

        assert "unavailable_ephemeris" in providers.list_provider_metadata()
        stored = providers.get_provider_metadata("unavailable_ephemeris")
        assert stored.available is False


def test_load_entry_point_providers_registers(monkeypatch):
    with isolated_registry() as providers:
        metadata = providers.ProviderMetadata(
            provider_id="entry_ephemeris",
            version="0.1.0",
            supported_bodies=("sun",),
            supported_frames=("ecliptic_true_date",),
            supports_declination=True,
            supports_light_time=False,
            cache_layout={"kernels": "<none>"},
            extras_required=(),
            description="Entry point provider",
            module="tests.test_provider_registry_metadata",
            available=True,
        )

        class DummyProvider(_StubProvider):
            provider_id = "entry_ephemeris"

        def entry_loader():
            return (DummyProvider(), metadata, ("entry_alias",))

        class DummyEntry(SimpleNamespace):
            def load(self):  # noqa: D401 - simple stub
                return self.payload

        class DummyEntries(list):
            def select(self, *, group):
                return self if group == "astroengine.providers" else []

        entries = DummyEntries(
            [DummyEntry(name="entry_provider", group="astroengine.providers", payload=entry_loader)]
        )

        monkeypatch.setattr(providers.importlib_metadata, "entry_points", lambda: entries)

        loaded = providers.load_entry_point_providers()
        assert "entry_ephemeris" in loaded
        assert providers.get_provider("entry_alias")
        stored = providers.get_provider_metadata("entry_ephemeris")
        assert stored.description == "Entry point provider"
        assert providers.get_provider_metadata_for_name("entry_alias") == stored
