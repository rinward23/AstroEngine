from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Dignities & Condition", page_icon="⚖️", layout="wide")
st.title("Dignities & Planetary Condition ⚖️")

api = APIClient()

with st.sidebar:
    st.header("Natal selection")
    default_id = st.session_state.get("dignities_last_id", "")
    natal_id = st.text_input("Natal ID", value=default_id, help="Identifier from the Natals vault")
    run_button = st.button("Analyze", type="primary")

if not run_button:
    st.info("Enter a natal ID from the vault and click Analyze to compute the report.")
    st.stop()

natal_id = natal_id.strip()
if not natal_id:
    st.error("Natal ID is required.")
    st.stop()

st.session_state["dignities_last_id"] = natal_id

try:
    payload = api.dignities_analysis(natal_id)
except Exception as exc:  # pragma: no cover - user facing
    st.error(f"API error: {exc}")
    st.stop()

settings = payload.get("settings", {})
if not settings.get("enabled", False):
    st.warning("Server configuration has dignity scoring disabled.")
    st.stop()

chart_meta: Dict[str, Any] = payload.get("chart", {})
natal_meta: Dict[str, Any] = payload.get("natal", {})
sect = chart_meta.get("sect", {})
label = sect.get("label", "day").title()
col1, col2, col3 = st.columns(3)
col1.metric("Total Essential", payload.get("totals", {}).get("essential", 0))
col2.metric("Total Accidental", payload.get("totals", {}).get("accidental", 0))
col3.metric("Overall", payload.get("totals", {}).get("overall", 0))

with st.expander("Chart context", expanded=True):
    if natal_meta:
        st.write({k: v for k, v in natal_meta.items() if v is not None})
    if chart_meta:
        st.write({
            "moment": chart_meta.get("moment"),
            "house_system": chart_meta.get("house_system"),
            "sect_label": label,
            "luminary": sect.get("luminary"),
            "benefic": sect.get("benefic"),
            "malefic": sect.get("malefic"),
            "sun_altitude_deg": sect.get("sun_altitude_deg"),
        })

planets: Dict[str, Any] = payload.get("planets", {})
rows = []
for planet, info in planets.items():
    rows.append(
        {
            "Planet": planet,
            "Sign": info.get("sign"),
            "Degree": round(float(info.get("degree_in_sign", 0.0)), 2),
            "House": info.get("house"),
            "Retrograde": bool(info.get("retrograde", False)),
            "Essential": info.get("essential", {}).get("score", 0),
            "Accidental": info.get("accidental", {}).get("score", 0),
            "Total": info.get("total", 0),
        }
    )

df = pd.DataFrame(rows)
if df.empty:
    st.warning("No planetary positions were returned in the report.")
    st.stop()

styled = df.style.background_gradient(subset=["Essential", "Accidental", "Total"], cmap="RdYlGn")
st.dataframe(styled, use_container_width=True, hide_index=True)

for planet, info in planets.items():
    with st.expander(f"{planet} breakdown", expanded=False):
        essential_components = info.get("essential", {}).get("components", [])
        accidental_components = info.get("accidental", {}).get("components", [])
        if essential_components:
            ess_df = pd.DataFrame(essential_components)
            st.subheader("Essential factors")
            st.dataframe(ess_df, use_container_width=True, hide_index=True)
        if accidental_components:
            acc_df = pd.DataFrame(accidental_components)
            st.subheader("Accidental factors")
            st.dataframe(acc_df, use_container_width=True, hide_index=True)
        if not essential_components and not accidental_components:
            st.write("No dignity data available for this body.")
