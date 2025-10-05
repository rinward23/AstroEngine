import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="System Doctor", page_icon="🩺", layout="wide")
st.title("🩺 System Doctor")

api = APIClient()

try:
    report = api.system_doctor()
except Exception as exc:  # pragma: no cover - user feedback only
    st.error(f"Unable to load diagnostics: {exc}")
    st.stop()

status_icon = {"ok": "✅", "warn": "⚠️", "error": "❌"}
overall_status = str(report.get("status", "warn"))
generated_at = report.get("generated_at")

info_cols = st.columns(2)
with info_cols[0]:
    st.metric("Overall Status", overall_status.upper(), help="Aggregated worst status across checks.")
with info_cols[1]:
    if generated_at:
        st.metric("Generated", generated_at)
    else:  # pragma: no cover - optional metadata
        st.metric("Generated", "n/a")

checks = report.get("checks", {})
if not isinstance(checks, dict):  # pragma: no cover - defensive
    st.warning("Doctor report did not include detailed checks.")
    st.stop()

for name in sorted(checks):
    payload = checks.get(name)
    if not isinstance(payload, dict):  # pragma: no cover - defensive
        continue
    status = str(payload.get("status", "warn"))
    icon = status_icon.get(status, "❔")
    detail = payload.get("detail", "")
    header = f"{icon} {name.replace('_', ' ').title()}"
    expanded = status != "ok"
    with st.expander(header, expanded=expanded):
        if detail:
            st.write(detail)
        data = payload.get("data")
        if isinstance(data, dict) and data:
            st.json(data)
        elif data:
            st.write(data)

st.caption("Results derive from live Swiss Ephemeris, database, migration, and cache checks.")
