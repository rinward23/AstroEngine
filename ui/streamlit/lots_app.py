"""Streamlit UI for building and exploring Arabic Lots."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import streamlit as st

from astroengine.engine.lots import (
    ChartContext,
    ChartLocation,
    aspects_to_lots,
    builtin_profile,
    compile_program,
    evaluate,
    list_builtin_profiles,
    load_custom_profiles,
    parse_lot_defs,
    save_custom_profile,
    scan_lot_events,
)
from astroengine.scoring.policy import load_orb_policy

try:  # pragma: no cover - optional dependency
    from astroengine.api.routers.lots import _SwissEphemerisWrapper as SwissWrapper
    HAVE_SWE = True
except Exception:  # pragma: no cover
    SwissWrapper = None
    HAVE_SWE = False

from .components import location_picker

st.set_page_config(page_title="Arabic Lots Builder", layout="wide")
st.title("Arabic Lots Builder")

DEFAULT_DSL = builtin_profile("Hellenistic").expr_text

if "lots_dsl" not in st.session_state:
    st.session_state["lots_dsl"] = DEFAULT_DSL
if "compiled_program" not in st.session_state:
    st.session_state["compiled_program"] = compile_program(parse_lot_defs(DEFAULT_DSL))
if "lot_results" not in st.session_state:
    st.session_state["lot_results"] = {}

builder_tab, presets_tab, aspects_tab, events_tab = st.tabs(
    ["Builder", "Presets", "Aspects", "Events"]
)


with builder_tab:
    st.subheader("Lot Definitions")
    source = st.text_area(
        "Lots DSL",
        st.session_state["lots_dsl"],
        height=220,
        help="Define lots using the arc/wrap/if_day DSL",
    )
    compile_col, eval_col = st.columns(2)
    with compile_col:
        if st.button("Compile", key="compile_button"):
            try:
                program = compile_program(parse_lot_defs(source))
            except Exception as exc:  # pragma: no cover - user feedback
                st.error(f"Compilation failed: {exc}")
            else:
                st.success("Program compiled")
                st.session_state["compiled_program"] = program
                st.session_state["lots_dsl"] = source
    with eval_col:
        positions_json = st.text_area(
            "Chart Positions (JSON)",
            json.dumps({"Sun": 120.0, "Moon": 15.0, "ASC": 100.0}, indent=2),
            height=220,
        )
        is_day = st.selectbox("Sect", ["Auto", "Day", "Night"], index=0)
        location_picker(
            "Chart location",
            default_query="London, United Kingdom",
            state_prefix="lots_location",
            help="Atlas lookup provides coordinates and timezone context for evaluation.",
        )
        lat_default = float(st.session_state.get("lots_location_lat", 0.0))
        lon_default = float(st.session_state.get("lots_location_lon", 0.0))
        latitude = st.number_input("Latitude", value=lat_default)
        longitude = st.number_input("Longitude", value=lon_default)
        st.session_state["lots_location_lat"] = float(latitude)
        st.session_state["lots_location_lon"] = float(longitude)
        moment = st.text_input(
            "Moment (ISO UTC)",
            value=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        if st.button("Evaluate", key="eval_button"):
            try:
                positions = json.loads(positions_json)
                moment_dt = datetime.fromisoformat(moment.replace("Z", "+00:00"))
                location = ChartLocation(latitude, longitude)
                ctx = ChartContext(
                    moment=moment_dt,
                    location=location,
                    positions=positions,
                    is_day_override=(
                        True if is_day == "Day" else False if is_day == "Night" else None
                    ),
                )
                results = evaluate(st.session_state["compiled_program"], ctx)
            except Exception as exc:  # pragma: no cover - user feedback
                st.error(f"Evaluation failed: {exc}")
            else:
                st.session_state["lot_results"] = results
                st.success("Lots computed")
                st.json(results)


with presets_tab:
    st.subheader("Built-in Profiles")
    builtin_cols = st.columns(2)
    for idx, profile in enumerate(list_builtin_profiles()):
        col = builtin_cols[idx % 2]
        with col:
            st.markdown(f"**{profile.name}**")
            st.caption(profile.description)
            if st.button(f"Load {profile.tradition}", key=f"load_{profile.profile_id}"):
                st.session_state["lots_dsl"] = profile.expr_text
                st.session_state["compiled_program"] = profile.compile()
                st.experimental_rerun()
    st.divider()
    st.subheader("Custom Presets")
    custom_profiles = load_custom_profiles()
    if custom_profiles:
        for profile in custom_profiles.values():
            with st.expander(profile.name):
                st.code(profile.expr_text)
    with st.form("save_preset_form"):
        st.write("Save current DSL as preset")
        pid = st.text_input("Profile ID", value="user_profile")
        name = st.text_input("Name", value="Custom Lots")
        description = st.text_area("Description", value="User defined lots")
        if st.form_submit_button("Save Preset"):
            profile = builtin_profile("Hellenistic")
            from astroengine.engine.lots import LotsProfile

            new_profile = LotsProfile(
                profile_id=pid,
                name=name,
                description=description,
                zodiac=profile.zodiac,
                house_system=profile.house_system,
                policy_id=profile.policy_id,
                expr_text=st.session_state["lots_dsl"],
                source_refs={},
                ayanamsha=profile.ayanamsha,
                tradition="Custom",
            )
            save_custom_profile(new_profile)
            st.success("Preset saved")


with aspects_tab:
    st.subheader("Aspects to Lots")
    lots = st.session_state.get("lot_results", {})
    if not lots:
        st.info("Compute lots on the Builder tab to enable aspect analysis.")
    else:
        bodies_json = st.text_area(
            "Body Positions (JSON)",
            json.dumps({"Mars": 45.0, "Venus": 210.0}, indent=2),
            height=180,
        )
        harmonics = st.multiselect(
            "Harmonics", [1, 2, 3, 4, 6, 8, 12], default=[1, 2, 3, 4]
        )
        if st.button("Compute Aspects", key="aspect_button"):
            try:
                bodies = json.loads(bodies_json)
                policy = load_orb_policy()
                hits = aspects_to_lots(lots, bodies, policy, harmonics)
            except Exception as exc:  # pragma: no cover - user feedback
                st.error(f"Aspect computation failed: {exc}")
            else:
                if not hits:
                    st.info("No aspects found within orb allowances.")
                else:
                    for hit in hits:
                        st.write(
                            f"{hit.body} → {hit.lot} at {hit.angle:.1f}° (orb {hit.orb:.2f}°)"
                        )


with events_tab:
    st.subheader("Transit Events")
    if not HAVE_SWE:
        st.warning("Swiss Ephemeris not available; install astroengine[ephem] for event scanning.")
    else:
        lot_name = st.text_input("Lot Name", value="Fortune")
        lot_value = st.number_input(
            "Lot Longitude", value=float(st.session_state.get("lot_results", {}).get(lot_name, 0.0))
        )
        bodies = st.multiselect(
            "Bodies",
            ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"],
            default=["Sun", "Mars"],
        )
        start = st.text_input(
            "Start (ISO UTC)", value=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        end = st.text_input(
            "End (ISO UTC)",
            value=(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0) + timedelta(days=30)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        )
        harmonics = st.multiselect("Harmonics", [1, 2, 3, 4, 6], default=[1, 2])
        step = st.slider("Step Hours", min_value=1.0, max_value=24.0, value=12.0)
        if st.button("Scan Events", key="event_button"):
            try:
                adapter = SwissWrapper()
                events = scan_lot_events(
                    adapter,
                    lot_value,
                    bodies,
                    datetime.fromisoformat(start.replace("Z", "+00:00")),
                    datetime.fromisoformat(end.replace("Z", "+00:00")),
                    load_orb_policy(),
                    harmonics,
                    step_hours=step,
                    lot_name=lot_name,
                )
            except Exception as exc:  # pragma: no cover - user feedback
                st.error(f"Event scan failed: {exc}")
            else:
                if not events:
                    st.info("No events detected in interval.")
                else:
                    for event in events:
                        st.write(
                            f"{event.timestamp.isoformat()} — {event.body} {event.angle:.1f}° {event.lot} (severity {event.severity:.2f})"
                        )
