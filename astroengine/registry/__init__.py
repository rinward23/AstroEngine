# >>> AUTO-GEN BEGIN: RegistryLoader v1.0
"""Lightweight registry loader that can read from either
- packaged path: `astroengine/registry/`
- repo root path: `./registry/`

This avoids a hard move of files while consolidating runtime onto `astroengine`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

try:
    # Python ≥3.9 importlib.resources.files API
    from importlib.resources import files as _files  # type: ignore
except Exception as exc:  # pragma: no cover
    LOG.debug("importlib.resources.files unavailable: %s", exc)
    _files = None  # type: ignore

from ..infrastructure.paths import registry_dir


def _candidate_dirs() -> list[Path]:
    roots: list[Path] = []
    # 1) packaged registry directory
    if _files is not None:  # pragma: no branch
        try:
            pkg_root = Path(_files(__package__))
            roots.append(pkg_root)
        except Exception as exc:
            LOG.debug("Unable to locate packaged registry via importlib: %s", exc)
    # 2) project root `registry/` (dev installs, editable mode)
    repo_registry = registry_dir()
    if repo_registry.exists():
        roots.append(repo_registry)
    cwd_registry = Path.cwd() / "registry"
    if cwd_registry.exists():
        roots.append(cwd_registry)
    # De-dup while preserving order
    seen: set[Path] = set()
    uniq: list[Path] = []
    for r in roots:
        if r not in seen:
            uniq.append(r)
            seen.add(r)
    return uniq


def load_yaml(name: str) -> Any:
    """Load a registry YAML by file name (e.g., "aspects.yaml").
    Searches packaged `astroengine/registry/` first, then `./registry/`.
    """
    if not name.lower().endswith(".yaml"):
        raise ValueError("registry files must end with .yaml")
    data = None
    last_err: Exception | None = None
    for root in _candidate_dirs():
        fp = root / name
        if fp.exists():
            try:
                import yaml  # lazy import to avoid hard dep during installs

                with fp.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                return data
            except Exception as e:  # pragma: no cover
                last_err = e
                break
    if last_err:
        raise last_err
    raise FileNotFoundError(
        f"Registry file not found: {name}; looked in: {', '.join(map(str, _candidate_dirs()))}"
    )


__all__ = ["load_yaml"]
# >>> AUTO-GEN END: RegistryLoader v1.0
