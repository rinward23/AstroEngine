from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Synastry & Composites", page_icon="💞", layout="wide")
st.title("Synastry & Composites 💞")
api = APIClient()

DEFAULT_ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile", "quincunx"]
SAMPLE_POSITIONS: Dict[str, Dict[str, float]] = {
    "NYC 1990-02-16 (regression)": {
        "Sun": 327.824967,
        "Moon": 226.812266,
        "Mercury": 306.587384,
        "Venus": 292.269912,
        "Mars": 283.177018,
        "Jupiter": 90.915699,
        "Saturn": 290.924799,
        "Uranus": 278.287469,
        "Neptune": 283.6611,
        "Pluto": 227.785695,
    },
    "London 1985-07-13 (regression)": {
        "Sun": 111.215606,
        "Moon": 61.184662,
        "Mercury": 137.755721,
        "Venus": 67.975138,
        "Mars": 112.558487,
        "Jupiter": 314.704774,
        "Saturn": 231.586352,
        "Uranus": 254.609143,
        "Neptune": 271.716086,
        "Pluto": 211.924831,
    },
    "Tokyo 2000-12-25 (regression)": {
        "Sun": 273.465699,
        "Moon": 265.156077,
        "Mercury": 272.986165,
        "Venus": 319.107477,
        "Mars": 210.803963,
        "Jupiter": 62.824828,
        "Saturn": 54.933695,
        "Uranus": 318.320888,
        "Neptune": 305.085719,
        "Pluto": 253.51329,
    },
}

TAB1, TAB2 = st.tabs(["Synastry", "Composites"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_json_textarea(label: str, *, default_obj: Dict[str, float], key: str) -> Dict[str, float]:
    """Render a textarea with preset/import helpers and return parsed JSON."""

    text_key = f"{key}_text"
    preset_key = f"{key}_preset"
    upload_key = f"{key}_upload"

    if text_key not in st.session_state:
        st.session_state[text_key] = json.dumps(default_obj, indent=2)

    presets = ["Custom"] + list(SAMPLE_POSITIONS)
    preset_choice = st.selectbox("Preset", presets, key=preset_key)

    preset_btn_col, upload_col = st.columns([1, 1])
    with preset_btn_col:
        if preset_choice != "Custom" and st.button("Load preset", key=f"{key}_load"):
            st.session_state[text_key] = json.dumps(SAMPLE_POSITIONS[preset_choice], indent=2)
    with upload_col:
        uploaded = st.file_uploader("Import JSON", type=["json"], key=upload_key)
        if uploaded is not None:
            try:
                payload = json.load(uploaded)
            except json.JSONDecodeError as exc:
                st.error(f"Failed to decode uploaded JSON: {exc}")
            else:
                if isinstance(payload, dict):
                    st.session_state[text_key] = json.dumps(payload, indent=2)
                else:
                    st.error("Uploaded JSON must be an object mapping names to longitudes.")

    st.text_area(label, value=st.session_state[text_key], height=200, key=text_key)
    raw = st.session_state[text_key]

    if not raw.strip():
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON for {label}: {exc}")
        return {}

    cleaned: Dict[str, float] = {}
    for name, value in data.items():
        try:
            cleaned[str(name)] = float(value)
        except (TypeError, ValueError):
            st.error(f"Value for '{name}' must be numeric; received {value!r}.")
            return {}
    return cleaned


def _maybe_convert_to_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Tab 1 — Synastry
# ---------------------------------------------------------------------------
with TAB1:
    st.subheader("Synastry — Inter-aspects")

    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Chart A (longitudes in degrees)")
        pos_a = _load_json_textarea(
            "Chart A JSON",
            default_obj=SAMPLE_POSITIONS["NYC 1990-02-16 (regression)"],
            key="chart_a",
        )
    with col_b:
        st.caption("Chart B (longitudes in degrees)")
        pos_b = _load_json_textarea(
            "Chart B JSON",
            default_obj=SAMPLE_POSITIONS["London 1985-07-13 (regression)"],
            key="chart_b",
        )

    aspects = st.multiselect(
        "Aspects",
        DEFAULT_ASPECTS,
        default=["conjunction", "sextile", "square", "trine"],
    )

    with st.expander("Inline orb policy (optional)", expanded=False):
        use_policy = st.checkbox("Enable inline orb policy", value=False, key="use_orb_policy")
        policy = None
        if use_policy:
            sext = st.number_input(
                "Sextile orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1
            )
            tri = st.number_input(
                "Trine orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1
            )
            sq = st.number_input(
                "Square orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1
            )
            conj = st.number_input(
                "Conjunction orb", min_value=0.1, max_value=10.0, value=8.0, step=0.1
            )
            opp = st.number_input(
                "Opposition orb", min_value=0.1, max_value=10.0, value=7.0, step=0.1
            )
            quinc = st.number_input(
                "Quincunx orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1
            )
            policy = {
                "per_aspect": {
                    "sextile": sext,
                    "trine": tri,
                    "square": sq,
                    "conjunction": conj,
                    "opposition": opp,
                    "quincunx": quinc,
                }
            }

    hint_col, action_col = st.columns([3, 1])
    with hint_col:
        st.caption(
            "Tip: Paste chart positions as `{\"Body\": longitude}`. Use presets or JSON import for quick testing."
        )
    with action_col:
        trigger_synastry = st.button("Compute synastry", type="primary")

    if trigger_synastry:
        if not pos_a or not pos_b:
            st.warning("Both charts must provide at least one longitude.")
        elif not aspects:
            st.warning("Select at least one aspect to compute synastry hits.")
        else:
            payload = {"pos_a": pos_a, "pos_b": pos_b, "aspects": aspects}
            if policy is not None:
                payload["orb_policy_inline"] = policy

            with st.spinner("Fetching synastry results..."):
                try:
                    data = api.synastry_compute(payload)
                except RuntimeError as exc:
                    st.error(f"API error: {exc}")
                else:
                    hits = data.get("hits", [])
                    grid = data.get("grid", {}).get("counts", {})

                    st.subheader("Hits")
                    if hits:
                        df = pd.DataFrame(hits)
                        sort_cols = [c for c in ("a_obj", "b_obj", "orb") if c in df.columns]
                        if sort_cols:
                            df.sort_values(sort_cols, inplace=True)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        dl_col_csv, dl_col_json = st.columns(2)
                        with dl_col_csv:
                            st.download_button(
                                "Download hits CSV",
                                df.to_csv(index=False).encode("utf-8"),
                                file_name="synastry_hits.csv",
                                mime="text/csv",
                            )
                        with dl_col_json:
                            st.download_button(
                                "Download JSON",
                                json.dumps(data, indent=2).encode("utf-8"),
                                file_name="synastry.json",
                                mime="application/json",
                            )

                        st.subheader("A×B object grid (counts)")
                        grid_df = pd.DataFrame(grid).fillna(0)
                        if not grid_df.empty:
                            grid_df = grid_df.astype(int).T
                            st.dataframe(grid_df, use_container_width=True)

                            with st.expander("Heatmap", expanded=False):
                                fig = px.imshow(
                                    grid_df,
                                    aspect="auto",
                                    text_auto=True,
                                    title="Synastry counts heatmap",
                                    color_continuous_scale="Blues",
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No synastry counts were returned for the selected bodies.")
                    else:
                        st.info("No inter-aspects matched with the current selection.")


# ---------------------------------------------------------------------------
# Tab 2 — Composites
# ---------------------------------------------------------------------------
with TAB2:
    st.subheader("Composite charts")
    mode = st.radio("Mode", ["Midpoint", "Davison"], horizontal=True)

    if mode == "Midpoint":
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Chart A (longitudes in degrees)")
            pos_a_c = _load_json_textarea(
                "Chart A JSON (longitudes)",
                default_obj=SAMPLE_POSITIONS["NYC 1990-02-16 (regression)"],
                key="mid_chart_a",
            )
        with col_b:
            st.caption("Chart B (longitudes in degrees)")
            pos_b_c = _load_json_textarea(
                "Chart B JSON (longitudes)",
                default_obj=SAMPLE_POSITIONS["London 1985-07-13 (regression)"],
                key="mid_chart_b",
            )

        shared_objects = sorted(set(pos_a_c) & set(pos_b_c))
        st.caption(
            "Objects (intersection of Chart A & B): "
            + (", ".join(shared_objects) if shared_objects else "—")
        )

        if st.button("Compute midpoint composite", type="primary"):
            if not shared_objects:
                st.warning("Charts must share at least one object to compute midpoints.")
            else:
                payload = {"pos_a": pos_a_c, "pos_b": pos_b_c, "objects": shared_objects}
                with st.spinner("Computing midpoint composite..."):
                    try:
                        res = api.composite_midpoint(payload)
                    except RuntimeError as exc:
                        st.error(f"API error: {exc}")
                    else:
                        positions = res.get("positions", {})
                        if not positions:
                            st.info("No positions returned for the midpoint composite.")
                        else:
                            df = pd.DataFrame(
                                {
                                    "object": list(positions.keys()),
                                    "longitude": [positions[obj] for obj in positions],
                                }
                            )
                            df.sort_values("object", inplace=True)
                            st.dataframe(df, use_container_width=True, hide_index=True)

                            with st.expander("Polar plot", expanded=True):
                                theta = df["longitude"].to_numpy()
                                r = np.ones_like(theta)
                                fig = go.Figure()
                                fig.add_trace(
                                    go.Scatterpolar(
                                        theta=theta,
                                        r=r,
                                        mode="markers+text",
                                        text=df["object"],
                                        textposition="top center",
                                    )
                                )
                                fig.update_layout(
                                    polar=dict(radialaxis=dict(visible=False)),
                                    showlegend=False,
                                    height=420,
                                )
                                st.plotly_chart(fig, use_container_width=True)

                            dl_c1, dl_c2 = st.columns(2)
                            with dl_c1:
                                st.download_button(
                                    "Download CSV",
                                    df.to_csv(index=False).encode("utf-8"),
                                    file_name="composite_midpoint.csv",
                                    mime="text/csv",
                                )
                            with dl_c2:
                                st.download_button(
                                    "Download JSON",
                                    json.dumps(res, indent=2).encode("utf-8"),
                                    file_name="composite_midpoint.json",
                                    mime="application/json",
                                )
    else:
        obj_text = st.text_input(
            "Objects (comma-separated)",
            value="Sun, Moon, Mercury, Venus, Mars",
        )
        objects = [item.strip() for item in obj_text.split(",") if item.strip()]

        now = datetime.now(timezone.utc)
        col_a, col_b = st.columns(2)
        dt_a_input = col_a.datetime_input(
            "Chart A datetime (UTC)",
            value=now - timedelta(days=10),
        )
        dt_b_input = col_b.datetime_input(
            "Chart B datetime (UTC)",
            value=now,
        )

        if st.button("Compute Davison", type="primary"):
            if not objects:
                st.warning("Provide at least one object to compute a Davison composite.")
            else:
                dt_a = _maybe_convert_to_utc(dt_a_input)
                dt_b = _maybe_convert_to_utc(dt_b_input)
                payload = {
                    "objects": objects,
                    "dt_a": dt_a.isoformat(),
                    "dt_b": dt_b.isoformat(),
                }
                with st.spinner("Computing Davison composite..."):
                    try:
                        res = api.composite_davison(payload)
                    except RuntimeError as exc:
                        st.error(f"API error: {exc}")
                    else:
                        positions = res.get("positions", {})
                        meta = res.get("meta", {})
                        midpoint_time = meta.get("midpoint_time", "—")
                        st.write(f"Midpoint time (UTC): `{midpoint_time}`")

                        if positions:
                            df = pd.DataFrame(
                                {
                                    "object": list(positions.keys()),
                                    "longitude": [positions[obj] for obj in positions],
                                }
                            )
                            df.sort_values("object", inplace=True)
                            st.dataframe(df, use_container_width=True, hide_index=True)

                            dl_d1, dl_d2 = st.columns(2)
                            with dl_d1:
                                st.download_button(
                                    "Download CSV",
                                    df.to_csv(index=False).encode("utf-8"),
                                    file_name="composite_davison.csv",
                                    mime="text/csv",
                                )
                            with dl_d2:
                                st.download_button(
                                    "Download JSON",
                                    json.dumps(res, indent=2).encode("utf-8"),
                                    file_name="composite_davison.json",
                                    mime="application/json",
                                )
                        else:
                            st.info(
                                "No positions returned — ensure the backend has an ephemeris provider configured."
                            )
