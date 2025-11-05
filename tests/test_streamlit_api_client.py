from __future__ import annotations

import sys
import types

import pytest

try:
    import requests  # type: ignore[assignment]
except ModuleNotFoundError:  # pragma: no cover - test shim for minimal envs
    requests = types.ModuleType("requests")

    class Response:  # type: ignore[too-many-ancestors]
        pass

    class RequestException(Exception):
        pass

    class HTTPError(RequestException):
        def __init__(self, message: str = "", response: Response | None = None) -> None:
            super().__init__(message)
            self.response = response

    def _unconfigured(*_args: object, **_kwargs: object) -> None:
        raise NotImplementedError("requests stub invoked")

    requests.Response = Response  # type: ignore[attr-defined]
    requests.RequestException = RequestException  # type: ignore[attr-defined]
    requests.HTTPError = HTTPError  # type: ignore[attr-defined]
    requests.get = _unconfigured  # type: ignore[attr-defined]
    requests.post = _unconfigured  # type: ignore[attr-defined]
    requests.put = _unconfigured  # type: ignore[attr-defined]
    sys.modules["requests"] = requests

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


def test_list_natals_supports_paging(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, params=None, timeout: int | None = None):  # type: ignore[override]
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse(json_data={"items": ["natal-a"]})

    monkeypatch.setattr("ui.streamlit.api.requests.get", fake_get)

    client = APIClient(base_url="http://astro.test")
    payload = client.list_natals(page=2, page_size=50)

    assert payload == {"items": ["natal-a"]}
    assert captured["url"] == "http://astro.test/v1/natals"
    assert captured["params"] == {"page": 2, "page_size": 50}
    assert captured["timeout"] == 30
