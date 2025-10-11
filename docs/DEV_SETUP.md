# >>> AUTO-GEN BEGIN: AstroEngine Dev Setup Guide v1.0
## Quick start (pip)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\\.venv\\Scripts\\Activate.ps1
pip install -e .[dev]
```

## Quick start (conda)

```bash
conda env update -f environment.yml --prune
conda activate astroengine
```

## Swiss Ephemeris data

`pyswisseph` loads ephemeris files from `SWE_EPH_PATH`. Set one of:

* Export `SWE_EPH_PATH` to a folder containing `sepl_*.se1`/`semo_*.se1` etc.
* Or place ephemeris files under `./ephe/` and set `SWE_EPH_PATH=./ephe`.
* Without licensed data the package falls back to the bundled
  `astroengine/datasets/swisseph_stub` directory for deterministic tests.

## Optional feature groups

The base installation already bundles the exporters, providers, CLI, and UI
dependencies so the Solar Fire data ingestion workflows operate without extra
flags. Extras remain available for compatibility with existing deployment
scripts; install them as needed:

```bash
pip install -e .[api]           # FastAPI server
pip install -e .[charts]        # plotting
pip install -e .[locational]    # astrocartography helpers
pip install -e .[fallback-ephemeris]
```

# >>> AUTO-GEN END: AstroEngine Dev Setup Guide v1.0

## Windows installer path

For per-user Windows setups that should mirror production environments,
use the one-click installer described in the
[Windows Installer Support Runbook](runbook/windows_installer_support.md).
That guide details log locations, silent install flags, and the repair
flow support should follow when issues arise.
