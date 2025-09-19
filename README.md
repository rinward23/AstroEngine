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

# Verify the Python environment and ephemeris setup
make preflight

# Generate a sample transit report (Mars conjunct natal Venus)
python -m astroengine.cli transits \
  --target-longitude 240.9623186447056 \
  --start 2025-10-20T00:00:00Z \
  --end 2025-11-20T00:00:00Z
```

````
# >>> AUTO-GEN BEGIN: Ephemeris Smoketest How-To v1.0
## Swiss Ephemeris smoketest (local)

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip && pip install -r requirements.txt

# Install Swiss data (either apt or manual files)
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install -y swe-data
export SE_EPHE_PATH=/usr/share/sweph

# Or manual files into ~/.sweph and set SE_EPHE_PATH accordingly
# mkdir -p ~/.sweph && (download sepl_18.se1, semo_18.se1, seas_18.se1, seleapsec.txt, sefstars.txt)
# export SE_EPHE_PATH=~/.sweph

python scripts/swe_smoketest.py --utc "2025-09-19T18:10:00Z"
```

The CI workflow `.github/workflows/swe-smoketest.yml` runs the same on every push/PR.

# >>> AUTO-GEN END: Ephemeris Smoketest How-To v1.0
````

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
