# AstroEngine Provider Registry

```AUTO-GEN[providers.registry]
PURPOSE
  - Document discovery, configuration, and conformance expectations for provider plugins exposed through the ``astroengine.providers`` entry-point group.

IMPLEMENTATION STATUS
  - `astroengine/providers/__init__.py` implements `ProviderMetadata`, `ProviderError`, alias-aware registration helpers, and `load_entry_point_providers()`.
  - Metadata availability is exercised by `tests/test_provider_registry_metadata.py` while registry wiring for module metadata lives in `tests/test_providers_module_registry.py`.

ENTRY POINT CONTRACT
  - Group: ``astroengine.providers``.
  - Each entry point must expose a callable ``load() -> EphemerisProvider``.
  - Entry point name SHOULD match ``{provider_id}`` declared in :class:`ProviderMetadata`.

METADATA REQUIREMENTS
  - Providers must populate :class:`ProviderMetadata` with:
        * ``provider_id``: snake_case identifier.
        * ``version``: semantic version string.
        * ``supported_bodies``: ordered list of canonical AstroEngine body IDs.
        * ``supported_frames``: e.g., ``['ecliptic_true_date', 'equatorial_true']``.
        * ``supports_declination`` / ``supports_light_time`` booleans.
        * ``cache_layout``: mapping of cache component → relative path templates.
        * ``extras_required``: extras marker (e.g., ``['skyfield']``).
  - Metadata must be serializable to JSON for registry export.

DISCOVERY FLOW
  1. Importlib iterates over entry points in deterministic sorted order.
  2. Call ``load()``; providers MUST raise ``ProviderError`` for misconfiguration.
  3. Register provider metadata in internal registry keyed by ``provider_id``; reject duplicates.
  4. Emit structured logs summarizing available providers, versions, cache paths, extras.

CONFIGURATION HIERARCHY
  - Global defaults from ``profiles/base_profile.yaml``.
  - Profile overrides via nested keys ``providers.{provider_id}.*``.
  - CLI/ENV overrides (highest precedence) using ``ASTROENGINE_PROVIDER_{ID}_*`` variables.

SECURITY & COMPLIANCE
  - Maintain whitelist of allowed cache directories; all paths resolved via ``Path.resolve()`` with root check.
  - Validate checksums before trusting cached ephemerides; log mismatches.
  - Store license metadata for each provider (SPDX identifier, URL) to support audits.

CONFORMANCE TESTING
  - Smoke test: instantiate each provider, run ``prime_cache`` + ``query`` for sample timestamp (2000-01-01T00:00:00Z) across bodies declared in metadata.
  - Determinism test: run repeated queries, hash results using canonical serializer.
  - Precision test: compare provider outputs vs reference (Skyfield) when available; enforce tolerance per body class.
  - Failure-path test: simulate missing cache directory, confirm provider raises documented ``ProviderError`` with correct ``retriable`` flag.

TELEMETRY REGISTRATION
  - Each provider must emit metrics/log labels ``provider_id`` and ``version``.
  - Registry module wires provider registrations into the Prometheus exporter using
    counters/gauges registered in :mod:`astroengine.observability.metrics`:
        * ``astroengine_provider_registrations_total`` (labels: ``provider_id``, ``version``).
        * ``astroengine_provider_registry_active`` (labels: ``provider_id``, ``version``).
        * ``astroengine_provider_queries_total`` (labels: ``provider_id``, ``call``).
        * ``astroengine_provider_cache_hits_total`` (labels: ``provider_id``).
        * ``astroengine_provider_failures_total`` (labels: ``provider_id``, ``error_code``).
  - Registered provider instances expose a ``metrics`` attribute referencing a
    :class:`~astroengine.observability.metrics.ProviderMetricRecorder` for direct
    emission of query/cache/failure counters.
```
