from __future__ import annotations

import importlib
import os
import sys
import types
import warnings
from pathlib import Path

# >>> AUTO-GEN BEGIN: AliasGeneratedToAstroengine v1.0
"""Pytest compatibility shim: route any `generated.*` imports to `astroengine`.
Idempotent and safe to keep during the deprecation window.
"""

if "generated" not in sys.modules:
    warnings.warn(
        "Tests importing 'generated' are deprecated; using 'astroengine' instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    gen = types.ModuleType("generated")
    sys.modules["generated"] = gen

# Always ensure the submodule alias exists
try:
    import astroengine as _ae  # noqa: F401

    sys.modules.setdefault("generated.astroengine", _ae)
except Exception:
    # If astroengine is not importable here, let pytest show the normal error later.
    pass
# >>> AUTO-GEN END: AliasGeneratedToAstroengine v1.0

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
GENERATED_ROOT = PROJECT_ROOT / "generated"
GENERATED_STR = str(GENERATED_ROOT)
DATASETS_ROOT = PROJECT_ROOT / "datasets"


def _refresh_paths_from_package() -> None:
    try:
        from astroengine.infrastructure.paths import (
            datasets_dir,
            generated_dir,
            project_root as pkg_project_root,
        )
    except Exception:
        return

    global PROJECT_ROOT, PROJECT_ROOT_STR, GENERATED_ROOT, GENERATED_STR, DATASETS_ROOT
    PROJECT_ROOT = pkg_project_root()
    PROJECT_ROOT_STR = str(PROJECT_ROOT)
    GENERATED_ROOT = generated_dir()
    GENERATED_STR = str(GENERATED_ROOT)
    DATASETS_ROOT = datasets_dir()


def _ensure_repo_package() -> None:
    while PROJECT_ROOT_STR in sys.path:
        sys.path.remove(PROJECT_ROOT_STR)
    sys.path.insert(0, PROJECT_ROOT_STR)
    for candidate in (GENERATED_STR, "generated"):
        while candidate in sys.path:
            sys.path.remove(candidate)
        sys.path.append(candidate)

    module = sys.modules.get("astroengine")
    if module is not None:
        module_file = getattr(module, "__file__", "") or ""
        if module_file and str(GENERATED_ROOT) in module_file:
            for key in list(sys.modules):
                if key == "astroengine" or key.startswith("astroengine."):
                    sys.modules.pop(key, None)
            module = None
    if module is None:
        importlib.invalidate_caches()
    try:
        module = importlib.import_module("astroengine")
    except ModuleNotFoundError:
        return
    module_file = getattr(module, "__file__", "") or ""
    if module_file and str(GENERATED_ROOT) in module_file:
        for key in list(sys.modules):
            if key == "astroengine" or key.startswith("astroengine."):
                sys.modules.pop(key, None)
        importlib.invalidate_caches()
        importlib.import_module("astroengine")

    _refresh_paths_from_package()


_ensure_repo_package()


def _ensure_swiss_stub() -> None:
    if os.getenv("SE_EPHE_PATH"):
        return
    stub = DATASETS_ROOT / "swisseph_stub"
    if stub.is_dir():
        os.environ.setdefault("SE_EPHE_PATH", str(stub))


_ensure_swiss_stub()

# >>> AUTO-GEN BEGIN: swiss availability gating v1.0
import pytest


def _have_pyswisseph() -> bool:
    try:
        import swisseph as _swe  # noqa: F401
        return True
    except Exception:
        return False


def _have_ephe_path() -> bool:
    p = os.getenv("SE_EPHE_PATH")
    return bool(p and os.path.isdir(p))


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked 'swiss' unless pyswisseph + ephemeris path are available."""
    swiss_missing = not _have_pyswisseph() or not _have_ephe_path()
    if not swiss_missing:
        return
    skip_swiss = pytest.mark.skip(reason="Swiss Ephemeris unavailable (no pyswisseph or SE_EPHE_PATH).")
    for item in items:
        if "swiss" in item.keywords:
            item.add_marker(skip_swiss)
# >>> AUTO-GEN END: swiss availability gating v1.0


@pytest.fixture(autouse=True)
def _restore_repo_package() -> None:
    _ensure_repo_package()
    yield
    _ensure_repo_package()
