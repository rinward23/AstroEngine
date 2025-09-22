"""Centralised filesystem path helpers for AstroEngine."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

__all__ = [
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
]


@dataclass(frozen=True)
class AstroPaths:
    """Resolved directory layout for the repository and installed package."""

    package_root: Path
    project_root: Path
    datasets: Path
    generated: Path
    profiles: Path
    registry: Path
    rulesets: Path
    schemas: Path

    def dataset(self, *parts: str | Path) -> Path:
        """Return a path under the ``datasets`` directory."""

        return self.datasets.joinpath(*parts)


@lru_cache(maxsize=1)
def get_paths() -> AstroPaths:
    """Return a cached :class:`AstroPaths` descriptor."""

    here = Path(__file__).resolve()
    package_root = here.parents[1]
    project_root = here.parents[2]
    return AstroPaths(
        package_root=package_root,
        project_root=project_root,
        datasets=project_root / "datasets",
        generated=project_root / "generated",
        profiles=project_root / "profiles",
        registry=project_root / "registry",
        rulesets=project_root / "rulesets",
        schemas=project_root / "schemas",
    )


def package_root() -> Path:
    """Return the root directory of the installed :mod:`astroengine` package."""

    return get_paths().package_root


def project_root() -> Path:
    """Return the repository root (editable installs) when available."""

    return get_paths().project_root


def datasets_dir() -> Path:
    """Return the repository ``datasets`` directory."""

    return get_paths().datasets


def dataset_path(*parts: str | Path) -> Path:
    """Return a path within the ``datasets`` directory."""

    return get_paths().dataset(*parts)


def generated_dir() -> Path:
    """Return the repository ``generated`` directory."""

    return get_paths().generated


def profiles_dir() -> Path:
    """Return the repository ``profiles`` directory."""

    return get_paths().profiles


def registry_dir() -> Path:
    """Return the repository ``registry`` directory."""

    return get_paths().registry


def rulesets_dir() -> Path:
    """Return the repository ``rulesets`` directory."""

    return get_paths().rulesets


def schemas_dir() -> Path:
    """Return the repository ``schemas`` directory."""

    return get_paths().schemas
