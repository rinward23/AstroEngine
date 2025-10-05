"""Streamlit helper for managing narrative profiles."""

from __future__ import annotations

import requests
import streamlit as st

from astroengine.config import (
    NarrativeCfg,
    list_narrative_profiles,
    load_settings,
)


st.set_page_config(page_title="AstroEngine — Narrative Profiles", layout="wide")
st.title("🗂️ Narrative Profiles")

API_BASE = "http://127.0.0.1:8000"

profile_lists = list_narrative_profiles()
left_column, right_column = st.columns([2, 3])

with left_column:
    st.subheader("Built-ins")
    built_in_names = profile_lists.get("built_in", [])
    selected_built_in = st.selectbox(
        "Choose a built-in",
        built_in_names,
        index=0 if built_in_names else None,
    )
    if st.button("Apply built-in", type="primary", disabled=not selected_built_in):
        try:
            response = requests.post(
                f"{API_BASE}/v1/narrative-profiles/{selected_built_in}/apply",
                timeout=10,
            )
        except requests.RequestException as exc:
            st.error(f"Failed to apply profile: {exc}")
        else:
            if response.ok:
                st.success("Applied narrative profile.")
            else:
                st.error(response.text)

    st.divider()
    st.subheader("Create / Update User Profile")
    current_settings = load_settings()
    current_narrative: NarrativeCfg = current_settings.narrative
    new_name = st.text_input("Profile name", placeholder="my_narrative")
    with st.expander("Edit narrative fields", expanded=False):
        modes = [
            "data_minimal",
            "traditional_classical",
            "modern_psychological",
            "vedic_parashari",
            "jungian_archetypal",
            "esoteric_tarot",
            "esoteric_numerology",
            "esoteric_mixed",
        ]
        mode_index = (
            modes.index(current_narrative.mode)
            if current_narrative.mode in modes
            else modes.index("modern_psychological")
        )
        mode = st.selectbox("Mode", modes, index=mode_index)
        tone = st.selectbox(
            "Tone",
            ["neutral", "teaching", "brief"],
            index=["neutral", "teaching", "brief"].index(current_narrative.tone),
        )
        length = st.selectbox(
            "Length",
            ["short", "medium", "long"],
            index=["short", "medium", "long"].index(current_narrative.length),
        )
        verbosity = st.slider(
            "Verbosity",
            0.0,
            1.0,
            float(current_narrative.verbosity),
            0.05,
        )
        disclaimers = st.toggle(
            "Include disclaimers",
            value=current_narrative.disclaimers,
        )

        st.markdown("**Sources included** (data the narrative may reference)")
        sources = dict(current_narrative.sources)
        source_columns = st.columns(3)
        for idx, key in enumerate(sorted(sources.keys())):
            with source_columns[idx % 3]:
                sources[key] = st.toggle(
                    key.replace("_", " ").title(),
                    value=sources[key],
                    key=f"src_{key}",
                )

        st.markdown("**Frameworks** (steer narrative style)")
        frameworks = dict(current_narrative.frameworks)
        framework_columns = st.columns(3)
        for idx, key in enumerate(sorted(frameworks.keys())):
            with framework_columns[idx % 3]:
                frameworks[key] = st.toggle(
                    key.replace("_", " ").title(),
                    value=frameworks[key],
                    key=f"fw_{key}",
                )

        st.markdown("**Esoteric overlays** (optional)")
        esoteric = dict(current_narrative.esoteric)
        esoteric["tarot_enabled"] = st.toggle(
            "Tarot overlay",
            value=bool(esoteric.get("tarot_enabled", False)),
        )
        esoteric["tarot_deck"] = st.selectbox(
            "Tarot deck",
            ["rws", "thoth", "marseille"],
            index=["rws", "thoth", "marseille"].index(
                esoteric.get("tarot_deck", "rws")
            ),
        )
        esoteric["numerology_enabled"] = st.toggle(
            "Numerology overlay",
            value=bool(esoteric.get("numerology_enabled", False)),
        )
        esoteric["numerology_system"] = st.selectbox(
            "Numerology system",
            ["pythagorean", "chaldean"],
            index=["pythagorean", "chaldean"].index(
                esoteric.get("numerology_system", "pythagorean")
            ),
        )

    if st.button("Save as user profile", disabled=not new_name):
        payload = {
            "name": new_name,
            "narrative": {
                "mode": mode,
                "tone": tone,
                "length": length,
                "verbosity": verbosity,
                "disclaimers": disclaimers,
                "sources": sources,
                "frameworks": frameworks,
                "esoteric": esoteric,
                "library": current_narrative.library,
                "language": current_narrative.language,
            },
        }
        try:
            response = requests.post(
                f"{API_BASE}/v1/narrative-profiles",
                json=payload,
                timeout=10,
            )
        except requests.RequestException as exc:
            st.error(f"Failed to save profile: {exc}")
        else:
            if response.ok:
                st.success("Saved narrative profile.")
            else:
                st.error(response.text)

with right_column:
    st.subheader("Explain profiles")
    st.markdown(
        """
    - **Data-minimal**: strictly chart data (aspects, midpoints) with sparse phrasing.
    - **Traditional / Classical**: emphasises dignities, sect, and classical techniques.
    - **Modern Psychological**: counselling tone with archetypal language.
    - **Vedic (Parāśari)**: shifts vocabulary and focus to Vedic practice.
    - **Jungian Archetypal**: highlights symbols and mythic framing.
    - **Esoteric – Tarot**: maps placements to tarot prompts when enabled.
    - **Esoteric – Numerology**: injects numerological motifs for opt-in flows.
    - **Esoteric – Mixed**: combines tarot and numerology overlays.
        """
    )

    st.divider()
    st.subheader("Preview current narrative config")
    st.json(load_settings().narrative.model_dump())

st.caption(
    "Narrative user profiles live under: ~/.astroengine/profiles/narrative"
    " (or %LOCALAPPDATA%/AstroEngine/profiles/narrative on Windows)."
)

