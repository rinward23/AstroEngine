# AstroEngine v1.0 — 100% Specification Completion Plan

This document enumerates the documentation and data deliverables required to declare
AstroEngine v1.0 "100% specced." Each checklist item results in text-only
artifacts (Markdown/JSON/YAML schemas, CSV dictionaries, or similar) that instruct
subsequent implementation change packets. The plan respects the module → submodule
→ channel → subchannel hierarchy and enforces lossless handling of referenced
assets (no module removals). Every output described below must source verifiable
astrological data (e.g., Solar Fire exports, Swiss Ephemeris, or vetted research
texts) — synthetic data is explicitly disallowed.

## Repository Targets & Traceability

* Create a `docs/` tree mirroring the runtime hierarchy:
  * `docs/module/` (top-level module narratives).
  * `docs/module/<module>/submodules/` (submodule specs).
  * `docs/module/<module>/channels/<channel>/` (channel+subchannel specs).
  * Newly established developer experience assets live under `docs/module/developer_platform.md` with supporting channel docs in `docs/module/developer_platform/` so SDK, CLI, portal, and webhook artefacts retain their module lineage.
* Within each scope, include provenance appendices for any dataset reference
  (CSV, SQLite, Parquet, etc.) and index the file offsets or table names needed
  by the runtime for deterministic retrieval.
* Each spec document records: date, author, source datasets, checksum or version,
  related profiles/rulesets, and downstream export links.

## 0) Definition of “Spec Complete”

Document in `docs/governance/spec_completion.md` the acceptance definition:

* (a) Scope & intent – plain-language description for each feature, linked to its
  module/channel home.
* (b) Inputs/outputs & units – enumerated lists, including coordinate frames and
  measurement units (degrees, arcminutes, arcseconds, hours, calendar date/time,
  etc.).
* (c) Default constants & profile toggles – tabulated defaults, profile names,
  JSON/YAML identifiers, and override precedence rules.
* (d) Gate/rules phrases – canonical sentences for DSL consumption and UI output.
* (e) Acceptance checks – deterministic scenarios, expected pass/fail conditions,
  and references to sample payloads or golden JSONL entries.
* (f) Interoperability/exports notes – mapping to AstroJSON, CSV, Parquet, SQLite,
  and ICS targets; include schema version references.
* (g) Observability hooks – structured log fields, metrics names, and severity
  routing guidelines.
* (h) Edge cases – curated table of edge scenarios (retro loops, DST transitions,
  high-latitude charts, etc.) with mitigation strategies.

## A) Core Transit Math — Close the Loop

Create `docs/module/core-transit-math.md` with appendices per subsection.

### A1. Aspect Canon

* Provide a canonical table enumerating all aspect families, angles (degrees),
  harmonic numbers, naming conventions, and symmetry properties (e.g., polarity,
  duplications at 360°−θ).
* Document allowed integer harmonics for each family, explicitly calling out
  exclusions and deprecated items.
* Include visualization guidance (e.g., circular diagram spec) for future UI.

### A2. Orbs Policy Matrix

* Deliver a matrix specification covering body class × natal point class × aspect
  family × context (angle/midpoint/fixed-star) × profile. Capture defaults,
  overrides, and fallback policies.
* Include JSON/YAML profile identifiers, default orb values (luminaries 8°, etc.),
  declination and partile thresholds, and rules for angle/midpoint/star overrides.
* Provide narrative on interpolation between profiles and conflict resolution.

### A3. Severity Model

* Specify the quadratic falloff formula, body and aspect weights, modifiers
  (partile, angularity, dignity, sect, retro phase), clamp bounds, and invariant
  properties (e.g., symmetry between applying/separating at equal Δλ).
* Supply sample score traces for representative events and define band thresholds
  (weak/moderate/strong/peak) with numeric ranges.
* Record required observability outputs (per-event severity score, contributing
  factors, normalized weights).

### A4. Applying/Separating & Δλ Continuity

* Formalize definitions for applying vs. separating based on relative longitudinal
  speed and Δλ continuity across 0°/360°.
* Detail handling for retrograde loops, stationary moments, and multi-body cases
  (e.g., midpoint triggers).
* Include algorithmic flowcharts for later implementation, ensuring testable edge
  cases are enumerated.

## B) Event Detectors — Full Coverage

Create `docs/module/event-detectors/overview.md` with subsections (one per
 detector) containing:

* Detector signature (function/DSL prototype) with required inputs and outputs.
* Threshold defaults, profile toggles, gate phrases, and acceptance scenarios.
* Observability hooks (log fields, metrics) and export mappings.
* Data requirements (ephemeris precision, dataset references, indexing strategy).

For each detector (Stations through Relocation/Astrocartography), supply:

1. Detector signature, inputs (ephemeris state, natal chart data, profile flags),
   outputs/flags (`station_kind`, `in_shadow`, etc.), thresholds, toggles, gate
   phrases, and deterministic acceptance scenarios (with Solar Fire cross-checks
   where applicable).
2. Special handling for optional detectors (Progressions/Directions, Relocation)
   including gating conditions and export expectations.

## C) Providers & Frames — Contract Finalization

Document in `docs/module/providers_and_frames.md`:

* Provider API contract for `ecliptic_state`, `lunation`, `eclipse`, `station`,
  `houses`, `ayanamsha`, `ephemeris_info` (method signatures, inputs/outputs,
  units, error handling, caching behavior).
* House system coverage with accuracy requirements and fallback logic for extreme
  latitudes; include tolerance tables against Swiss Ephemeris/Skyfield.
* Ayanamsha definitions with references, epochs, and formulas.
* Topocentric switch behavior (altitude, latitude, refraction policy) and required
  dataset fields.
* Ephemeris cache policy (supported sets, checksums, offline behavior, CLI
  commands for `ephem pull/list/verify`).

## D) Ruleset DSL — Grammar & Linter

Write `docs/module/ruleset_dsl.md` capturing:

* Full EBNF grammar, type system, comparison operators, list literals, and
  function call syntax.
* Predicate catalog (stations, ingresses, etc.) including argument lists, return
  types, and associated gate phrases.
* Error taxonomy (unknown predicate, arity mismatch, type mismatch, unreachable
  gates) with diagnostic examples and remediation guidance.
* Linter rule list covering rule overlaps, missing caps, severity range checks,
  orphan exports, and module/channel integrity.

## E) Data Packs — Content & Licensing

Create `docs/module/data-packs.md` detailing:

* Fixed star bright list v1 fields, orbs per star, provenance (catalog, epoch),
  licensing terms, and precession/proper motion methodology.
* Dignities & sect tables (rulership, exaltation, triplicity day/night, terms,
  faces, benefic/malefic designations, weightings) with source citations.
* House rulers (traditional vs. modern) as sign → planet tables with references.
* Minor planet IDs (Ceres, Pallas, Juno, Vesta, optional Eris/Sedna) including
  default orbs, profile toggles, and licensing notes.
* I18N label maps for signs/houses/aspects (key structure, English baseline,
  extension policy) and instructions for localization packages.
* Atlas/TZ requirements (tzid resolution flow, OSM/Nominatim usage, DST ambiguity
  handling, consent/licensing).

## F) Exports & Interop — Schemas & Conventions

Define in `docs/module/interop.md`:

* AstroJSON schemas (`natal_v1`, `event_v1`, `transit_v1`) with fields, units,
  nullability, enums, and versioning policies.
* CSV/Parquet export field lists, partitioning schemes, encoding, and compression
  defaults.
* SQLite schema for `transits_events` (columns, indices, version tables).
* ICS event format (SUMMARY template, PRIORITY mapping from severity, DESCRIPTION
  metadata structure) and compatibility considerations with major calendar apps.
* Provenance requirements (provider IDs, profile IDs, ruleset tag, ephemeris
  checksum, scan window) for every export channel.

## G) QA & Acceptance — What Makes It Testable

Produce `docs/module/qa_acceptance.md` outlining:

* Determinism controls (golden JSONL location, SHA256 update workflow, env
  toggles).
* Property test inventory (angle wrapping, Δλ continuity, severity symmetry,
  antiscia/parallel invariants, determinism).
* Cross-backend parity checks (Skyfield vs. SWE) with tolerance bands.
* Performance targets (30-day window throughput, refinement iteration medians,
  CI regression thresholds) and measurement methodology.
* Edge-case catalog (high latitudes, BCE/Julian, DST ambiguities, retro loops)
  with expected behavior.
* Synastry/composite and mundane acceptance scenarios, including data sources
  and verification steps.

## H) Release & Ops — Ship-Ready

Summarize in `docs/module/release_ops.md`:

* Packaging extras (`skyfield`, `swe`, `parquet`, `cli`, `dev`, `maps`) with
  dependency lists and compatibility guarantees.
* Compatibility matrix skeleton showing module ↔ ruleset ↔ profile ↔ provider
  support, and procedures for updates without module loss.
* Docker image requirements (runtime vs. lab, ephemeris cache strategy,
  configuration injection).
* Conda-forge feedstock plan post-0.1.0 (build matrix, testing, license).
* Observability stack (JSON logs, Prometheus/statsd counters, CLI flags) with
  event fields and severity guidelines.
* PII/security policy (redaction defaults, user consent tracking, license audit,
  OIDC publishing guardrails).

## I) Burn-Down to 100%

Track progress in `docs/burndown.md` with a task list for the next actions:

1. Ruleset DSL EBNF + error taxonomy + linter rule list (link to section D).
2. Orbs severity matrix (full enumeration, overrides, two named profiles).
3. Provider spec (house list, ayanamshas, parity thresholds, ephemeris cache).
4. Event detectors (stations, ingresses, lunations/eclipses, combust/OOB,
   declination, antiscia, midpoints, fixed stars, Vertex) — thresholds & gates.
5. Data packs (fixed-star bright list v1, dignities/sect tables, house rulers,
   minor planets, licensing notes).
6. Interop (AstroJSON v1, export schemas, SQLite/ICS conventions).
7. QA docs (determinism/property tests, performance targets, edge-case catalog).
8. Ops (compatibility matrix, packaging extras, Docker & conda plans).

Each burn-down item records owner, status, due date, dependencies, and links to
supporting documents. Completion requires peer review sign-off and dataset
integrity verification (checksum alignment with source archives).

## J) Acceptance for “100% Specced”

Create `docs/governance/acceptance_checklist.md` consolidating completion
criteria:

* Confirm every section (A–H) has a document containing defaults, toggles, gate
  phrases, and acceptance checks, signed off by the ruleset committee.
* Verify datasets (stars, dignities, rulers, minor planets) include provenance,
  licensing, and integrity hashes.
* Ensure DSL grammar/linter docs ship with worked examples and failure messages.
* Validate export schemas expose stable field lists and provenance metadata.
* Confirm QA documents define golden scenarios, property tests, performance
  targets, and edge-case coverage.
* Sign off on release/ops plans (compatibility matrix, packaging, Docker, conda,
  observability, PII/security safeguards).

Once the acceptance checklist is complete and the repository maintains a clean
module/submodule/channel/subchannel index without deletions, AstroEngine may be
declared **100% specced**, unlocking implementation change packets.
