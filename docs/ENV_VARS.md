# >>> AUTO-GEN BEGIN: docs-env-vars v1.0
## Ephemeris data paths
- **SE_EPHE_PATH** (canonical) — directory containing Swiss Ephemeris data files.
- **SWE_EPH_PATH** (alias) — accepted for compatibility.

## Database connections
- **DATABASE_URL** — SQLAlchemy connection string consumed by the FastAPI app
  (`app/db/session.py`) and Alembic migrations (`alembic.ini`). Export this
  before running `uvicorn`, `python -m app.*`, or any `alembic` command:

  ```bash
  export DATABASE_URL="sqlite:///./dev.db"  # swap in your Postgres URL when needed
  ```

  The helpers do not read `DB_URL`; ensure automation and developer machines
  consistently set `DATABASE_URL` so the API and migration stack point at the
  same datastore.

## Skyfield kernels
Searched in: `./kernels`, `~/.skyfield`, `~/.astroengine/kernels`. Use helper
`astroengine.providers.skyfield_kernels.ensure_kernel(download=True)` to fetch `de440s.bsp`.
# >>> AUTO-GEN END: docs-env-vars v1.0
