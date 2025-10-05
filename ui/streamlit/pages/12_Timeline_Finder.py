from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Sequence

import pandas as pd
import streamlit as st

from astroengine.config import default_settings, load_settings
from astroengine.export.ics import to_ics
from ui.streamlit.api import APIClient

st.set_page_config(page_title="Timeline Finder", page_icon="🗓️", layout="wide")
st.title("Timeline Finder 🗓️")

try:
    SETTINGS = load_settings()
except Exception:  # pragma: no cover - streamlit runtime fallback
    SETTINGS = default_settings()

if not getattr(SETTINGS, "timeline_ui", True):
    st.warning("Timeline UI is disabled in the current configuration.")
    st.stop()

api = APIClient()

st.sidebar.header("Timeline Window")
now = datetime.now(UTC)
def_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
def_end = def_start + timedelta(days=30)
start_dt = st.sidebar.datetime_input("Start (UTC)", value=def_start, step=timedelta(hours=1))
end_dt = st.sidebar.datetime_input("End (UTC)", value=def_end, step=timedelta(hours=1))

if end_dt <= start_dt:
    st.sidebar.error("End must be after start.")

type_labels = {
    "Lunations": "lunations",
    "Eclipses": "eclipses",
    "Stations": "stations",
    "Void-of-course Moon": "void_of_course",
}
selected_types = st.sidebar.multiselect(
    "Event Types",
    list(type_labels.keys()),
    default=["Lunations", "Eclipses", "Stations"],
)
requested_types = [type_labels[label] for label in selected_types] or list(type_labels.values())

station_default = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
station_bodies: Sequence[str] = st.sidebar.multiselect(
    "Station Bodies",
    [
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    ],
    default=station_default,
)

sign_orb = st.sidebar.slider("Void-of-course sign orb (°)", 0.0, 5.0, 0.0, 0.5)

with st.sidebar.expander("Options", expanded=False):
    st.caption("Adjust filters and click **Fetch Timeline** to query the API.")

trigger = st.button("Fetch Timeline", type="primary")

if trigger:
    if end_dt <= start_dt:
        st.stop()

    with st.spinner("Fetching timeline events..."):
        payload = api.timeline(
            start_dt.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            end_dt.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            types=requested_types,
            bodies=station_bodies,
            sign_orb=sign_orb,
        )
    events = payload.get("events", [])
    if not events:
        st.info("No timeline events for the selected parameters.")
        st.stop()

    df = pd.DataFrame(events)
    if "ts" in df:
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
    if "end_ts" in df:
        df["end_ts"] = pd.to_datetime(df["end_ts"], utc=True, errors="coerce")
    df.sort_values("ts", inplace=True)

    st.subheader("Timeline Events")
    display_cols = [col for col in ["type", "summary", "ts", "end_ts"] if col in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    st.subheader("Event Details")
    detail_df = df.copy()
    if "details" in detail_df:
        detail_df["details"] = detail_df["details"].apply(
            lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        )
    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    def _timeline_events_to_ics(raw_events: Sequence[dict[str, object]]) -> bytes:
        calendar_events = []
        for idx, event in enumerate(raw_events):
            start_iso = str(event.get("ts"))
            end_iso = str(event.get("end_ts") or event.get("ts"))
            calendar_events.append(
                {
                    "uid": f"timeline-{idx}-{start_iso}",
                    "kind": str(event.get("type", "event")),
                    "summary": str(event.get("summary", "Timeline Event")),
                    "start": start_iso,
                    "end": end_iso,
                    "description": json.dumps(event.get("details", {}), ensure_ascii=False, sort_keys=True),
                    "meta": event,
                }
            )
        return to_ics(calendar_events, calendar_name="AstroEngine Timeline")

    ics_bytes = _timeline_events_to_ics(events)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download CSV",
            csv_bytes,
            file_name="timeline_events.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            "Download ICS",
            ics_bytes,
            file_name="timeline_events.ics",
            mime="text/calendar",
        )
else:
    st.caption("Configure filters and click **Fetch Timeline** to populate the results.")
