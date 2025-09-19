# Data Packs Specification

- **Module**: `data-packs`
- **Maintainer**: Data Stewardship Team
- **Source artifacts**:
  - `profiles/dignities.csv`
  - `profiles/fixed_stars.csv`
  - `profiles/vca_outline.json`
  - `schemas/orbs_policy.json`
  - `profiles/base_profile.yaml`

AstroEngine bundles a small number of static datasets that are consumed by the registry-backed modules. This document enumerates the files, their fields, and the validation coverage inside the repository so the assets remain traceable and no modules lose access to required inputs.

## Dataset inventory

| File | Purpose | Key fields | Validation hook |
| --- | --- | --- | --- |
| `profiles/dignities.csv` | Records essential dignity and sect modifiers used by severity scoring. | `planet`, `sign`, `dignity_type`, `sect`, `start_deg`, `end_deg`, `modifier`, `source`. | Referenced by `profiles/base_profile.yaml` severity modifiers; reviewed when adjusting dignity multipliers. |
| `profiles/fixed_stars.csv` | Provides bright fixed-star positions and orb policies. | `star_id`, `name`, `ra_deg`, `dec_deg`, `ecliptic_longitude_deg`, `epoch`, `magnitude`, `orb_default_deg`, `orb_mag_le_1_deg`, `provenance`. | Used by fixed-star feature flags in `profiles/base_profile.yaml`; consumed by forthcoming detector work. |
| `profiles/vca_outline.json` | Encodes the canonical Venus Cycle Analytics outline (body groups, aspect sets, domain weights). | `modules`, `bodies.include`, `bodies.optional_groups`, `aspects`, `orbs`, `domain`, `flags`. | Exercised by `tests/test_vca_profile.py` when loading JSON profiles and by `tests/test_domain_scoring.py`. |
| `schemas/orbs_policy.json` | JSON document exposing aspect families and profile multipliers for downstream tooling. | `schema`, `profiles.standard|tight|wide`, `aspects` (with `base_orb` and overrides). | Validated by `tests/test_orbs_policy.py`. |
| `profiles/base_profile.yaml` | Baseline profile wiring the datasets above into runtime configuration (orbs, severity weights, feature flags). | `orb_policies`, `severity_modifiers`, `feature_flags`, `providers`. | Loaded in `tests/test_vca_profile.py`; referenced throughout module documentation. |

## Provenance and maintenance

- Each CSV includes a `source` or `provenance` column with human-readable citations (e.g., Skyscript rulership tables, Hipparcos catalogue). Updates must preserve those citations and append any new sources rather than overwriting existing notes.
- JSON/YAML assets include version or date fields (`profiles/vca_outline.json.version`, `profiles/base_profile.yaml.updated_at`). Increment those fields when publishing revisions so downstream systems can detect changes.
- When adding new datasets, register them here and update `docs/burndown.md` with the owning team and validation evidence.

## Integrity checks

- Run `pytest` to ensure schema loaders continue to accept the bundled data and that `validate_payload` can still resolve the orb policy document.
- Use `python -m astroengine.infrastructure.environment numpy pandas scipy` before regenerating CSVs to capture the interpreter state used to compute or verify the numbers.
- Store checksum information (e.g., SHA-256 digests) alongside large datasets if additional files are introduced; the existing files are small enough to review directly in version control.

Keeping this inventory in sync with the repository prevents silent drift and guarantees that any ruleset or detector depending on these packs can cite a concrete file in git history.
