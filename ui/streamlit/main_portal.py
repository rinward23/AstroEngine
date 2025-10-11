from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from ui.streamlit.components.chatgpt_panel import chatgpt_panel
from ui.streamlit.panes import PaneSpec, load_registered_panes

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
      .launchpad-card { border-radius: 16px; background: var(--secondary-background-color); padding: 1rem; border: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; gap: 0.4rem; min-height: 160px; }
      .launchpad-card h4 { margin: 0; font-size: 1.05rem; }
      .launchpad-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; font-size: 12px; }
      .launchpad-tag { background: rgba(255,255,255,0.1); padding: 0.1rem 0.5rem; border-radius: 999px; }
      .launchpad-card .stPageLink { margin-top: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌌 AstroEngine — Main Portal")
st.page_link("ui/streamlit/chart_library.py", label="Open Chart Library →")
PANES: dict[str, PaneSpec] = load_registered_panes()


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


def _slot_selector(slot: str, categories: list[str], panes: dict[str, PaneSpec]) -> None:
    current = st.session_state.dashboard_slots.get(slot, "Empty")
    slot_key = slot.replace(" ", "_").lower()

    if current == "Empty":
        current_category = "Empty"
    else:
        pane_meta = panes.get(current)
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
        key for key, pane in panes.items() if pane.category == selected_category
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
        format_func=lambda key: panes[key].label,
        key=f"dashboard_slot_{slot_key}_pane",
        label_visibility="collapsed",
    )
    st.caption(panes[selected_pane].label)
    st.session_state.dashboard_slots[slot] = selected_pane


def _layout_toolbar(panes: dict[str, PaneSpec]) -> None:
    categories: list[str] = sorted({pane.category for pane in panes.values()})
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
                    _slot_selector(slot, categories, panes)

            st.markdown("</div>", unsafe_allow_html=True)


def _render_slot(slot: str, pane_key: str, panes: dict[str, PaneSpec]) -> None:
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
        pane = panes.get(pane_key)
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
    _layout_toolbar(PANES)

    top_split = max(min(st.session_state.dashboard_top_split, 0.65), 0.35)
    top_left = max(int(round(top_split * 100)), 1)
    top_right = max(int(round((1 - top_split) * 100)), 1)
    top = st.columns([top_left, top_right], gap="small")
    with top[0]:
        _render_slot(
            "Top Left",
            st.session_state.dashboard_slots.get("Top Left", "Empty"),
            PANES,
        )
    with top[1]:
        _render_slot(
            "Top Right",
            st.session_state.dashboard_slots.get("Top Right", "Empty"),
            PANES,
        )

    bottom_split = max(min(st.session_state.dashboard_bottom_split, 0.65), 0.35)
    bottom_left = max(int(round(bottom_split * 100)), 1)
    bottom_right = max(int(round((1 - bottom_split) * 100)), 1)
    bottom = st.columns([bottom_left, bottom_right], gap="small")
    with bottom[0]:
        _render_slot(
            "Bottom Left",
            st.session_state.dashboard_slots.get("Bottom Left", "Empty"),
            PANES,
        )
    with bottom[1]:
        _render_slot(
            "Bottom Right",
            st.session_state.dashboard_slots.get("Bottom Right", "Empty"),
            PANES,
        )

# --- Right: ChatGPT ---------------------------------------------------------
with right:
    chatgpt_panel()
