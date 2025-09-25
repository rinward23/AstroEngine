"""Infrastructure helpers (environment diagnostics, git utilities, etc.)."""

from __future__ import annotations

from .environment import EnvironmentReport, collect_environment_report
from .environment import main as environment_main
from .git_access import GitAuth, GitRepository
from .paths import (
    AstroPaths,
    dataset_path,
    datasets_dir,
    generated_dir,
    get_paths,
    package_root,
    profiles_dir,
    project_root,
    registry_dir,
    rulesets_dir,
    schemas_dir,
)
from .storage import (
    SQLiteMigrator,
    downgrade_sqlite,
    ensure_sqlite_schema,
    get_sqlite_config,
    upgrade_sqlite,
)

__all__ = [
    "EnvironmentReport",
    "collect_environment_report",
    "environment_main",
    "GitAuth",
    "GitRepository",
    "AstroPaths",
    "get_paths",
    "package_root",
    "project_root",
    "datasets_dir",
    "dataset_path",
    "generated_dir",
    "profiles_dir",
    "registry_dir",
    "rulesets_dir",
    "schemas_dir",
    "SQLiteMigrator",
    "ensure_sqlite_schema",
    "upgrade_sqlite",
    "downgrade_sqlite",
    "get_sqlite_config",
]
