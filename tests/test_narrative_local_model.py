from __future__ import annotations

import pytest

from astroengine.narrative.local_model import (
    LocalBackendUnavailable,
    LocalNarrativeClient,
    available_backends,
    register_backend,
    unregister_backend,
)


def test_local_client_uses_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def adapter(prompt: str, *, temperature: float = 0.2, **kwargs: object) -> str:
        captured["prompt"] = prompt
        captured["temperature"] = temperature
        captured["kwargs"] = kwargs
        return "ok"

    client = LocalNarrativeClient(adapter=adapter)
    assert client.available
    result = client.summarize("hello", temperature=0.5)
    assert result == "ok"
    assert captured["prompt"] == "hello"
    assert captured["temperature"] == 0.5
    assert isinstance(captured["kwargs"], dict)


def test_local_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    def factory(options: dict[str, object]) -> callable:
        def adapter(prompt: str, *, temperature: float = 0.2, **_: object) -> str:
            return f"{prompt}|{temperature}|{options.get('scale')}"

        return adapter

    register_backend("test-backend", factory, replace=True)
    monkeypatch.setenv("ASTROENGINE_LOCAL_MODEL", "test-backend")
    monkeypatch.setenv("ASTROENGINE_LOCAL_MODEL_OPTIONS", "scale=2")
    try:
        client = LocalNarrativeClient.from_env()
        assert client.available
        assert "|0.2|2" in client.summarize("prompt")
    finally:
        unregister_backend("test-backend")
        monkeypatch.delenv("ASTROENGINE_LOCAL_MODEL", raising=False)
        monkeypatch.delenv("ASTROENGINE_LOCAL_MODEL_OPTIONS", raising=False)


def test_local_client_missing_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(LocalBackendUnavailable):
        LocalNarrativeClient(backend="missing", allow_stub=False)


def test_available_backends_updates() -> None:
    name = "temp-backend"

    def factory(_options: dict[str, object]) -> callable:
        return lambda prompt, **_: prompt

    register_backend(name, factory, replace=True)
    try:
        assert name in available_backends()
    finally:
        unregister_backend(name)

