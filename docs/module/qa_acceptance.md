# QA & Acceptance Plan

- **Module**: `qa_acceptance`
- **Maintainer**: Quality Guild
- **Source artifacts**:
  - Automated tests under `tests/`
  - Schemas in `schemas/`
  - Registry wiring in `astroengine/modules`
  - Profiles and data packs in `profiles/`

This plan captures the checks that must pass before shipping changes to the runtime or documentation. The focus is on the artefacts that currently exist in the repository; as new modules land, extend the plan and add corresponding tests.

## Determinism & environment controls

1. Create or activate a virtual environment and install dependencies via `pip install -e .[dev]`.
2. Capture an environment report with `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb`; attach the JSON output to QA notes when publishing releases.
3. Run `pytest` to execute the automated suite. The current tests are fast (≪1 s) and provide coverage for schemas, registry wiring, profiles, and scoring helpers.
4. For any changes impacting ephemeris or scoring, generate a Solar Fire comparison report (CSV or PDF) and capture the checksum alongside the QA artefacts. This proves runtime output matches the external benchmark.

## Automated test inventory

| Test file | Focus | Notes |
| --- | --- | --- |
| `tests/test_module_registry.py` | Ensures the default registry registers key modules (`vca`, `integrations`) and their submodules/channels. | Protects the module → submodule → channel hierarchy. |
| `tests/test_vca_ruleset.py` | Verifies aspect angles and orb lookups exposed through `astroengine.rulesets`. | Guards the values documented in `docs/module/core-transit-math.md`. |
| `tests/test_vca_profile.py` | Loads JSON/YAML profiles and confirms active aspect angles match expectations. | Exercises `profiles/base_profile.yaml` and `profiles/vca_outline.json`. |
| `tests/test_domain_scoring.py` | Checks domain weighting methods (`weighted`, `top`, `softmax`). | Ensures severity scaling remains deterministic. |
| `tests/test_domains.py` | Validates zodiac element and domain resolution helpers. | Keeps `astroengine.domains` aligned with documentation. |
| `tests/test_orbs_policy.py` | Validates `schemas/orbs_policy.json` contents and schema registration filters. | Guarantees orb policy data stays in sync with documentation. |
| `tests/test_result_schema.py` | Validates the run result schema using `astroengine.validation.validate_payload`. | Confirms required fields and nested structures. |
| `tests/test_contact_gate_schema.py` | Performs the same checks for contact gate decisions. | Prevents incompatible gate payloads from shipping. |
| `tests/test_sanity.py` | Placeholder guard that keeps the suite green even when no other tests run. | Should remain trivial and quick. |
| `tests/test_provider_parity.py` | Cross-validates Skyfield and Swiss Ephemeris results using shared QA fixtures. | Loads `qa/artifacts/provider_parity/charts.json` and enforces tolerances documented in `docs/module/providers_and_frames.md`. |

## Future additions

As additional modules come online (e.g., event detectors, provider parity suites), extend this plan with:

- Golden dataset comparisons for detector outputs.
- Performance benchmarks with clearly documented thresholds.
- Maintain cross-provider parity tests to ensure Skyfield and Swiss Ephemeris remain within the documented tolerances (`tests/test_provider_parity.py`).
- Documentation of new QA artefacts in `docs/burndown.md` and, when data changes, entries in `docs/governance/data_revision_policy.md`.
- Automated verification that Solar Fire comparison reports match the runtime output for a rolling sample of charts (store hashes for each report).

Documenting these expectations ensures every release remains tied to reproducible test evidence generated inside the maintained environment.
