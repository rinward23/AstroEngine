# >>> AUTO-GEN BEGIN: Swiss Ephemeris Setup v1.0
# Swiss Ephemeris — Setup

AstroEngine can use `pyswisseph` (Swiss Ephemeris). Without data files, it will fall back to the built-in Moshier model (lower precision but fine for CI/dev).

## Install the library
```bash
pip install pyswisseph
```

## Data files (optional, for high precision)

1. Obtain the Swiss Ephemeris data package from the official distributor.
2. Unpack into a local folder, e.g. `~/ephe/se/`.
3. Point the engine to it:

   ```bash
   export SE_EPHE_PATH=~/ephe/se
   # Windows (PowerShell): $Env:SE_EPHE_PATH = "C:\\ephe\\se"
   ```

## Verify

```bash
python -m astroengine.diagnostics --strict
python -m astroengine.diagnostics --smoketest "2025-01-01T00:00:00Z"
```

# >>> AUTO-GEN END: Swiss Ephemeris Setup v1.0
