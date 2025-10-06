import streamlit as st

from ui.streamlit.api import APIClient
from ui.streamlit.doctor import render_report

st.set_page_config(page_title="System Doctor", page_icon="🩺", layout="wide")
st.title("🩺 System Doctor")

api = APIClient()

try:
    report = api.system_doctor()
except Exception as exc:  # pragma: no cover - user feedback only
    st.error(f"Unable to load diagnostics: {exc}")
    st.stop()

render_report(report)
