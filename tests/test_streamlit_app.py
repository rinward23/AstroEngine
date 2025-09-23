"""Tests for the Streamlit transit scanner app using the local stub."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_STUB_SPEC = spec_from_file_location(
    "astroengine_streamlit_stub",
    Path(__file__).resolve().parents[1] / "streamlit" / "testing" / "v1" / "__init__.py",
)
assert _STUB_SPEC is not None and _STUB_SPEC.loader is not None
_STUB_MODULE = module_from_spec(_STUB_SPEC)
sys.modules.setdefault(_STUB_SPEC.name, _STUB_MODULE)
_STUB_SPEC.loader.exec_module(_STUB_MODULE)

AppTest = _STUB_MODULE.AppTest


def test_streamlit_scan_caches_results(monkeypatch):
    monkeypatch.setenv("ASTROENGINE_SCAN_ENTRYPOINTS", "tests.fixtures.stub_scan:fake_scan")

    app = AppTest.from_file("apps/streamlit_transit_scanner.py")
    app.run(timeout=5)

    detectors = app.sidebar.multiselect("Detectors")
    assert "lunations" in detectors.options

    app.button("Run scan").click().run(timeout=5)
    assert app.session_state["scan_last_cache_hit"] is False

    app.button("Run scan").click().run(timeout=5)
    assert app.session_state["scan_last_cache_hit"] is True
