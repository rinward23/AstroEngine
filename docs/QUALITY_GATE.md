# >>> AUTO-GEN BEGIN: Quality Gate v1.0
# AstroEngine Quality Gate — One-Command Usability Check

**Primary prompt (run everything):**
```bash
python -m astroengine.maint --full --strict
```

This runs:

1. Diagnostics (strict) — environment, imports, Swiss Ephemeris, profiles.
2. Format/Lint — ruff, black, isort (with auto-fix when `--fix` or `--full`).
3. Tests — `pytest -q` (if `--with-tests` or `--full`).
4. Optional build — when `--with-build`.

**Optional auto-fix & install:**

```bash
python -m astroengine.maint --full --strict --auto-install all --yes
```

* Reads `requirements-dev.txt` and installs any missing packages.
* Never installs anything unless `--auto-install` is provided (and `--yes` to skip prompts).

**Cleanup:**

```bash
python -m astroengine.maint --clean
```

**Make targets:**

```bash
make fullcheck
make repair
make build
```

**Exit codes:**

* `0` = all gates passed; `1` = at least one gate failed.

Notes:

* High-precision Swiss Ephemeris data is optional; set `SE_EPHE_PATH` to enable.
* The orchestrator is idempotent and safe to re-run at any time.

# >>> AUTO-GEN END: Quality Gate v1.0
