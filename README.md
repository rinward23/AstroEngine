# AstroEngine — Runtime & Schema Contracts

![Coverage](docs/badges/coverage.svg)

AstroEngine provides schema definitions and Python helpers for building
real-time astrology pipelines.  The codebase has been rebuilt to avoid
Conda-specific tooling and now organises assets using a
**module → submodule → channel → subchannel** hierarchy so SolarFire data
can be indexed safely without losing any modules during future edits.

## Licensing & ephemeris defaults

AstroEngine is distributed under the **GNU Affero General Public License
v3.0 only (AGPL-3.0-only)**. Every runtime and documentation contribution in
this repository inherits that copyleft. Commercial deployments must publish
source changes and network-accessible modifications consistent with the
AGPL’s network use clause.

The runtime ships with open-source ephemerides and defaults to the bundled
Moshier model when no proprietary data is configured. High-precision Swiss
Ephemeris files remain optional and are gated by their own licence terms; you
may fetch them with the `astroengine-ephe` helper once you have reviewed and
agreed to the upstream terms via the `--agree-license` flag.

---

## Quick start

# >>> AUTO-GEN BEGIN: README Quick Start v1.1
## Quick start (devs)
```bash
# one-liners
make setup    # or follow docs/DEV_ENV.md
make doctor   # environment sanity (strict)
make test     # run unit tests
make migrate  # apply latest alembic migrations to your local DB
make cache-warm  # populate ephemeris cache with verified data
make run-api  # start the FastAPI service on http://127.0.0.1:8000
make run-ui   # launch the Streamlit workspace on http://127.0.0.1:8501
export SE_EPHE_PATH=/path/to/se/data   # optional for precision; falls back if missing
# Windows (PowerShell): $env:SE_EPHE_PATH="C:/AstroEngine/ephe"
# Windows (Command Prompt, persistent): setx SE_EPHE_PATH "C:\AstroEngine\ephe"
```

### One-command usability check

```bash
python -m astroengine.maint --full --strict
# or, to auto-install declared dev deps:
python -m astroengine.maint --full --strict --auto-install all --yes
```

See `docs/DIAGNOSTICS.md`, `docs/SWISS_EPHEMERIS.md`, and `docs/QUALITY_GATE.md` for details.

### Run API + Streamlit in 2 commands

```bash
export DATABASE_URL="sqlite+pysqlite:///${PWD}/dev.db" SE_EPHE_PATH="$HOME/.sweph/ephe"
make run-api
make run-ui
```

The environment exports pin the SQLite dev database (`dev.db` in the repo root)
and point Swiss Ephemeris to your local data so neither service falls back to
reduced-precision providers. Separate terminals running `make run-api` and
`make run-ui` mimic the production topology while staying entirely data-backed.

### Docker Compose workflow

The repository now ships a compose bundle that launches the API on `:8000`, the
Streamlit UI on `:8501`, and mounts `./data/ephe` into `/opt/ephe` so Swiss
Ephemeris files are shared across services. Containers default to
`LOG_LEVEL=INFO`; override it (for example, `LOG_LEVEL=DEBUG`) to increase
verbosity when diagnosing issues.

1. Prepare the shared volume and (optionally) download licensed Swiss data:
   ```bash
   mkdir -p data/ephe
   docker compose run --rm api astroengine-ephe --agree-license --dest /opt/ephe
   ```
   The download step is optional; omit it to keep the default Moshier ephemeris.

2. Build and start the API:
   ```bash
   docker compose up --build api
   ```

3. In a separate shell, build and start the UI (Compose will reuse the running API container or start one if needed):
   ```bash
   docker compose up --build ui
   ```

4. (Optional) Launch a tooling container to run CLI commands inside the same
   environment:
   ```bash
   docker compose run --rm tools astroengine --help
   ```

The bind mount keeps ephemeris data at `/opt/ephe` so both services reuse the
same Swiss Ephemeris cache without copying files into the container image.
# >>> AUTO-GEN END: README Quick Start v1.1

### Windows desktop shell

The packaged Windows experience wraps the FastAPI service, Streamlit UI, and
diagnostics inside a WebView2-powered desktop window. Launch it locally with:

```bash
python -m app.desktop.launch_desktop
```

The embedded first-run wizard refuses to save configuration unless it detects
real Swiss Ephemeris data files in the provided directory and, when the offline
atlas toggle is enabled, verifies the SQLite database can be read without
mutation. The wizard prints a summary with file and table counts so operators
can confirm every module remains data-backed before proceeding to production
checks.

To build the Windows 11 installer, run `packaging\windows\make.bat` from a
Developer Command Prompt. The script creates `dist\AstroEngine\AstroEngine.exe`
using PyInstaller (pointing at the native desktop shell) and, if Inno Setup is
available, emits an installer at `packaging\windows\Output` that places
shortcuts in the Start menu and on the desktop. Double-clicking the bundled
`AstroEngine.exe` brings up the self-contained desktop app—no browser is opened
and the FastAPI/Streamlit processes are orchestrated by the embedded shell.

Key behaviour:

* **Native menus & tray.** Start/stop the API, reopen the embedded UI, tail
  logs, or quit directly from the title bar menu or system tray icon.
* **Settings editor.** Configuration lives at
  `%LOCALAPPDATA%/AstroEngine/config.yaml` and includes database connection
  details, Swiss Ephemeris path validation, API/Streamlit port overrides,
  caching knobs (`AE_QCACHE_*`), logging level, theme, and auto-start toggles.
  Updates are validated (including a live database connectivity check) before
  being applied.
* **Observability helpers.** Diagnostics, `/healthz`, `/metrics`, and log
  viewers are available from the menus, and a one-click issue report bundles an
  anonymised diagnostics snapshot for support.
* **Bundled portal launcher.** CI publishes a PyInstaller build generated from
  `packaging/windows/astroengine.spec`. The executable ships the Streamlit
  `main_portal.py` experience inside the desktop shell with the Swiss ephemeris
  stub baked in and keeps user data under `%LOCALAPPDATA%/AstroEngine`.
* **Ruleset parity.** The PyInstaller spec now copies every packaged ruleset,
  dataset, schema, and HTML asset so the desktop API uses the same
  data-backed modules as source installs—no functionality is lost in the
  Windows bundle.
* **ChatGPT copilot.** The dockable copilot panel can tail logs, run
  diagnostics, summarise API errors, and explain endpoints. Provide an OpenAI
  API key and model in Settings to enable remote completions; otherwise the
  panel falls back to deterministic tool output. Token usage is tracked with a
  daily guardrail sourced from the desktop config.

All values surfaced by the desktop shell originate from the same data-backed
modules shipped with AstroEngine—no synthetic astrology data or guessed
ephemerides are injected into the workflow.

### First transit sanity check

Once the virtual environment is ready, confirm that the bundled CLI can
resolve ephemeris data and emit real transits. The command below scans
for aspects between the Moon and Sun over the first week of 2024 and
writes a JSON payload containing every hit and its severity score:

```bash
python -m astroengine transits \
  --start 2024-01-01T00:00:00Z \
  --end 2024-01-07T00:00:00Z \
  --moving moon \
  --target sun \
  --provider swiss \
  --step 180 \
  --json moon_sun_transits.json
```

Inspecting the generated file is a convenient way to verify that Swiss
Ephemeris (or the PyMeeus fallback) is configured correctly before
trying richer recipes.

### v1 release verification checklist

Teams bringing up the v1 stack for the first time can lean on the
following repeatable sequence to validate that every module, submodule,
channel, and subchannel remains intact and data-backed:

1. **Provision dependencies & run the default test suite**
   ```bash
   make setup
   make doctor
   make test
   ```
   These targets install the declared extras, confirm the environment is
   healthy, and execute the repository's deterministic unit coverage.

2. **Execute the maintainer diagnostic**
   ```bash
   python -m astroengine.maint --full --strict
   # auto-install any optional extras that are missing
   python -m astroengine.maint --full --strict --auto-install all --yes
   ```
   The maintainer harness walks the module hierarchy, ensuring that each
   registered provider and ephemeris bridge loads correctly.

3. **Generate a Moon/Sun transit report**
   Use the CLI recipe in the section above to emit a JSON transit file.
   Inspecting the resulting dataset guarantees the ephemerides feeding
   v1 are returning verifiable positions.

4. **Smoke-test the interactive UI**
   ```bash
   streamlit run apps/streamlit_transit_scanner.py
   ```
   The Streamlit bundle surfaces the same data-backed scans, highlights
   Swiss Ephemeris status, and exposes export paths for CSV/SQLite/Parquet.

5. **Bring up the v1 REST API**
   ```bash
   uvicorn app.relationship_api:create_app --factory --host 0.0.0.0 --port 8000
   ```
   Hit `/v1/relationship/synastry`, `/v1/relationship/composite`,
   `/v1/relationship/davison`, and `/v1/healthz` with real Solar Fire or
   Swiss-derived datasets to confirm the deployed service returns
   verifiable payloads.

# >>> AUTO-GEN BEGIN: Minimal App Quickstart v1.1
## Run the minimal application

1. **Python 3.11** recommended. Create a venv and install runtime + optional UI deps:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e .[ui]
   # optional exports/providers:
   pip install pyarrow skyfield jplephem
   ```

2. Ensure Swiss ephemeris files exist and set `SE_EPHE_PATH` (if using swiss provider):

   ```bash
   export SE_EPHE_PATH="$HOME/.sweph/ephe"
   # Windows (PowerShell): $env:SE_EPHE_PATH="C:/AstroEngine/ephe"
   # Windows (Command Prompt, persistent): setx SE_EPHE_PATH "C:\AstroEngine\ephe"
   ```

3. (Optional) Pin scan functions by exporting `ASTROENGINE_SCAN_ENTRYPOINTS` (comma/space separated `module:function`):

   ```bash
   export ASTROENGINE_SCAN_ENTRYPOINTS="astroengine.engine:scan_window astroengine.core.transit_engine:scan_contacts"
   ```

4. Launch the app:

   ```bash
   streamlit run apps/streamlit_transit_scanner.py
   ```

   > **Heads-up:** the repository ships a ``streamlit/`` testing shim for
   > unit suites. Always start UI scripts with ``streamlit run`` rather than
   > ``python`` so the real Streamlit package loads before the shim.

* **Scan Transits**: choose provider/time window/bodies/targets; optionally pin an entrypoint; previews canonical events and exports to SQLite/Parquet.
* **Swiss Smoketest**: runs `scripts/swe_smoketest.py` to validate Swiss setup.
* The sidebar lists detected scan entrypoints and environment overrides; install `pandas` for the tabular preview.

> If import fails about `get_se_ephe_path`, this CP also restores `astroengine/ephemeris/utils.py`.

# >>> AUTO-GEN END: Minimal App Quickstart v1.1

### Streamlit synastry & composite playground

The Streamlit bundle now ships a dedicated **Synastry & Composites** page that
calls the FastAPI routes introduced in STEP‑A‑027. Launch it with:

```bash
export API_BASE_URL="http://localhost:8000"  # point to your running FastAPI app
streamlit run ui/streamlit/pages/05_Synastry_Composite.py
```

The page offers real datasets for quick regression checks:

- **Synastry tab** – Paste or upload JSON longitude maps (e.g. Solar Fire
  exports). Choose aspects, optionally override orb policies inline, and view
  the returned hit table, grid counts, and heatmap.
- **Composites tab** – Compute midpoint composites from paired position maps or
  Davison composites from two datetimes. Results include tabular outputs, CSV
  and JSON downloads, and a polar plot for midpoint longitudes.

Sample longitude presets bundled with the page correspond to historical charts
captured from published ephemerides so the outputs remain fully data-backed.

### Quantized refinement cache tuning

High-frequency refinement loops now consult a tiny process-local LRU that
quantizes Terrestrial Time (TT) into short bins so repeat calls within the same
window reuse identical Swiss Ephemeris samples. Control the cache via env vars:

- `AE_QCACHE_SEC` – quantization window in seconds (default `1.0`). Lower values
  tighten the window; increase to broaden cache hits when input jitter exceeds
  a second.
- `AE_QCACHE_SIZE` – maximum cached entries (default `4096`). Raise this if
  long-running transit scans churn through the default footprint.

Heavy relationship or mundane timeline scans benefit from a denser cache. For
those workloads export `AE_QCACHE_SEC=0.25 AE_QCACHE_SIZE=16384` to mirror the
container tuned defaults.

Daily Swiss-ephemeris lookups can be precomputed on disk across the 1900‑2100
span via `make cache-warm`. Override the range with `AE_WARM_START` and
`AE_WARM_END` when you need narrower warms (e.g. CI disk quotas).

Both knobs act locally per process and can be tuned without code changes when
profiling heavy refinement workloads.

### Relationship API (v1)

The new FastAPI-powered relationship service exposes deterministic REST
endpoints at the `/v1` base path. Launch it via Uvicorn with

```bash
uvicorn app.relationship_api:create_app --factory --host 0.0.0.0 --port 8000
```

The Docker entrypoint now auto-detects an appropriate worker count using
`os.cpu_count()` so container deployments saturate available vCPUs. Override the
value by exporting `UVICORN_WORKERS` when launching locally or in orchestration
manifests.

Key routes:

- `POST /v1/relationship/synastry` → synastry hits, grids, overlays, scores
- `POST /v1/relationship/composite` → midpoint composites for selected bodies
- `POST /v1/relationship/davison` → Davison mid-time/space positions via Swiss/Skyfield
- `GET /v1/healthz` → service health probe

All requests accept strict JSON payloads using Pydantic v2 models and return
`{code, message, details}` error envelopes on failure. ETags, request IDs, and
rate limiting headers are emitted automatically for production observability.

### Next steps

The documentation set now includes step-by-step recipes for three common
workflows:

- Daily planner view that combines transiting bodies with natal
  positions.
- Electional window sweeps that surface promising aspect windows for
  a specific transiting body.
- Transit-to-progressed synastry comparisons for relationship or event
  tracking.

Start with `docs/quickstart.md` for an annotated walkthrough, then jump
to `docs/recipes/` to reproduce the detailed examples without additional
setup.

# >>> AUTO-GEN BEGIN: README Import Snippet v1.0
### Import the package

```python
import astroengine
```
# >>> AUTO-GEN END: README Import Snippet v1.0

# >>> AUTO-GEN BEGIN: Canonical Transit Types v1.0
## Canonical types (stable API surface)

Import once, use everywhere:

```python
from astroengine import TransitEvent, BodyPosition
from astroengine.canonical import events_from_any
```

* **TransitEvent** is the single event model returned by scans and written by exporters.
* **BodyPosition** is the provider position record (lon/lat/dec/speed_lon).

### Export helpers

```python
from astroengine.exporters import write_sqlite_canonical, write_parquet_canonical
from astroengine.canonical import sqlite_read_canonical
from astroengine.exporters_ics import write_ics
from astroengine.infrastructure.storage.sqlite import ensure_sqlite_schema

rows = write_sqlite_canonical("events.db", events)     # accepts dicts/legacy/canonical
rows = write_parquet_canonical("events.parquet", events, compression="gzip")
ensure_sqlite_schema("events.db")  # applies Alembic migrations in-place
events = sqlite_read_canonical("events.db")
write_ics(
    "events.ics",
    events,
    calendar_name="AstroEngine",
    summary_template="{label} [{natal_id}]",
)
```

- Canonical SQLite exports store a fully versioned `transits_events` schema with
  indexed columns (`profile_id`, `natal_id`, `event_year`, `score`).
- Parquet exports are partitioned by `natal_id/event_year` to support efficient
  downstream filtering. The `compression` keyword controls the codec (snappy,
  gzip, brotli, ...).
- ICS exports accept summary/description templates and understand ingress and
  return events alongside standard transits.

### CLI integration (maintainers)

Scan commands can call `_cli_export(args, events)` after adding
`add_canonical_export_args(parser)` to gain `--sqlite/--parquet` switches. A
companion query tool exposes indexed lookups:

```
astroengine query --sqlite events.db --limit 5 --natal-id n001
```

### CLI enhancements

* Global options `--zodiac`, `--ayanamsha`, and `--house-system` mirror the runtime `ChartConfig`, allowing sidereal and non-Placidus workflows to run directly from the CLI without rewriting chart code.
* `astroengine ingresses --start … --end …` reports sign changes for any supported body and supports JSON/SQLite/Parquet exports.
* `astroengine timelords --start … --vimshottari --moon-longitude …` computes Vimshottari dashas; pair with `--zr --fortune-longitude …` to emit zodiacal releasing tables.
* `astroengine transits … --narrative` summarises the top scored events via the new narrative layer (falls back to a deterministic template when no GPT backend is configured).

# >>> AUTO-GEN END: Canonical Transit Types v1.0

The CI workflow `.github/workflows/ci.yml` covers Python 3.10–3.11 and archives diagnostics output for each run.

The package exposes a registry-based API for discovering datasets and
rulesets.  See `astroengine/modules` for details.

---

## Development workflow

The repository ships a lightweight `Makefile` that documents the most common
developer activities.  Run `make` (or `make help`) to view the curated targets.

- `make format` — apply Ruff autofixes alongside Black and isort formatting.
- `make lint` — check code style without mutating the working tree.
- `make typecheck` — execute `mypy` on the typed package surfaces.
- `make test` — ensure the test dependency stack is installed and then run the
  full `pytest` suite, including CLI and ephemeris tests.
  - When invoking `pytest` manually, run it from the repository root so the
    `pytest.ini` entry `pythonpath = generated` stays in effect.  This keeps the
    deprecated compatibility package `generated.astroengine` visible to tests
    and local scripts that still import from that namespace.
- `make check` — convenience target that executes linting, type checking,
  and tests in sequence to validate merge readiness.

These helpers ensure the module → submodule → channel → subchannel hierarchy
remains intact, particularly when integrating new Solar Fire derived datasets or
augmenting the runtime with additional registries.

Before running diagnostics, walk through this checklist:

- [ ] Install the providers extras with `pip install -e .[providers]` (or run
  `make install-optional`).
- [ ] Export `SE_EPHE_PATH` to your Swiss ephemeris data directory; when no
  licensed files are available the bundled fallback
  `datasets/swisseph_stub` keeps deterministic tests passing.
- [ ] Apply the latest database schema with `alembic upgrade head`.

Completing these steps clears the WARNs surfaced by
`python -m astroengine.diagnostics --strict`.

### Updating dependency manifests

`requirements/base.in`, `requirements/dev.in`, and
`requirements-optional.txt` are generated from `pyproject.toml` so the
dependency graph only has one source of truth. Refresh the unpinned inputs with:

```bash
python scripts/generate_requirements.py
```

Pass `--check` to verify whether the tracked files already match the
`pyproject` declarations. Pinned lockfiles live at `requirements/base.txt` and
`requirements/dev.txt`; regenerate them with `pip-compile` (or `uv lock`):

```bash
pip-compile requirements/base.in --output-file requirements/base.txt
pip-compile requirements/dev.in --output-file requirements/dev.txt
```

# >>> AUTO-GEN BEGIN: AE README Providers Addendum v1.2
### Optional providers & catalogs
The core package now installs the previously optional exporters, narrative, CLI,
UI, and reporting stacks by default so Solar Fire derived datasets and
rendering workflows work out of the box. Use the helper script to install the
complete optional stack, including the
patched flatlib workflow that keeps the mandatory `pyswisseph` runtime at
2.10.3.2:

```bash
make install-optional
# or
python scripts/install_optional_dependencies.py --upgrade-pip
```

The script installs `requirements-optional.txt`, verifies every optional stack
import—including exporters like `ics`, reporting libraries such as
`weasyprint`, and runtime services like `fastapi`—and installs `flatlib==0.2.3`
without pulling its outdated `pyswisseph==2.08` constraint so the Swiss
bindings remain on the supported 2.10 series.

### CLI

```bash
python -m astroengine provider list
python -m astroengine provider check swiss
astroengine scan --start-utc 2024-01-01T00:00:00Z --end-utc 2024-01-02T00:00:00Z \
  --moving Sun Moon --targets natal:Sun natal:Moon --target-frame natal --detector lunations
```

Use `astroengine codex tree` to render the module → submodule → channel →
subchannel hierarchy directly in the terminal, or `astroengine codex show` to
inspect metadata for specific entries. The command is backed by the same
`astroengine.codex` helpers that power developer tooling, so every path it
reports corresponds to real documentation or dataset files in the repository.

> **Licensing note:** Swiss Ephemeris is AGPL/commercial for distribution. Keep data files outside the wheel; users should provide `SWE_EPH_PATH/SE_EPHE_PATH`.

`pyswisseph==2.10.3.2` now ships with the core package, ensuring Swiss
Ephemeris integrations are present for every install. If the binding cannot
load (for example, due to missing system libraries) the engine automatically
registers a **Swiss fallback provider** powered by PyMeeus analytical series.
The fallback keeps the Swiss handle usable inside this repository’s test
environment while still producing real geocentric ecliptic longitudes,
latitudes, and longitudinal speeds for the visible planets and Pluto. Install
the official Swiss ephemeris data files for production deployments to regain
full Swiss precision.

# External integrations registry

AstroEngine catalogues third-party libraries and desktop suites inside the
`integrations` module.  Review
[`docs/integrations/external_tools.md`](docs/integrations/external_tools.md) for
install sources covering Swiss Ephemeris (`sweph`/`pyswisseph`), Skyfield,
Flatlib, Maitreya, Jagannatha Hora, and open-source Panchanga projects.

# >>> AUTO-GEN END: AE README Providers Addendum v1.2

# >>> AUTO-GEN BEGIN: AE README Aspects + Domain Report v1.0
### Minor & harmonic aspects (default policy)
Minor and harmonic families ship **enabled by default** through
`profiles/aspects_policy.json`. Adjust `enabled_minors` or
`enabled_harmonics` (accepts canonical names or harmonic numbers 5–12) to
disable or extend the active set, then:
```bash
python -m astroengine scan --start 2024-06-01T00:00:00Z --end 2024-06-07T00:00:00Z \
  --moving mars --target venus --provider swiss
````

> Tip: adjust the `partile_threshold_deg` field in this policy to tune the
> ≤0°10′ tagging window used for partile aspects.

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
- Dataset: `datasets/star_names_iau.csv` (official WGSN catalogue derived from HYG Database v4.1, CC-BY-SA 4.0).
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

- `astroengine transits ... --decl-only` scans only declination parallels/contraparallels.
- Override the antiscia axis (Cancer–Capricorn by default) with `--mirror-axis` when running `astroengine transits`.

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

> The base development container only installs the core runtime so images stay
> lightweight. API-facing dependencies such as `fastapi`, `uvicorn`,
> `pydantic`, and `icalendar` therefore are not present until you explicitly
> install the `api` extra (e.g. `pip install -e .[api,dev]`) or the mirrored
> bundle in `requirements-optional.txt`.

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
- Install the developer extras and run `black`, `ruff check --fix`, and `pytest`
  locally (or via `pre-commit run --all-files`) before pushing.

Install the repo’s pre-commit hooks once per clone to enforce formatting and
baseline hygiene automatically:

```bash
pip install pre-commit
pre-commit install
```

These hooks run Black, Ruff, and whitespace fixers using the configuration in
`.pre-commit-config.yaml`.

```bash
python -m astroengine scan \
  --start 2024-06-01T00:00:00Z \
  --end   2024-06-07T00:00:00Z \
  --moving mars --target venus \

