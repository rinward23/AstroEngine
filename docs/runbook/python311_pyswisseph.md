# End-to-End Runbook — Python 3.11 with pyswisseph

This runbook records a full local bootstrap of AstroEngine on Python 3.11 with
Swiss Ephemeris support enabled. Every command below was validated inside a
fresh Ubuntu 22.04 container using Python 3.11.9.

## 0. Confirm the interpreter

```bash
python3.11 --version
# Expected: Python 3.11.x
```

## 1. Create a virtual environment and install runtime dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel setuptools
pip install -r requirements/base.txt
pip install -e .
```

## 2. Configure Swiss Ephemeris data (optional but recommended)

Point `SE_EPHE_PATH` to the directory that contains the Swiss ephemeris
(`*.se1`, `*.se2`, …) data files.

```bash
export SE_EPHE_PATH="/absolute/path/to/sweph"
```

## 3. Apply database migrations

```bash
export DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head
```

Ensure `dev.db` is created and populated; `alembic` prints `INFO` lines for each
migration revision that ran.

## 4. Smoke checks

```bash
python -m compileall -q .
python -c "import astroengine; print('astroengine OK:', astroengine.get_version())"
```

The import check must echo the real version reported by
`astroengine.get_version()`.

## 5. Command-line interface

```bash
python -m astroengine --help
```

Verify the help text renders without tracebacks and documents the installed
channels and subchannels.

## 6. API server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Watch the startup logs for confirmations from FastAPI and SQLAlchemy. When the
server binds successfully, visit `/docs` in a browser to inspect the generated
OpenAPI schema.

## 7. Streamlit UI

Run the Streamlit frontend once the backend API is healthy.

```bash
streamlit run ui/streamlit/vedic_app.py
```

Streamlit will report the local URL (typically `http://localhost:8501`).

## Troubleshooting quick reference

| Error | Cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: alembic` | Alembic not installed | `pip install alembic` (present in `requirements/base.txt`) |
| `ModuleNotFoundError: sqlalchemy` | SQLAlchemy not installed | `pip install SQLAlchemy` (present in `requirements/base.txt`) |
| `ModuleNotFoundError: swisseph` | `pyswisseph` missing or Python 3.12 used | Re-run under Python 3.11 and `pip install pyswisseph` |
| `OSError: sweph not found` | Swiss ephemeris data absent | Set `SE_EPHE_PATH` and confirm `sweph` files exist |
| `sqlite3.OperationalError: database is locked` | Multiple SQLite writers | Limit to a single writer or enable WAL/backoff; consider Postgres for concurrency |
| `Address already in use :8000` | Port conflict | Stop the other process or choose `--port 8001` |
| `ImportError: app.main` | Wrong ASGI path | Use `uvicorn app.main:app` |

Document any deviations from these steps in project notes to preserve the
integrity of downstream astrology data flows.
