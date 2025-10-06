from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

if __package__ is None or __package__ == "":  # pragma: no cover - runtime import guard
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Electional Constraint Search", page_icon="🗳️", layout="wide")
st.title("Electional Constraint Search 🗳️")
api = APIClient()

BODIES = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
]
AXES = {
    "Ascendant": "asc",
    "Descendant": "desc",
    "Midheaven": "mc",
    "Imum Coeli": "ic",
}
ASPECT_TYPES = [
    "conjunction",
    "sextile",
    "square",
    "trine",
    "opposition",
    "quincunx",
]


def _init_state() -> None:
    st.session_state.setdefault("aspect_constraints", [])
    st.session_state.setdefault("antiscia_constraints", [])
    st.session_state.setdefault("declination_constraints", [])


def _datetime_input(label: str, value: datetime, key: str) -> datetime:
    base = value.astimezone(UTC)
    date_val = st.date_input(f"{label} date", base.date(), key=f"{key}_date")
    time_val = st.time_input(f"{label} time", base.time(), key=f"{key}_time")
    return datetime.combine(date_val, time_val, tzinfo=UTC)


def _add_aspect_constraint() -> None:
    body = st.session_state.get("_aspect_body")
    target = st.session_state.get("_aspect_target")
    aspect = st.session_state.get("_aspect_type")
    orb = st.session_state.get("_aspect_orb")
    if not body or not target or not aspect:
        st.warning("Select body, target, and aspect before adding.")
        return
    target_value = AXES.get(target, target)
    entry = {
        "aspect": {
            "body": body.lower(),
            "target": target_value,
            "type": aspect,
            "max_orb": orb,
        }
    }
    st.session_state.aspect_constraints.append(entry)


def _add_antiscia_constraint() -> None:
    body = st.session_state.get("_antiscia_body")
    target = st.session_state.get("_antiscia_target")
    orb = st.session_state.get("_antiscia_orb")
    kind = st.session_state.get("_antiscia_type")
    axis = st.session_state.get("_antiscia_axis")
    if not body or not target:
        st.warning("Select both bodies for antiscia constraint.")
        return
    entry = {
        "antiscia": {
            "body": body.lower(),
            "target": target.lower(),
            "type": kind,
            "axis": axis,
            "max_orb": orb,
        }
    }
    st.session_state.antiscia_constraints.append(entry)


def _add_declination_constraint() -> None:
    body = st.session_state.get("_decl_body")
    target = st.session_state.get("_decl_target")
    orb = st.session_state.get("_decl_orb")
    kind = st.session_state.get("_decl_type")
    if not body or not target:
        st.warning("Select both bodies for declination constraint.")
        return
    entry = {
        "declination": {
            "body": body.lower(),
            "target": target.lower(),
            "type": kind,
            "max_orb": orb,
        }
    }
    st.session_state.declination_constraints.append(entry)


def _constraints_payload(avoid_voc: bool, voc_orb: float, avoid_malefic: bool, malefic_orb: float) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    payload.extend(st.session_state.aspect_constraints)
    payload.extend(st.session_state.antiscia_constraints)
    payload.extend(st.session_state.declination_constraints)
    if avoid_voc:
        payload.append({"moon": {"void_of_course": False, "max_orb": voc_orb}})
    if avoid_malefic:
        payload.append({"malefic_to_angles": {"allow": False, "max_orb": malefic_orb}})
    return payload


_init_state()

with st.sidebar:
    st.header("Scan Window")
    now = datetime.now(UTC)
    start = _datetime_input("Start (UTC)", value=now, key="start")
    end = _datetime_input("End (UTC)", value=now + timedelta(days=7), key="end")
    step_minutes = st.number_input("Step minutes", min_value=1, max_value=720, value=30, step=5)
    limit = st.number_input("Result limit", min_value=1, max_value=200, value=50, step=1)
    st.header("Location")
    lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=0.0, step=0.1)
    lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=0.0, step=0.1)
    st.header("Filters")
    avoid_voc = st.toggle("Avoid void-of-course Moon", value=True)
    voc_orb = st.number_input("VoC orb (°)", min_value=0.5, max_value=12.0, value=6.0, step=0.5)
    avoid_malefic = st.toggle("Avoid malefics on angles", value=True)
    malefic_orb = st.number_input("Malefic/angle orb (°)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)

st.subheader("Aspect Constraints")
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    st.selectbox("Body", BODIES, key="_aspect_body")
with col2:
    st.selectbox("Target", BODIES + list(AXES.keys()), key="_aspect_target")
with col3:
    st.selectbox("Aspect", ASPECT_TYPES, key="_aspect_type")
with col4:
    st.number_input("Max orb", min_value=0.1, max_value=12.0, value=3.0, step=0.1, key="_aspect_orb")
add_aspect = st.button("➕ Add aspect")
if add_aspect:
    _add_aspect_constraint()

if st.session_state.aspect_constraints:
    df_aspects = pd.DataFrame([row["aspect"] for row in st.session_state.aspect_constraints])
    st.dataframe(df_aspects, use_container_width=True)
    if st.button("🧹 Clear aspects"):
        st.session_state.aspect_constraints = []
        st.experimental_rerun()

with st.expander("Advanced: Antiscia / Declination", expanded=False):
    st.markdown("**Antiscia constraint**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.selectbox("Body", BODIES, key="_antiscia_body")
    with c2:
        st.selectbox("Target", BODIES, key="_antiscia_target")
    with c3:
        st.selectbox("Type", ["antiscia", "contra"], key="_antiscia_type")
    with c4:
        st.number_input("Orb", min_value=0.1, max_value=6.0, value=2.0, step=0.1, key="_antiscia_orb")
    st.text_input("Axis", value="aries_libra", key="_antiscia_axis")
    if st.button("➕ Add antiscia"):
        _add_antiscia_constraint()

    if st.session_state.antiscia_constraints:
        df_anti = pd.DataFrame([row["antiscia"] for row in st.session_state.antiscia_constraints])
        st.dataframe(df_anti, use_container_width=True)
        if st.button("🧹 Clear antiscia"):
            st.session_state.antiscia_constraints = []
            st.experimental_rerun()

    st.markdown("**Declination constraint**")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.selectbox("Body", BODIES, key="_decl_body")
    with d2:
        st.selectbox("Target", BODIES, key="_decl_target")
    with d3:
        st.selectbox("Type", ["parallel", "contraparallel"], key="_decl_type")
    with d4:
        st.number_input("Orb", min_value=0.1, max_value=3.0, value=1.0, step=0.1, key="_decl_orb")
    if st.button("➕ Add declination"):
        _add_declination_constraint()
    if st.session_state.declination_constraints:
        df_decl = pd.DataFrame([row["declination"] for row in st.session_state.declination_constraints])
        st.dataframe(df_decl, use_container_width=True)
        if st.button("🧹 Clear declination"):
            st.session_state.declination_constraints = []
            st.experimental_rerun()

constraints_payload = _constraints_payload(avoid_voc, voc_orb, avoid_malefic, malefic_orb)

st.divider()
st.subheader("Search")
st.json(constraints_payload)

if st.button("🔎 Run search", type="primary"):
    if end <= start:
        st.error("End must be after start")
        st.stop()
    if not constraints_payload:
        st.error("Add at least one constraint or enable a filter.")
        st.stop()

    payload = {
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "step_minutes": int(step_minutes),
        "location": {"lat": float(lat), "lon": float(lon)},
        "constraints": constraints_payload,
        "limit": int(limit),
    }
    try:
        response = api.electional_search(payload)
    except Exception as exc:  # pragma: no cover - UI surface
        st.error(f"API error: {exc}")
        st.stop()

    candidates = response.get("candidates", [])
    if not candidates:
        st.info("No instants satisfied all constraints.")
        st.stop()

    table = []
    for item in candidates:
        ts = item.get("ts")
        score = item.get("score")
        table.append({"timestamp": ts, "score": score})
    df = pd.DataFrame(table)
    st.dataframe(df, use_container_width=True)

    selected = st.selectbox("Inspect candidate", options=range(len(candidates)), format_func=lambda idx: candidates[idx].get("ts", f"#{idx}"))
    detail = candidates[int(selected)]
    evaluations = pd.DataFrame(detail.get("evaluations", []))
    st.subheader("Constraint evaluations")
    st.dataframe(evaluations, use_container_width=True)

