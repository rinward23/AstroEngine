# Data Packs Specification

- **Module**: `data_packs` (docs slug `data-packs`)
- **Maintainer**: Data Stewardship Team
- **Source artifacts**:
  - `profiles/dignities.csv`
  - `profiles/fixed_stars.csv`
  - `profiles/vca_outline.json`
  - `schemas/orbs_policy.json`
  - `profiles/base_profile.yaml`

AstroEngine bundles a small number of static datasets that are consumed by the registry-backed modules. This document enumerates the files, their fields, and the validation coverage inside the repository so the assets remain traceable and no modules lose access to required inputs.

## Registry mapping

The default registry exposes the following paths for this module:

- `data_packs.profiles.catalogue.base_profile`
- `data_packs.profiles.catalogue.vca_outline`
- `data_packs.catalogs.csv.{dignities,fixed_stars,star_names}`
- `data_packs.schemas.orbs.policy`

Each entry points to the datasets listed below with provenance metadata taken directly from the files or accompanying documentation.

## Dataset inventory

### `profiles/dignities.csv`

- **Purpose**: Captures essential dignity, detriment, exaltation, and sect modifiers that feed the severity weighting model.
- **Origins**: Solar Fire 9 `ESSENTIAL.DAT` export cross-referenced with traditional sources (Ptolemy, Lilly, Houlding). The
  `source` column stores the citation or export identifier so every row can be audited.
- **Structure**: Indexed by `(planet, sign)` with additional columns for term rulers, decan rulers, and sect-specific weights.
  The CSV must remain sorted to guarantee deterministic lookups during profile loading.
- **Integrity**: When modifiers change, update the provenance column and add a revision entry to
  `docs/governance/data_revision_policy.md`. Tests in `tests/test_domain_scoring.py` and `tests/test_vca_profile.py` ensure the
  data stays in sync with `profiles/base_profile.yaml`.

### `profiles/fixed_stars.csv`

- **Purpose**: Provides FK6-derived longitude/declination positions, magnitudes, and orb widths for bright fixed stars referenced
  by the future fixed-star detector channel.
- **Origins**: Solar Fire “Bright Stars” catalogue (Hipparcos/ FK6 reduction). The `provenance` column records the export file
  hash and capture date.
- **Structure**: Primary key `star_id`; includes columns for `ra_deg`, `dec_deg`, `ecliptic_longitude_deg`, `epoch`,
  `orb_default_deg`, and `orb_mag_le_1_deg`. These values feed the `fixed_star_orbs_deg` block in `profiles/base_profile.yaml`.
- **Integrity**: When a new catalogue is imported, compute a SHA-256 checksum, store it in the CSV, and index the dataset in
  SQLite if it grows beyond a few hundred rows. Document the import command and verification steps in the revision log.

### `datasets/star_names_iau.csv`

- **Purpose**: Provides official WGSN star names and J2000 equatorial positions for the fixed-star utilities (`astroengine.fixedstars`).
- **Origins**: Derived from the HYG Database v4.1 (`c7f7f883fe678cc7680169a50ccd7dcc49b060ce`, CC-BY-SA 4.0) which mirrors the IAU Working Group for Star Names list as of March 2023. Unofficial duplicate component names (e.g., “Revati B”) are excluded.
- **Structure**: Columns `name`, `hip`, `hr`, `ra_deg`, `dec_deg`, `notes`. Right ascension values are converted from hours to degrees; declinations remain in degrees (epoch/equinox J2000). The `notes` column captures Bayer/Flamsteed, HD, or Gliese identifiers plus the source citation.
- **Integrity**: Preserve alphabetical ordering and regenerate the file via the documented import script whenever the WGSN list updates. Record the upstream HYG commit hash in the header comments and update `docs/governance/data_revision_policy.md` if provenance changes.

### `profiles/vca_outline.json`

- **Purpose**: Declares the module → submodule → channel → subchannel hierarchy for the Venus Cycle Analytics runtime.
- **Origins**: Derived from Solar Fire transit planning worksheets and AstroEngine’s module registry design sessions.
- **Structure**: The `modules` array maps registry paths to body groups, detectors, and progression flags. Each entry includes a
  `registry_path` property so documentation can reference exact nodes.
- **Integrity**: `tests/test_vca_profile.py` loads the JSON to guarantee schema compatibility. When channels are added or renamed,
  update this file first, then adjust documentation and the registry wiring.

### `profiles/base_profile.yaml`

- **Purpose**: Binds the CSV/JSON datasets into a runnable profile that detectors consume during scoring and reporting.
- **Origins**: Calibrated against Solar Fire default orb/severity preferences with Swiss Ephemeris DE441 checks for angular
  velocities and combustion windows.
- **Structure**: Contains `provenance` metadata, provider cadence settings, body enablement flags, orb policies, severity
  modifiers, and feature toggles. The `updated_at` timestamp must advance whenever any section changes.
- **Integrity**: Regression coverage in `tests/test_vca_profile.py` ensures round-trip loading; the burndown tracker lists this
  profile as evidence for runtime readiness.

### `schemas/orbs_policy.json`

- **Purpose**: Publishes the orb profiles (`standard`, `tight`, `wide`) and the subset of aspect classes exposed for external
  tooling. Downstream consumers use it to align gating with the runtime engine.
- **Origins**: Values mirror the Solar Fire default profile and the AstroEngine multipliers encoded in `profiles/base_profile.yaml`.
- **Structure**: Top-level schema metadata followed by `profiles` (with multipliers) and `aspects` (with base orbs and optional
  overrides). Each object includes descriptive notes for integrators.
- **Integrity**: Validated by `tests/test_orbs_policy.py`; update the schema version and notes whenever aspect data changes.

## Provenance and maintenance

- Each dataset file must retain or expand its `source`/`provenance` columns; never delete historical entries. Append new rows when
  datasets are refreshed so the history remains auditable.
- Record checksum information in the dataset itself or alongside it (e.g., `profiles/fixed_stars.csv` includes the FK6 hash). If a
  dataset is too large for CSV, commit a SQLite index and document the schema.
- Any change requires a matching entry in `docs/governance/data_revision_policy.md` and an update to `docs/burndown.md` with the
  owning team and validation evidence.
- Mirror updated checksums in `docs/provenance/solarfire_exports.md` so release notes capture the exact digests shipped with v1.

## Integrity checks

- Run `pytest` after modifying any dataset to ensure loaders (`astroengine.data.schemas`, `astroengine.validation`) accept the new
  values.
- Capture the execution environment via `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb` and store the JSON
  output with release artefacts.
- When importing Solar Fire or Swiss Ephemeris data, archive the raw export in an internal bucket and reference it by checksum in
  the revision log so audits can reproduce the build.

Keeping this inventory in sync with the repository prevents silent drift and guarantees that any ruleset or detector depending on
these packs can cite a concrete file in git history. No module should emit output without pointing back to one of the datasets
listed above.
