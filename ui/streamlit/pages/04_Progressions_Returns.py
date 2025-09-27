from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.charts_plus.progressions import (
    secondary_progressed_datetime,
    secondary_progressed_positions,
    solar_arc_positions,
)
from core.charts_plus.returns import find_next_return, find_returns_in_window, ReturnWindow

# ---------------------------------------------------------------------------
# Demo provider — linear ecliptic motion in deg/day
# ---------------------------------------------------------------------------
@dataclass
class LinearEphemeris:
    """Minimal linear ephemeris for demos and verification."""

    t0: datetime
    base: Dict[str, float]
    rates: Dict[str, float]

    def __call__(self, ts: datetime) -> Dict[str, float]:
        dt_days = (ts - self.t0).total_seconds() / 86400.0
        return {
            k: (self.base.get(k, 0.0) + self.rates.get(k, 0.0) * dt_days) % 360.0
            for k in self.base
        }

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Progressions & Returns", page_icon="🌀", layout="wide")
st.title("Progressions & Returns 🌀")

st.caption("This page uses the pure-Python engines (no external ephemeris required) with a configurable linear demo provider. Swap in your real provider later.")

# ------------------------------ Provider config -----------------------------
st.sidebar.header("Ephemeris (demo)")
now = datetime.now(timezone.utc)

default_base = {
    "Sun": 10.0,
    "Moon": 50.0,
    "Mercury": 20.0,
    "Venus": 30.0,
    "Mars": 40.0,
    "Jupiter": 80.0,
    "Saturn": 120.0,
    "Uranus": 200.0,
    "Neptune": 300.0,
    "Pluto": 280.0,
}

# Reasonable demo rates (deg/day)
default_rates = {
    "Sun": 0.9856,
    "Moon": 13.0,
    "Mercury": 1.2,
    "Venus": 1.2,
    "Mars": 0.5,
    "Jupiter": 0.083,
    "Saturn": 0.033,
    "Uranus": 0.0117,
    "Neptune": 0.006,
    "Pluto": 0.004,
}

# Basic toggles
colP1, colP2 = st.sidebar.columns(2)
start_year = colP1.number_input("Provider epoch year", min_value=1900, max_value=2100, value=now.year)
start_month = colP2.number_input("Epoch month", min_value=1, max_value=12, value=now.month)
start_day = st.sidebar.number_input("Epoch day", min_value=1, max_value=31, value=now.day)

# Allow small adjustments to a couple rates for experimentation
st.sidebar.markdown("**Adjust demo rates (deg/day)**")
adj_sun = st.sidebar.slider("Sun", 0.1, 1.5, float(default_rates["Sun"]), 0.005)
adj_moon = st.sidebar.slider("Moon", 5.0, 15.0, float(default_rates["Moon"]), 0.1)
adj_mer = st.sidebar.slider("Mercury", 0.2, 2.0, float(default_rates["Mercury"]), 0.05)

rates = dict(default_rates)
rates.update({"Sun": adj_sun, "Moon": adj_moon, "Mercury": adj_mer})

provider = LinearEphemeris(
    t0=datetime(int(start_year), int(start_month), int(start_day), tzinfo=timezone.utc),
    base=default_base,
    rates=rates,
)

# Common controls
ALL_OBJECTS = list(default_base.keys())
sel_objects: List[str] = st.multiselect("Objects", ALL_OBJECTS, default=["Sun","Moon","Mercury","Venus","Mars"])  # shared between tabs

# ============================== Tabs =======================================
TAB1, TAB2 = st.tabs(["Progressions", "Returns"])

# ---------------------------------------------------------------------------
# Tab 1 — Progressions
# ---------------------------------------------------------------------------
with TAB1:
    st.subheader("Progressions")
    col1, col2, col3 = st.columns(3)

    natal_dt = col1.datetime_input("Natal datetime (UTC)", value=datetime(now.year-30, 6, 1, 12, 0, tzinfo=timezone.utc))
    target_dt = col2.datetime_input("Target datetime (UTC)", value=now)
    mode = col3.selectbox("Mode", ["Secondary", "Solar Arc"], index=0)

    compute_progressions = st.button("Compute Progressions", type="primary")

    if compute_progressions:
        if mode == "Secondary":
            prog_dt, pos = secondary_progressed_positions(sel_objects, natal_dt, target_dt, provider)
            st.write(f"**Progressed datetime (secondary)**: `{prog_dt.isoformat()}`")
        else:
            prog_dt = secondary_progressed_datetime(natal_dt, target_dt)
            arc, pos = solar_arc_positions(sel_objects, natal_dt, target_dt, provider)
            st.write(f"**Solar Arc** added to natal: `{arc:.4f}°`")
            st.write(f"**Secondary progressed datetime**: `{prog_dt.isoformat()}`")

        df = pd.DataFrame({"object": list(pos.keys()), "longitude": [pos[k] for k in pos.keys()]})
        st.dataframe(df.sort_values("object"), use_container_width=True, hide_index=True)

        # Simple polar plot of ecliptic longitudes
        with st.expander("Polar plot", expanded=True):
            if not df.empty:
                theta = df["longitude"].values
                r = np.ones_like(theta)
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(theta=theta, r=r, mode="markers+text", text=df["object"], textposition="top center"))
                fig.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)

        # Export
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="progressions.csv", mime="text/csv")
        with c2:
            payload = {
                "mode": mode,
                "natal_dt": natal_dt.isoformat(),
                "target_dt": target_dt.isoformat(),
                "progressed_dt": prog_dt.isoformat(),
                "positions": pos,
            }
            if mode == "Solar Arc":
                payload["solar_arc_deg"] = arc
            st.download_button(
                "Download JSON",
                json.dumps(payload, indent=2).encode("utf-8"),
                file_name="progressions.json",
                mime="application/json",
            )

# ---------------------------------------------------------------------------
# Tab 2 — Returns
# ---------------------------------------------------------------------------
with TAB2:
    st.subheader("Returns")
    col1, col2, col3 = st.columns(3)
    body = col1.selectbox("Body", ALL_OBJECTS, index=ALL_OBJECTS.index("Sun"))
    natal_lon = col2.number_input("Natal longitude (deg)", min_value=0.0, max_value=360.0, value=default_base.get(body, 0.0), step=0.1)
    mode = col3.selectbox("Mode", ["Next after date", "All in window"], index=0)

    if mode == "Next after date":
        after = st.datetime_input("After (UTC)", value=now)
        span_days = st.slider("Search span (days)", min_value=1, max_value=400, value=380)
        if st.button("Find Next Return", type="primary"):
            win = ReturnWindow(start=after, end=after + timedelta(days=int(span_days)))
            res = find_next_return(body, float(natal_lon), win, provider, step_minutes=720)
            if not res:
                st.warning("No return in the selected window.")
            else:
                st.success(f"Next {body} return at **{res.exact_time.isoformat()}** (|Δ|={res.orb:.6f}°)")
    else:
        start = st.datetime_input("Window start (UTC)", value=now - timedelta(days=30))
        end = st.datetime_input("Window end (UTC)", value=now + timedelta(days=380))
        step_minutes = st.slider("Step (minutes)", 60, 1440, 720, 60)
        if st.button("Find Returns in Window", type="primary"):
            win = ReturnWindow(start=start, end=end)
            results = find_returns_in_window(body, float(natal_lon), win, provider, step_minutes=step_minutes)
            if not results:
                st.info("No returns found in this window.")
            else:
                df = pd.DataFrame({
                    "body": [body]*len(results),
                    "exact_time": [r.exact_time for r in results],
                    "orb": [r.orb for r in results],
                })
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), file_name="returns.csv", mime="text/csv")
