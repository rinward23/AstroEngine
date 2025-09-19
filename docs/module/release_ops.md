# Release & Operations Plan

- **Module**: `release_ops`
- **Author**: AstroEngine Release Guild
- **Date**: 2024-05-27
- **Source datasets**: `pyproject.toml` extras definitions, Dockerfiles (`docker/`), observability templates (`observability/*.json`), compatibility matrices from Solar Fire deployment guides, conda-forge packaging notes.
- **Downstream links**: QA acceptance (`docs/module/qa_acceptance.md`), interop spec (`docs/module/interop.md`), governance checklist (`docs/governance/acceptance_checklist.md`).

This plan covers packaging extras, compatibility tracking, containerization, and observability requirements so production deployments remain reproducible.

## Packaging Extras

| Extra | Dependencies | Purpose | Notes |
| ----- | ------------ | ------- | ----- |
| `skyfield` | `skyfield`, `jplephem` | Alternate ephemeris backend | Keep pinned to JPL DE441 release |
| `swe` | `pyswisseph` | Primary high-precision ephemeris | Requires Swiss Ephemeris license acceptance |
| `parquet` | `pyarrow`, `fastparquet` | Parquet export support | Align version with interop schema tests |
| `cli` | `click`, `rich` | Command-line tooling | CLI commands documented in README |
| `dev` | `pytest`, `black`, `ruff`, `mypy` | Developer workflow | Matches CI configuration |
| `maps` | `cartopy`, `shapely`, `pyproj` | Astrocartography and map exports | Requires system GEOS/PROJ dependencies |

Extras must stay additive—no removal without governance approval. Update `pyproject.toml` and this table simultaneously.

## Compatibility Matrix Skeleton

| Module | Submodule | Channel | Profiles | Providers | Exports |
| ------ | --------- | ------- | -------- | --------- | ------- |
| `core-transit-math` | `severity` | `default` | `vca_default`, `vca_tight`, `vca_support` | `swe`, `skyfield` | `astrojson.event_v1`, `csv.transits_events` |
| `event-detectors` | `stations` | `direct` | `vca_default`, `mundane_profile` | `swe` | `astrojson.event_v1`, `ics.station_alert` |
| `event-detectors` | `eclipses` | `solar` | `mundane_profile` | `swe` | `astrojson.event_v1`, `ics.eclipse_path` |
| `providers` | `houses` | `placidus` | `all` | `swe` | `n/a` (runtime service) |
| `ruleset_dsl` | `compiler` | `linter` | `all` | `n/a` | `json.lint_report` |
| `data-packs` | `fixed_stars` | `bright_list_v1` | `all` | `n/a` | `n/a` |

Future modules append rows; existing rows remain immutable to prove no module loss.

## Docker Strategy

- Maintain two Dockerfiles: `docker/runtime.Dockerfile` (minimal runtime) and `docker/lab.Dockerfile` (includes dev extras and datasets).
- Base image: `python:3.11-slim`. Install system dependencies for maps extra (GEOS, PROJ) only in lab image.
- Volume mount ephemeris cache at `/var/lib/astroengine/ephemeris` with checksum verification on container start via entrypoint script.
- Include healthcheck running `python -m astroengine.infrastructure.environment numpy pandas scipy --as-json`.

## Conda-Forge Plan (Post-0.1.0)

- Create feedstock referencing PyPI tarball with extras disabled (wheel remains extras-free).
- Use CI matrix: Linux x86_64, macOS arm64/x86_64, Python 3.10–3.12.
- Patch recipe to download Swiss Ephemeris from official mirror and record checksum.
- Tests: run `pytest -m "not perf"` with Swiss Ephemeris stub to confirm packaging integrity.

## Observability Stack

- Logging: JSON structured logs with fields `timestamp`, `module_path`, `event_id`, `severity_band`, `dataset_urn`, `profile_id`, `message`.
- Metrics: Prometheus counters `astroengine_events_total{module_path,profile_id}`, histograms `astroengine_export_latency_seconds`.
- Tracing: Optional OpenTelemetry instrumentation with `service.name=astroengine`.
- Alerts: define alert rules for severity backlog (no peak events exported in >7 days) and dataset checksum mismatch.

## PII & Security

- Sensitive data (user names, email) stored in exports must be redacted or hashed before leaving system; apply to ICS descriptions.
- Maintain license audit log in `docs/governance/acceptance_checklist.md` referencing Solar Fire and ACS Atlas entitlements.
- Require OIDC tokens for publishing exports; tokens stored in HashiCorp Vault with rotation policy 90 days.

## Release Workflow

1. Tag release in git (`vX.Y.Z`) after QA acceptance sign-off.
2. Build wheel and source distribution via `python -m build` inside clean virtualenv.
3. Run `pytest` and `python -m astroengine.infrastructure.environment numpy pandas scipy` to capture environment report.
4. Publish to PyPI and attach environment JSON to release notes.
5. Update `docs/burndown.md` with release status and outstanding items.

This operations plan ensures packaging, deployment, and observability adhere to governance requirements while safeguarding module integrity.
