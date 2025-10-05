"""Streamlit page for exploring planetary midpoints and midpoint trees."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

from astroengine.analysis.midpoints import compute_midpoints, get_midpoint_settings
from astroengine.chart.config import ChartConfig
from astroengine.chart.natal import ChartLocation, DEFAULT_BODIES, compute_natal_chart
from astroengine.providers.swisseph_adapter import SE_MEAN_NODE, SE_TRUE_NODE
from astroengine.userdata.vault import list_natals, load_natal

st.set_page_config(page_title="Midpoint Explorer", page_icon="🌓", layout="wide")

st.title("🌓 Midpoint Explorer")
st.caption("Compute circular midpoints for natal placements or custom longitude sets.")

midpoint_cfg = get_midpoint_settings()
if not midpoint_cfg.enabled:
    st.warning(
        "Midpoint analysis is disabled in the current settings. Update your configuration to enable it."
    )
    st.stop()

st.sidebar.header("Options")
include_nodes_default = midpoint_cfg.include_nodes
include_nodes = st.sidebar.checkbox(
    "Include lunar nodes", value=include_nodes_default, help="Toggle north/south node pairs."
)

if midpoint_cfg.tree.enabled:
    st.sidebar.info(
        f"Midpoint tree expansion is enabled (max depth {midpoint_cfg.tree.max_depth})."
    )
else:
    st.sidebar.info("Midpoint tree expansion is disabled in the current settings.")

source_choice = st.radio(
    "Select midpoint source",
    options=("Manual longitudes", "Stored natal chart"),
    index=0,
)


def _pair_depth(pair: tuple[str, str]) -> int:
    return max(segment.count("/") for segment in pair) + 1


def _chart_config(include_nodes_flag: bool) -> tuple[ChartConfig, dict[str, int]]:
    cfg = ChartConfig()
    bodies = dict(DEFAULT_BODIES)
    if include_nodes_flag:
        node_code = SE_TRUE_NODE if cfg.nodes_variant == "true" else SE_MEAN_NODE
        label = "True Node" if cfg.nodes_variant == "true" else "Mean Node"
        bodies.setdefault(label, node_code)
        bodies.setdefault("South Node", node_code)
    return cfg, bodies


def _load_natal_positions(natal_id: str, include_nodes_flag: bool) -> dict[str, float]:
    record = load_natal(natal_id)
    moment = datetime.fromisoformat(record.utc.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    config, bodies = _chart_config(include_nodes_flag)
    chart = compute_natal_chart(
        moment,
        ChartLocation(latitude=float(record.lat), longitude=float(record.lon)),
        bodies=bodies,
        config=config,
    )
    return {name: pos.longitude for name, pos in chart.positions.items()}


def _longitudes_from_text(raw: str) -> dict[str, float]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Longitudes payload must be a JSON object")
    parsed: dict[str, float] = {}
    for key, value in data.items():
        if key is None or key == "":
            continue
        parsed[str(key)] = float(value)
    return parsed


longitudes_input: dict[str, float] | None = None
source_meta: dict[str, Any] | None = None

if source_choice == "Manual longitudes":
    sample_payload = {
        "Sun": 10.0,
        "Moon": 350.0,
        "Mercury": 44.5,
        "Venus": 182.2,
    }
    default_text = json.dumps(sample_payload, indent=2)
    payload_text = st.text_area(
        "Longitude map (JSON)",
        value=default_text,
        height=240,
        help="Provide a JSON object mapping body names to degrees.",
    )
    if st.button("Compute midpoints", type="primary"):
        try:
            longitudes_input = _longitudes_from_text(payload_text)
            source_meta = {"type": "inline", "count": len(longitudes_input)}
        except Exception as exc:  # pragma: no cover - interactive validation
            st.error(f"Unable to parse longitudes: {exc}")
else:
    available_natals = list_natals()
    if not available_natals:
        st.info("No stored natal charts were found in the local vault.")
    else:
        selected = st.selectbox("Natal record", available_natals)
        if st.button("Compute midpoints", type="primary") and selected:
            try:
                longitudes_input = _load_natal_positions(selected, include_nodes)
                source_meta = {"type": "natal", "natal_id": selected, "count": len(longitudes_input)}
            except Exception as exc:  # pragma: no cover - interactive validation
                st.error(f"Failed to load natal '{selected}': {exc}")

if not longitudes_input:
    st.stop()

midpoint_map = compute_midpoints(longitudes_input, include_nodes=include_nodes)
if not midpoint_map:
    st.warning("No midpoint pairs were generated. Ensure at least two positions are available.")
    st.stop()

rows = [
    {
        "Body A": pair[0],
        "Body B": pair[1],
        "Midpoint (°)": value,
        "Depth": _pair_depth(pair),
    }
    for pair, value in midpoint_map.items()
]

df = pd.DataFrame(rows)
df.sort_values(["Depth", "Body A", "Body B"], inplace=True, ignore_index=True)

st.subheader("Midpoint table")
st.dataframe(df, use_container_width=True, hide_index=True)

if source_meta:
    st.caption(
        "Source: "
        + ", ".join(f"{key}={value}" for key, value in source_meta.items())
        + ". Midpoint of 10° and 350° resolves to 0° by circular averaging."
    )

if midpoint_cfg.tree.enabled and df["Depth"].max() > 1:
    st.subheader("Midpoint tree levels")
    for depth, group in df.groupby("Depth"):
        st.markdown(f"**Depth {int(depth)}**")
        display = group[["Body A", "Body B", "Midpoint (°)"]].reset_index(drop=True)
        st.table(display)
else:
    st.info("Tree expansion is unavailable with the current configuration.")
