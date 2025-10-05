"""Access control policies for in-app developer mode editing."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

# Editable (same as before)
WHITELIST = [
    "astroengine/",
    "app/routers/",
    "ui/streamlit/",
    "app/telemetry.py",
    "app/metrics.py",
    "app/devmode/",
]

# Never allow (even with override) — package/build infra & meta
BLOCKLIST = [
    "installer/",
    "packaging/",
    ".github/",
    "ops/",
    "scripts/",
    "Dockerfile",
    "docker-compose.yml",
    "requirements",
    "pyproject.toml",
]

# PROTECTED (allowed only with explicit override + typed confirmation)
# Rationale: editing these can brick startup, DB, or safety rails.
PROTECTED = [
    # Entrypoints & bootstrap
    "app/main.py",
    "app/uvicorn_runner.py",
    "app/observability.py",
    "app/metrics.py",

    # Safety rails (keep guard editable but gated)
    "app/devmode/security.py",

    # Core engine & config
    "astroengine/__init__.py",
    "astroengine/config.py",
    "astroengine/core/",
    "astroengine/engine/",
    "astroengine/ephemeris/",
    "astroengine/visual/base/",
    "astroengine/plugins/registry.py",

    # Database plumbing & schema
    "app/db/session.py",
    "app/db/base.py",
    "app/db/models/",
    "migrations/",
    "alembic.ini",
]


def _match_any(path: str, patterns: Iterable[str]) -> bool:
    """Return True if *path* matches any of the glob-like *patterns*."""

    p = Path(path).as_posix()
    for pat in patterns:
        normalized = pat.rstrip("/")
        if not normalized:
            continue
        if p == normalized or p.startswith(f"{normalized}/"):
            return True
    return False


def is_blocked(path: str) -> bool:
    """Return True if *path* lives under a non-editable area."""

    return _match_any(path, BLOCKLIST)


def is_allowed(path: str) -> bool:
    """Return True when a path is editable without elevated confirmation."""

    p = Path(path).as_posix()
    if is_blocked(p):
        return False
    if _match_any(p, PROTECTED):
        # Protected files can be edited, but require explicit confirmation.
        return True
    return _match_any(p, WHITELIST)


def is_protected(path: str) -> bool:
    """Return True when editing *path* requires explicit confirmation."""

    return _match_any(path, PROTECTED)
