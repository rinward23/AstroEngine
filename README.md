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

# >>> AUTO-GEN BEGIN: AE README Providers Addendum v1.2
### Optional providers & catalogs
Install selectively via extras:

```bash
pip install -e .[fallback-ephemeris]   # skyfield + jplephem
pip install -e .[astro-core]           # astropy frames/units
pip install -e .[catalogs]             # astroquery (Horizons/SBDB/VizieR)
pip install -e .[tz]                   # offline timezone lookup
pip install -e .[qa-novas]             # NOVAS QA checks
pip install -e .[trad]                 # flatlib (dignities/lots)
```

### CLI

```bash
python -m astroengine provider list
python -m astroengine provider check swiss
```

> **Licensing note:** Swiss Ephemeris is AGPL/commercial for distribution. Keep data files outside the wheel; users should provide `SWE_EPH_PATH/SE_EPHE_PATH`.

When `pyswisseph` is unavailable the engine automatically registers a
**Swiss fallback provider** powered by PyMeeus analytical series.  The
fallback keeps the Swiss handle usable inside this repository’s test
environment while still producing real geocentric ecliptic longitudes,
latitudes, and longitudinal speeds for the visible planets and Pluto.
Install `pyswisseph` alongside the official ephemeris files for
production deployments to regain full Swiss Ephemeris precision.

# >>> AUTO-GEN END: AE README Providers Addendum v1.2

# >>> AUTO-GEN BEGIN: AE README Aspects + Domain Report v1.0
### Enable minor aspects (optional)
Edit `profiles/aspects_policy.json` and add to `enabled_minors`, then:
```bash
python -m astroengine scan --start 2024-06-01T00:00:00Z --end 2024-06-07T00:00:00Z \
  --moving mars --target venus --provider swiss
````

### Domain report

```bash
python -m astroengine report \
  --start 2024-06-01T00:00:00Z \
  --end   2024-06-07T00:00:00Z \
  --moving mars --target venus \
  --provider swiss --decl-orb 0.5 --mirror-orb 2.0 --step 60 \
  --out domain_report.json
```

This prints and writes a JSON with domain/channel/subchannel scores and totals.

# >>> AUTO-GEN END: AE README Aspects + Domain Report v1.0


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

# >>> AUTO-GEN BEGIN: AE README Stars/SBDB/Decl Addendum v1.0
### Fixed stars (Skyfield & Swiss)
- Dataset: `datasets/star_names_iau.csv` (replace with full WGSN list as needed).
- Skyfield method requires a local JPL kernel (e.g., `de440s.bsp`).

```bash
python -m astroengine star Regulus --provider skyfield
python -m astroengine star Regulus --provider swiss
```

### Declination & antiscia utilities

```bash
python -m astroengine decl decl --lon 123.4 --lat 0.0
python -m astroengine decl mirror --type antiscia --lon 10
python -m astroengine decl mirror --type contra --lon 10
python -m astroengine decl parallel --dec1 12.0 --dec2 -11.7 --tol 0.5
```

### SBDB fetch (with cache)

```python
from astroengine.catalogs.sbdb import fetch_sbdb
obj = fetch_sbdb("433 Eros")  # caches JSON under datasets/sbdb_cache/
```

> Tests will auto-skip when optional extras or kernels are not present.

# >>> AUTO-GEN END: AE README Stars/SBDB/Decl Addendum v1.0

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
# >>> AUTO-GEN BEGIN: AE README Scan Addendum v1.0
### Scan for declination/mirror contacts
```bash
python -m astroengine scan \
  --start 2024-06-01T00:00:00Z \
  --end   2024-06-07T00:00:00Z \
  --moving mars --target venus \
  --provider swiss --decl-orb 0.5 --mirror-orb 2.0 \
  --sqlite transits.sqlite
```
# >>> AUTO-GEN END: AE README Scan Addendum v1.0

# >>> AUTO-GEN BEGIN: AE README Valence Addendum v1.0
### Universal valence model
- Configure intrinsic valence for **bodies**, **aspects**, and **contacts** in `profiles/valence_policy.json`.
- Neutral entries specify a `neutral_mode`: `amplify` or `attenuate`; global factors live under `neutral_effects`.
- Each event now carries:
  - `score` (base 0..1), `valence` (`positive|neutral|negative`), `valence_factor` (>=0), and `signed_score` (may be negative).
- Domain rollups split **neutral** events 50/50 (after factor), push **positive** to positive subchannels, **negative** to negative.

```bash
python -m astroengine scan --start 2024-06-01T00:00:00Z --end 2024-06-07T00:00:00Z \
  --moving mars --target venus --provider swiss --decl-orb 0.5 --mirror-orb 2.0
```
# >>> AUTO-GEN END: AE README Valence Addendum v1.0
