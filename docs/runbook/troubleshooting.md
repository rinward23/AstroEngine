# Troubleshooting Quick Fixes

This reference summarizes the fastest path to resolve high-frequency issues reported by the on-call rotation. Each fix should be applied only after confirming the associated error message in logs or terminal output.

| Symptom | Immediate Fix |
| --- | --- |
| `ModuleNotFoundError: alembic` | Install Alembic, set `DATABASE_URL`, then apply the latest head: `pip install alembic && export DATABASE_URL="sqlite:///./dev.db" && alembic upgrade head`. Replace the SQLite DSN with your staging/production URL as needed. |
| `ModuleNotFoundError: pyswisseph` or build failures on Python 3.12 | Switch to Python 3.11 (our supported runtime) and install the Swiss Ephemeris bindings: `pyenv local 3.11 && pip install pyswisseph`. |
| `OSError: sweph not found` | Export `SE_EPHE_PATH` to point to the directory that contains the Swiss Ephemeris data files before running the engine. |
| `sqlite3.OperationalError: database is locked` | Confirm there is only one writer, enable WAL mode if disabled, and retry the job with exponential backoff. |
| `Address already in use :8000` | Terminate the existing process bound to port 8000 or restart the service on an alternate port such as `--port 8001`. |
| `ImportError: app.main` | Set the `APP_MODULE` environment variable to the fully qualified module path (for example, `app.main:app`). |

For longer-term remediation, add notes to the incident retrospective and update automation so the underlying issue cannot recur silently.
