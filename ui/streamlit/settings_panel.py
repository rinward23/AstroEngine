"""Streamlit settings management UI for AstroEngine."""

from __future__ import annotations

import streamlit as st

from astroengine.config import config_path, load_settings, save_settings, Settings

st.set_page_config(page_title="AstroEngine Settings", layout="wide")

st.title("⚙️ AstroEngine Settings")

current_settings = load_settings()
st.sidebar.success(f"Profile: {config_path()}")

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

st.subheader("Mirror Contacts")
col_mirror_toggle, col_mirror_orb = st.columns(2)
with col_mirror_toggle:
    antiscia_enabled = st.toggle(
        "Enable antiscia / contra-antiscia",
        value=current_settings.antiscia.enabled,
        help="Include solstitial mirror contacts in scans when supported.",
    )
with col_mirror_orb:
    antiscia_orb = st.slider(
        "Antiscia Orb (deg)",
        0.1,
        5.0,
        float(current_settings.antiscia.orb),
        0.1,
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
render_layers.setdefault("antiscia_overlay", current_settings.antiscia.show_overlay)
layer_labels = {"antiscia_overlay": "Antiscia points/lines"}
layer_columns = st.columns(3)
for idx, key in enumerate(list(render_layers.keys())):
    label = layer_labels.get(key, key.replace("_", " ").title())
    with layer_columns[idx % 3]:
        render_layers[key] = st.toggle(
            label,
            value=render_layers.get(key, False),
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
        antiscia={
            "enabled": antiscia_enabled,
            "orb": antiscia_orb,
            "show_overlay": render_layers.get("antiscia_overlay", False),
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
    )
    save_settings(updated)
    st.success("Settings saved. Some changes may require restarting the API.")

st.caption(f"Tip: The settings are stored in {config_path()}")
