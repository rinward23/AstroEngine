from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Event Explorer", page_icon="🗓️", layout="wide")
st.title("Event Explorer 🗓️")
api = APIClient()

DEFAULT_ASPECTS = ["conjunction","opposition","square","trine","sextile"]
DEFAULT_OTHERS = ["Sun","Mercury","Venus","Mars","Jupiter","Saturn"]

TAB1, TAB2, TAB3 = st.tabs(["VoC Moon", "Combust/Cazimi", "Returns"]) 

# --------------------------- Helpers ---------------------------------------
def _render_intervals(df: pd.DataFrame, title: str) -> None:
    """Show table + Gantt-like bars using Plotly timeline."""
    st.subheader(title)
    if df.empty:
        st.info("No intervals.")
        return
    # Normalize columns
    df = df.copy()
    df["start"] = pd.to_datetime(df["start"], utc=True)
    df["end"] = pd.to_datetime(df["end"], utc=True)
    if "kind" not in df.columns:
        df["kind"] = "interval"
    st.dataframe(df, use_container_width=True, hide_index=True)
    try:
        fig = px.timeline(df, x_start="start", x_end="end", y="kind", color="kind")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True, theme="streamlit")
    except Exception:
        st.caption("Timeline unavailable; showing table only.")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="events.csv", mime="text/csv")
    with c2:
        st.download_button("Download JSON", df.to_json(orient="records", date_format="iso").encode("utf-8"), file_name="events.json", mime="application/json")


# --------------------------- Tab 1: VoC Moon -------------------------------
with TAB1:
    st.subheader("Void‑of‑Course Moon")
    now = datetime.now(timezone.utc)
    col1, col2 = st.columns(2)
    start = col1.datetime_input("Start (UTC)", value=now)
    end = col2.datetime_input("End (UTC)", value=now + timedelta(days=3))

    aspects = st.multiselect("Aspects to consider", DEFAULT_ASPECTS, default=DEFAULT_ASPECTS)
    others_txt = st.text_input("Other bodies (comma‑sep)", value=", ".join(DEFAULT_OTHERS))
    others = [x.strip() for x in others_txt.split(',') if x.strip()]
    step = st.slider("Scan step (minutes)", 15, 180, 60, 5)

    with st.expander("Inline Orb Policy (optional)", expanded=False):
        conj = st.number_input("conjunction orb", 0.1, 10.0, 8.0, 0.1)
        opp = st.number_input("opposition orb", 0.1, 10.0, 7.0, 0.1)
        sq = st.number_input("square orb", 0.1, 10.0, 6.0, 0.1)
        tri = st.number_input("trine orb", 0.1, 10.0, 6.0, 0.1)
        sex = st.number_input("sextile orb", 0.1, 10.0, 3.0, 0.1)
        policy = {"per_aspect": {"conjunction": conj, "opposition": opp, "square": sq, "trine": tri, "sextile": sex}}

    if st.button("Detect VoC", type="primary"):
        payload = {
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "aspects": aspects,
            "other_objects": others,
            "step_minutes": int(step),
            "orb_policy_inline": policy,
        }
        try:
            data = api.voc_moon(payload)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()
        df = pd.DataFrame(data)
        # Add sign index (if provided in meta) and duration
        if not df.empty:
            df["duration_h"] = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.total_seconds() / 3600.0
            if "meta" in df.columns:
                df["sign"] = df["meta"].apply(lambda m: m.get("sign") if isinstance(m, dict) else None)
        _render_intervals(df, "VoC Intervals")

# --------------------------- Tab 2: Combust/Cazimi -------------------------
with TAB2:
    st.subheader("Combust / Cazimi / Under‑Beams")
    now = datetime.now(timezone.utc)
    col1, col2 = st.columns(2)
    start = col1.datetime_input("Start (UTC)", value=now)
    end = col2.datetime_input("End (UTC)", value=now + timedelta(days=20))
    planet = st.selectbox("Planet", ["Mercury","Venus","Mars","Jupiter","Saturn"], index=0)
    step = st.slider("Step (minutes)", 5, 120, 10, 5)

    with st.expander("Thresholds", expanded=False):
        caz = st.number_input("cazimi (deg)", 0.01, 1.0, 0.2667, 0.01)
        com = st.number_input("combust (deg)", 1.0, 20.0, 8.0, 0.1)
        ub = st.number_input("under‑beams (deg)", 5.0, 40.0, 15.0, 0.1)

    if st.button("Detect Combust/Cazimi", type="primary"):
        payload = {
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "planet": planet,
            "step_minutes": int(step),
            "cfg": {"cazimi_deg": float(caz), "combust_deg": float(com), "under_beams_deg": float(ub)},
        }
        try:
            data = api.combust_cazimi(payload)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()
        df = pd.DataFrame(data)
        _render_intervals(df, "Combust/Cazimi Intervals")

# --------------------------- Tab 3: Returns --------------------------------
with TAB3:
    st.subheader("Returns")
    now = datetime.now(timezone.utc)
    col1, col2 = st.columns(2)
    start = col1.datetime_input("Start (UTC)", value=now - timedelta(days=5))
    end = col2.datetime_input("End (UTC)", value=now + timedelta(days=400))

    body = st.text_input("Body name", value="Sun")
    target = st.number_input("Target longitude (deg)", 0.0, 360.0, 10.0, 0.1)
    step = st.slider("Step (minutes)", 60, 1440, 720, 60)

    if st.button("Find Returns", type="primary"):
        payload = {
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "body": body,
            "target_lon": float(target),
            "step_minutes": int(step),
        }
        try:
            data = api.returns(payload)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()
        df = pd.DataFrame(data)
        if not df.empty:
            df["start"] = pd.to_datetime(df["start"], utc=True)
            if "kind" not in df.columns:
                df["kind"] = "return"
            plot_df = df.copy()
            plot_df["occurrence"] = 0
            st.dataframe(df, use_container_width=True, hide_index=True)
            # Plot points along time
            fig = px.scatter(plot_df, x="start", y="occurrence", color="kind", title="Return Points")
            fig.update_yaxes(visible=False, showticklabels=False)
            st.plotly_chart(fig, use_container_width=True, theme="streamlit")
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="returns.csv", mime="text/csv")
            st.download_button("Download JSON", json.dumps(data, indent=2).encode("utf-8"), file_name="returns.json", mime="application/json")
        else:
            st.info("No returns found in the window.")
