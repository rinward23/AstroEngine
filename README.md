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

# Install AstroEngine and optional developer tooling
pip install -e .[dev]

# Verify the Python environment without relying on Conda
python -m astroengine.infrastructure.environment \
  pyswisseph numpy pydantic python-dateutil timezonefinder tzdata \
  pyyaml click rich orjson pyarrow duckdb
```

The package exposes a registry-based API for discovering datasets and
rulesets.  See `astroengine/modules` for details.

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
- `astroengine/modules` — registry classes for organising datasets.
- `astroengine/modules/vca` — bundled Venus Cycle Analytics assets
  registered under module/submodule/channel/subchannel nodes.
- `astroengine/infrastructure` — environment diagnostics and other
  operational utilities.

The default registry can be inspected by importing
`astroengine.DEFAULT_REGISTRY` or calling
`astroengine.bootstrap_default_registry()`.

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
