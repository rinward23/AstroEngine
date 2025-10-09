# >>> AUTO-GEN BEGIN: Swiss Ephemeris Setup v1.0
# Swiss Ephemeris — Setup

AstroEngine ships with `pyswisseph==2.10.3.2` (Swiss Ephemeris). Without data files, it will fall back to the built-in Moshier model (lower precision but fine for CI/dev).

Every wheel now bundles an empty `astroengine/datasets/swisseph_stub/` directory so
`SE_EPHE_PATH` can always point somewhere deterministic even outside the source tree.
Replace its contents with the proprietary `.se1` files when you have a licensed copy
of the data pack.

## Install the library
The core package already declares the dependency, so a standard
`pip install astroengine` (or `pip install -e .`) pulls the wheel
automatically. Reinstall manually only when testing alternative builds.

## Data files (optional, for high precision)

1. Obtain the Swiss Ephemeris data package from the official distributor.
2. Unpack into a local folder, e.g. `~/ephe/se/`.
3. Point the engine to it:

   ```bash
   export SE_EPHE_PATH=~/ephe/se
   # Windows (PowerShell): $Env:SE_EPHE_PATH = "C:\\ephe\\se"
   ```

## Download helper (license acceptance required)

Install the lightweight tooling extra to pull in `requests` and run the installer:

```bash
pip install -e .[tools]
astroengine-ephe --install https://example.com/path/to/swiss-ephemeris.zip --target ~/ephe/se --agree-license
```

The `astroengine-ephe` CLI prints an error and exits unless `--agree-license` is provided,
reinforcing that downloads are allowed only after you have reviewed and accepted the
Swiss Ephemeris terms from Astrodienst.

## Verify

```bash
python -m astroengine.diagnostics --strict
python -m astroengine.diagnostics --smoketest "2025-01-01T00:00:00Z"
```

# >>> AUTO-GEN END: Swiss Ephemeris Setup v1.0
