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
python -m astroengine.infrastructure.environment numpy pandas
```

The package exposes a registry-based API for discovering datasets and
rulesets.  See `astroengine/modules` for details.

---

## Schemas

All JSON schema payloads live under [`./schemas`](./schemas).  They are
kept outside the Python package namespace to honour the append-only data
workflow.

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
