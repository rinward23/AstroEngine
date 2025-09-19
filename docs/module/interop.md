# Exports & Interoperability Specification

- **Module**: `interop`
- **Maintainer**: Integration Guild
- **Source artifacts**:
  - `schemas/result_schema_v1.json`
  - `schemas/result_schema_v1_with_domains.json`
  - `schemas/contact_gate_schema_v2.json`
  - `schemas/natal_input_v1_ext.json`
  - `schemas/orbs_policy.json`
  - Test coverage in `tests/test_result_schema.py`, `tests/test_contact_gate_schema.py`, and `tests/test_orbs_policy.py`

The AstroEngine validation layer loads JSON schemas and supporting data from `./schemas`. This document describes the current files so downstream exporters know which payloads are supported and how they are tested. The schema keys are registered via `astroengine.data.schemas` and exercised through `astroengine.validation.validate_payload`.

## Schema catalogue

| Key | File | Purpose | Primary sections |
| --- | --- | --- | --- |
| `result_v1` | `schemas/result_schema_v1.json` | Defines the baseline run result payload used by `tests/test_result_schema.py`. | `schema`, `run`, `window`, `subjects`, `channels`, `events`. |
| `result_v1_with_domains` | `schemas/result_schema_v1_with_domains.json` | Extends `result_v1` with domain annotations for each subject/channel. | Adds `domains` array alongside the standard result structure. |
| `contact_gate_v2` | `schemas/contact_gate_schema_v2.json` | Captures gating decisions that map result events into UI narratives. | `schema`, `run`, `gates[*].{channel, decision, window, evidence, audit}`. |
| `natal_input_v1_ext` | `schemas/natal_input_v1_ext.json` | Documents optional metadata collected with Solar Fire imports (rating, zodiac mode, house system). | Enumerated values for `source_rating`, `zodiac`, `house_system`, `preferred_orb_profile`. |
| `orbs_policy` | `schemas/orbs_policy.json` | JSON data (not a JSON Schema) exposing aspect families and profile multipliers so external tools can align orbs with the engine. | `schema`, `profiles.{standard,tight,wide}`, `aspects.{conjunction,…}`. |

## Validation hooks

- `tests/test_result_schema.py` loads a canonical payload via `validate_payload("result_v1", ...)` and asserts that removing required fields (e.g., `events[*].channel`) raises `SchemaValidationError`.
- `tests/test_contact_gate_schema.py` performs the same checks for `contact_gate_v2`.
- `tests/test_orbs_policy.py` ensures that `schemas/orbs_policy.json` stays in sync with the documentation by loading the document through `astroengine.data.schemas.load_schema_document` and inspecting the multipliers.
- `tests/test_module_registry.py` indirectly checks that schema keys remain registered by comparing the registry payload emitted by `serialize_vca_ruleset()` with the documentation.

## Usage notes

- Schema identifiers (`$id`) are stable and should be used when emitting payloads to external systems. Any change requires a version bump and a corresponding update to this file.
- The validation helpers return detailed error messages listing the JSON Pointer path of failing fields. Integrations should surface those messages when rejecting payloads.
- `orbs_policy` is intentionally distributed as data rather than a JSON Schema so that client applications can present profile-aware orb sliders without hard-coding numbers.

## Extending interoperability

When introducing new exports:

1. Add the schema or data file under `schemas/`.
2. Register a key in the schema loader (see `astroengine/data/schemas.py`).
3. Document the new file in the table above.
4. Add pytest coverage that loads the schema via `validate_payload` or `load_schema_document`.
5. Update `docs/burndown.md` to reflect the new deliverable.

Keeping the documentation aligned with the actual files guarantees that every run sequence and export references authentic data rather than inferred values.
