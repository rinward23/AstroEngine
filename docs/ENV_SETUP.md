# >>> AUTO-GEN BEGIN: Docs Env Setup v1.0
# AstroEngine — Environment Setup & Doctor

This guide helps you verify a healthy Conda/Mamba/Micromamba setup and safely clean/recreate the project env.

## TL;DR
- Prefer **Micromamba**. If you already use Conda/Mamba, that's fine.
- Target env name: **py311** (configurable).
- One-liners:
  - Check: `python -m astroengine.doctor_conda --check`
  - Clean caches: `python -m astroengine.doctor_conda --fix-cache`
  - Remove env: `python -m astroengine.doctor_conda --remove-env py311`
  - Recreate env: `python -m astroengine.doctor_conda --recreate-env`

## 1) Verify installation
Run:
```bash
which micromamba || which mamba || which conda
conda --version 2>/dev/null || true
micromamba --version 2>/dev/null || true
```

Windows (PowerShell):

```powershell
Get-Command micromamba, mamba, conda -ErrorAction SilentlyContinue
```

If none are found, install **Micromamba**:

* Linux/macOS: [https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
* Windows: Scoop/Chocolatey or the official installer. Ensure it’s on PATH.

## 2) Create/activate env

```bash
# Create (Micromamba recommended)
micromamba create -f environment.yml -y   # or: conda env create -f environment.yml

# Activate
micromamba activate py311                 # or: conda activate py311
```

## 3) Common cleanups

* **Caches** (safe):

  * `micromamba clean --all --yes`
  * `conda clean --all -y`
* **Remove env** (irreversible):

  * `micromamba env remove -n py311`
  * `conda env remove -n py311 -y`
* **Recreate env**:

  * `micromamba create -f environment.yml -y`

## 4) Doctor utility (scripted)

Run checks:

```bash
python -m astroengine.doctor_conda --check --expect-name py311
```

Optional fixes:

```bash
python -m astroengine.doctor_conda --fix-cache
python -m astroengine.doctor_conda --remove-env py311
python -m astroengine.doctor_conda --recreate-env
```

Exit codes: `0` success, `2` operational error; removal/creation failures will return `2`.

## 5) Fallback: pure venv

If Conda/Mamba are not desired:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

# >>> AUTO-GEN END: Docs Env Setup v1.0

