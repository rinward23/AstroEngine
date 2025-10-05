"""Streamlit UI for the in-app developer mode workflow."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="Dev Mode", layout="wide")
API_ROOT = os.getenv("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/")

if not os.getenv("DEV_MODE"):
    st.error("Dev mode is disabled. Set DEV_MODE=1 and restart the API server.")
    st.stop()

st.title("🛠️ Dev Mode — Safe Patching")

CONFIRM_PHRASE = os.environ.get(
    "DEV_CORE_EDIT_CONFIRM", "I UNDERSTAND THIS MAY BREAK THE APP"
)

validate_tab, apply_tab, history_tab = st.tabs([
    "Validate",
    "Apply Patch",
    "History & Restore",
])


with validate_tab:
    st.subheader("Run validation pipeline")
    if st.button("Run compile/lint/tests", key="run-validation"):
        try:
            response = requests.post(f"{API_ROOT}/v1/dev/validate", timeout=180)
            response.raise_for_status()
            st.json(response.json())
        except requests.RequestException as exc:
            st.error(f"Validation request failed: {exc}")


with apply_tab:
    st.subheader("Apply unified diff")
    default_user = (
        os.getenv("USERNAME")
        or os.getenv("USER")
        or os.getenv("LOGNAME")
        or "anonymous"
    )
    user = st.text_input("Your name (for history)", value=default_user)
    message = st.text_input("Change message", value="devmode patch")
    allow_core = st.toggle(
        "Allow edits to PROTECTED core files (danger)", value=False
    )
    if allow_core:
        st.warning(
            "Editing core files can destabilise the app. Ensure you have a recent backup before proceeding."
        )
        typed_phrase = st.text_input(
            "Type the confirmation phrase to proceed",
            value="",
            placeholder=CONFIRM_PHRASE,
        )
    else:
        typed_phrase = ""
    diff_payload = st.text_area("Paste unified diff here", height=300)
    if st.button("Apply patch", type="primary", key="apply-patch"):
        payload: dict[str, Any] = {
            "diff": diff_payload,
            "message": message,
            "user": user,
            "allow_core_edits": allow_core,
        }
        if allow_core:
            payload["confirm_phrase"] = typed_phrase
        try:
            response = requests.post(
                f"{API_ROOT}/v1/dev/apply", json=payload, timeout=180
            )
            st.json(response.json())
        except requests.RequestException as exc:
            st.error(f"Apply request failed: {exc}")


with history_tab:
    st.subheader("Version history & restore")
    try:
        response = requests.get(f"{API_ROOT}/v1/dev/history", timeout=30)
        response.raise_for_status()
        history_items = response.json()
    except requests.RequestException as exc:
        st.error(f"Unable to load history: {exc}")
        history_items = []

    if not history_items:
        st.info("No history recorded yet.")
    else:
        for entry in reversed(history_items[-50:]):
            with st.container(border=True):
                st.write(
                    f"**{entry.get('message', 'devmode patch')}** — ``{entry.get('commit', '')[:7]}`` — {entry.get('user', 'unknown')}"
                )
                st.caption(
                    "Core edited: "
                    + ("Yes" if entry.get("core_edited") else "No")
                )
                touched = entry.get("touched_files") or []
                if touched:
                    st.code("\n".join(touched), language="text")
                cols = st.columns(3)
                with cols[0]:
                    if st.button(
                        "Restore this version",
                        key=f"restore-{entry.get('commit')}",
                    ):
                        try:
                            restore_resp = requests.post(
                                f"{API_ROOT}/v1/dev/restore",
                                json={"commit": entry.get("commit")},
                                timeout=60,
                            )
                            st.json(restore_resp.json())
                        except requests.RequestException as exc:
                            st.error(f"Restore failed: {exc}")
                with cols[1]:
                    st.caption("Backup snapshot")
                    st.code(entry.get("snapshot", ""), language="text")
                with cols[2]:
                    st.caption("Changelog is updated in CHANGELOG.md")
