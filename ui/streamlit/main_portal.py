from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

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
      .dashboard-toolbar { background: rgba(22, 26, 35, 0.85); border-radius: 14px; padding: 12px 18px; margin-bottom: 1.2rem; }
      .dashboard-toolbar .stSelectbox div[data-baseweb="select"] { min-height: 34px; }
      .dashboard-toolbar .stSlider { padding-top: 0; }
      .dashboard-slot > div:first-child { padding: 0.75rem; border-radius: 16px; background: var(--secondary-background-color); border: 1px solid rgba(255,255,255,0.08); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌌 AstroEngine — Main Portal")
st.page_link("ui/streamlit/chart_library.py", label="Open Chart Library →")


def _api_base() -> str:
    return os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/")


def _render_chart(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Chart Wheel**")
    url = f"{_api_base()}/v1/plots/wheel"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            target.image(r.content, caption="Current Chart")
        else:
            target.info("Chart image endpoint not available yet. Add /v1/plots/wheel to the API to enable.")
    except Exception:
        target.info("Chart endpoint unreachable.")


def _render_aspects(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Aspect Grid**")
    url = f"{_api_base()}/v1/plots/aspects"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            target.image(r.content, caption="Aspect Grid")
        else:
            target.info("Aspect grid not available yet. Add /v1/plots/aspects.")
    except Exception:
        target.info("Aspect endpoint unreachable.")


def _render_timeline(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Timeline**")
    url = f"{_api_base()}/v1/timeline?from=now-30d&to=now+30d"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            data = r.json()
            target.json(data[:25] if isinstance(data, list) else data)
        else:
            target.info("Timeline endpoint not ready. See Task 7/10.")
    except Exception:
        target.info("Timeline endpoint unreachable.")


def _render_map(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Astrocartography Map**")
    try:
        import pydeck as pdk

        url = f"{_api_base()}/v1/astrocartography"
        r = requests.get(url, timeout=5)
        if r.ok:
            geo = r.json()
            layer = pdk.Layer("GeoJsonLayer", geo, pickable=True)
            view_state = pdk.ViewState(latitude=0, longitude=0, zoom=0.8)
            target.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
        else:
            target.info("Map endpoint not ready. See Task 12.")
    except Exception:
        target.info("pydeck not installed or map endpoint unreachable.")


def _render_custom(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Custom Panel**")
    target.caption("Bring your own graphic here — embed images, tables, or KPIs.")
    target.write("")


def _render_health(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Service Health**")
    url = f"{_api_base()}/healthz"
    try:
        r = requests.get(url, timeout=3)
        target.markdown(f"`GET {url}` → **{r.status_code}**")
        content_type = r.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            target.json(r.json())
        else:
            target.code(r.text[:2000])
    except Exception as exc:
        target.warning(f"Health endpoint unreachable: {exc}")


def _render_settings_snapshot(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Configuration Snapshot**")
    url = f"{_api_base()}/v1/settings"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            target.json(r.json())
        else:
            target.info("Settings endpoint responded without data. Ensure /v1/settings is implemented.")
    except Exception as exc:
        target.warning(f"Settings endpoint unreachable: {exc}")


def _render_metrics(target: DeltaGenerator | None = None) -> None:
    target = target or st
    target.markdown("**Prometheus Metrics**")
    url = f"{_api_base()}/metrics"
    try:
        r = requests.get(url, timeout=4)
        if r.ok:
            target.code(r.text[:4000] + ("\n…" if len(r.text) > 4000 else ""), language="text")
        else:
            target.info("Metrics endpoint responded without data. Ensure Prometheus middleware is enabled.")
    except Exception as exc:
        target.warning(f"Metrics endpoint unreachable: {exc}")


@dataclass(frozen=True)
class PaneDefinition:
    label: str
    category: str
    renderer: Callable[[DeltaGenerator], None]


PANE_LIBRARY: dict[str, PaneDefinition] = {
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
    st.session_state.setdefault("dashboard_column_ratio", 0.65)
    st.session_state.setdefault("dashboard_top_split", 0.5)
    st.session_state.setdefault("dashboard_bottom_split", 0.5)
    st.session_state.setdefault("dashboard_slot_height", 420)


def _slot_selector(slot: str, categories: list[str]) -> None:
    current = st.session_state.dashboard_slots.get(slot, "Empty")
    slot_key = slot.replace(" ", "_").lower()

    if current == "Empty":
        current_category = "Empty"
    else:
        pane_meta = PANE_LIBRARY.get(current)
        current_category = pane_meta.category if pane_meta else "Empty"

    st.caption(slot)
    category_options = ["Empty", *categories]
    selected_category = st.selectbox(
        f"{slot} Category",
        options=category_options,
        index=category_options.index(current_category)
        if current_category in category_options
        else 0,
        key=f"dashboard_slot_{slot_key}_category",
        label_visibility="collapsed",
    )
    st.write("")

    if selected_category == "Empty":
        st.session_state.dashboard_slots[slot] = "Empty"
        st.session_state[f"dashboard_slot_{slot_key}_pane"] = "Empty"
        return

    panes_in_category = [
        key
        for key, pane in PANE_LIBRARY.items()
        if pane.category == selected_category
    ]
    if not panes_in_category:
        st.session_state.dashboard_slots[slot] = "Empty"
        st.warning(f"No panels available for category {selected_category}.")
        return

    default_pane = current if current in panes_in_category else panes_in_category[0]
    selected_pane = st.selectbox(
        f"{slot} Pane",
        options=panes_in_category,
        index=panes_in_category.index(default_pane),
        format_func=lambda key: PANE_LIBRARY[key].label,
        key=f"dashboard_slot_{slot_key}_pane",
        label_visibility="collapsed",
    )
    st.caption(PANE_LIBRARY[selected_pane].label)
    st.session_state.dashboard_slots[slot] = selected_pane


def _layout_toolbar() -> None:
    categories: list[str] = sorted({pane.category for pane in PANE_LIBRARY.values()})
    st.markdown("#### Dashboard Menu")
    with st.container():
        toolbar = st.container()
        with toolbar:
            st.markdown('<div class="dashboard-toolbar">', unsafe_allow_html=True)
            ratio_col, height_col = st.columns([3, 2])
            with ratio_col:
                st.slider(
                    "Dashboard / Copilot Width",
                    min_value=0.45,
                    max_value=0.8,
                    step=0.05,
                    value=float(st.session_state.dashboard_column_ratio),
                    key="dashboard_column_ratio",
                    help="Adjust the horizontal space dedicated to the dashboard versus the Copilot panel.",
                )
                st.slider(
                    "Top Row Split",
                    min_value=0.35,
                    max_value=0.65,
                    step=0.05,
                    value=float(st.session_state.dashboard_top_split),
                    key="dashboard_top_split",
                    help="Widen or narrow the top row panes without allowing them to collapse.",
                )
                st.slider(
                    "Bottom Row Split",
                    min_value=0.35,
                    max_value=0.65,
                    step=0.05,
                    value=float(st.session_state.dashboard_bottom_split),
                    key="dashboard_bottom_split",
                    help="Adjust the proportions for the lower panes.",
                )
            with height_col:
                st.slider(
                    "Panel Minimum Height",
                    min_value=260,
                    max_value=640,
                    step=20,
                    value=int(st.session_state.dashboard_slot_height),
                    key="dashboard_slot_height",
                    help="Increase height for richer visuals or shrink for quick-glance metrics.",
                )

                st.caption(
                    "Pane controls stay constrained so the layout remains legible even when resized."
                )

            st.markdown("<hr style='margin: 0.8rem 0 1rem 0; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

            selector_cols = st.columns(4)
            for slot, column in zip(DEFAULT_LAYOUT.keys(), selector_cols, strict=False):
                with column:
                    _slot_selector(slot, categories)

            st.markdown("</div>", unsafe_allow_html=True)


def _render_slot(slot: str, pane_key: str) -> None:
    min_height = int(st.session_state.get("dashboard_slot_height", 420))
    slot_container = st.container()
    slot_container.markdown(
        f"<div class='dashboard-slot' style='min-height: {min_height}px'>",
        unsafe_allow_html=True,
    )
    slot_body = slot_container.container()
    if pane_key == "Empty":
        slot_body.info("Select a panel from the menu above to populate this slot.")
    else:
        pane = PANE_LIBRARY.get(pane_key)
        if not pane:
            slot_body.warning(f"Unknown panel: {pane_key}")
        else:
            pane.renderer(slot_body)
    slot_container.markdown("</div>", unsafe_allow_html=True)


_init_dashboard_state()

dashboard_weight = max(min(st.session_state.dashboard_column_ratio, 0.8), 0.45)
copilot_weight = max(1.0 - dashboard_weight, 0.2)
left_weight = max(int(round(dashboard_weight * 100)), 1)
right_weight = max(int(round(copilot_weight * 100)), 1)
left, right = st.columns([left_weight, right_weight], gap="large")

# --- Left: Configurable dashboard ------------------------------------------
with left:
    st.subheader("Visuals")
    _layout_toolbar()

    top_split = max(min(st.session_state.dashboard_top_split, 0.65), 0.35)
    top_left = max(int(round(top_split * 100)), 1)
    top_right = max(int(round((1 - top_split) * 100)), 1)
    top = st.columns([top_left, top_right], gap="small")
    with top[0]:
        _render_slot("Top Left", st.session_state.dashboard_slots.get("Top Left", "Empty"))
    with top[1]:
        _render_slot("Top Right", st.session_state.dashboard_slots.get("Top Right", "Empty"))

    bottom_split = max(min(st.session_state.dashboard_bottom_split, 0.65), 0.35)
    bottom_left = max(int(round(bottom_split * 100)), 1)
    bottom_right = max(int(round((1 - bottom_split) * 100)), 1)
    bottom = st.columns([bottom_left, bottom_right], gap="small")
    with bottom[0]:
        _render_slot("Bottom Left", st.session_state.dashboard_slots.get("Bottom Left", "Empty"))
    with bottom[1]:
        _render_slot("Bottom Right", st.session_state.dashboard_slots.get("Bottom Right", "Empty"))

# --- Right: ChatGPT ---------------------------------------------------------
with right:
    chatgpt_panel()
