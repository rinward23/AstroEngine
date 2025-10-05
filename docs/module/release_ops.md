# Release & Operations Plan

- **Module**: `release_ops`
- **Maintainer**: Release Guild
- **Source artifacts**:
  - `pyproject.toml`
  - `docs/ENV_SETUP.md`
  - `docs/module/qa_acceptance.md`
  - Registry snapshot (`astroengine/modules/__init__.py`)

This plan documents the concrete release steps supported by the repository today. Update it whenever packaging options or registry modules change so downstream teams can audit the process.

## Packaging & extras

| Extra | Dependencies | Purpose |
| --- | --- | --- |
| `dev` | `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `black`, `isort`, `mypy`, `pre-commit`, `mkdocs-material`, `mkdocs-gen-files` | Local development, typing, and documentation tooling. |
| `optional` | `skyfield`, `fastapi`, `uvicorn`, `jinja2`, `numba`, `ics`, `pandas` | Optional runtime providers, web API surface, and export helpers. |

The core package depends on `pyswisseph`, `numpy`, `pydantic>=2`, `python-dateutil`, `timezonefinder`, `tzdata`, `pyyaml`, `click`, `rich`, `orjson`, `pyarrow`, and `duckdb` as declared in `pyproject.toml`. Additional extras (e.g., provider-specific dependencies) should be added alongside documentation updates once implementations land.

Versioning is managed by [`setuptools-scm`](https://github.com/pypa/setuptools_scm):

- Publish releases from annotated git tags so the generated version matches the
  governance artefacts. Untagged builds fall back to `0.0.0`, eliminating the
  `0+unknown` metadata previously produced by ad-hoc wheels.
- Keep `astroengine/_version.py` untracked locally; it is generated during build
  and allows runtime components to expose the exact release number without
  importing packaging metadata.

Dependency lockfiles are produced with `pip-compile` to guarantee reproducible
builds:

```bash
pip-compile --resolver=backtracking --generate-hashes --extra dev \
  --output-file requirements.lock/py311.txt pyproject.toml
```

Hashing is required; in air-gapped environments `uv pip compile` with hash
output is an acceptable substitute. Commit the updated lockfile alongside release
tags so downstream images resolve the same versions recorded in Solar Fire
comparison artefacts.

## Registry compatibility snapshot

The default registry currently exposes the following modules:

- `vca`: Venus Cycle Analytics datasets (`catalogs`, `profiles`, `uncertainty`, `rulesets`).
- `event_detectors`: Stations, ingresses, lunations, declination, and overlay detectors backed by Swiss Ephemeris rulesets.
- `esoterica`: Decans, tarot, numerology, and oracular correspondences tied to documented sources.
- `mundane`: Solar ingress chart generation with aspect overlays.
- `jyotish`: Parasara dignities, karakas, and graha yuddha reference tables.
- `narrative`: Bundled narrative summaries, profile templates, and time-lord overlays.
- `ritual`: Planetary day/hour tables, void-of-course filters, and electional guidelines.
- `predictive`: Progressions, directions, returns, midpoint overlays, and vedic gochara scaffolding.
- `ux`: Placeholder channels for maps, timelines, and plugin surfaces.
- `integrations`: External tool catalogues (Swiss Ephemeris, Skyfield, Flatlib, Maitreya, JHora, Panchanga projects).
- `data_packs`: CSV/YAML/JSON datasets such as `profiles/base_profile.yaml`, `profiles/dignities.csv`, and `schemas/orbs_policy.json`.
- `providers`: Ephemeris provider registry metadata and cadence/frame preferences.
- `interop`: Export schemas (`schemas/result_schema_v1.json`, `schemas/contact_gate_schema_v2.json`, etc.).
- `developer_platform`: Planned SDKs, CLI workflows, portal surfaces, and webhook contracts.

New modules must extend this list and keep their documentation in `docs/module/` aligned with the registry to preserve the module → submodule → channel → subchannel hierarchy.

## Release checklist

1. Ensure a clean environment by running the commands in `docs/ENV_SETUP.md`.
2. Capture an environment report with `python -m astroengine.infrastructure.environment pyswisseph numpy pydantic python-dateutil timezonefinder tzdata pyyaml click rich orjson pyarrow duckdb`.
3. Execute `pytest` and confirm all tests pass.
4. Review the documentation updates in `docs/module/*.md`, `docs/governance/*.md`, and `docs/burndown.md` to make sure they reference real files. Note any schema or dataset edits in `docs/governance/data_revision_policy.md`.
5. Verify Solar Fire comparison reports and dataset indexes referenced by the release (e.g., natal return tables, transit exports). Record the checksums in the release notes so future audits can reproduce the run.
6. Tag the release (`git tag vX.Y.Z`) and push the tag after tests succeed.
7. Build distribution artifacts using `python -m build` (add the build dependency when publishing to PyPI).
8. Attach the environment report, pytest log, and Solar Fire verification artefacts to the release notes.

## Observability & support

- Keep the compatibility table above in sync with the registry to ensure no module paths disappear between releases.
- Record any manual steps (e.g., dataset checksum verification) in `docs/burndown.md` under the relevant task.
- When new operational tooling (Docker images, monitoring hooks) is introduced, link the documentation here and add automated checks where possible.
- If a release consumes new Solar Fire datasets or indexes, ensure the raw exports (or access instructions) are referenced from the release notes and the provenance log. Never claim support for a dataset unless the files are committed or their checksums are recorded.

Following this plan aligns releases with the validated environment and ensures the governance artefacts always reflect what shipped.
