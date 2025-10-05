"""Streamlit UI for blending narrative profiles with adjustable weights."""

from __future__ import annotations

import os
from typing import Dict

import requests
import streamlit as st

from astroengine.config import list_narrative_profiles

st.set_page_config(page_title="AstroEngine — Narrative Mixer", layout="wide")
st.title("🎚️ Narrative Mixer — Blend Multiple Styles")

API_DEFAULT = os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000")

profiles_catalog = list_narrative_profiles()
all_profiles = profiles_catalog.get("built_in", []) + profiles_catalog.get("user", [])

control_col, preview_col = st.columns([3, 4], gap="large")

with control_col:
    st.subheader("Select Profiles & Weights")
    api_base = st.text_input(
        "API base URL",
        value=st.session_state.get("narrative_mix_api", API_DEFAULT),
        help="Endpoint used when applying the mix.",
    )
    st.session_state["narrative_mix_api"] = api_base

    default_selection = [name for name in ("modern_psychological", "data_minimal") if name in all_profiles]
    picked = st.multiselect(
        "Profiles to mix",
        all_profiles,
        default=default_selection or all_profiles[:2],
        help="Pick one or more narrative profiles to blend.",
    )

    weights: Dict[str, float] = {}
    for name in picked:
        key = f"mix_weight_{name}"
        current = st.session_state.get(key, 0.5)
        weights[name] = st.slider(
            f"Weight — {name}",
            min_value=0.0,
            max_value=1.0,
            value=float(current),
            step=0.05,
            key=key,
        )

    actions = st.columns(3)
    with actions[0]:
        if st.button("Equalize") and picked:
            equal = round(1.0 / len(picked), 4)
            for name in picked:
                st.session_state[f"mix_weight_{name}"] = equal
            st.rerun()
    with actions[1]:
        normalize = st.toggle(
            "Normalize weights",
            value=st.session_state.get("mix_normalize", True),
            help="If enabled, weights are scaled to sum to 1.0 before mixing.",
            key="mix_normalize",
        )
    with actions[2]:
        save_as = st.text_input(
            "Save blend as",
            value=st.session_state.get("mix_save_name", ""),
            placeholder="my_jungian_mix",
            key="mix_save_name",
        )

    if st.button("Apply Mix", type="primary"):
        payload = {
            "profiles": {name: st.session_state.get(f"mix_weight_{name}", weight) for name, weight in weights.items()},
            "normalize": normalize,
            "save_as": save_as or None,
        }
        try:
            response = requests.post(
                api_base.rstrip("/") + "/v1/narrative-mix/apply",
                json=payload,
                timeout=15,
            )
        except Exception as exc:  # pragma: no cover - network errors in UI only
            st.error(f"Request failed: {exc}")
        else:
            if response.ok:
                st.success("Mix applied and persisted to settings.")
            else:
                st.error(f"Failed to apply mix: {response.status_code} — {response.text}")

with preview_col:
    st.subheader("Preview Effective Narrative")
    try:
        preview = requests.get(
            st.session_state["narrative_mix_api"].rstrip("/") + "/v1/narrative-mix",
            timeout=10,
        )
    except Exception as exc:  # pragma: no cover - UI only
        st.error(f"Could not contact API: {exc}")
    else:
        if preview.ok:
            data = preview.json()
            st.caption("Current mix configuration")
            st.json(data.get("mix", {}))
            st.caption("Effective narrative (used by the copilot & interpreters)")
            st.json(data.get("effective", {}))
            with st.expander("Available profiles", expanded=False):
                st.json(data.get("available", {}))
        else:
            st.error(f"Failed to load mix: {preview.status_code} — {preview.text}")

st.caption("Adjust narrative profiles to fine-tune tone, sources, and esoteric layers.")
