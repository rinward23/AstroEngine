from __future__ import annotations

import pytest
import requests

from ui.streamlit.api import APIClient


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"",
        json_data: object | None = None,
        text: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.content = content
        self._json_data = json_data
        if text is not None:
            self.text = text
        elif isinstance(content, bytes):
            self.text = content.decode("utf-8", errors="ignore")
        else:
            self.text = str(content)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)

    def json(self) -> object:
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data


def test_export_bundle_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, params=None, timeout: int | None = None):  # type: ignore[override]
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse(content=b"zip-bytes")

    monkeypatch.setattr("ui.streamlit.api.requests.get", fake_get)

    client = APIClient(base_url="http://astro.test")
    payload = client.export_bundle()

    assert payload == b"zip-bytes"
    assert captured["url"] == "http://astro.test/v1/export"
    assert captured["timeout"] == 60
    assert captured["params"] == {"scope": "charts,settings"}


def test_export_bundle_custom_scope(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, params=None, timeout: int | None = None):  # type: ignore[override]
        captured["params"] = params
        return DummyResponse(content=b"zip-bytes")

    monkeypatch.setattr("ui.streamlit.api.requests.get", fake_get)

    client = APIClient(base_url="http://astro.test")
    client.export_bundle(["charts", " settings "])

    assert captured["params"] == {"scope": "charts,settings"}


def test_export_bundle_http_error(monkeypatch) -> None:
    def fake_get(url: str, params=None, timeout: int | None = None):  # type: ignore[override]
        assert params == {"scope": "charts"}
        return DummyResponse(status_code=500, json_data={"detail": "failure"})

    monkeypatch.setattr("ui.streamlit.api.requests.get", fake_get)

    client = APIClient(base_url="http://astro.test")

    with pytest.raises(RuntimeError) as excinfo:
        client.export_bundle(["charts"])

    assert "failure" in str(excinfo.value)
