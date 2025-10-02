# Solar Fire Export Provenance Log

- **Updated**: 2025-10-02
- **Maintainer**: Data Stewardship Guild
- **Scope**: Enumerates Solar Fire derived assets that ship with AstroEngine v1.0 and the evidence collected to prove their integrity. Every checksum below was generated from files committed to this repository; rerun the documented commands whenever the source exports are refreshed.

## Verification checklist

1. Compute the SHA-256 digests exactly as shown under each dataset. Reject a release if any digest differs from the values recorded here.
2. Archive the raw Solar Fire export (CSV/TXT) referenced in the table together with the environment report produced by `python -m astroengine.infrastructure.environment ...`.
3. Update `docs/governance/data_revision_policy.md` and append a new row to `docs/burndown.md` whenever a dataset changes.

## Dataset inventory

| Dataset | Repository path | Solar Fire origin | SHA-256 | Notes |
| --- | --- | --- | --- | --- |
| Dignities & Sect table | `profiles/dignities.csv` | `ESSENTIAL.DAT` export (Solar Fire 9) | `991ae2d4d61a5046f162ddff35c72c65c210590fd772dadae46f2e85c2ad881c` | Columns track rulership, exaltation, triplicity (day/night), terms, faces, and sect weights. The `provenance` column holds the Solar Fire file hash captured at export time. |
| Fixed star catalogue | `profiles/fixed_stars.csv` | Bright Stars catalogue (Hipparcos FK6 reduction shipped with Solar Fire 9) | `e0906237ccd0371926b4ab838eb9ecd02417bdeeeab19ef41ccb2ad63cbac992` | Stores FK6 longitudes/declinations, magnitudes, and orb widths. `provenance` cites the upstream catalogue revision. |
| Base runtime profile | `profiles/base_profile.yaml` | Solar Fire default transit profile (orbs, severity multipliers) | `ec1a3b1215a9e48be4cae052d7a34ae2cf57541b11885c9df5217b296607318f` | Binds CSV datasets into the executable runtime profile. Keep `updated_at` aligned with the export date. |
| VCA outline | `profiles/vca_outline.json` | Solar Fire transit planning worksheets | `6ee43dacc3fd4585b3aa1e2e7034e877ec991208627719f4ccb57f50aa837851` | Declares the registry hierarchy so modules/submodules/channels resolve consistently during scans. |

### Command transcript

```bash
sha256sum \
  profiles/dignities.csv \
  profiles/fixed_stars.csv \
  profiles/base_profile.yaml \
  profiles/vca_outline.json
```

The command above produced the digests recorded in the table on 2025-10-02.

## Environment evidence

Run the environment probe before tagging a release to confirm the dependency versions that processed the Solar Fire exports:

```bash
python -m astroengine.infrastructure.environment \
  pyswisseph numpy pydantic python-dateutil timezonefinder tzdata \
  pyyaml click rich orjson pyarrow duckdb
```

Attach the JSON (or text) output to release artefacts. The 2025-10-02 execution reported Python 3.11.12 with `pyswisseph 2.10.3.2`, `numpy 2.3.3`, `pyarrow 21.0.0`, and other pinned dependencies, matching the QA environment.

## Release actions

- Mirror this document into release notes so auditors can trace every Solar Fire derived number back to a file and checksum.
- If a dataset must be redacted for licensing reasons, store the checksum and export metadata in the internal vault and reference the vault record here instead of deleting the row.
- Update `docs/module/data-packs.md` when adding or deprecating datasets so the registry and documentation stay aligned.
