# Acceptance Checklist for "100% Specced"

- **Author**: AstroEngine Governance Board
- **Date**: 2024-05-27

This checklist records the formal approval required to declare the AstroEngine specification complete. Populate each section with signatures, dates, and evidence links. All evidence must reference real datasets and documentation produced in this repository.

## Section A — Module Documentation

- [ ] `core-transit-math` documentation reviewed, provenance verified (`docs/module/core-transit-math.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `event-detectors` overview validated (`docs/module/event-detectors/overview.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `providers` contract confirmed (`docs/module/providers_and_frames.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `ruleset_dsl` grammar/linter approved (`docs/module/ruleset_dsl.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `data-packs` provenance checked (`docs/module/data-packs.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `interop` spec aligned with schemas (`docs/module/interop.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `qa_acceptance` plan executed (`docs/module/qa_acceptance.md`). Reviewer: __________________ Date: __________ Evidence: __________________
- [ ] `release_ops` plan approved (`docs/module/release_ops.md`). Reviewer: __________________ Date: __________ Evidence: __________________

## Section B — Dataset Integrity

- [ ] Solar Fire exports (stations, ingresses, combustion, etc.) checksums recorded and verified. Evidence: __________________
- [ ] Swiss Ephemeris cache checksums verified via `astroengine ephem verify`. Evidence: __________________
- [ ] Atlas/TZ database license and checksum recorded in `docs/module/data-packs.md`. Evidence: __________________
- [ ] Minor planet elements cross-checked with JPL Horizons logs. Evidence: __________________

## Section C — QA & Testing

- [ ] `pip install -e .[dev]` executed in clean virtualenv (attach environment report from `python -m astroengine.infrastructure.environment numpy pandas scipy`). Evidence: __________________
- [ ] `pytest -m "not perf"` passed on reference hardware. Evidence: __________________
- [ ] `pytest -m perf --benchmark-only` meets performance targets. Evidence: __________________
- [ ] Parity suite `pytest tests/parity` within tolerances. Evidence: __________________
- [ ] Golden datasets diff-free (`tests/data/golden_events.jsonl`). Evidence: __________________

## Section D — Interop & Releases

- [ ] AstroJSON schemas published with version increments logged. Evidence: __________________
- [ ] CSV/Parquet/SQLite exports validated against sample data. Evidence: __________________
- [ ] ICS templates verified for severity priority mapping. Evidence: __________________
- [ ] Release checklist executed (tag, wheel build, environment report). Evidence: __________________

## Section E — Security & Compliance

- [ ] License entitlements documented (Solar Fire, ACS Atlas, Swiss Ephemeris). Evidence: __________________
- [ ] OIDC secret rotation logs updated. Evidence: __________________
- [ ] PII redaction checks performed on exports. Evidence: __________________

## Section F — Sign-Off

- **QA Lead**: __________________ Date: __________
- **Data Steward**: __________________ Date: __________
- **Governance Chair**: __________________ Date: __________

Completion of this checklist with supporting evidence authorizes the AstroEngine team to declare the specification complete while preserving module integrity and dataset authenticity.
