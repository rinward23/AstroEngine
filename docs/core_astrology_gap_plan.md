# Core Astrology Gap Closure Plan

- **Author**: Runtime & Architecture Guild
- **Updated**: 2024-06-06
- **Source baselines**: Swiss Ephemeris 2.10 (via `pyswisseph`), Solar Fire 9 exports (transits, directions, dashā tables), Atlas index (ACS Atlas SQLite mirror), `profiles/base_profile.yaml`, `schemas/natal_input_v1_ext.json`.
- **Scope**: tracks implementation-ready gaps that block "100^1 Coverage" and Inclusion Contract deliverables for classical, predictive, and locational workflows. Every gap references the module → submodule → channel path reserved in the runtime registry so code landings cannot accidentally prune modules.

## Module mapping summary

| Gap | Module → Submodule → Channel target | Coverage contract | Current blockers |
| --- | --- | --- | --- |
| Sidereal ayanāṁśa wiring | `providers.swiss` → `frames.zodiacal` → `sidereal.<ayanamsha>` | Implementation Roadmap, 100^1 Coverage | Adapter never calls `swe.set_sid_mode`; CLI lacks toggle plumbing. |
| Swiss houses parity | `providers.swiss` → `houses` → `placidus/koch/porphyry/equal/whole_sign` | Core Architecture, Inclusion Contract | Adapter ignores configured house system identifiers. |
| Vertex, lots, Lilith | `chart.points` → `derived_points.vertex`, `derived_points.lots`, `derived_points.lilith` | Inclusion Contract, VCA Outline | Catalogued in `astroengine.catalogs.points`, but calculators absent. |
| Primary directions | `predictive.directions` → `primary.<key>` | Core Architecture | Only solar arc implementation exists. |
| Draconic charts | `derived_charts` → `draconic.natal` | Implementation Roadmap | Schema + flags present; chart builder missing. |
| Out-of-bounds detector | `event-detectors/declination` → `declination.oob` | Inclusion Contract | Declination scan reads catalog but lacks declination threshold check. |
| Aries ingress detector/chart | `event-detectors/ingresses` → `ingresses.aries` + `mundane.ingress.aries_chart` | Implementation Roadmap | Mundane ingress doc exists; runtime not wired. |
| Time-lords (Vimśottarī, ZR) | `timelords` → `vimsottari.*`, `zodiacal_releasing.*` | 100^1 Coverage, Implementation Roadmap | Profiles expose toggles, but engines absent. |
| Locational overlays | `locational` → `relocation.chart`, `maps.astrocartography`, `maps.local_space` | Inclusion Contract | No relocation matrix builder or A*C*G/Local Space lines produced. |

## 1. Sidereal end-to-end wiring

**Modules impacted**: `astroengine.providers.swiss_provider.SwissProvider`, CLI contexts (`astroengine.cli`, `apps/*/cli.py`), profile ingestion (`astroengine.profiles.loader`).

**Required work**:

1. Extend `EphemerisConfig` / `SwissProvider.configure` so the sidereal flag selects the ayanāṁśa enum and invokes `swe.set_sid_mode(mode, 0, 0)` using the identifiers defined in `schemas/natal_input_v1_ext.json`.
2. Surface a CLI/app option (`--zodiac sidereal --ayanamsha <name>`) that writes through to chart configs without bypassing the module hierarchy.
3. Record provenance: capture ayanāṁśa tables in `datasets/ayanamsha/*.csv` with hashes referenced in `docs/governance/data_revision_policy.md`.
4. Add regression tests comparing Lahiri and Krishnamurti offsets against Solar Fire exports to guarantee non-synthetic numbers.

**Verification**: Golden Solar Fire charts for Aries 2000, Lahiri vs. Krishnamurti, stored under `datasets/verification/sidereal/` with README linking to Solar Fire instructions.

## 2. House systems honored in the Swiss adapter

**Modules impacted**: `astroengine.providers.swiss_provider`, `astroengine.chart.houses`, CLI config layer.

**Required work**:

1. Map profile `house_system` identifiers to Swiss Ephemeris constants and call `swe_houses_ex` with the correct flag on every sample.
2. Ensure fallback for high latitude cases follows `docs/HOUSES_FALLBACK_SPEC.md`—log a provenance entry when fallback occurs.
3. Add integration tests comparing Placidus, Koch, Porphyry, Equal, and Whole-sign outputs against Solar Fire reference CSV indexed under `datasets/verification/houses/`.
4. Update CLI/app configuration flows to respect per-profile house settings without losing module references (`module.houses.<system>`).

**Verification**: Parity diff script in `scripts/verify_houses.py` using Solar Fire exports for Anchorage, Reykjavik, and Quito.

## 3. Points & lots computations

**Modules impacted**: `astroengine.chart.points`, `astroengine.catalogs.points`, `astroengine.detectors_aspects`, `astroengine.exporters`.

**Required work**:

1. Implement Vertex/Antivertex using local horizon coordinates (Swiss altitude/azimuth) and document formulas sourced from Solar Fire technical manual section 9.
2. Compute Lot of Fortune/Spirit with day/night condition (diurnal if Sun above horizon). Use `ChartContext.is_day_chart` for gating.
3. Support Lilith (mean/true): call `swe_calc_ut` with `SE_MEAN_APOG`/`SE_TRUE_NODE` values and align enumerations with catalogs.
4. Update exporters and CLI to flag these points while preserving module paths under `chart.points.<name>` and extend schemas in `docs/module/interop.md`.
5. Tests: replicate Solar Fire natal chart (e.g., 1987-05-23 04:15 EDT) to compare computed longitudes/latitudes.

**Verification**: Document reference tables in `datasets/points/lots_reference.csv` with checksums.

## 4. Primary directions

**Modules impacted**: `astroengine.detectors.directions`, `astroengine.chart.directions`, `tests/test_directions.py` (to be added), CLI overlays.

**Required work**:

1. Implement Ptolemaic primary directions (semi-arc) with latitude corrections, referencing Rumen Kolev's Solar Fire tables.
2. Provide zodiacal and mundane options via profile toggles, maintaining module paths `predictive.directions.primary.zodiacal` and `.mundane`.
3. Integrate time keys (Naibod, Ptolemy) configurable through `rulesets/predictive/directions.ruleset.md` (to be authored alongside code).
4. Add sample dataset: Solar Fire export for natal chart + directed hits stored under `datasets/directions/primary/`.

**Verification**: Unit tests comparing directed Midheaven hits against Solar Fire 9 (Arcsec error < 0.1).

## 5. Draconic charts

**Modules impacted**: `astroengine.chart.draconic`, `astroengine.chart.config.ChartConfig`, CLI overlays, schema docs.

**Required work**:

1. Build draconic conversion (subtract mean lunar node longitude) as standalone builder returning `Chart` preserving module path `derived_charts.draconic.natal`.
2. Ensure compatibility with sidereal flag—respect `profiles/base_profile.yaml` `draconic.enabled` toggle.
3. Capture Solar Fire draconic chart outputs under `datasets/derived/draconic/` with metadata.
4. Extend `docs/module/predictive_charts.md` to include draconic entry once implemented; update interop schema with `chart_kind="draconic"`.

**Verification**: CLI recipe that builds natal + draconic pair and cross-checks with Solar Fire.

## 6. Out-of-Bounds detector

**Modules impacted**: `astroengine.detectors.declination`, `astroengine.events`, `rulesets/transit/scan.ruleset.md` (threshold documentation), tests.

**Required work**:

1. Add declination limit constant (|δ| > 23°27′) parameterized via `profiles/base_profile.yaml` for luminaries vs. planets.
2. Wire Swiss declination samples into detector pipeline and emit events under channel `event-detectors/declination.oob`.
3. Provide CLI output summarizing start/end timestamps per body with Solar Fire dataset verification (CSV under `datasets/transits/oob/`).
4. Document severity scaling in `docs/module/event-detectors/channels/declination_oob.md` (to be authored when code lands).

**Verification**: Regression test for Moon OOB episodes in 2024 referencing Solar Fire timeline.

## 7. Ingress detector & Aries ingress charts

**Modules impacted**: `astroengine.detectors.ingresses`, `astroengine.mundane.ingress`, CLI modules, exporters.

**Required work**:

1. Extend ingresses detector to flag Aries ingress timestamps (Sun entering 0° Aries) and emit dedicated events under `event-detectors/ingresses.aries`.
2. Build Aries ingress chart generator under `mundane.ingress.aries_chart`, using location defaults from `profiles/mundane.yaml` and verifying with Solar Fire mundane module.
3. Document dataset expectations in `docs/mundane_ingress.md` (append Aries-specific tables) and add Solar Fire exports to `datasets/mundane/aries_ingress/`.
4. Tests comparing 2024 Aries ingress chart angles and luminary positions with Solar Fire (error < 0.05°).

**Verification**: CLI command `astroengine mundanes aries-ingress --year 2024 --location "Washington, DC"` referencing stored dataset.

## 8. Time-lords: Vimśottarī Dashā & Zodiacal Releasing

**Modules impacted**: `astroengine.timelords`, `astroengine.profiles`, CLI/app overlays, exporters.

**Required work**:

1. Implement Vimśottarī engine using Lahiri-based nakṣatra mapping; load sequence lengths from `datasets/timelords/vimsottari.csv` (Solar Fire export) and respect ayanāṁśa selected in profile.
2. Implement Zodiacal Releasing per Hellenistic schema (lot-based sign periods) with dataset cross-checks from Zodiacal Releasing tables (Chris Brennan/Valens). Store verifying data under `datasets/timelords/zodiacal_releasing/`.
3. Register module channels `timelords.vimsottari.major/minor` and `timelords.zodiacal_releasing.l1-l4` in registry ensuring CLI exposures.
4. Tests: Add property-based checks to ensure sequences are contiguous and align with Solar Fire sample outputs.
5. Update `docs/timelords.md` to include new sequences and provenance.

**Verification**: Provide Solar Fire exported timeline for Barack Obama natal chart (widely referenced) to validate sequences.

## 9. Locational astrology overlays

**Modules impacted**: `astroengine.locational` (to be created), `astroengine.chart.relocation`, `astroengine.exporters.maps`, CLI modules.

**Required work**:

1. Implement relocation chart builder (recompute angles using new location, preserve natal positions) referencing Solar Fire relocation exports.
2. Produce AstroCartoGraphy lines using Swiss RA/declination samples; store line coordinates in indexed SQLite for efficient map queries.
3. Implement Local Space azimuth calculations (Solar Fire Local Space module) with dataset stored under `datasets/locational/local_space_reference.csv`.
4. Register module paths `locational.relocation.chart`, `locational.maps.astrocartography`, `locational.maps.local_space` and expose CLI commands.
5. Update `docs/MAPS_SPEC.md` with deterministic rendering requirements and link to dataset provenance.

**Verification**: Visual diff pipeline comparing generated A*C*G lines with Solar Fire map overlays for sample chart.

---

Document each closure in `docs/burndown.md` (IDs I-10 through I-18) and record provenance entries in `docs/governance/data_revision_policy.md` when datasets are introduced or refreshed.
