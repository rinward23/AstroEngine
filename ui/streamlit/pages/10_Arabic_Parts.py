from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Arabic Parts", page_icon="⚙️", layout="wide")
st.title("Arabic Parts — Fortune & Companions ⚙️")

api = APIClient()

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def _load_natals() -> list[dict[str, Any]]:
    try:
        return api.list_natals_items(page_size=100)
    except Exception as exc:  # pragma: no cover - UI feedback only
        st.sidebar.error(f"Unable to load natals: {exc}")
        return []


def _format_longitude(value: float) -> tuple[float, str]:
    lon = float(value) % 360.0
    sign_index = int(lon // 30.0)
    sign_name = SIGNS[sign_index]
    degrees_in_sign = lon % 30.0
    deg = int(degrees_in_sign)
    minutes_float = (degrees_in_sign - deg) * 60.0
    minutes = int(minutes_float)
    seconds = int(round((minutes_float - minutes) * 60.0))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        deg += 1
    if deg == 30:
        deg = 0
        sign_index = (sign_index + 1) % 12
        sign_name = SIGNS[sign_index]
    sign_str = f"{sign_name} {deg:02d}°{minutes:02d}'{seconds:02d}\""
    return lon, sign_str


def _build_dataframe(results: dict[str, Any]) -> pd.DataFrame:
    lots = results.get("lots", []) if isinstance(results, dict) else []
    rows: list[dict[str, Any]] = []
    for entry in lots:
        if not isinstance(entry, dict):
            continue
        try:
            raw_lon = float(entry.get("longitude", 0.0))
        except (TypeError, ValueError):
            continue
        lon, sign = _format_longitude(raw_lon)
        rows.append(
            {
                "Lot": entry.get("name"),
                "Longitude (°)": lon,
                "Sign": sign,
                "House": entry.get("house"),
                "Source": entry.get("source"),
                "Description": entry.get("description"),
                "Day Formula": entry.get("day_formula"),
                "Night Formula": entry.get("night_formula"),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "Lot",
                "Longitude (°)",
                "Sign",
                "House",
                "Source",
                "Description",
                "Day Formula",
                "Night Formula",
            ]
        )
    df = pd.DataFrame(rows)
    return df.sort_values("Lot").reset_index(drop=True)


natals = _load_natals()

st.sidebar.header("Natal Selection")
if not natals:
    st.sidebar.info("No natal charts available. Add a chart via the Natals panel.")
    st.stop()

options = {item.get("natal_id"): item for item in natals if isinstance(item, dict)}
labels = [
    f"{details.get('name') or details.get('natal_id')} ({nid})"
    for nid, details in options.items()
]

selected_label = st.sidebar.selectbox("Natal chart", options=labels)
selected_id = None
for nid, details in options.items():
    label = f"{details.get('name') or details.get('natal_id')} ({nid})"
    if label == selected_label:
        selected_id = nid
        selected_details = details
        break
else:  # pragma: no cover - defensive fallback
    st.sidebar.error("Unable to determine selected natal chart.")
    st.stop()

try:
    response = api.analysis_lots(selected_id)
except Exception as exc:  # pragma: no cover - UI feedback only
    st.error(f"API error: {exc}")
    st.stop()

metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
is_day = response.get("is_day") if isinstance(response, dict) else None
moment = response.get("moment") if isinstance(response, dict) else None

info_cols = st.columns(3)
with info_cols[0]:
    st.metric("Natal", selected_details.get("name") or selected_id)
with info_cols[1]:
    st.metric("Moment (UTC)", str(moment))
with info_cols[2]:
    st.metric("Sect", "Day" if is_day else "Night")

st.caption(
    "House system: {house} · Zodiac: {zodiac}".format(
        house=metadata.get("house_system", "?"),
        zodiac=metadata.get("zodiac", "?"),
    )
)

results_df = _build_dataframe(response)
if results_df.empty:
    st.info("No lots computed. Check settings.arabic_parts to enable presets or define custom lots.")
else:
    st.dataframe(results_df, use_container_width=True, hide_index=True)

with st.expander("Formulas", expanded=False):
    if results_df.empty:
        st.write("No formulas available.")
    else:
        for _, row in results_df.iterrows():
            st.markdown(
                f"**{row['Lot']}** — {row['Source'].title()}\n\n"
                f"• Day: `{row['Day Formula']}`\n\n"
                f"• Night: `{row['Night Formula']}`\n"
            )
