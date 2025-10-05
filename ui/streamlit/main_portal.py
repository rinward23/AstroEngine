from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Dict

import requests
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from ui.streamlit.components.chatgpt_panel import chatgpt_panel

st.set_page_config(page_title="AstroEngine Portal", layout="wide")

# --- Header / style ---------------------------------------------------------
st.markdown(
    """
    <style>
      .stMetric, .element-container { padding-top: 2px !important; }
      .gallery-card { border-radius: 16px; padding: 12px; background: var(--secondary-background-color); }
      .muted { color: #9aa0a6; font-size: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌌 AstroEngine — Main Portal")


def _api_base() -> str:
    return os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/")


def _render_chart() -> None:
    st.markdown("**Chart Wheel**")
    url = f"{_api_base()}/v1/plots/wheel"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            st.image(r.content, caption="Current Chart")
        else:
            st.info("Chart image endpoint not available yet. Add /v1/plots/wheel to the API to enable.")
    except Exception:
        st.info("Chart endpoint unreachable.")


def _render_aspects() -> None:
    st.markdown("**Aspect Grid**")
    url = f"{_api_base()}/v1/plots/aspects"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            st.image(r.content, caption="Aspect Grid")
        else:
            st.info("Aspect grid not available yet. Add /v1/plots/aspects.")
    except Exception:
        st.info("Aspect endpoint unreachable.")


def _render_timeline() -> None:
    st.markdown("**Timeline**")
    url = f"{_api_base()}/v1/timeline?from=now-30d&to=now+30d"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            data = r.json()
            st.json(data[:25] if isinstance(data, list) else data)
        else:
            st.info("Timeline endpoint not ready. See Task 7/10.")
    except Exception:
        st.info("Timeline endpoint unreachable.")


def _render_map() -> None:
    st.markdown("**Astrocartography Map**")
    try:
        import pydeck as pdk

        url = f"{_api_base()}/v1/astrocartography"
        r = requests.get(url, timeout=5)
        if r.ok:
            geo = r.json()
            layer = pdk.Layer("GeoJsonLayer", geo, pickable=True)
            view_state = pdk.ViewState(latitude=0, longitude=0, zoom=0.8)
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
        else:
            st.info("Map endpoint not ready. See Task 12.")
    except Exception:
        st.info("pydeck not installed or map endpoint unreachable.")


def _render_custom() -> None:
    st.markdown("**Custom Panel**")
    st.caption("Bring your own graphic here — embed images, tables, or KPIs.")
    st.write("")


PANE_RENDERERS: Dict[str, Callable[[], None]] = {
    "Chart": _render_chart,
    "Aspects": _render_aspects,
    "Timeline": _render_timeline,
    "Map": _render_map,
    "Custom": _render_custom,
}


DEFAULT_LAYOUT = {
    "Top Left": "Chart",
    "Top Right": "Timeline",
    "Bottom Left": "Map",
    "Bottom Right": "Aspects",
}


def _init_dashboard_state() -> None:
    if "dashboard_slots" not in st.session_state:
        st.session_state.dashboard_slots = DEFAULT_LAYOUT.copy()


def _layout_controls() -> None:
    with st.expander("Dashboard Layout", expanded=False):
        st.markdown(
            "Select which insight appears in each quadrant. Choose **Empty** to clear a slot."
        )
        options = ["Empty", *PANE_RENDERERS.keys()]
        for slot in DEFAULT_LAYOUT:
            current = st.session_state.dashboard_slots.get(slot, "Empty")
            selected = st.selectbox(
                slot,
                options=options,
                index=options.index(current) if current in options else 0,
                key=f"dashboard_slot_{slot.replace(' ', '_').lower()}",
            )
            st.session_state.dashboard_slots[slot] = selected


def _render_slot(slot: str, pane_key: str) -> None:
    with st.container(border=True):
        if pane_key == "Empty":
            st.info("Select a panel from the layout controls to populate this slot.")
            return
        renderer = PANE_RENDERERS.get(pane_key)
        if not renderer:
            st.warning(f"Unknown panel: {pane_key}")
            return
        renderer()


_init_dashboard_state()

left, right = st.columns([7, 5], gap="large")

# --- Left: Configurable dashboard ------------------------------------------
with left:
    st.subheader("Visuals")
    _layout_controls()

    top = st.columns(2)
    with top[0]:
        _render_slot("Top Left", st.session_state.dashboard_slots.get("Top Left", "Empty"))
    with top[1]:
        _render_slot("Top Right", st.session_state.dashboard_slots.get("Top Right", "Empty"))

    bottom = st.columns(2)
    with bottom[0]:
        _render_slot("Bottom Left", st.session_state.dashboard_slots.get("Bottom Left", "Empty"))
    with bottom[1]:
        _render_slot("Bottom Right", st.session_state.dashboard_slots.get("Bottom Right", "Empty"))

# --- Right: ChatGPT ---------------------------------------------------------
with right:
    chatgpt_panel()
