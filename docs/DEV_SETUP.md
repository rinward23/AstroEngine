# >>> AUTO-GEN BEGIN: AstroEngine Dev Setup Guide v1.0
## Quick start (pip)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\\.venv\\Scripts\\Activate.ps1
export PIP_CONSTRAINT=constraints.txt
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

## Optional feature groups

Install extras as needed:

```bash
pip install -e .[api]           # FastAPI server
pip install -e .[charts]        # plotting
pip install -e .[locational]    # astrocartography helpers
pip install -e .[fallback-ephemeris]
```

# >>> AUTO-GEN END: AstroEngine Dev Setup Guide v1.0
