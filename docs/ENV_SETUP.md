# AstroEngine — Environment Setup

The project now relies on plain Python virtual environments and no longer
requires Conda/Mamba tooling.  Use the steps below to create an isolated
runtime and verify the interpreter health.

## 0) Confirm platform prerequisites

Before creating the virtual environment, ensure the host system provides the
tools AstroEngine expects during development:

- **Python 3.11.x** — verify with `python3.11 --version` to confirm the
  interpreter matches the supported series.
- **Git 2.30+** — required for cloning the repository and managing updates.
- **Build toolchain** — install `build-essential` on Linux or the Xcode
  Command Line Tools on macOS so native extensions compile without issues.

With the prerequisites in place, proceed to the virtual environment setup.

## 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## 2) Install AstroEngine

```bash
pip install -e .[dev]
```

The optional ``dev`` extras install the full tooling stack—`pytest`,
`pytest-cov`, `hypothesis`, `ruff`, `black`, `isort`, `mypy`, `pre-commit`,
`mkdocs-material`, and `mkdocs-gen-files`—to match the continuous-integration
toolchain.

## 3) Inspect the environment

```bash
python -m astroengine.infrastructure.environment \
  pyswisseph numpy pydantic python-dateutil timezonefinder tzdata \
  pyyaml click rich orjson pyarrow duckdb
```

The command prints a concise report with the Python version, executable
path, platform, and package versions.  Use ``--as-json`` to capture the
information programmatically.  If any package is reported as ``missing``,
re-run ``pip install -e .[dev]`` to pull the required dependency set so
the runtime matches production expectations.

## 4) Updating dependencies

Because the package is now managed via ``pyproject.toml``, upgrades are
handled with ``pip``:

```bash
pip install -e . --upgrade
```

If you prefer a clean install, remove the ``.venv`` directory and repeat
steps 1–3.

## 5) Running the test suite

Before invoking ``pytest``, execute::

    python scripts/install_test_dependencies.py --quiet

The helper validates that FastAPI, pandas, Jinja2, PyYAML, and the Swiss
Ephemeris bindings are present (installing them when necessary) so the test
suite no longer aborts during collection.
