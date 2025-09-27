from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.streamlit.api import APIClient
from ui.streamlit.utils import hits_to_dataframe

st.set_page_config(page_title="Aspectarian Timeline", page_icon="📈", layout="wide")
st.title("Aspectarian Timeline 📈")

api = APIClient()

# ------------------------------- Sidebar -----------------------------------
st.sidebar.header("Query")
DEFAULT_OBJECTS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
DEFAULT_ASPECTS = ["conjunction","opposition","square","trine","sextile","quincunx"]

objects: List[str] = st.sidebar.multiselect("Objects", DEFAULT_OBJECTS, default=["Sun","Moon","Mars","Venus"])
aspects: List[str] = st.sidebar.multiselect("Aspects", DEFAULT_ASPECTS, default=["sextile","trine","square"])
harmonics_str = st.sidebar.text_input("Harmonics (comma-sep)", value="5,7,13")

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start (UTC)", value=datetime.now(timezone.utc).date())
end_date = col2.date_input("End (UTC)", value=(datetime.now(timezone.utc) + timedelta(days=180)).date())

step_minutes = st.sidebar.slider("Step (minutes)", min_value=5, max_value=240, value=60, step=5)
limit = st.sidebar.slider("Limit", min_value=100, max_value=5000, value=2000, step=100)
order_by = st.sidebar.selectbox("Order by", options=["time","severity","orb"], index=0)

with st.sidebar.expander("Orb Policy (inline)", expanded=False):
    sextile = st.number_input("sextile orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
    square = st.number_input("square orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1)
    trine = st.number_input("trine orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1)
    conj = st.number_input("conjunction orb", min_value=0.1, max_value=10.0, value=8.0, step=0.1)
    quincunx = st.number_input("quincunx orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1)

harmonics: List[int] = []
if harmonics_str.strip():
    try:
        harmonics = [int(x.strip()) for x in harmonics_str.split(',') if x.strip()]
    except Exception:
        st.sidebar.error("Invalid harmonics list; use comma-separated integers.")

start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc)

payload = {
    "objects": objects,
    "aspects": aspects,
    "harmonics": harmonics,
    "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
    "step_minutes": step_minutes,
    "limit": limit,
    "offset": 0,
    "order_by": order_by,
    "orb_policy_inline": {
        "per_aspect": {
            "sextile": sextile, "square": square, "trine": trine, "conjunction": conj, "quincunx": quincunx,
        }
    },
}

# ------------------------------- Fetch -------------------------------------
colA, colB = st.columns([1,3])
with colA:
    go = st.button("Fetch & Plot", type="primary")
with colB:
    st.caption("Click legend items to filter aspects. Use the range slider to zoom.")

if go:
    with st.spinner("Querying aspects..."):
        data = api.aspects_search(payload)
    hits = data.get("hits", [])
    df = hits_to_dataframe(hits)
    df.sort_values(["pair", "exact_time"], inplace=True)

    if df.empty:
        st.info("No hits for these parameters.")
        st.stop()

    # ------------------------------ Chart ----------------------------------
    # Size by severity (fallback to small if NaN)
    df["sev_size"] = df["severity"].fillna(0.1) * 15 + 6

    fig = px.scatter(
        df,
        x="exact_time",
        y="pair",
        color="aspect",
        size="sev_size",
        hover_data={"exact_time": "|%Y-%m-%d %H:%M UTC", "orb": ".2f", "severity": ".2f", "pair": True, "aspect": True},
        title="Aspectarian Timeline",
    )
    fig.update_layout(xaxis=dict(rangeslider=dict(visible=True)))

    st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    # --------------------------- Visible Window ----------------------------
    st.subheader("Details (visible window)")
    # We can't read the plotly viewport easily without a custom component.
    # Provide manual window to filter details quickly.
    c1, c2 = st.columns(2)
    win_start = c1.datetime_input("Window start", value=df["exact_time"].min().to_pydatetime())
    win_end = c2.datetime_input("Window end", value=df["exact_time"].max().to_pydatetime())

    mask = (df["exact_time"] >= pd.to_datetime(win_start, utc=True)) & (df["exact_time"] <= pd.to_datetime(win_end, utc=True))
    vis = df.loc[mask].copy()
    vis.sort_values("exact_time", inplace=True)

    detail_cols = ["exact_time", "pair", "aspect", "orb", "severity"]
    available_detail = [c for c in detail_cols if c in vis.columns]
    st.dataframe(vis[available_detail], use_container_width=True, hide_index=True)

    # ------------------------------ Export ---------------------------------
    c3, c4 = st.columns(2)
    export_df = vis.drop(columns=["sev_size"], errors="ignore")
    export_df = export_df.sort_values("exact_time")
    with c3:
        st.download_button(
            "Download Visible CSV",
            export_df.to_csv(index=False).encode("utf-8"),
            file_name="aspectarian_visible.csv",
            mime="text/csv",
        )
    with c4:
        st.download_button(
            "Download Visible JSON",
            json.dumps(export_df.to_dict(orient="records"), default=str).encode("utf-8"),
            file_name="aspectarian_visible.json",
            mime="application/json",
        )
else:
    st.caption("Set parameters and click **Fetch & Plot** to render the timeline.")
