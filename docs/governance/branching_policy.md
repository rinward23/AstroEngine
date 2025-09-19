# Branch Hygiene & Merge Conflict Avoidance

This guide documents how AstroEngine contributors keep the specification and
runtime repositories conflict-free while respecting the module → submodule →
channel → subchannel hierarchy and the "no module removals" guarantee.

## Why conflicts reappear

AstroEngine intentionally centralises high-traffic specifications — module
completion plans, governance manifests, and SolarFire-derived records. When
multiple long-lived branches diverge from `main`, their commits all try to edit
the same documents (for example shared dataset indexes or module-level specs),
generating frequent merge conflicts. The new
[Data Revision Policy](data_revision_policy.md) keeps these edits
traceable without forcing append-only churn that amplifies conflicts.

## Branch workflow

1. **Branch from a fresh `main`.** Start every feature branch with
   `git fetch origin && git switch main && git pull --ff-only`.
2. **Keep branches short-lived.** Group work by module/submodule scope so the
   affected files remain disjoint from other efforts.
3. **Rebase before pushing for review.** Run `git fetch origin && git rebase
   origin/main` to replay your commits on top of the latest `main`.
4. **Avoid force-pushing during review.** Add incremental commits so reviewers
   can reconcile history; only clean up history once the review is approved.
5. **Resolve conflicts locally, once.** After a rebase resolves conflicts, push
   the branch immediately so teammates do not repeat the same work.

## Formatting & linting

Install the developer dependencies (`pip install -e .[dev]`) and run the
configured tooling locally before committing:

- `black` keeps Python code consistently formatted.
- `ruff --fix` handles import ordering and common lint rules.
- `pytest` verifies runtime behaviour and schema helpers.

To make this automatic, install pre-commit hooks once per clone:

```bash
pre-commit install
```

The repository supplies `.pre-commit-config.yaml` to execute Black, Ruff, and
baseline hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`).

## Documentation & data scoping

- Place new documentation under the module/submodule/channel/subchannel tree in
  `docs/` so concurrent efforts touch separate files.
- Follow the [Data Revision Policy](data_revision_policy.md) when updating
  shared datasets (CSV, SQLite, JSONL).  Edit rows in place as needed, but log
  the change with a `revision` identifier so provenance remains auditable.
- When updating rulesets or schema indexes, add new nodes rather than editing or
  removing existing module definitions. This preserves traceability and avoids
  data loss while still allowing surgical edits.

## Cross-team coordination

- Announce large documentation pushes in stand-ups and split work by module to
  avoid overlapping edits.
- Record change intent in `docs/module/**/release_ops.md` or a submodule-specific
  change log when introducing new Solar Fire derived datasets.
- Use feature flags or configuration profiles instead of removing legacy
  modules; mark them deprecated in documentation until migration is complete.

Adhering to this workflow keeps AstroEngine merge-friendly while guaranteeing
that every run sequence is backed by verifiable, non-synthetic data sources.
