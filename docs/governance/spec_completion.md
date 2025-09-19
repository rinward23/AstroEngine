# Definition of "Spec Complete"

- **Author**: AstroEngine Governance Board
- **Date**: 2024-05-27
- **Scope**: Applies to AstroEngine modules, submodules, channels, and subchannels registered in `astroengine.modules.registry`.

Achieving "spec complete" status requires satisfying the criteria below. Each section references real datasets and documents to ensure no requirement is fulfilled with synthetic information.

## A. Scope & Intent

- Enumerate every module/submodule/channel/subchannel and map them to documentation under `docs/module/`.
- Record intent statements summarizing functionality and dataset dependencies. Example: `event-detectors/stations/direct` → uses Swiss Ephemeris DE441 and Solar Fire station exports.
- Any new module must append to this mapping; removal requires governance vote recorded in meeting minutes.

## B. Inputs, Outputs & Units

- Document inputs (e.g., ephemeris state vectors, natal chart metadata) with explicit units (degrees, arcminutes, arcseconds, UTC timestamps).
- Reference actual data sources such as Solar Fire exports (`exports/`), NASA eclipse tables, or Swiss Ephemeris binaries. Synthetic placeholders are prohibited.
- Ensure outputs specify their serialization format (`astrojson.event_v1`, CSV, SQLite) with field units described in `docs/module/interop.md`.

## C. Default Constants & Profile Toggles

- Consolidate default values (orbs, severity weights, house system fallbacks) using tables from `docs/module/core-transit-math.md`, `docs/module/data-packs.md`, and `docs/module/providers_and_frames.md`.
- Profile toggles (e.g., `vca_tight`, `mundane_profile`) must cite underlying dataset references and appear in registry manifests.
- Changes to defaults require governance approval and an update to provenance tables with new checksums.

## D. Gate/Rules Phrases

- Maintain canonical phrasing for user-facing gate descriptions (e.g., "when Mars enters Leo") and DSL tokens documented in `docs/module/ruleset_dsl.md`.
- Phrases must align with Solar Fire vocabulary to guarantee user familiarity and accurate localization.
- Store phrase templates alongside localization pack entries (`rulesets/i18n/sign_labels.csv`).

## E. Acceptance Checks

- Each module references deterministic QA scenarios defined in `docs/module/qa_acceptance.md` and golden datasets.
- Acceptance requires passing `pytest` suites (functional, property, parity) on the approved environment (Python ≥3.10 with `numpy`, `pandas`, `scipy`).
- Severity thresholds must match Solar Fire exports within documented tolerances.

## F. Interoperability & Exports

- Confirm export formats (AstroJSON, CSV, Parquet, SQLite, ICS) match definitions in `docs/module/interop.md`.
- Every export route includes dataset URNs and checksum validation to prove data lineage.
- Upgrades must be backward compatible; deprecation requires migration documentation and timeline.

## G. Observability Hooks

- Modules must emit structured logs and metrics fields enumerated in their documentation (e.g., `core-transit-math` severity logs, `event-detectors` detector events).
- Observability payloads include dataset checksums and registry identifiers for audit trails.
- Alerting thresholds (e.g., missing peak events) align with `docs/module/release_ops.md`.

## H. Edge Cases

- Edge case catalogs maintained in module docs (retrograde loops, DST transitions, high-latitude charts, eclipse visibility) must link to real datasets from Solar Fire, NASA, or atlas databases.
- Governance board verifies each edge case has reproducible data and QA coverage.

## Verification & Sign-Off Process

1. Module owners submit documentation updates and link to relevant datasets.
2. QA guild confirms deterministic tests, parity, and performance metrics met.
3. Governance board reviews changes, ensuring registry integrity (no module loss) and provenance completeness.
4. Once all criteria satisfied, board records approval in `docs/governance/acceptance_checklist.md` with signatures and dates.

Spec complete status expires if datasets lose provenance, critical tests fail, or modules are removed without board approval.
