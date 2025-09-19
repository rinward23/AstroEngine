# AstroEngine — Schema Contracts

JSON Schema definitions that mirror the **ruleset appendix contracts** consumed by AstroEngine runtimes.  
Operators can run “doctor-style” validations before launching a scenario using the built-in helpers.

---

## Contents

- [Schemas](#schemas)
- [Quick start](#quick-start)
- [Local validations](#local-validations)
- [Repo layout](#repo-layout)
- [CI & quality gates](#ci--quality-gates)
- [Contributing](#contributing)
- [FAQ](#faq)

---

## Schemas

All schema payloads live under [`./schemas`](./schemas):

- `result_schema_v1.json` — structure for full run result payloads (channels, events, provenance).
- `contact_gate_schema_v2.json` — captures gating decisions near thresholds with supporting evidence.
- `orbs_policy.json` — orb policy profiles informing gating and scoring.

Schemas live outside the Python modules to honor the **append-only** workflow and keep data assets out of the package namespace.

> **Schema registry keys** used by the validator:
> - `result_v1` → `schemas/result_schema_v1.json`  
> - `contact_gate_v2` → `schemas/contact_gate_schema_v2.json`  
> - `orbs_policy` → `schemas/orbs_policy.json`

---

## Quick start

### Option A — Conda/Micromamba (recommended)

```bash
# Create and activate the environment (micromamba or conda)
micromamba create -f environment.yml -y   # or: conda env create -f environment.yml
micromamba activate py311                 # or: conda activate py311

# (Optional) dev tools
pip install -r requirements-dev.txt  # pytest, ruff, black if not in environment.yml
