"""Streamlit single-page app for the Relationship Lab."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta

import pandas as pd

try:  # pragma: no cover - Streamlit import guarded for tests
    import streamlit as st
except Exception:  # pragma: no cover - surfaced to CLI when dependencies missing
    print("This app requires the UI extras. Install with: pip install -e .[ui]")
    raise

from .api import build_backend
from .constants import ASPECTS, EXTENDED_ASPECTS, MAJOR_ASPECTS
from .samples import DEFAULT_PAIR, get_sample, sample_labels
from .state import export_state_payload, get_state, update_state
from .views import (
    build_summary_markdown,
    filter_hits,
    render_grid,
    render_hits_table,
    render_markdown_copy,
    render_overlay_table,
    render_scores,
)
from .wheels import render_wheel_svg


def _parse_positions(text: str) -> dict[str, float]:
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ValueError("Positions JSON must be an object mapping names to degrees")
    result: dict[str, float] = {}
    for key, value in data.items():
        try:
            result[str(key)] = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Longitude for '{key}' must be numeric") from exc
    return result


def _ensure_text_key(st_module, key: str, default_text: str) -> None:
    if key not in st_module.session_state:
        st_module.session_state[key] = default_text


def _positions_editor(column, label: str, state_attr: str, default_sample: str) -> str:
    state = get_state(st)
    text_key = f"{state_attr}_textarea"
    current_default = getattr(state, state_attr) or json.dumps(get_sample(default_sample).positions, indent=2)
    _ensure_text_key(st, text_key, current_default)

    options = ["Custom"] + sample_labels()
    default_index = options.index(default_sample) if default_sample in options else 0
    choice = column.selectbox("Sample", options, index=default_index, key=f"{state_attr}_sample")
    if choice != "Custom" and column.button("Load sample", key=f"{state_attr}_load"):
        payload = json.dumps(get_sample(choice).positions, indent=2)
        st.session_state[text_key] = payload
        update_state(st, **{state_attr: payload})
    upload = column.file_uploader("Upload ChartPositions JSON", type=["json"], key=f"{state_attr}_upload")
    if upload is not None:
        try:
            payload = json.load(upload)
        except json.JSONDecodeError as exc:
            column.error(f"Failed to parse uploaded JSON: {exc}")
        else:
            if isinstance(payload, Mapping):
                text_payload = json.dumps(payload, indent=2)
                st.session_state[text_key] = text_payload
                update_state(st, **{state_attr: text_payload})
            else:
                column.error("Uploaded JSON must be an object mapping names to longitudes.")
    text = column.text_area(label, key=text_key, height=240)
    update_state(st, **{state_attr: text})
    return text


def _weights_payload(profile: str, aspects: Iterable[str]) -> dict[str, float] | None:
    if profile == "flat":
        return {aspect: 1.0 for aspect in aspects}
    return None


def _wheel_section(pos_a: Mapping[str, float], pos_b: Mapping[str, float]) -> None:
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("**Chart A**")
        svg_a = render_wheel_svg(pos_a)
        st.markdown(svg_a, unsafe_allow_html=True)
    with col_right:
        st.markdown("**Chart B**")
        svg_b = render_wheel_svg(pos_b)
        st.markdown(svg_b, unsafe_allow_html=True)


def _composite_wheel(title: str, positions: Mapping[str, float]) -> None:
    st.markdown(f"**{title}**")
    svg = render_wheel_svg(positions, size=360)
    st.markdown(svg, unsafe_allow_html=True)


def run() -> None:
    st.set_page_config(page_title="Relationship Lab", page_icon="💞", layout="wide")
    state = get_state(st)

    st.title("Relationship Lab")

    with st.sidebar:
        st.header("Configuration")
        mode_labels = {"API (B-003)": "api", "Local (in-process)": "local"}
        current_label = next((label for label, value in mode_labels.items() if value == state.mode), "API (B-003)")
        selected_label = st.radio("Computation mode", list(mode_labels.keys()), index=list(mode_labels.keys()).index(current_label))
        mode = mode_labels[selected_label]
        update_state(st, mode=mode)
        if mode == "api":
            base = st.text_input("API base URL", value=state.api_base_url)
            update_state(st, api_base_url=base)
        else:
            st.caption("Local mode uses the in-process relationship engine if available.")

        min_sev = st.slider("Minimum severity", 0.0, 1.0, value=state.min_severity, step=0.05)
        update_state(st, min_severity=min_sev)

        aspect_modes = ["Majors only", "Majors + minors", "Custom"]
        aspect_mode = st.radio("Aspect set", aspect_modes, index=aspect_modes.index("Majors + minors" if state.aspect_mode == "extended" else ("Majors only" if state.aspect_mode == "majors" else "Custom")))
        if aspect_mode == "Majors only":
            aspects = list(MAJOR_ASPECTS)
            update_state(st, aspect_mode="majors", aspects=aspects)
        elif aspect_mode == "Majors + minors":
            aspects = list(EXTENDED_ASPECTS)
            update_state(st, aspect_mode="extended", aspects=aspects)
        else:
            all_options = list(ASPECTS.keys())
            selected = st.multiselect("Select aspects", all_options, default=state.aspects)
            if selected:
                update_state(st, aspect_mode="custom", aspects=selected)
            aspects = state.aspects

        weights_profile = st.selectbox("Weights profile", ["default", "flat"], format_func=lambda key: "Default policy" if key == "default" else "Flat (1.0)", index=["default", "flat"].index(state.weights_profile if state.weights_profile in ("default", "flat") else "default"))
        update_state(st, weights_profile=weights_profile)

        with st.expander("Session state", expanded=False):
            exported = json.dumps(export_state_payload(state), indent=2)
            st.download_button("Export session JSON", data=exported, file_name="relationship_lab_state.json", mime="application/json")
            imported = st.file_uploader("Import session JSON", type=["json"], key="session_import")
            if imported is not None:
                try:
                    payload = json.load(imported)
                except json.JSONDecodeError as exc:
                    st.error(f"Failed to decode session JSON: {exc}")
                else:
                    if isinstance(payload, Mapping):
                        update_state(st, **payload)
                        st.success("Session state imported. Reloading…")
                        st.experimental_rerun()
                    else:
                        st.error("Session JSON must be an object.")

    state = get_state(st)

    col_a, col_b = st.columns(2)
    text_a = _positions_editor(col_a, "Chart A — ChartPositions JSON", "positions_a_text", DEFAULT_PAIR[0])
    text_b = _positions_editor(col_b, "Chart B — ChartPositions JSON", "positions_b_text", DEFAULT_PAIR[1])

    tabs = st.tabs(["Synastry", "Composite", "Davison"])

    backend_kwargs = {"base_url": state.api_base_url} if state.mode == "api" else {}
    backend = build_backend(state.mode, **backend_kwargs)

    with tabs[0]:
        st.subheader("Synastry: aspects, grid, scores")
        if st.button("Compute synastry", type="primary"):
            try:
                pos_a = _parse_positions(text_a)
                pos_b = _parse_positions(text_b)
            except ValueError as exc:
                st.error(str(exc))
            else:
                payload = {
                    "posA": pos_a,
                    "posB": pos_b,
                    "aspects": list(get_state(st).aspects),
                }
                weights = _weights_payload(get_state(st).weights_profile, payload["aspects"])
                if weights:
                    payload["per_aspect_weight"] = weights
                try:
                    result = backend.synastry(payload)
                except Exception as exc:
                    st.error(f"Failed to compute synastry: {exc}")
                else:
                    update_state(st, last_synastry=result)
        result = get_state(st).last_synastry
        if result:
            try:
                pos_a = _parse_positions(text_a)
                pos_b = _parse_positions(text_b)
            except ValueError:
                pos_a = {}
                pos_b = {}
            _wheel_section(pos_a, pos_b)
            hits = result.get("hits", [])
            filtered_hits = filter_hits(hits, get_state(st).min_severity)
            hits_df = render_hits_table(hits, min_severity=get_state(st).min_severity)
            grid_df = render_grid(result.get("grid", {}))
            scores_summary = render_scores(filtered_hits)
            overlay_df = render_overlay_table(result.get("overlay", {}))
            summary_text = build_summary_markdown("Synastry summary", filtered_hits, scores_summary)
            with st.expander("Copy summary", expanded=False):
                render_markdown_copy(summary_text)
            if hits_df is not None:
                st.download_button(
                    "Download hits CSV",
                    data=hits_df.to_csv(index=False).encode("utf-8"),
                    file_name="synastry_hits.csv",
                    mime="text/csv",
                )
            st.download_button(
                "Download synastry JSON",
                data=json.dumps(result, indent=2),
                file_name="synastry_result.json",
                mime="application/json",
            )
            with st.expander("Import saved synastry result", expanded=False):
                uploaded = st.file_uploader("Load synastry JSON", type=["json"], key="synastry_import")
                if uploaded is not None:
                    try:
                        payload = json.load(uploaded)
                    except json.JSONDecodeError as exc:
                        st.error(f"Failed to decode synastry JSON: {exc}")
                    else:
                        if isinstance(payload, Mapping):
                            update_state(st, last_synastry=payload)
                            st.experimental_rerun()
                        else:
                            st.error("Synastry JSON must be an object.")

    with tabs[1]:
        st.subheader("Composite — midpoint positions")
        if st.button("Compute composite"):
            try:
                pos_a = _parse_positions(text_a)
                pos_b = _parse_positions(text_b)
            except ValueError as exc:
                st.error(str(exc))
            else:
                bodies = sorted(set(pos_a) & set(pos_b)) or None
                payload = {"posA": pos_a, "posB": pos_b}
                if bodies:
                    payload["bodies"] = bodies
                try:
                    result = backend.composite(payload)
                except Exception as exc:
                    st.error(f"Failed to compute composite positions: {exc}")
                else:
                    update_state(st, last_composite=result)
        result = get_state(st).last_composite
        if result:
            positions = result.get("positions", {})
            if positions:
                df = pd.DataFrame({"Body": list(positions.keys()), "Longitude": [positions[k] for k in positions]})
                st.dataframe(df, use_container_width=True, hide_index=True)
                _composite_wheel("Composite wheel", positions)
                st.download_button(
                    "Download composite JSON",
                    data=json.dumps(result, indent=2),
                    file_name="composite_positions.json",
                    mime="application/json",
                )
            else:
                st.info("Composite result does not contain positions.")

    with tabs[2]:
        st.subheader("Davison — midpoint chart")
        now = datetime.now(UTC)
        col_dt_a, col_dt_b = st.columns(2)
        dt_a = col_dt_a.datetime_input("Chart A datetime (UTC)", value=now - timedelta(days=7))
        dt_b = col_dt_b.datetime_input("Chart B datetime (UTC)", value=now)
        col_geo_a, col_geo_b = st.columns(2)
        lat_a = col_geo_a.number_input("Chart A latitude (°)", -90.0, 90.0, value=0.0, step=0.1)
        lon_a = col_geo_a.number_input("Chart A longitude east (°)", -180.0, 180.0, value=0.0, step=0.1)
        lat_b = col_geo_b.number_input("Chart B latitude (°)", -90.0, 90.0, value=0.0, step=0.1)
        lon_b = col_geo_b.number_input("Chart B longitude east (°)", -180.0, 180.0, value=0.0, step=0.1)
        bodies_text = st.text_input("Bodies (comma separated, optional)", value=", ".join(get_state(st).aspects[:5]))
        if st.button("Compute Davison"):
            def _ensure_utc(dt: datetime) -> datetime:
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=UTC)
                return dt.astimezone(UTC)

            dt_a_utc = _ensure_utc(dt_a)
            dt_b_utc = _ensure_utc(dt_b)
            bodies = [part.strip() for part in bodies_text.split(",") if part.strip()]
            payload = {
                "dtA": dt_a_utc.isoformat(),
                "dtB": dt_b_utc.isoformat(),
                "locA": {"lat_deg": float(lat_a), "lon_deg_east": float(lon_a)},
                "locB": {"lat_deg": float(lat_b), "lon_deg_east": float(lon_b)},
            }
            if bodies:
                payload["bodies"] = bodies
            try:
                result = backend.davison(payload)
            except Exception as exc:
                st.error(f"Failed to compute Davison positions: {exc}")
            else:
                update_state(st, last_davison=result)
        result = get_state(st).last_davison
        if result:
            midpoint = result.get("midpoint_time_utc")
            if midpoint:
                st.caption(f"Midpoint UTC: {midpoint}")
            positions = result.get("positions", {})
            if positions:
                df = pd.DataFrame({"Body": list(positions.keys()), "Longitude": [positions[k] for k in positions]})
                st.dataframe(df, use_container_width=True, hide_index=True)
                _composite_wheel("Davison wheel", positions)
                st.download_button(
                    "Download Davison JSON",
                    data=json.dumps(result, indent=2),
                    file_name="davison_positions.json",
                    mime="application/json",
                )
            else:
                st.info("Davison result did not include positions.")


if __name__ == "__main__":  # pragma: no cover - manual execution guard
    run()
