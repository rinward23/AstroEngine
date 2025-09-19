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
| `dev` | `pytest`, `black`, `ruff` | Local development and CI tooling. |

The core package depends on `numpy`, `pandas`, and `scipy` as declared in `pyproject.toml`. Additional extras (e.g., provider-specific dependencies) should be added alongside documentation updates once implementations land.

## Registry compatibility snapshot

The default registry currently exposes a single module:

| Module | Submodules | Channels | Source |
| --- | --- | --- | --- |
| `vca` | `catalogs`, `profiles`, `rulesets` | `catalogs.bodies.{core,extended,centaurs,tnos,sensitive_points}`, `profiles.domain.{vca_neutral,vca_mind_plus,vca_body_plus,vca_spirit_plus}`, `rulesets.aspects.definitions` | `astroengine/modules/vca/__init__.py` |

When new modules are registered, update this table and the documentation in `docs/module/event-detectors/overview.md` to preserve the module → submodule → channel → subchannel hierarchy.

## Release checklist

1. Ensure a clean environment by running the commands in `docs/ENV_SETUP.md`.
2. Capture an environment report with `python -m astroengine.infrastructure.environment numpy pandas scipy`.
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
