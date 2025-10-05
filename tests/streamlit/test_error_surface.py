from __future__ import annotations

import logging

import pytest

import streamlit as st
import ui.streamlit  # noqa: F401 - trigger error instrumentation on import


@pytest.mark.usefixtures("caplog")
def test_streamlit_error_emits_toast_and_logs(monkeypatch, caplog):
    recorded: dict[str, list[str] | str] = {}

    class _ToastRecorder:
        def __init__(self, message: str, icon: str | None) -> None:
            recorded["message"] = message
            recorded["icon"] = icon or ""
            recorded.setdefault("captions", [])
            recorded.setdefault("codes", [])

        def caption(self, text: str) -> None:
            assert isinstance(recorded.get("captions"), list)
            recorded["captions"].append(text)

        def code(self, text: str, *, language: str | None = None) -> None:  # noqa: ARG002 - API parity
            assert isinstance(recorded.get("codes"), list)
            recorded["codes"].append(text)

    def fake_toast(message: str, *, icon: str | None = None) -> _ToastRecorder:
        return _ToastRecorder(message, icon)

    monkeypatch.setattr(st, "toast", fake_toast)
    caplog.set_level(logging.ERROR)

    result = st.error("Boom")

    assert "message" in recorded and recorded["message"] == "Boom"
    assert recorded.get("icon") == "⚠️"
    assert recorded.get("captions") == ["Error ID (click to copy):"]
    assert len(recorded.get("codes", [])) == 1

    record = caplog.records[-1]
    assert hasattr(record, "error_id")
    error_id = getattr(record, "error_id")
    assert isinstance(error_id, str)
    assert len(error_id) == 12
    assert error_id.isupper()
    assert error_id == recorded["codes"][0]
    assert record.message == f"Error {error_id}: Boom"

    if result is not None:
        assert getattr(result, "error_id", error_id) == error_id
