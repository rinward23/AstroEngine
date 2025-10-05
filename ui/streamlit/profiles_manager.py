"""Streamlit UI for managing AstroEngine profiles and presets."""

from __future__ import annotations

import requests
import streamlit as st
import yaml

from astroengine.config import (
    USE_CASE_PRESETS,
    apply_profile_overlay,
    list_profiles,
    load_profile_overlay,
    load_settings,
    profile_description,
    profile_label,
    profiles_home,
    save_user_profile,
)

st.set_page_config(page_title="AstroEngine — Profiles", layout="wide")
st.title("📚 Profiles & Presets")

api_base = st.session_state.get("API_BASE") or "http://127.0.0.1:8000"


def apply_profile_via_api(name: str, *, label: str | None = None) -> None:
    """Invoke the backend to apply ``name`` and report status."""

    display_name = label or profile_label(name)
    try:
        response = requests.post(
            f"{api_base}/v1/profiles/{name}/apply",
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        st.error(f"Failed to apply {display_name} profile: {exc}")
    else:
        st.success(f"{display_name} profile applied and saved.")

left, right = st.columns([2, 3])

with left:
    catalog = list_profiles()
    built_in = catalog.get("built_in", [])
    user_profiles = catalog.get("user", [])

    st.subheader("Use-case presets")
    use_case_available = [name for name in USE_CASE_PRESETS if name in built_in]
    if use_case_available:
        for preset in use_case_available:
            label = profile_label(preset)
            description = profile_description(preset)
            preset_cols = st.columns([3, 1])
            with preset_cols[0]:
                st.markdown(f"**{label}**")
                if description:
                    st.caption(description)
            with preset_cols[1]:
                if st.button(
                    f"Apply {label}",
                    key=f"usecase_apply_{preset}",
                    type="primary",
                ):
                    apply_profile_via_api(preset, label=label)
    else:
        st.info("No use-case presets available.")

    st.divider()
    st.subheader("Built-in profiles")
    selectable_built_in = [
        name for name in built_in if name not in use_case_available
    ]
    if not selectable_built_in:
        selectable_built_in = built_in

    if selectable_built_in:
        default_index = (
            selectable_built_in.index("modern_western")
            if "modern_western" in selectable_built_in
            else 0
        )
        selected_builtin = st.selectbox(
            "Select a built-in profile",
            selectable_built_in,
            index=default_index,
            format_func=profile_label,
        )
        if st.button("Apply built-in profile", type="primary", disabled=not selected_builtin):
            apply_profile_via_api(selected_builtin)
    else:
        st.info("No built-in profiles available.")

    st.divider()
    st.subheader("User profiles")
    selected_user = st.selectbox(
        "Select a user profile",
        user_profiles,
        index=0 if user_profiles else None,
        placeholder="No user profiles yet",
    )

    cols_actions = st.columns(3)
    with cols_actions[0]:
        if st.button("Apply user profile", disabled=not selected_user):
            apply_profile_via_api(selected_user, label=selected_user)
    with cols_actions[1]:
        if st.button("Delete user profile", disabled=not selected_user):
            try:
                response = requests.delete(
                    f"{api_base}/v1/profiles/{selected_user}", timeout=15
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                st.error(f"Failed to delete profile: {exc}")
            else:
                st.success("Profile deleted.")
                st.rerun()
    with cols_actions[2]:
        if selected_user:
            overlay = load_profile_overlay(selected_user)
            st.download_button(
                "Export YAML",
                yaml.safe_dump(overlay, sort_keys=False).encode("utf-8"),
                file_name=f"{selected_user}.yaml",
            )
        else:
            st.download_button(
                "Export YAML",
                b"",
                file_name="profile.yaml",
                disabled=True,
            )

    st.divider()
    st.subheader("Save current settings as a profile")
    new_profile_name = st.text_input("Profile name", placeholder="my_team_preset")
    if st.button("Save current settings", type="primary", disabled=not new_profile_name):
        settings = load_settings()
        save_user_profile(new_profile_name, settings)
        st.success("Profile saved.")
        st.rerun()

    st.divider()
    st.subheader("Import profile YAML")
    uploaded_file = st.file_uploader("Choose a .yaml profile", type=["yaml", "yml"])
    import_name = st.text_input("Import as", value="imported_profile")
    if uploaded_file and st.button("Import profile", disabled=not import_name):
        try:
            overlay = yaml.safe_load(uploaded_file.getvalue()) or {}
            current = load_settings()
            merged = apply_profile_overlay(current, overlay)
            save_user_profile(import_name, merged)
        except yaml.YAMLError as exc:
            st.error(f"Invalid YAML: {exc}")
        else:
            st.success("Profile imported.")
            st.rerun()

with right:
    st.subheader("Preview changes")
    mode = st.radio("Profile source", ["Built-in", "User"], horizontal=True)
    target_name = None
    if mode == "Built-in" and built_in:
        target_name = st.selectbox(
            "Preview built-in",
            built_in,
            key="preview_builtin",
            format_func=profile_label,
        )
    elif mode == "User" and user_profiles:
        target_name = st.selectbox("Preview user", user_profiles, key="preview_user")

    if target_name:
        try:
            overlay = load_profile_overlay(target_name)
            base = load_settings()
            merged = apply_profile_overlay(base, overlay)
        except FileNotFoundError:
            st.error("Profile not found on disk.")
        else:
            st.caption("Settings preview after applying the profile")
            st.json(merged.model_dump())
            st.caption("Top-level keys that would change")
            current_dump = base.model_dump()
            merged_dump = merged.model_dump()
            changed_keys = [
                key
                for key, value in merged_dump.items()
                if current_dump.get(key) != value
            ]
            st.code("\n".join(changed_keys) if changed_keys else "No changes", language="text")
    else:
        st.info("Select a profile to preview differences.")

st.caption(f"Profiles are stored in: {profiles_home()}")
