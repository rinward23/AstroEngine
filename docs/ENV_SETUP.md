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

The optional ``dev`` extras install pytest, ruff, and black to match the
continuous-integration toolchain.

## 3) Inspect the environment

```bash
python -m astroengine.infrastructure.environment numpy pandas scipy
```

The command prints a concise report with the Python version, executable
path, platform, and package versions.  Use ``--as-json`` to capture the
information programmatically.

## 4) Updating dependencies

Because the package is now managed via ``pyproject.toml``, upgrades are
handled with ``pip``:

```bash
pip install -e . --upgrade
```

If you prefer a clean install, remove the ``.venv`` directory and repeat
steps 1–3.
