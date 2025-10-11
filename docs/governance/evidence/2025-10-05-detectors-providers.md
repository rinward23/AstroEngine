# Evidence Log — Detectors & Providers Implementation

- **Date**: 2025-10-05
- **Scope**: Event detector registry wiring, provider metadata/entrypoint infrastructure.

## Runtime updates
- `astroengine/providers/__init__.py` now exposes `ProviderMetadata`, `ProviderError`, alias-aware `register_provider`, and `load_entry_point_providers()` alongside metadata lookups.
- `astroengine/providers/swiss_provider.py` and `astroengine/providers/skyfield_provider.py` publish metadata (including availability flags and aliases) when registering their adapters.
- `astroengine/modules/providers/__init__.py` marks the `skyfield` channel active and links to the live runtime module.
- `astroengine/modules/event_detectors/__init__.py` references `tests/test_event_detectors_module_registry.py` to keep the documentation-aligned wiring auditable.

## Test coverage
- `tests/test_provider_registry_metadata.py` verifies provider registration, metadata queries, and entry-point loading helpers.
- `tests/test_providers_module_registry.py` asserts that the providers module exports the documented metadata for `skyfield`.
- `tests/test_event_detectors_module_registry.py` checks that every documented resolver in `docs/module/event-detectors/overview.md` is present in the registry snapshot.

## Documentation
- `docs/module/event-detectors/overview.md` links the registry table to the new automated test.
- `docs/module/providers_and_frames.md` documents the provider metadata API, entry-point loader, and the tests backing the Skyfield implementation.
- `docs/providers/registry.md` records the implementation status and associated tests for the provider registry.
- `docs/governance/spec_completion.md` notes that the previously planned detectors/providers are now shipped and references the governing tests.

These artefacts collectively demonstrate that the planned detector and provider modules described in the specifications are live, tested, and documented.
