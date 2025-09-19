# AstroEngine — Runtime & Schema Contracts

AstroEngine provides schema definitions and Python helpers for building
real-time astrology pipelines.  The codebase has been rebuilt to avoid
Conda-specific tooling and now organises assets using a
**module → submodule → channel → subchannel** hierarchy so SolarFire data
can be indexed safely without losing any modules during future edits.

---

## Quick start

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install AstroEngine and optional developer tooling via the Makefile helper
make env


```

The CI workflow `.github/workflows/swe-smoketest.yml` runs the same on every push/PR.

# >>> AUTO-GEN END: Ephemeris Smoketest How-To v1.0
````

# >>> AUTO-GEN BEGIN: AE README CLI Addendum v1.1
### CLI quickstart
```bash
python -m astroengine env   # prints imports + ephemeris path hint
```

### Local dev bootstrap

```bash
bash scripts/dev_setup.sh   # macOS/Linux
# or
powershell -ExecutionPolicy Bypass -File scripts/dev_setup.ps1
```

# >>> AUTO-GEN END: AE README CLI Addendum v1.1

The package exposes a registry-based API for discovering datasets and
rulesets.  See `astroengine/modules` for details.

---

## Development workflow

The repository ships a lightweight `Makefile` that documents the most common
developer activities.  Run `make` (or `make help`) to view the curated targets.

- `make format` — apply Ruff autofixes alongside Black and isort formatting.
- `make lint` — check code style without mutating the working tree.
- `make typecheck` — execute `mypy` on the typed package surfaces.
- `make test` — run the full `pytest` suite, including CLI and ephemeris tests.
- `make check` — convenience target that executes linting, type checking,
  and tests in sequence to validate merge readiness.

These helpers ensure the module → submodule → channel → subchannel hierarchy
remains intact, particularly when integrating new Solar Fire derived datasets or
augmenting the runtime with additional registries.

### Optional dependency extras

`pyproject.toml` defines optional extras that cluster runtime dependencies by
concern:

- `astroengine[cli]` installs `click` and `rich` for forthcoming interactive
  tooling.
- `astroengine[data]` pulls scientific stack dependencies (`numpy`, `pandas`,
  `scipy`) when working with large Solar Fire exports or indexed CSV datasets.
- `astroengine[time]` installs timezone helpers (`python-dateutil`, `pytz`) for
  ingestion pipelines that reconcile historical chart metadata.

The `dev` extra used by `make env` includes all of the above to keep local
development frictionless while still allowing production environments to select
only what they require.

---

## Schemas

All JSON schema payloads live under [`./schemas`](./schemas).  They are
kept outside the Python package namespace so versioned edits can happen
without risking accidental module loss.  When a schema needs to change,
update the existing file with a new `revision` entry (see
[`docs/governance/data_revision_policy.md`](docs/governance/data_revision_policy.md))
instead of cloning the entire document into a new append-only record.

> **Schema registry keys**
> - `result_v1` → `schemas/result_schema_v1.json`
> - `contact_gate_v2` → `schemas/contact_gate_schema_v2.json`
> - `orbs_policy` → `schemas/orbs_policy.json`

---

## Architecture overview

- `astroengine/core` — fundamental runtime helpers (domains, scoring,
  transit event dataclasses).
- `astroengine/ephemeris` — Swiss Ephemeris adapter emitting deterministic
  position/house payloads for chart modules.
- `astroengine/chart` — natal and transit calculators that lean on the
  Swiss adapter and orb policy to stay deterministic.
- `astroengine/modules` — registry classes for organising datasets.
- `astroengine/modules/vca` — bundled Venus Cycle Analytics assets
  registered under module/submodule/channel/subchannel nodes.
- `astroengine/infrastructure` — environment diagnostics and other
  operational utilities.

The transit/natal calculators ship with golden regression tests covering
three Solar Fire reference charts so future changes stay anchored to real
ephemeris data.

The default registry can be inspected by importing
`astroengine.DEFAULT_REGISTRY` or calling
`astroengine.bootstrap_default_registry()`.

### Automating Git operations

`astroengine.infrastructure` now exposes lightweight helpers for
repositories that require SSH deploy keys.  Use
`GitRepository.clone(..., auth=GitAuth(key_path=...))` to clone, commit,
and push while the helper manages ``GIT_SSH_COMMAND`` for you.  The API
avoids third-party wrappers and operates on real files inside the
working tree so downstream automation stays deterministic.

---

## Tests & validation

Install the optional `dev` extras and run the test suite:

```bash
pytest
```

Schema validation helpers reside in `astroengine/validation` and operate
on the JSON documents stored in `./schemas`.

---

## Contribution workflow

Follow the [branch hygiene guide](docs/governance/branching_policy.md) to keep
pull requests conflict-free. In summary:

- Start each feature branch from the latest `main`, keep it short-lived, and
  rebase before opening or updating a pull request.
- Scope documentation and dataset changes by module/submodule/channel to respect
  the repository hierarchy and avoid accidental module removals.
- Install the developer extras and run `black`, `ruff --fix`, and `pytest`
  locally (or via `pre-commit run --all-files`) before pushing.

Install the repo’s pre-commit hooks once per clone to enforce formatting and
baseline hygiene automatically:

```bash
pip install pre-commit
pre-commit install
```

These hooks run Black, Ruff, and whitespace fixers using the configuration in
`.pre-commit-config.yaml`.
