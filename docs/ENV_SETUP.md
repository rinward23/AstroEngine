# AstroEngine — Environment Setup

The project now relies on plain Python virtual environments and no longer
requires Conda/Mamba tooling.  Use the steps below to create an isolated
runtime and verify the interpreter health.

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
information programmatically.  If any package is reported as ``MISSING``,
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
