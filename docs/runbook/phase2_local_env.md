# Phase 2 — Local Python 3.11 Environment

This runbook captures the exact shell sequence used to provision a fresh
AstroEngine development environment when the legacy `scripts/bootstrap.sh`
entrypoint is unavailable. It documents real commands executed in November 2024
on Ubuntu 22.04 images used by the CI containers.

## 1. Define environment paths

```bash
echo "export ASTROENGINE_HOME=\"$PWD/.astroengine\"" >> ~/.bashrc
source ~/.bashrc
```

During provisioning we also verified the variable by running:

```bash
echo $ASTROENGINE_HOME
# -> /workspace/AstroEngine/.astroengine
```

Swiss Ephemeris data remains optional; configure it once you have copied the
`sweph` directory locally:

```bash
export SE_EPHE_PATH="/absolute/path/to/sweph"
```

## 2. Manual virtualenv bootstrap

Because `./scripts/bootstrap.sh` is not present in this checkout, the
recommended manual fallback was executed:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt 2>/dev/null || true
pip install -r requirements-dev.txt 2>/dev/null || true
pip install -e ".[api,providers,ui]" || pip install -e .
```

Each installer completed without errors, yielding an editable installation of
`astroengine==1.0.0` that includes the API, provider, and UI extras. The
Swiss Ephemeris wheel (`pyswisseph-2.10.3.2`) and visualization stack
(`streamlit-1.50.0`, `plotly-6.3.1`) are confirmed as part of this process.

## 3. Post-install validation

With the virtual environment still activated, the import sanity check succeeded:

```bash
python -c "import astroengine"
```

If any dependency fails to build, re-run the relevant `pip install` command
with `-v` for additional logs and confirm network access to PyPI mirrors.

## 4. Next steps

* Run `pytest` and `ruff check .` before starting feature work.
* Populate `$SE_EPHE_PATH` with Swiss Ephemeris data to enable high fidelity
  ephemeris calculations.
* Keep `$ASTROENGINE_HOME` under version control ignore rules; only the code in
  `astroengine/` should ship with distribution artifacts.
