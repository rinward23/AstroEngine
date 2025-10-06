"""Streamlit UI for the in-app developer mode workflow."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="Dev Mode", layout="wide")
API_ROOT = os.getenv("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_PIN = os.getenv("DEV_PIN", "")

pin_value = st.sidebar.text_input(
    "Developer PIN",
    value=DEFAULT_PIN,
    type="password",
    help="Required to access protected developer APIs.",
)


def request_with_pin(method: str, url: str, **kwargs):
    """Issue a request with the PIN header when provided."""

    headers = kwargs.pop("headers", {}) or {}
    if pin_value:
        headers = {**headers, "X-Dev-Pin": pin_value}
    return requests.request(method=method, url=url, headers=headers, **kwargs)

if not os.getenv("DEV_MODE"):
    st.error("Dev mode is disabled. Set DEV_MODE=1 and restart the API server.")
    st.stop()

st.title("🛠️ Dev Mode — Safe Patching")

CONFIRM_PHRASE = os.environ.get(
    "DEV_CORE_EDIT_CONFIRM", "I UNDERSTAND THIS MAY BREAK THE APP"
)

validate_tab, apply_tab, history_tab, backups_tab = st.tabs([
    "Validate",
    "Apply Patch",
    "History & Restore",
    "Backups & Retention",
])


with validate_tab:
    st.subheader("Run validation pipeline")
    if st.button("Run compile/lint/tests", key="run-validation"):
        try:
            response = request_with_pin(
                "post", f"{API_ROOT}/v1/dev/validate", timeout=180
            )
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
            response = request_with_pin(
                "post", f"{API_ROOT}/v1/dev/apply", json=payload, timeout=180
            )
            st.json(response.json())
        except requests.RequestException as exc:
            st.error(f"Apply request failed: {exc}")


with history_tab:
    st.subheader("Version history & restore")
    try:
        response = request_with_pin(
            "get", f"{API_ROOT}/v1/dev/history", timeout=30
        )
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
                            restore_resp = request_with_pin(
                                "post",
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


with backups_tab:
    st.subheader("Scheduled backups")
    try:
        data = request_with_pin("get", f"{API_ROOT}/v1/dev/backups", timeout=30)
        data.raise_for_status()
        backup_data = data.json()
    except requests.RequestException as exc:
        st.error(f"Unable to load backup status: {exc}")
        backup_data = {}

    schedule_info = backup_data.get("schedule") or {}
    backup_items = backup_data.get("backups") or []
    retention_policy = backup_data.get("retention_policy") or {}
    retention_preview = backup_data.get("retention_preview") or {}

    cols = st.columns(2)
    with cols[0]:
        if schedule_info:
            st.metric(
                "Next run",
                schedule_info.get("next_run_iso") or "unscheduled",
                delta=f"Last: {schedule_info.get('last_run_iso', 'never')}",
            )
            st.caption(f"Job state: {schedule_info.get('job_state', 'n/a')}")
        else:
            st.info("No automated backup schedule configured.")
    with cols[1]:
        if st.button("Create backup now", key="run-backup-now"):
            try:
                resp = request_with_pin(
                    "post", f"{API_ROOT}/v1/dev/backups/run", timeout=120
                )
                resp.raise_for_status()
                st.success(resp.json())
            except requests.RequestException as exc:
                st.error(f"Backup request failed: {exc}")

    with st.form("schedule-backups-form"):
        st.write("Update backup cadence")
        interval_default = float(schedule_info.get("interval_seconds", 86400)) / 3600.0
        interval_hours = st.number_input(
            "Run every (hours)",
            min_value=0.0,
            value=max(interval_default, 0.0),
            step=1.0,
        )
        start_in = st.number_input(
            "Delay first run (hours)",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )
        submitted = st.form_submit_button("Save schedule")
        if submitted:
            payload: dict[str, float] = {"interval_hours": float(interval_hours)}
            if start_in > 0:
                payload["start_in_hours"] = float(start_in)
            try:
                resp = request_with_pin(
                    "post",
                    f"{API_ROOT}/v1/dev/backups/schedule",
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                st.success(resp.json())
            except requests.RequestException as exc:
                st.error(f"Unable to update schedule: {exc}")

    if st.button("Cancel scheduled backups", key="cancel-backup-schedule"):
        try:
            resp = request_with_pin(
                "delete", f"{API_ROOT}/v1/dev/backups/schedule", timeout=30
            )
            resp.raise_for_status()
            st.warning(resp.json())
        except requests.RequestException as exc:
            st.error(f"Failed to cancel schedule: {exc}")

    st.markdown("---")
    st.subheader("Backup archives")
    if not backup_items:
        st.info("No backups recorded yet.")
    else:
        for item in backup_items:
            with st.container(border=True):
                st.write(f"**{item.get('name', 'backup')}** — {item.get('modified_iso', 'unknown')}")
                st.caption(f"Size: {item.get('size', 0)} bytes")
                path = item.get("path")
                if path:
                    if st.button("Restore from this ZIP", key=f"restore-zip-{path}"):
                        try:
                            resp = request_with_pin(
                                "post",
                                f"{API_ROOT}/v1/dev/backups/restore",
                                json={"archive_path": path},
                                timeout=120,
                            )
                            resp.raise_for_status()
                            st.success(resp.json())
                        except requests.RequestException as exc:
                            st.error(f"Restore failed: {exc}")

    st.markdown("---")
    st.subheader("Retention policy")
    retention_days = int(retention_policy.get("temporary_derivatives_days", 7) or 0)
    st.caption(
        "Temporary derivatives include ad-hoc transit runs and cached exports stored under"
        " the AstroEngine home directory."
    )
    with st.form("retention-policy-form"):
        new_days = st.number_input(
            "Keep temporary derivatives for N days", min_value=0, value=retention_days, step=1
        )
        run_purge = st.checkbox("Purge old derivatives immediately", value=True)
        submitted = st.form_submit_button("Update retention policy")
        if submitted:
            payload = {"temporary_derivatives_days": int(new_days), "run_purge": run_purge}
            try:
                resp = request_with_pin(
                    "post",
                    f"{API_ROOT}/v1/dev/retention",
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                st.success(resp.json())
            except requests.RequestException as exc:
                st.error(f"Unable to update retention policy: {exc}")

    if retention_preview:
        st.caption(
            "Preview: "
            + f"{retention_preview.get('eligible', 0)} files older than cutoff "
            + f"{retention_preview.get('cutoff')} (dry-run)."
        )
