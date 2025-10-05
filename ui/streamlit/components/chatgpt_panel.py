from __future__ import annotations

import os
from typing import Any, Dict, List

import streamlit as st

SYSTEM_PROMPT = (
    "You are AstroEngine Copilot — an astrology assistant. "
    "Be concise, accurate, and cite internal findings by referring to data returned by local endpoints when available. "
    "If the user asks about charts, techniques, or diagnostics, you may suggest hitting local endpoints like /v1/settings or /healthz if the user consents. "
    "Never fabricate data; if unsure, ask to run a local check (e.g., /healthz)."
)

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_API_BASE = os.environ.get("OPENAI_BASE_URL", None)


def _ensure_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = DEFAULT_MODEL


def _call_openai(messages: List[Dict[str, Any]], model: str, stream: bool = True):
    """Lightweight wrapper that supports both new and legacy openai clients."""
    api_key = os.environ.get("OPENAI_API_KEY") or st.session_state.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Set it in env or the field above.")

    try:
        # New SDK style
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=DEFAULT_API_BASE)
        return client.chat.completions.create(model=model, messages=messages, stream=stream)
    except Exception:
        # Legacy fallback
        import openai  # type: ignore

        openai.api_key = api_key
        if DEFAULT_API_BASE:
            openai.base_url = DEFAULT_API_BASE
        return openai.ChatCompletion.create(model=model, messages=messages, stream=stream)


def _render_stream(stream_obj):
    """Render a streaming response into the last assistant message container."""
    full = []
    for chunk in stream_obj:
        try:
            # New SDK delta
            delta = chunk.choices[0].delta.get("content")
        except Exception:
            # Legacy SDK delta
            delta = chunk["choices"][0]["delta"].get("content") if isinstance(chunk, dict) else None
        if delta:
            full.append(delta)
            yield delta
    return "".join(full)


def _do_local_action(cmd: str, base_url: str) -> str:
    import requests

    cmd = cmd.strip().lower()
    if cmd == "/health":
        url = base_url.rstrip("/") + "/healthz"
        r = requests.get(url, timeout=5)
        return f"GET {url}\nStatus: {r.status_code}\n\n{r.text[:4000]}"
    if cmd == "/settings":
        url = base_url.rstrip("/") + "/v1/settings"
        r = requests.get(url, timeout=5)
        return f"GET {url}\nStatus: {r.status_code}\n\n{r.text[:4000]}"
    if cmd == "/metrics":
        url = base_url.rstrip("/") + "/metrics"
        r = requests.get(url, timeout=5)
        return f"GET {url}\nStatus: {r.status_code}\n\n{r.text[:2000]}\n..."
    return "Unknown command. Try /health, /settings, or /metrics."


def chatgpt_panel() -> None:
    _ensure_state()

    with st.container(border=True):
        st.markdown("### 🤖 ChatGPT Copilot")
        # API key & model controls (local-only; not persisted to disk)
        with st.expander("Model & Connection", expanded=False):
            st.session_state.OPENAI_API_KEY = st.text_input(
                "OpenAI API Key",
                type="password",
                value=os.environ.get("OPENAI_API_KEY", ""),
                help="Only stored in-memory during this session.",
            )
            st.session_state.openai_model = st.text_input(
                "Model",
                value=st.session_state.openai_model,
                help="e.g., gpt-4o-mini, gpt-4.1-mini",
            )
            api_base = st.text_input("(Optional) API Base URL", value=DEFAULT_API_BASE or "")
            if api_base:
                os.environ["OPENAI_BASE_URL"] = api_base

        # Local API base for slash-commands
        api_local = st.text_input(
            "Local API Base",
            value=os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000"),
            help="Used for /health, /settings, /metrics",
        )

        # Render prior conversation
        for msg in st.session_state.chat_messages:
            if msg["role"] == "system":
                continue
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Composer
        prompt = st.chat_input(placeholder="Ask about a chart, run /health, or say hi…")
        if prompt:
            # Slash-commands (no call to OpenAI)
            if prompt.strip().startswith("/"):
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                result = _do_local_action(prompt.strip(), api_local)
                st.session_state.chat_messages.append({"role": "assistant", "content": f"````text\n{result}\n````"})
                st.rerun()

            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                # Stream tokens
                try:
                    stream = _call_openai(
                        messages=st.session_state.chat_messages,
                        model=st.session_state.openai_model,
                        stream=True,
                    )
                    placeholder = st.empty()
                    acc = ""
                    for token in _render_stream(stream):
                        acc += token
                        placeholder.markdown(acc)
                    st.session_state.chat_messages.append({"role": "assistant", "content": acc})
                except Exception as e:
                    st.warning(f"Chat error: {e}")
