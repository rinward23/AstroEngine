from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

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


def _render_health() -> None:
    st.markdown("**Service Health**")
    url = f"{_api_base()}/healthz"
    try:
        r = requests.get(url, timeout=3)
        st.markdown(f"`GET {url}` → **{r.status_code}**")
        content_type = r.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            st.json(r.json())
        else:
            st.code(r.text[:2000])
    except Exception as exc:
        st.warning(f"Health endpoint unreachable: {exc}")


def _render_settings_snapshot() -> None:
    st.markdown("**Configuration Snapshot**")
    url = f"{_api_base()}/v1/settings"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            st.json(r.json())
        else:
            st.info("Settings endpoint responded without data. Ensure /v1/settings is implemented.")
    except Exception as exc:
        st.warning(f"Settings endpoint unreachable: {exc}")


def _render_metrics() -> None:
    st.markdown("**Prometheus Metrics**")
    url = f"{_api_base()}/metrics"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            st.code(r.text[:4000] + ("\n…" if len(r.text) > 4000 else ""), language="text")
        else:
            st.info("Metrics endpoint responded without data. Ensure Prometheus middleware is enabled.")
    except Exception as exc:
        st.warning(f"Metrics endpoint unreachable: {exc}")


@dataclass(frozen=True)
class PaneDefinition:
    label: str
    category: str
    renderer: Callable[[], None]


PANE_LIBRARY: Dict[str, PaneDefinition] = {
    "chart_wheel": PaneDefinition("Chart Wheel", "Charts", _render_chart),
    "aspect_grid": PaneDefinition("Aspect Grid", "Charts", _render_aspects),
    "timeline": PaneDefinition("Event Timeline", "Temporal", _render_timeline),
    "astro_map": PaneDefinition("Astrocartography Map", "Geospatial", _render_map),
    "custom_panel": PaneDefinition("Custom Panel", "Custom", _render_custom),
    "api_health": PaneDefinition("API Health", "Diagnostics", _render_health),
    "api_settings": PaneDefinition("Configuration Snapshot", "Diagnostics", _render_settings_snapshot),
    "api_metrics": PaneDefinition("Prometheus Metrics", "Diagnostics", _render_metrics),
}


DEFAULT_LAYOUT = {
    "Top Left": "chart_wheel",
    "Top Right": "timeline",
    "Bottom Left": "astro_map",
    "Bottom Right": "aspect_grid",
}


def _init_dashboard_state() -> None:
    if "dashboard_slots" not in st.session_state:
        st.session_state.dashboard_slots = DEFAULT_LAYOUT.copy()


def _layout_controls() -> None:
    with st.expander("Dashboard Layout", expanded=False):
        st.markdown(
            "Select which insight appears in each quadrant. Choose a category to filter the available panels."
        )
        categories: List[str] = sorted({pane.category for pane in PANE_LIBRARY.values()})
        for slot in DEFAULT_LAYOUT:
            current = st.session_state.dashboard_slots.get(slot, "Empty")
            slot_key = slot.replace(" ", "_").lower()

            if current == "Empty":
                current_category = "Empty"
            else:
                pane_meta = PANE_LIBRARY.get(current)
                current_category = pane_meta.category if pane_meta else "Empty"

            category_options = ["Empty", *categories]
            selected_category = st.selectbox(
                f"{slot} Category",
                options=category_options,
                index=category_options.index(current_category)
                if current_category in category_options
                else 0,
                key=f"dashboard_slot_{slot_key}_category",
            )

            if selected_category == "Empty":
                st.session_state.dashboard_slots[slot] = "Empty"
                st.session_state[f"dashboard_slot_{slot_key}_pane"] = "Empty"
                continue

            panes_in_category = [
                key
                for key, pane in PANE_LIBRARY.items()
                if pane.category == selected_category
            ]
            if not panes_in_category:
                st.session_state.dashboard_slots[slot] = "Empty"
                st.warning(f"No panels available for category {selected_category}.")
                continue

            default_pane = current if current in panes_in_category else panes_in_category[0]
            selected_pane = st.selectbox(
                slot,
                options=panes_in_category,
                index=panes_in_category.index(default_pane),
                format_func=lambda key: PANE_LIBRARY[key].label,
                key=f"dashboard_slot_{slot_key}_pane",
            )
            st.session_state.dashboard_slots[slot] = selected_pane


def _render_slot(slot: str, pane_key: str) -> None:
    with st.container(border=True):
        if pane_key == "Empty":
            st.info("Select a panel from the layout controls to populate this slot.")
            return
        pane = PANE_LIBRARY.get(pane_key)
        if not pane:
            st.warning(f"Unknown panel: {pane_key}")
            return
        pane.renderer()


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
