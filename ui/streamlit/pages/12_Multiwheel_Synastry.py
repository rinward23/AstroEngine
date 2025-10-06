from __future__ import annotations

import json
from collections.abc import Mapping

import streamlit as st

from astroengine.config import Settings, load_settings
from astroengine.visual import (
    MultiWheelComposition,
    MultiWheelLayer,
    MultiWheelOptions,
    export_multiwheel,
    render_multiwheel_svg,
)

st.set_page_config(page_title="Multi-wheel Synastry", page_icon="🪐", layout="wide")
st.title("Multi-wheel Synastry 🪐")

# ---------------------------------------------------------------------------
# Defaults

SAMPLE_DATA: Mapping[str, dict[str, object]] = {
    "natal": {
        "label": "Natal",
        "positions": {
            "Sun": 15.2,
            "Moon": 122.4,
            "Mercury": 3.9,
            "Venus": 84.1,
            "Mars": 192.5,
            "Jupiter": 280.3,
            "Saturn": 300.8,
        },
        "houses": [21.0, 53.3, 83.8, 112.1, 141.7, 173.4, 201.6, 233.2, 263.8, 292.5, 321.1, 351.0],
        "declinations": {
            "Sun": 0.6,
            "Moon": 5.2,
            "Mercury": -2.1,
            "Venus": 8.9,
            "Mars": -12.4,
            "Jupiter": -18.1,
            "Saturn": -20.4,
        },
    },
    "secondary_progressions": {
        "label": "Progressed",
        "positions": {
            "Sun": 16.5,
            "Moon": 150.9,
            "Mercury": 18.7,
            "Venus": 90.3,
            "Mars": 206.8,
            "Jupiter": 283.5,
            "Saturn": 302.1,
        },
        "houses": None,
        "declinations": {
            "Sun": 0.8,
            "Moon": 6.1,
            "Mercury": -1.8,
            "Venus": 9.1,
            "Mars": -11.6,
            "Jupiter": -18.0,
            "Saturn": -20.2,
        },
    },
    "transits": {
        "label": "Transit",
        "positions": {
            "Sun": 195.3,
            "Moon": 12.0,
            "Mercury": 210.7,
            "Venus": 144.2,
            "Mars": 52.4,
            "Jupiter": 22.6,
            "Saturn": 333.5,
        },
        "houses": None,
        "declinations": {
            "Sun": -1.2,
            "Moon": 5.9,
            "Mercury": -2.8,
            "Venus": 9.4,
            "Mars": 16.1,
            "Jupiter": 0.3,
            "Saturn": -19.7,
        },
    },
}

DEFAULT_ASPECTS = ["conjunction", "opposition", "trine", "square", "sextile"]

settings: Settings = load_settings()
profile_names: list[str] = list(settings.synastry.wheel_profiles)

if not settings.multiwheel.enabled:
    st.warning("Multi-wheel rendering is disabled in settings. Enable it in the settings panel to activate this tool.")

sidebar = st.sidebar
with sidebar:
    st.header("Configuration")
    max_wheels = max(2, min(settings.multiwheel.max_wheels, 3))
    default_wheels = min(max_wheels, max(2, settings.multiwheel.default_wheels))
    wheel_count = st.slider(
        "Wheel count",
        min_value=2,
        max_value=max_wheels,
        value=default_wheels,
        help="Number of concentric wheels to render",
    )
    chart_order: list[str] = []
    available_profiles = profile_names or ["natal", "secondary_progressions", "transits"]
    for idx in range(wheel_count):
        key = f"wheel_profile_{idx}"
        chart = st.selectbox(
            f"Wheel {idx + 1} chart",
            options=available_profiles,
            index=min(idx, len(available_profiles) - 1),
            key=key,
        )
        chart_order.append(chart)

    st.divider()
    st.subheader("Rendering")
    size = st.slider("Size (px)", min_value=500, max_value=1200, value=880, step=20)
    show_aspects = st.toggle("Show aspect lines", value=settings.multiwheel.enabled)
    show_houses = st.toggle(
        "House overlay",
        value=settings.multiwheel.house_overlay and (settings.synastry.house_overlay if settings.synastry.house_overlay is not None else True),
    )
    show_declination = st.toggle(
        "Declination synastry",
        value=settings.synastry.declination,
    )
    aspect_choices = st.multiselect(
        "Aspect set",
        options=DEFAULT_ASPECTS,
        default=DEFAULT_ASPECTS,
    )
    st.caption("Input positions/declinations are interpreted as degrees.")

    st.divider()
    st.header("Layers JSON")

layer_inputs: list[dict] = []
for idx, chart in enumerate(chart_order):
    defaults = SAMPLE_DATA.get(chart, {})
    st.subheader(f"{defaults.get('label', chart.title())} positions")
    pos_default = json.dumps(defaults.get("positions", {}), indent=2)
    positions_txt = st.text_area(
        f"Wheel {idx + 1} positions (name → longitude°)",
        value=pos_default,
        height=160,
        key=f"pos_{idx}",
    )
    houses_default = defaults.get("houses")
    houses_txt = st.text_area(
        f"Wheel {idx + 1} houses (optional)",
        value="" if houses_default is None else json.dumps(houses_default),
        height=80,
        key=f"houses_{idx}",
    )
    decl_default = json.dumps(defaults.get("declinations", {}), indent=2)
    decl_txt = st.text_area(
        f"Wheel {idx + 1} declinations (optional)",
        value=decl_default,
        height=120,
        key=f"decl_{idx}",
    )
    layer_inputs.append(
        {
            "label": defaults.get("label", chart.title()),
            "positions": positions_txt,
            "houses": houses_txt,
            "declinations": decl_txt,
        }
    )

st.divider()
col_left, col_right = st.columns([2, 1])

with col_left:
    title = st.text_input("Title", value="Synastry Multi-wheel")
    subtitle = st.text_input("Subtitle", value="Layered comparison")

render_button = st.button("Render multi-wheel", type="primary")

if render_button:
    layers: list[MultiWheelLayer] = []
    errors: list[str] = []
    for idx, payload in enumerate(layer_inputs):
        try:
            pos_data = json.loads(payload["positions"]) if payload["positions"].strip() else {}
            positions = {str(name): float(lon) for name, lon in pos_data.items()}
        except Exception as exc:
            errors.append(f"Wheel {idx + 1} positions error: {exc}")
            positions = {}
        houses: list[float] | None = None
        houses_txt = payload["houses"].strip()
        if houses_txt:
            try:
                house_values = json.loads(houses_txt)
                houses = [float(value) for value in house_values]
            except Exception as exc:
                errors.append(f"Wheel {idx + 1} houses error: {exc}")
        declinations: dict[str, float] | None = None
        decl_txt = payload["declinations"].strip()
        if decl_txt:
            try:
                decl_data = json.loads(decl_txt)
                declinations = {str(name): float(dec) for name, dec in decl_data.items()}
            except Exception as exc:
                errors.append(f"Wheel {idx + 1} declinations error: {exc}")
        if not positions:
            errors.append(f"Wheel {idx + 1} requires at least one body position")
            continue
        layers.append(
            MultiWheelLayer(
                label=payload["label"],
                bodies=positions,
                houses=houses,
                declinations=declinations,
            )
        )

    if errors:
        st.error("\n".join(errors))
        st.stop()

    composition = MultiWheelComposition(layers=tuple(layers), title=title, subtitle=subtitle)
    options = MultiWheelOptions(
        size=int(size),
        wheel_count=len(layers),
        show_aspects=bool(show_aspects),
        show_house_overlay=bool(show_houses),
        show_declination_synastry=bool(show_declination),
        aspect_set=aspect_choices or DEFAULT_ASPECTS,
    )

    svg = render_multiwheel_svg(composition, options=options, settings=settings)
    st.components.v1.html(svg, height=int(size) + 220, scrolling=False)

    svg_bytes = export_multiwheel(composition, options=options, settings=settings, fmt="svg")
    png_bytes = export_multiwheel(composition, options=options, settings=settings, fmt="png")

    st.download_button(
        "Download SVG",
        svg_bytes,
        file_name="multiwheel.svg",
        mime="image/svg+xml",
    )
    st.download_button(
        "Download PNG",
        png_bytes,
        file_name="multiwheel.png",
        mime="image/png",
    )

with col_right:
    st.markdown(
        """
        **Tips**

        * Use the sidebar to choose natal, progressed, or transit layers.
        * Provide declinations for declination synastry overlays.
        * Aspect lists respect the active orb policy from settings.
        """
    )
