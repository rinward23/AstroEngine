from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pandas as pd
import plotly.express as px
import streamlit as st

from core.viz_plus.wheel_svg import WheelOptions, render_chart_wheel
from ui.streamlit.api import APIClient

st.set_page_config(page_title="Relationship Lab", page_icon="💞", layout="wide")
st.title("Relationship Lab 💞")
api = APIClient()

TAB_SYN, TAB_COMP, TAB_DAV = st.tabs(["Synastry", "Composite", "Davison"])

# ------------------------------- Helpers -----------------------------------
DEFAULT_POS_A = {"Sun": 350.0, "Moon": 20.0, "Mercury": 10.0, "Venus": 70.0, "Mars": 100.0}
DEFAULT_POS_B = {"Sun": 10.0, "Moon": 80.0, "Mercury": 30.0, "Venus": 200.0, "Mars": 280.0}
DEFAULT_ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile"]

def _as_json(text: str) -> Any:
    if not text.strip():
        return {}
    return json.loads(text)


def _download_buttons(df: pd.DataFrame, basename: str) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"{basename}.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Download JSON",
            df.to_json(orient="records", date_format="iso").encode("utf-8"),
            file_name=f"{basename}.json",
            mime="application/json",
        )


# ------------------------------- Synastry ----------------------------------
with TAB_SYN:
    st.subheader("Synastry — inter-aspects, grid, scores")

    colL, colR = st.columns(2)
    with colL:
        posA_txt = st.text_area(
            "Chart A — Positions JSON (deg)",
            value=json.dumps(DEFAULT_POS_A, indent=2),
            height=180,
        )
    with colR:
        posB_txt = st.text_area(
            "Chart B — Positions JSON (deg)",
            value=json.dumps(DEFAULT_POS_B, indent=2),
            height=180,
        )

    aspects = st.multiselect("Aspects", DEFAULT_ASPECTS, default=DEFAULT_ASPECTS)

    with st.expander("Inline orb policy", expanded=False):
        c = st.columns(5)
        conj = c[0].number_input("conj", 0.1, 15.0, 8.0, 0.1)
        opp = c[1].number_input("opp", 0.1, 15.0, 7.0, 0.1)
        sq = c[2].number_input("sq", 0.1, 15.0, 6.0, 0.1)
        tri = c[3].number_input("tri", 0.1, 15.0, 6.0, 0.1)
        sex = c[4].number_input("sex", 0.1, 15.0, 3.0, 0.1)
        policy = {
            "per_aspect": {
                "conjunction": conj,
                "opposition": opp,
                "square": sq,
                "trine": tri,
                "sextile": sex,
            }
        }

    with st.expander("Weights (optional)", expanded=False):
        w_conj = st.slider("Conjunction weight", 0.0, 3.0, 1.2, 0.1)
        w_trine = st.slider("Trine weight", 0.0, 3.0, 1.0, 0.1)
        w_sex = st.slider("Sextile weight", 0.0, 3.0, 0.9, 0.1)
        w_sq = st.slider("Square weight", 0.0, 3.0, 1.1, 0.1)
        w_opp = st.slider("Opposition weight", 0.0, 3.0, 1.0, 0.1)
        per_aspect_weight = {
            "conjunction": w_conj,
            "trine": w_trine,
            "sextile": w_sex,
            "square": w_sq,
            "opposition": w_opp,
        }

    if st.button("Compute Synastry", type="primary"):
        try:
            posA = _as_json(posA_txt)
            posB = _as_json(posB_txt)
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"Invalid JSON: {exc}")
            st.stop()

        payload = {
            "posA": posA,
            "posB": posB,
            "aspects": aspects,
            "orb_policy_inline": policy,
            "per_aspect_weight": per_aspect_weight,
        }
        try:
            resp = api.relationship_synastry(payload)
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"API error: {exc}")
            st.stop()

        # Wheels side by side
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Chart A Wheel**")
            svgA = render_chart_wheel(posA, options=WheelOptions(size=600, show_aspects=False))
            st.components.v1.html(svgA, height=640, scrolling=False)
        with c2:
            st.markdown("**Chart B Wheel**")
            svgB = render_chart_wheel(posB, options=WheelOptions(size=600, show_aspects=False))
            st.components.v1.html(svgB, height=640, scrolling=False)

        # Hits table
        hits = resp.get("hits", [])
        st.subheader("Aspect Hits")
        if hits:
            df = pd.DataFrame(hits)
            st.dataframe(df, use_container_width=True, hide_index=True)
            _download_buttons(df, basename="synastry_hits")
        else:
            st.info("No aspect hits under current policy.")

        # Grid
        grid = resp.get("grid", {})
        if grid:
            st.subheader("Aspect Grid (symbols)")
            grid_df = pd.DataFrame(grid).fillna("").T
            st.dataframe(grid_df, use_container_width=True)
            _download_buttons(grid_df.reset_index(), basename="synastry_grid")

        # Scores
        scores = resp.get("scores", {})
        if scores:
            st.subheader("Scores")
            by_aspect = (
                pd.DataFrame(list(scores.get("by_aspect", {}).items()), columns=["aspect", "score"])
                .sort_values("score", ascending=False)
            )
            by_A = (
                pd.DataFrame(list(scores.get("by_bodyA", {}).items()), columns=["body", "score"])
                .sort_values("score", ascending=False)
            )
            by_B = (
                pd.DataFrame(list(scores.get("by_bodyB", {}).items()), columns=["body", "score"])
                .sort_values("score", ascending=False)
            )
            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                if not by_aspect.empty:
                    st.plotly_chart(px.bar(by_aspect, x="aspect", y="score"), use_container_width=True)
            with cc2:
                if not by_A.empty:
                    st.plotly_chart(
                        px.bar(by_A, x="body", y="score", title="Chart A bodies"),
                        use_container_width=True,
                    )
            with cc3:
                if not by_B.empty:
                    st.plotly_chart(
                        px.bar(by_B, x="body", y="score", title="Chart B bodies"),
                        use_container_width=True,
                    )

# ------------------------------- Composite ---------------------------------
with TAB_COMP:
    st.subheader("Composite — midpoint positions")
    colL, colR = st.columns(2)
    with colL:
        posA_txt = st.text_area(
            "Chart A — Positions JSON (deg)",
            value=json.dumps(DEFAULT_POS_A, indent=2),
            height=180,
            key="compA",
        )
    with colR:
        posB_txt = st.text_area(
            "Chart B — Positions JSON (deg)",
            value=json.dumps(DEFAULT_POS_B, indent=2),
            height=180,
            key="compB",
        )

    if st.button("Compute Composite"):
        try:
            posA = _as_json(posA_txt)
            posB = _as_json(posB_txt)
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"Invalid JSON: {exc}")
            st.stop()
        payload = {"posA": posA, "posB": posB}
        try:
            resp = api.relationship_composite(payload)
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"API error: {exc}")
            st.stop()
        comps = resp.get("positions", {})
        if comps:
            df = pd.DataFrame(
                {"body": list(comps.keys()), "longitude": [comps[k] for k in comps.keys()]}
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            _download_buttons(df, basename="composite_positions")
            st.markdown("**Composite Wheel**")
            svg = render_chart_wheel(comps, options=WheelOptions(size=600, show_aspects=False))
            st.components.v1.html(svg, height=640, scrolling=False)

# ------------------------------- Davison -----------------------------------
with TAB_DAV:
    st.subheader("Davison — positions at time midpoint (MVP)")
    now = datetime.now(timezone.utc)
    dtA = st.datetime_input("A — Date/Time (UTC)", value=now - timedelta(days=5))
    dtB = st.datetime_input("B — Date/Time (UTC)", value=now + timedelta(days=5))

    c1, c2 = st.columns(2)
    with c1:
        latA = st.number_input("A — Latitude (°)", -90.0, 90.0, 10.0, 0.1)
        lonA = st.number_input("A — Longitude East (°)", -180.0, 180.0, 20.0, 0.1)
    with c2:
        latB = st.number_input("B — Latitude (°)", -90.0, 90.0, -10.0, 0.1)
        lonB = st.number_input("B — Longitude East (°)", -180.0, 180.0, 40.0, 0.1)

    bodies_txt = st.text_input(
        "Bodies (comma-sep, optional)", value="Sun, Moon, Mercury, Venus, Mars"
    )

    if st.button("Compute Davison"):
        bodies = [b.strip() for b in bodies_txt.split(",") if b.strip()]
        payload = {
            "dtA": dtA.isoformat(),
            "dtB": dtB.isoformat(),
            "locA": {"lat_deg": float(latA), "lon_deg_east": float(lonA)},
            "locB": {"lat_deg": float(latB), "lon_deg_east": float(lonB)},
            "bodies": bodies or None,
        }
        try:
            resp = api.relationship_davison(payload)
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"API error: {exc}")
            st.stop()
        pos = resp.get("positions", {})
        mid_dt = resp.get("midpoint_time_utc")
        if mid_dt:
            st.caption(f"Midpoint time (UTC): {mid_dt}")
        if pos:
            df = pd.DataFrame(
                {"body": list(pos.keys()), "longitude": [pos[k] for k in pos.keys()]}
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            _download_buttons(df, basename="davison_positions")
            st.markdown("**Davison Wheel**")
            svg = render_chart_wheel(pos, options=WheelOptions(size=600, show_aspects=False))
            st.components.v1.html(svg, height=640, scrolling=False)
