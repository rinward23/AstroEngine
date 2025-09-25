from streamlit.testing.v1 import AppTest


def test_streamlit_scan_caches_results(monkeypatch):
    monkeypatch.setenv(
        "ASTROENGINE_SCAN_ENTRYPOINTS", "tests.fixtures.stub_scan:fake_scan"
    )

    app = AppTest.from_file("apps/streamlit_transit_scanner.py")
    app.run(timeout=5)

    detectors = app.sidebar.multiselect("Detectors")
    assert "lunations" in detectors.options

    app.button("Run scan").click().run(timeout=5)
    assert app.session_state["scan_last_cache_hit"] is False

    app.button("Run scan").click().run(timeout=5)
    assert app.session_state["scan_last_cache_hit"] is True
