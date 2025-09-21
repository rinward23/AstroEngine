# >>> AUTO-GEN BEGIN: RegistryLoader v1.0
"""Lightweight registry loader that can read from either
- packaged path: `astroengine/registry/`
- repo root path: `./registry/`

This avoids a hard move of files while consolidating runtime onto `astroengine`.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

try:
    # Python ≥3.9 importlib.resources.files API
    from importlib.resources import files as _files  # type: ignore
except Exception:  # pragma: no cover
    _files = None  # type: ignore


def _candidate_dirs() -> list[Path]:
    roots: list[Path] = []
    # 1) packaged registry directory
    if _files is not None:  # pragma: no branch
        try:
            pkg_root = Path(_files(__package__))
            roots.append(pkg_root)
        except Exception:
            pass
    # 2) project root `registry/` (dev installs, editable mode)
    here = Path(__file__).resolve()
    for up in (here.parents[1], Path.cwd()):
        cand = up / "registry"
        if cand.exists():
            roots.append(cand)
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
    raise FileNotFoundError(f"Registry file not found: {name}; looked in: {', '.join(map(str, _candidate_dirs()))}")


__all__ = ["load_yaml"]
# >>> AUTO-GEN END: RegistryLoader v1.0
