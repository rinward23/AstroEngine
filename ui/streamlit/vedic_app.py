"""Streamlit viewer for AstroEngine's Vedic toolkit."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from astroengine.chart.config import VALID_NODE_VARIANTS
from astroengine.detectors.ingresses import ZODIAC_SIGNS, sign_index
from astroengine.engine.vedic import (
    VARGA_DEFINITIONS,
    VimshottariOptions,
    build_context,
    build_vimshottari,
    build_yogini,
    compute_varga,
    nakshatra_info,
    nakshatra_of,
    position_for,
)
from astroengine.engine.vedic.dasha_yogini import YoginiOptions

from ui.streamlit.api import APIClient
from .components import location_picker


def _serialize_period(period) -> dict[str, Any]:
    return {
        "system": period.system,
        "level": period.level,
        "ruler": period.ruler,
        "start": _iso(period.start),
        "end": _iso(period.end),
        "metadata": period.metadata,
    }

st.set_page_config(page_title="AstroEngine Vedic Viewer", layout="wide")

api = APIClient()


@st.cache_data(show_spinner=False)
def _profile_catalog() -> dict[str, list[str]]:
    try:
        return api.list_profiles()
    except Exception:  # pragma: no cover - network/path issues
        return {"built_in": [], "user": []}


def _apply_profile_defaults(profile_name: str) -> None:
    try:
        settings = api.get_profile_settings(profile_name)
    except Exception as exc:  # pragma: no cover - network/path issues
        st.error(f"Unable to load profile '{profile_name}': {exc}")
        return
    st.session_state["vedic_profile_defaults"] = settings
    zodiac = settings.get("zodiac", {})
    houses = settings.get("houses", {})
    if "type" in zodiac:
        st.session_state["vedic_zodiac_type"] = str(zodiac.get("type", "tropical"))
    if "ayanamsa" in zodiac:
        st.session_state["vedic_ayanamsa"] = str(zodiac.get("ayanamsa", "lahiri"))
    if "system" in houses:
        st.session_state["vedic_house_system"] = str(houses.get("system", "whole_sign"))
    st.session_state["vedic_profile_applied"] = profile_name
    st.experimental_rerun()

AYANAMSA_CHOICES = [
    "lahiri",
    "krishnamurti",
    "raman",
    "fagan_bradley",
    "yukteshwar",
    "galactic_center_0_sag",
    "sassanian",
    "deluce",
]

NODE_VARIANT_CHOICES = sorted(VALID_NODE_VARIANTS)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _to_utc(value).isoformat().replace("+00:00", "Z")


def _nakshatra_payload(name: str, longitude: float) -> dict[str, Any]:
    idx = nakshatra_of(longitude)
    info = nakshatra_info(idx)
    pos = position_for(longitude)
    sign_idx = sign_index(longitude)
    return {
        "Body": name,
        "Longitude": round(longitude % 360.0, 4),
        "Sign": ZODIAC_SIGNS[sign_idx],
        "Nakshatra": info.name,
        "Pada": pos.pada,
        "Lord": info.lord,
        "Deg in Pada": round(pos.degree_in_pada, 4),
    }


def _build_wheel(data: list[dict[str, Any]], title: str) -> go.Figure:
    fig = go.Figure()
    for idx in range(12):
        start = idx * 30
        end = start + 30
        fig.add_trace(
            go.Scatterpolar(
                r=[1, 1],
                theta=[360 - start, 360 - end],
                mode="lines",
                line=dict(color="#888", width=0.6),
                showlegend=False,
            )
        )
    for row in data:
        theta = (360.0 - row["Longitude"]) % 360.0
        fig.add_trace(
            go.Scatterpolar(
                r=[1.02],
                theta=[theta],
                mode="markers+text",
                marker=dict(size=10),
                text=[row["Body"]],
                textposition="top center",
                name=row["Body"],
            )
        )
    fig.update_layout(
        title=title,
        polar=dict(
            radialaxis=dict(visible=False),
            angularaxis=dict(direction="clockwise", rotation=90, tickmode="array", tickvals=[i * 30 for i in range(12)], ticktext=ZODIAC_SIGNS),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=20),
    )
    return fig


def _dasha_dataframe(periods) -> pd.DataFrame:
    rows = []
    for period in periods:
        rows.append(
            {
                "Level": period.level,
                "Ruler": period.ruler,
                "Start": _iso(period.start),
                "End": _iso(period.end),
                "Span (days)": round((period.end - period.start).total_seconds() / 86400.0, 3),
                "Metadata": period.metadata,
            }
        )
    return pd.DataFrame(rows)


st.title("Vedic Astrology Dashboard")

profiles = _profile_catalog()
profile_options = ["—"] + profiles.get("built_in", []) + profiles.get("user", [])
with st.sidebar:
    st.subheader("Profiles")
    selected_profile = st.selectbox(
        "Apply profile defaults",
        profile_options,
        index=profile_options.index(st.session_state.get("vedic_profile_applied", "—"))
        if st.session_state.get("vedic_profile_applied", "—") in profile_options
        else 0,
        help="Fetches settings from the Profiles API and applies them to this form.",
        key="vedic_profile_choice",
    )
    if selected_profile != "—" and st.button("Apply profile", type="secondary"):
        _apply_profile_defaults(selected_profile)
    if st.session_state.get("vedic_profile_applied"):
        st.caption(
            f"Defaults sourced from profile: {st.session_state['vedic_profile_applied']}"
        )

with st.sidebar:
    st.header("Inputs")
    date_value = st.date_input("Date", datetime(1990, 5, 4).date())
    time_value = st.time_input("Time (UTC)", datetime(1990, 5, 4, 12, 30).time())
    location_picker(
        "Birth location",
        default_query="New York, United States",
        state_prefix="vedic_location",
        help="Atlas-backed lookup populates the coordinates and timezone context.",
    )
    lat_default = float(st.session_state.get("vedic_location_lat", 40.7128))
    lon_default = float(st.session_state.get("vedic_location_lon", -74.0060))
    lat = st.number_input("Latitude", value=lat_default, format="%.4f")
    lon = st.number_input("Longitude", value=lon_default, format="%.4f")
    st.session_state["vedic_location_lat"] = float(lat)
    st.session_state["vedic_location_lon"] = float(lon)
    zodiac_options = ["tropical", "sidereal"]
    default_zodiac = st.session_state.get("vedic_zodiac_type", zodiac_options[0])
    if default_zodiac not in zodiac_options:
        default_zodiac = zodiac_options[0]
        st.session_state["vedic_zodiac_type"] = default_zodiac
    zodiac_type = st.selectbox(
        "Zodiac",
        zodiac_options,
        index=zodiac_options.index(default_zodiac),
        key="vedic_zodiac_type",
    )
    default_ayanamsa = st.session_state.get("vedic_ayanamsa", AYANAMSA_CHOICES[0])
    if default_ayanamsa not in AYANAMSA_CHOICES:
        default_ayanamsa = AYANAMSA_CHOICES[0]
        st.session_state["vedic_ayanamsa"] = default_ayanamsa
    ayanamsa = st.selectbox(
        "Ayanamsa",
        AYANAMSA_CHOICES,
        index=AYANAMSA_CHOICES.index(default_ayanamsa),
        key="vedic_ayanamsa",
    )
    house_options = ["whole_sign", "placidus", "koch"]
    default_house = st.session_state.get("vedic_house_system", house_options[0])
    if default_house not in house_options:
        default_house = house_options[0]
        st.session_state["vedic_house_system"] = default_house
    house_system = st.selectbox(
        "House system",
        house_options,
        index=house_options.index(default_house),
        key="vedic_house_system",
    )
    node_variant_index = NODE_VARIANT_CHOICES.index("mean") if "mean" in NODE_VARIANT_CHOICES else 0
    nodes_variant = st.selectbox(
        "Lunar node variant",
        NODE_VARIANT_CHOICES,
        index=node_variant_index,
        help="Choose whether to use mean or true lunar nodes when casting the chart.",
    )
    level_choice = st.slider("Vimśottarī levels", min_value=1, max_value=3, value=3)

moment = datetime.combine(date_value, time_value).replace(tzinfo=UTC)
context = build_context(
    moment,
    lat,
    lon,
    ayanamsa=ayanamsa,
    house_system=house_system,
    nodes_variant=nodes_variant,
)
chart = context.chart

positions = [_nakshatra_payload(name, pos.longitude) for name, pos in chart.positions.items()]
asc_value = chart.houses.ascendant if chart.houses else None
if asc_value is not None:
    positions.append(_nakshatra_payload("Ascendant", asc_value))

vim_periods = build_vimshottari(context, levels=level_choice, options=VimshottariOptions())
yogini_periods = build_yogini(context, levels=2, options=YoginiOptions())

varga_codes = ["D3", "D7", "D9", "D10", "D12", "D16", "D24", "D45", "D60"]
varga_results = {
    code: compute_varga(chart.positions, code, ascendant=asc_value)
    for code in varga_codes
}
navamsa = varga_results["D9"]
dasamsa = varga_results["D10"]


chart_tab, nak_tab, dasha_tab, varga_tab, export_tab = st.tabs(
    ["Chart", "Nakshatras", "Dashas", "Vargas", "Export"]
)

with chart_tab:
    st.subheader("Sidereal Chart Overview")
    meta_cols = st.columns(5)
    meta_cols[0].metric("Ayanamsa", chart.ayanamsa or "-")
    meta_cols[1].metric("Ayanamsa °", f"{chart.ayanamsa_degrees:.6f}" if chart.ayanamsa_degrees is not None else "-")
    meta_cols[2].metric("House System", chart.metadata.get("house_system") if chart.metadata else house_system)
    meta_cols[3].metric("Moment", _iso(chart.moment))
    meta_cols[4].metric("Node Variant", context.config.nodes_variant.title())
    st.plotly_chart(_build_wheel(positions, "Sidereal Wheel"), use_container_width=True)
    st.dataframe(pd.DataFrame(positions), use_container_width=True)

with nak_tab:
    st.subheader("Nakshatra Highlights")
    moon_row = next((row for row in positions if row["Body"] == "Moon"), None)
    asc_row = next((row for row in positions if row["Body"] == "Ascendant"), None)
    cols = st.columns(2)
    if moon_row:
        cols[0].write("**Moon**")
        cols[0].json(moon_row)
    if asc_row:
        cols[1].write("**Ascendant**")
        cols[1].json(asc_row)
    st.write("All placements")
    st.dataframe(pd.DataFrame(positions), use_container_width=True)

with dasha_tab:
    st.subheader("Vimśottarī")
    st.dataframe(_dasha_dataframe(vim_periods), use_container_width=True)
    st.subheader("Yoginī")
    st.dataframe(_dasha_dataframe(yogini_periods), use_container_width=True)

with varga_tab:

    for code in varga_codes:
        definition = VARGA_DEFINITIONS[code]
        st.subheader(f"{definition.name} ({code})")
        st.caption(definition.rule_description)
        data = varga_results[code]
        st.dataframe(pd.DataFrame.from_dict(data, orient="index"), use_container_width=True)
        if code in {"D9", "D10"}:
            st.plotly_chart(
                _build_wheel(
                    [
                        {"Body": name, "Longitude": payload["longitude"]}
                        for name, payload in data.items()
                    ],
                    f"{definition.name} Wheel",
                ),
                use_container_width=True,
            )


with export_tab:
    st.subheader("Export JSON")
    payload = {
        "metadata": {
            "moment": _iso(chart.moment),
            "ayanamsa": chart.ayanamsa,
            "ayanamsa_degrees": chart.ayanamsa_degrees,
            "location": {"lat": lat, "lon": lon},
        },
        "positions": positions,
        "vimshottari": [_serialize_period(period) for period in vim_periods],
        "yogini": [_serialize_period(period) for period in yogini_periods],
        "rasi": rasi,
        "saptamsa": saptamsa,
        "navamsa": navamsa,
        "dasamsa": dasamsa,

        "vargas": varga_results,

    }
    st.download_button(
        "Download JSON",
        data=json.dumps(payload, indent=2, default=str),
        file_name="vedic_chart.json",
        mime="application/json",
    )
