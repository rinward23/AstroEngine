"""Data access helpers for AstroEngine.

The project intentionally keeps large CSV and ruleset
files outside of the Python package so that they may be
updated independently without risking module loss.  This
module exposes a couple of convenience accessors that
resolve those resources relative to the repository root.
"""

from __future__ import annotations

from pathlib import Path

from ..infrastructure.paths import package_root as _package_root
from ..infrastructure.paths import project_root as _project_root
from ..infrastructure.paths import schemas_dir as _schemas_dir

__all__ = [
    "PACKAGE_ROOT",
    "ASTROENGINE_ROOT",
    "REPO_ROOT",
    "SCHEMA_DIR",
    "project_root",
    "schema_dir",
]

PACKAGE_ROOT = Path(__file__).resolve().parent
ASTROENGINE_ROOT = _package_root()
REPO_ROOT = _project_root()
SCHEMA_DIR = _schemas_dir()


def project_root() -> Path:
    """Return the filesystem root of the repository."""

    return REPO_ROOT


def schema_dir() -> Path:
    """Return the directory that stores JSON schema resources."""

    return SCHEMA_DIR
