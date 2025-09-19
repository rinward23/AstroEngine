# Data Packs Specification

- **Module**: `data-packs`
- **Author**: AstroEngine Data Stewardship Team
- **Date**: 2024-05-27
- **Source datasets**: FK6 bright stars catalogue (`resources/fk6_bright_stars.csv`), dignities tables from Deborah Houlding (*Houses: Temples of the Sky*), Solar Fire `HOUSE_RULERS.CSV`, Minor Planet Center orbital elements (Ceres, Pallas, Juno, Vesta), AstroEngine localization pack (`rulesets/i18n/sign_labels.csv`), Atlas/TZ SQLite dataset (`data/atlas_tz.sqlite`).
- **Downstream links**: severity matrix (`docs/module/core-transit-math.md`), interop schemas (`docs/module/interop.md`), QA acceptance (`docs/module/qa_acceptance.md`).

This specification enumerates bundled datasets, provenance, and licensing so runtime modules can reference real data without risking silent drift. Each dataset entry records source, checksum, fields, and upgrade procedure.

## Fixed Star Bright List v1

- **Source**: FK6 reduction of Hipparcos/Tycho data, curated for magnitude ≤ 4.5.
- **File**: `resources/fk6_bright_stars.csv`
- **Fields**:
  - `star_id` (string, e.g., `spica`),
  - `name`, `constellation`,
  - `ra_deg`, `dec_deg` (J2000),
  - `mag_v`,
  - `spectral_type`,
  - `orb_longitude_deg` (default orb in longitude),
  - `orb_declination_deg`,
  - `source_checksum` (FK6 file hash),
  - `last_verified` (ISO date).
- **Default orbs**: 1° longitude, 0°30′ declination, matching Solar Fire defaults.
- **Upgrade path**:
  1. Download new FK6 release from Astronomisches Rechen-Institut.
  2. Validate RA/Dec conversions with Swiss Ephemeris `fixstar_ut` (difference ≤0.1 arcsecond).
  3. Update `source_checksum` and provenance entry in this document.
  4. Regenerate localization labels via `python -m astroengine.data.fixstars sync-labels`.

## Dignities & Sect Tables

- **Source**: Deborah Houlding, *Houses: Temples of the Sky*; William Lilly, *Christian Astrology*; Solar Fire essential dignities export.
- **File**: `rulesets/venus_cycle/dignities.csv`
- **Fields**: `sign`, `ruler_day`, `ruler_night`, `exaltation`, `fall`, `triplicity_day`, `triplicity_night`, `terms_scheme`, `face_start_deg`, `face_ruler`, `sect_weight`.
- **Method**: Weights align with severity modifiers defined in `docs/module/core-transit-math.md`. Day/night rulership determined by natal chart sect flag.
- **Integrity**: Each row includes citations and page references; QA cross-checks values against Solar Fire `ESSENTIAL.DAT`.

## House Rulers Table

- **Source**: Solar Fire `HOUSE_RULERS.CSV` (traditional), AstroEngine `rulesets/modern_house_rulers.csv`.
- **Fields**: `house_number`, `traditional_ruler`, `modern_ruler`, `notes`, `source`.
- **Usage**: Combines with ruleset DSL to evaluate house emphasis actions.
- **Upgrade**: When new rulership schemes added, append new columns rather than overwrite existing rows to preserve historical traceability.

## Minor Planet Pack

- **Source**: Minor Planet Center orbital elements for Ceres, Pallas, Juno, Vesta, optional Eris and Sedna.
- **File**: `data/minor_planets/orbital_elements.csv`
- **Fields**: `body`, `epoch_jd`, `a_au`, `e`, `i_deg`, `long_node_deg`, `perihelion_deg`, `mean_anomaly_deg`, `absolute_mag`, `slope_param`, `orb_deg_default`.
- **License**: MPC data (public domain).
- **Processing**: Convert orbital elements to ephemeris vectors using `astroengine.data.minor_planets.build_state`. Validate against JPL Horizons (difference ≤0.01° for 1950–2050).
- **Profile toggles**: `vca_support` enables Eris/Sedna with default orb 2°.

## Localization Pack (I18N)

- **Source**: AstroEngine-managed localization CSV referencing Solar Fire glyph lists for baseline English.
- **File**: `rulesets/i18n/sign_labels.csv`
- **Fields**: `locale`, `key`, `label`, `last_verified`, `source`.
- **Policy**: All locales must include provenance (translator, dataset). English baseline derived from Solar Fire string table `SF_LANG_EN.DAT`.
- **Upgrade**: Add locales by appending rows; maintain `last_verified` with translation QA date.

## Atlas & Time Zone Requirements

- **Source**: `data/atlas_tz.sqlite`, derived from ACS Atlas (licensed) and IANA tzdata 2024a.
- **Tables**:
  - `locations` (id, name, lat, lon, altitude, source_id, checksum),
  - `timezones` (tzid, offset_minutes, dst_ruleset_id, checksum),
  - `dst_rulesets` (id, description, rules_json, checksum).
- **Indexing**: Provide indices on `(lat, lon)` and `(tzid)` for quick retrieval. All lookups referenced by URNs like `atlas://locations/<id>`.
- **Upgrade**: When tzdata updates, update `timezones` table with new offsets and record new checksums in provenance appendix.

## Provenance Table

| Dataset | File | SHA256 | License | Maintainer | Last verified |
| ------- | ---- | ------ | ------- | ---------- | ------------- |
| FK6 bright stars v1 | `resources/fk6_bright_stars.csv` | `51a3ac2ff7fb0fcebe663c9baf7b5c6f0f31d3dc4d2222ca4bb7a8a9f14ebd19` | FK6 terms | AstroEngine data team | 2024-04-22 |
| Dignities table | `rulesets/venus_cycle/dignities.csv` | `9d5b89244f91c4bd119b842a0a87c67b0d3ba9ab9db769da9f09ef19a2f49dd8` | Solar Fire license required | VCA ruleset committee | 2024-05-10 |
| House rulers | `rulesets/house_rulers.csv` | `b99aa48062374319f49e693597890131a7fba02aab7a25c07dcb1a6bbd4e5e53` | Solar Fire license required | AstroEngine house systems WG | 2024-05-12 |
| Minor planets | `data/minor_planets/orbital_elements.csv` | `a3c5fdb9cda75cf6a5ce653645d902b7ce1f3b1e34d29cb3b08e8df4ec5c23bd` | MPC public domain | AstroEngine minor bodies WG | 2024-05-18 |
| Localization pack | `rulesets/i18n/sign_labels.csv` | `15db722a20f3066cf2bc2b817b4548bff1c0d016e18ef2cf8b3c1f5f5cf9d7c8` | CC-BY 4.0 | Localization team | 2024-05-05 |
| Atlas/TZ database | `data/atlas_tz.sqlite` | `f2d551d4f8940052156f498d9d945361675f915f2e57de5986c00c2d2fe8b8ab` | Licensed (ACS) | Atlas maintainers | 2024-04-28 |

Any dataset updates must append new rows rather than editing existing checksum entries, creating an auditable history.

## Licensing & Compliance

- Maintain license documents alongside datasets (`licenses/` directory) and record URLs in this spec.
- Datasets requiring commercial licenses (Solar Fire exports, ACS Atlas) must include proof-of-purchase references stored in `docs/governance/acceptance_checklist.md`.
- Public domain datasets still require checksum verification before runtime ingestion.

This module-level documentation ensures data packs remain verifiable, upgradeable, and tightly coupled to real-world sources so runtime outputs never rely on fabricated values.
