from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
import types
import warnings
from pathlib import Path

import pytest

if importlib.util.find_spec("swisseph") is None:
    warnings.warn(
        "pyswisseph not installed; Swiss-marked tests will be skipped.",
        RuntimeWarning,
        stacklevel=1,
    )

import st_shim as _st_shim


def _flag_enabled(name: str) -> bool:
    """Return True when the boolean-like environment flag is enabled."""

    value = os.getenv(name)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}

# >>> AUTO-GEN BEGIN: AliasGeneratedToAstroengine v1.0
"""Pytest compatibility shim: route any `generated.*` imports to `astroengine`.
Idempotent and safe to keep during the deprecation window.
"""

LOG = logging.getLogger(__name__)

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
except Exception as exc:
    # If astroengine is not importable here, let pytest show the normal error later.
    LOG.debug("Deferred astroengine import during test shim setup: %s", exc)

# Provide compatibility alias for the legacy ``streamlit`` shim used in tests.
_disable_shim = os.getenv("ASTROENGINE_DISABLE_STREAMLIT_SHIM", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

if _disable_shim:
    try:
        import streamlit as _streamlit_module  # type: ignore
    except ModuleNotFoundError:
        sys.modules.setdefault("streamlit", _st_shim)
    else:
        sys.modules.setdefault("streamlit", _streamlit_module)
else:
    sys.modules.setdefault("streamlit", _st_shim)
# >>> AUTO-GEN END: AliasGeneratedToAstroengine v1.0

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT_STR = str(PROJECT_ROOT)
GENERATED_ROOT = PROJECT_ROOT / "generated"
GENERATED_STR = str(GENERATED_ROOT)
DATASETS_ROOT = PROJECT_ROOT / "datasets"

_HTTP_TEST_FILES = {
    (PROJECT_ROOT / rel).resolve()
    for rel in (
        Path("tests/test_api_aspects_search.py"),
        Path("tests/test_api_electional.py"),
        Path("tests/test_api_events.py"),
        Path("tests/test_api_interpret.py"),
        Path("tests/test_api_lots.py"),
        Path("tests/test_api_policies.py"),
        Path("tests/test_api_relationship.py"),
        Path("tests/test_api_score_series.py"),
        Path("tests/test_api_synastry_composites.py"),
        Path("tests/test_openapi_examples.py"),
        Path("tests/test_relationship_api.py"),
        Path("tests/test_report_relationship_export.py"),
        Path("tests/e2e/test_end_to_end.py"),
    )
}

_HTTP_TEST_DIRS = {
    (PROJECT_ROOT / rel).resolve() for rel in (Path("tests/api"),)
}

_PLUGIN_TEST_FILES = {
    (PROJECT_ROOT / rel).resolve() for rel in (Path("tests/test_entrypoints.py"),)
}


def _refresh_paths_from_package() -> None:
    try:
        from astroengine.infrastructure.paths import datasets_dir, generated_dir
        from astroengine.infrastructure.paths import project_root as pkg_project_root
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
    except ImportError as exc:
        LOG.debug("Deferred astroengine import during repo package setup: %s", exc)
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
    """Apply dynamic skips for optional integrations during collection."""

    swiss_missing = not _have_pyswisseph() or not _have_ephe_path()
    http_disabled = not _flag_enabled("ASTROENGINE_ENABLE_HTTP_TESTS")
    plugin_disabled = not _flag_enabled("ASTROENGINE_ENABLE_PLUGIN_TESTS")

    skip_swiss = None
    skip_http = None
    skip_plugin = None

    if swiss_missing:
        skip_swiss = pytest.mark.skip(
            reason="Swiss Ephemeris unavailable (no pyswisseph or SE_EPHE_PATH)."
        )

    if http_disabled:
        skip_http = pytest.mark.skip(reason="HTTP API checks disabled during development.")

    if plugin_disabled:
        skip_plugin = pytest.mark.skip(
            reason="Plugin discovery checks disabled during development."
        )

    if not any((skip_swiss, skip_http, skip_plugin)):
        return

    for item in items:
        item_path = None

        if skip_swiss and "swiss" in item.keywords:
            item.add_marker(skip_swiss)

        if skip_http or skip_plugin:
            item_path = Path(str(item.fspath)).resolve()

        if skip_http and (
            item_path in _HTTP_TEST_FILES
            or any(parent in _HTTP_TEST_DIRS for parent in item_path.parents)
        ):
            item.add_marker(skip_http)

        if skip_plugin and item_path in _PLUGIN_TEST_FILES:
            item.add_marker(skip_plugin)


# >>> AUTO-GEN END: swiss availability gating v1.0


@pytest.fixture(autouse=True)
def _restore_repo_package(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("no_repo_package"):
        yield
        return

    _ensure_repo_package()
    yield
    _ensure_repo_package()


@pytest.fixture(scope="session")
def swiss_ephemeris() -> "types.ModuleType":
    """Return the Swiss Ephemeris module when available.

    Tests that depend on precise Swiss data can request this fixture rather than
    importing :mod:`swisseph` directly.  The fixture honours the same gating
    checks used by the ``swiss`` marker so that collection skips occur
    consistently when either the Python bindings or the ephemeris files are
    missing.
    """

    if not (_have_pyswisseph() and _have_ephe_path()):
        pytest.skip("Swiss Ephemeris unavailable (missing pyswisseph or SE_EPHE_PATH).")

    from astroengine.ephemeris.swe import swe as swe_proxy

    return swe_proxy()
