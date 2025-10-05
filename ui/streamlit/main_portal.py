from __future__ import annotations

import os

import requests
import streamlit as st

from astroengine.config import load_settings
from ui.streamlit.components.chatgpt_panel import chatgpt_panel

st.set_page_config(page_title="AstroEngine Portal", layout="wide")

# --- Header / style ---------------------------------------------------------
st.markdown(
    """
    <style>
      .stMetric, .element-container { padding-top: 2px !important; }
      .gallery-card { border-radius: 16px; padding: 12px; background: var(--secondary-background-color); }
      .muted { color: #9aa0a6; font-size: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌌 AstroEngine — Main Portal")
settings = load_settings()

left, right = st.columns([7, 5], gap="large")

# --- Left: Multi-graphic gallery -------------------------------------------
with left:
    st.subheader("Visuals")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Chart", "Aspects", "Timeline", "Map", "Custom"])

    with tab1:
        st.markdown("**Chart Wheel**")
        # If your API exposes an image, render it. Otherwise, placeholder.
        url = os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/") + "/v1/plots/wheel"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                st.image(r.content, caption="Current Chart")
            else:
                st.info("Chart image endpoint not available yet. Add /v1/plots/wheel to the API to enable.")
        except Exception:
            st.info("Chart endpoint unreachable.")

    with tab2:
        st.markdown("**Aspect Grid**")
        url = os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/") + "/v1/plots/aspects"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                st.image(r.content, caption="Aspect Grid")
            else:
                st.info("Aspect grid not available yet. Add /v1/plots/aspects.")
        except Exception:
            st.info("Aspect endpoint unreachable.")

    with tab3:
        st.markdown("**Timeline**")
        url = os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/") + "/v1/timeline?from=now-30d&to=now+30d"
        try:
            r = requests.get(url, timeout=4)
            if r.ok:
                data = r.json()
                st.json(data[:25] if isinstance(data, list) else data)
            else:
                st.info("Timeline endpoint not ready. See Task 7/10.")
        except Exception:
            st.info("Timeline endpoint unreachable.")

    with tab4:
        st.markdown("**Astrocartography Map**")
        try:
            import pydeck as pdk

            # Expect GeoJSON FeatureCollection from /v1/astrocartography
            url = os.environ.get("ASTROENGINE_API", "http://127.0.0.1:8000").rstrip("/") + "/v1/astrocartography"
            r = requests.get(url, timeout=5)
            if r.ok:
                geo = r.json()
                layer = pdk.Layer("GeoJsonLayer", geo, pickable=True)
                view_state = pdk.ViewState(latitude=0, longitude=0, zoom=0.8)
                st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
            else:
                st.info("Map endpoint not ready. See Task 12.")
        except Exception:
            st.info("pydeck not installed or map endpoint unreachable.")

    with tab5:
        st.markdown("**Custom**")
        st.caption("Bring your own graphic here — embed images, tables, or KPIs.")
        st.write("")

# --- Right: ChatGPT ---------------------------------------------------------
with right:
    chatgpt_panel()
