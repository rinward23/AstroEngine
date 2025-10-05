from __future__ import annotations

import pytest

import st_shim
from st_shim.testing.v1 import AppTest


class _DummyResponse:
    def __init__(self, payload: dict | None = None, status: int = 200) -> None:
        self._payload = payload or {}
        self.status_code = status
        self.text = "OK"
        self.ok = status == 200

    def json(self) -> dict:
        return dict(self._payload)


@pytest.mark.parametrize("script", ["ui/streamlit/narrative_mixer.py"])
def test_streamlit_ui_smoke(monkeypatch: pytest.MonkeyPatch, script: str) -> None:
    monkeypatch.setenv("ASTROENGINE_API", "http://localhost:8123")
    monkeypatch.setattr(
        "astroengine.config.list_narrative_profiles",
        lambda: {"built_in": ["profile_a", "profile_b"], "user": []},
    )

    if not hasattr(st_shim, "toggle"):
        def _fake_toggle(label: str, *, value: bool = False, key: str | None = None, **kwargs):
            return st_shim.checkbox(label, value=value, key=key, **kwargs)

        monkeypatch.setattr(st_shim, "toggle", _fake_toggle, raising=False)

    calls: list[tuple[str, str]] = []
    posted: list[dict] = []

    def fake_get(url: str, *args, **kwargs):  # noqa: ANN001 - signature matches requests
        calls.append(("GET", url))
        return _DummyResponse(
            {
                "mix": {"profiles": {"profile_a": 0.5}},
                "effective": {"tone": "neutral"},
                "available": {"built_in": ["profile_a"], "user": []},
            }
        )

    def fake_post(url: str, *args, json: dict | None = None, **kwargs):  # noqa: ANN001
        calls.append(("POST", url))
        if json is not None:
            posted.append(json)
        return _DummyResponse({"status": "ok"})

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    app = AppTest.from_file(script)
    app.run(timeout=5)
    app.button("Apply Mix").click().run(timeout=5)

    assert any(kind == "GET" for kind, _ in calls)
    assert any(kind == "POST" for kind, _ in calls)
    assert posted, "UI did not issue POST to apply the mix"
    payload = posted[-1]
    assert "profiles" in payload and "normalize" in payload
    assert app.session_state["narrative_mix_api"].startswith("http://localhost")
