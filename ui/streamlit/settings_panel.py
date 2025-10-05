"""Streamlit settings management UI for AstroEngine."""

from __future__ import annotations

import streamlit as st

from astroengine.config import (
    PluginCfg,
    Settings,
    config_path,
    load_settings,
    save_settings,
)
from astroengine.plugins.registry import (
    PLUGIN_DIRECTORY,
    ensure_user_plugins_loaded,
    iter_aspect_plugins,
    iter_lot_plugins,
)

st.set_page_config(page_title="AstroEngine Settings", layout="wide")

st.title("⚙️ AstroEngine Settings")

current_settings = load_settings()
st.sidebar.success(f"Profile: {config_path()}")

ensure_user_plugins_loaded()
aspect_plugins = list(iter_aspect_plugins())
lot_plugins = list(iter_lot_plugins())

plugin_aspect_state = {
    key: bool(value)
    for key, value in (current_settings.plugins.aspects or {}).items()
}
plugin_lot_state = {
    key: bool(value)
    for key, value in (current_settings.plugins.lots or {}).items()
}

available_aspect_keys = {spec.key for spec in aspect_plugins}
available_lot_keys = {spec.key for spec in lot_plugins}
plugin_aspect_state = {
    key: val for key, val in plugin_aspect_state.items() if key in available_aspect_keys
}
plugin_lot_state = {
    key: val for key, val in plugin_lot_state.items() if key in available_lot_keys
}

preset_options = [
    "modern_western",
    "traditional_western",
    "hellenistic",
    "vedic",
    "minimalist",
]
preset = st.selectbox(
    "Preset", preset_options, index=preset_options.index(current_settings.preset)
)

st.subheader("Zodiac & Houses")
col_zodiac, col_houses = st.columns(2)
with col_zodiac:
    zodiac_type = st.selectbox(
        "Zodiac",
        ["tropical", "sidereal"],
        index=["tropical", "sidereal"].index(current_settings.zodiac.type),
    )
    ayanamsa = st.selectbox(
        "Ayanamsa",
        [
            "lahiri",
            "fagan_bradley",
            "krishnamurti",
            "de_luce",
            "raman",
            "none",
        ],
        index=[
            "lahiri",
            "fagan_bradley",
            "krishnamurti",
            "de_luce",
            "raman",
            "none",
        ].index(current_settings.zodiac.ayanamsa),
    )
with col_houses:
    house_system = st.selectbox(
        "House System",
        [
            "placidus",
            "whole_sign",
            "equal",
            "koch",
            "porphyry",
            "regiomontanus",
            "alcabitius",
            "campanus",
        ],
        index=[
            "placidus",
            "whole_sign",
            "equal",
            "koch",
            "porphyry",
            "regiomontanus",
            "alcabitius",
            "campanus",
        ].index(current_settings.houses.system),
    )

st.subheader("Bodies & Points")
body_groups = current_settings.bodies.groups.copy()
cols_bodies = st.columns(4)
for idx, key in enumerate(list(body_groups.keys())):
    with cols_bodies[idx % 4]:
        body_groups[key] = st.toggle(
            key.replace("_", " ").title(), value=body_groups[key], key=f"b_{key}"
        )
custom_asteroids_raw = st.text_input(
    "Custom Asteroids (comma-separated IDs)",
    value=",".join(str(x) for x in current_settings.bodies.custom_asteroids),
)
if custom_asteroids_raw.strip():
    custom_asteroids = [
        int(chunk)
        for chunk in custom_asteroids_raw.split(",")
        if chunk.strip().isdigit()
    ]
else:
    custom_asteroids = []

st.subheader("Aspects & Orbs")
aspect_sets = current_settings.aspects.sets.copy()
col_ptolemaic, col_minor, col_harmonics = st.columns(3)
with col_ptolemaic:
    aspect_sets["ptolemaic"] = st.toggle(
        "Ptolemaic", aspect_sets.get("ptolemaic", True)
    )
with col_minor:
    aspect_sets["minor"] = st.toggle("Minor", aspect_sets.get("minor", True))
with col_harmonics:
    aspect_sets["harmonics"] = st.toggle(
        "Harmonics", aspect_sets.get("harmonics", False)
    )
patterns = st.toggle(
    "Detect Aspect Patterns (T-square, Grand Trine, Yod…)",
    current_settings.aspects.detect_patterns,
)
orbs_global = st.slider(
    "Global Orb (deg)", 1.0, 12.0, float(current_settings.aspects.orbs_global), 0.5
)

st.subheader("Plugins")
plugin_root_display = str(PLUGIN_DIRECTORY)
if not aspect_plugins and not lot_plugins:
    st.info(
        "No user plugin files detected. Add .py files under "
        f"`{plugin_root_display}` to register custom aspects or lots."
    )
else:
    st.caption(
        "User plugins are loaded from "
        f"`{plugin_root_display}`. Toggle entries to enable them for this profile."
    )
    if aspect_plugins:
        st.markdown("**Custom Aspects**")
        for spec in aspect_plugins:
            default_enabled = plugin_aspect_state.get(spec.key, True)
            help_parts = [f"Angle: {spec.angle:g}°"]
            desc = spec.metadata.get("description") if isinstance(spec.metadata, dict) else None
            if desc:
                help_parts.append(str(desc))
            if spec.origin:
                help_parts.append(f"Module: {spec.origin}")
            if spec.path:
                help_parts.append(f"File: {spec.path}")
            if spec.replace:
                help_parts.append("Overrides a built-in aspect definition.")
            plugin_aspect_state[spec.key] = st.toggle(
                spec.ui_label(),
                value=default_enabled,
                help="\n".join(help_parts),
                key=f"plugin_aspect_{spec.key}",
            )
    if lot_plugins:
        st.markdown("**Custom Lots**")
        for spec in lot_plugins:
            default_enabled = plugin_lot_state.get(spec.key, True)
            help_parts = []
            if spec.description:
                help_parts.append(spec.description)
            help_parts.append(f"Day: {spec.day_formula}")
            help_parts.append(f"Night: {spec.night_formula}")
            if spec.origin:
                help_parts.append(f"Module: {spec.origin}")
            if spec.path:
                help_parts.append(f"File: {spec.path}")
            if spec.replace:
                help_parts.append("Overrides a built-in lot definition.")
            plugin_lot_state[spec.key] = st.toggle(
                spec.name,
                value=default_enabled,
                help="\n".join(help_parts),
                key=f"plugin_lot_{spec.key}",
            )

st.subheader("Chart Types & Techniques")
chart_flags = current_settings.charts.enabled.copy()
cols_charts = st.columns(4)
for idx, key in enumerate(sorted(chart_flags.keys())):
    with cols_charts[idx % 4]:
        chart_flags[key] = st.toggle(
            key.replace("_", " ").title(), value=chart_flags[key], key=f"c_{key}"
        )

st.subheader("Narrative & Rendering")
library = st.selectbox(
    "Narrative Library",
    ["western_basic", "hellenistic", "vedic", "none"],
    index=["western_basic", "hellenistic", "vedic", "none"].index(
        current_settings.narrative.library
    ),
)
tone = st.selectbox(
    "Tone",
    ["neutral", "teaching", "brief"],
    index=["neutral", "teaching", "brief"].index(current_settings.narrative.tone),
)
length = st.selectbox(
    "Length",
    ["short", "medium", "long"],
    index=["short", "medium", "long"].index(current_settings.narrative.length),
)
language = st.text_input("Language (IETF)", current_settings.narrative.language)

render_layers = current_settings.rendering.layers.copy()
layer_columns = st.columns(3)
for idx, key in enumerate(list(render_layers.keys())):
    with layer_columns[idx % 3]:
        render_layers[key] = st.toggle(
            key.replace("_", " ").title(),
            value=render_layers[key],
            key=f"r_{key}",
        )

st.subheader("Ephemeris & Performance")
ephemeris_source = st.selectbox(
    "Ephemeris Source",
    ["swiss", "approx"],
    index=["swiss", "approx"].index(current_settings.ephemeris.source),
)
se_path = st.text_input(
    "Swiss Ephemeris Path (optional)", current_settings.ephemeris.path or ""
)
qcache_size = st.number_input(
    "In-proc Cache Size", min_value=512, step=512, value=int(current_settings.perf.qcache_size)
)
qcache_seconds = st.number_input(
    "Quantization Seconds",
    min_value=0.05,
    step=0.05,
    format="%.2f",
    value=float(current_settings.perf.qcache_sec),
)
max_scan_days = st.number_input(
    "Max Scan Days",
    min_value=30,
    step=30,
    value=int(current_settings.perf.max_scan_days),
)

if st.button("💾 Save Settings", type="primary"):
    updated = Settings(
        preset=preset,
        zodiac={"type": zodiac_type, "ayanamsa": ayanamsa},
        houses={"system": house_system},
        bodies={"groups": body_groups, "custom_asteroids": custom_asteroids},
        aspects={
            "sets": aspect_sets,
            "detect_patterns": patterns,
            "orbs_global": orbs_global,
            "orbs_by_aspect": current_settings.aspects.orbs_by_aspect,
            "orbs_by_body": current_settings.aspects.orbs_by_body,
            "use_moiety": current_settings.aspects.use_moiety,
            "show_applying": current_settings.aspects.show_applying,
        },
        charts={"enabled": chart_flags},
        narrative={
            "library": library,
            "tone": tone,
            "length": length,
            "language": language,
            "disclaimers": current_settings.narrative.disclaimers,
        },
        rendering={
            "layers": render_layers,
            "theme": current_settings.rendering.theme,
            "glyph_set": current_settings.rendering.glyph_set,
        },
        ephemeris={
            "source": ephemeris_source,
            "path": se_path or None,
            "precision": current_settings.ephemeris.precision,
        },
        perf={
            "qcache_size": qcache_size,
            "qcache_sec": qcache_seconds,
            "max_scan_days": max_scan_days,
        },
        plugins=PluginCfg(aspects=plugin_aspect_state, lots=plugin_lot_state),
    )
    save_settings(updated)
    st.success("Settings saved. Some changes may require restarting the API.")

st.caption(f"Tip: The settings are stored in {config_path()}")
