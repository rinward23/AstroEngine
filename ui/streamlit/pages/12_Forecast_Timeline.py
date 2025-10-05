from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Forecast Timeline", page_icon="🔭", layout="wide")
st.title("Forecast Timeline 🔭")

api = APIClient()

TECHNIQUE_OPTIONS = ["transits", "progressions", "solar_arc"]

def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


st.sidebar.header("Configuration")

try:
    natal_records = api.list_natals()
except Exception as exc:  # pragma: no cover - streamlit runtime
    natal_records = []
    st.sidebar.warning(f"Unable to load stored natals: {exc}")

if natal_records:
    options = [record.get("natal_id") for record in natal_records if record.get("natal_id")]
    if options:
        natal_id = st.sidebar.selectbox("Natal ID", options=options, index=0)
    else:
        natal_id = st.sidebar.text_input("Natal ID", value="")
else:
    natal_id = st.sidebar.text_input("Natal ID", value="")

preset = st.sidebar.radio(
    "Quick preset",
    options=["7 days", "30 days", "1 year", "Custom"],
    index=1,
)
now = datetime.now(tz=UTC)
if preset == "Custom":
    start_date = st.sidebar.date_input("Start date", value=now.date())
    end_date = st.sidebar.date_input("End date", value=(now + timedelta(days=30)).date())
    start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=UTC)
else:
    span = {"7 days": 7, "30 days": 30, "1 year": 365}[preset]
    start_dt = now
    end_dt = now + timedelta(days=span)

selected_techniques = st.sidebar.multiselect(
    "Techniques",
    TECHNIQUE_OPTIONS,
    default=TECHNIQUE_OPTIONS,
)

fetch_button = st.sidebar.button("Fetch timeline", type="primary")

if fetch_button:
    if not natal_id:
        st.error("Provide a natal identifier to build the forecast stack.")
        st.stop()

    if end_dt <= start_dt:
        st.error("End date must be after the start date.")
        st.stop()

    params_techniques = selected_techniques if set(selected_techniques) != set(TECHNIQUE_OPTIONS) else None

    with st.spinner("Loading forecast stack..."):
        try:
            payload = api.forecast_stack(natal_id, _iso(start_dt), _iso(end_dt), techniques=params_techniques)
        except Exception as exc:  # pragma: no cover - runtime guard
            st.error(f"API request failed: {exc}")
            st.stop()

    events = payload.get("events", [])
    if not events:
        st.info("No forecast events for the selected window.")
        st.stop()

    df = pd.DataFrame(events)
    df["start"] = pd.to_datetime(df["start"], utc=True, errors="coerce")
    df["end"] = pd.to_datetime(df["end"], utc=True, errors="coerce")
    df.dropna(subset=["start", "end"], inplace=True)

    csv_text: str | None = None
    try:
        csv_text = api.forecast_stack_csv(natal_id, _iso(start_dt), _iso(end_dt), techniques=params_techniques)
    except Exception as exc:  # pragma: no cover - runtime guard
        st.warning(f"CSV export unavailable: {exc}")

    if csv_text is not None:
        try:
            csv_df = pd.read_csv(StringIO(csv_text))
            if len(csv_df) != len(df):
                st.warning("CSV export row count differs from JSON payload.")
        except Exception as exc:  # pragma: no cover - runtime guard
            st.warning(f"Could not validate CSV export: {exc}")

    st.subheader("Filters")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        bodies = sorted(df["body"].unique())
        selected_bodies = st.multiselect("Bodies", bodies, default=bodies)
    with col_b:
        aspects = sorted(df["aspect"].unique())
        selected_aspects = st.multiselect("Aspects", aspects, default=aspects)
    with col_c:
        techniques_filter = st.multiselect(
            "Techniques", TECHNIQUE_OPTIONS, default=selected_techniques or TECHNIQUE_OPTIONS
        )

    filtered = df[
        df["body"].isin(selected_bodies)
        & df["aspect"].isin(selected_aspects)
        & df["technique"].isin(techniques_filter)
    ].copy()

    if filtered.empty:
        st.warning("All events were filtered out. Adjust the filters to see results.")
        st.stop()

    display_df = filtered.copy()
    mask_zero = display_df["end"] <= display_df["start"]
    display_df.loc[mask_zero, "end"] = display_df.loc[mask_zero, "start"] + pd.Timedelta(minutes=1)

    st.subheader("Timeline")
    fig = px.timeline(
        display_df,
        x_start="start",
        x_end="end",
        y="body",
        color="technique",
        hover_data={
            "start": "|%Y-%m-%d %H:%M UTC",
            "end": "|%Y-%m-%d %H:%M UTC",
            "aspect": True,
            "target": True,
            "exactness": ".3f",
        },
    )
    fig.update_layout(height=600, showlegend=True)
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Event Table")
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Export")
    if csv_text is not None:
        st.download_button(
            "Download CSV",
            csv_text.encode("utf-8"),
            file_name="forecast_stack.csv",
            mime="text/csv",
        )
    else:
        st.caption("CSV export not available for this query.")

    filtered_csv = filtered.to_csv(index=False)
    st.download_button(
        "Download filtered CSV",
        filtered_csv.encode("utf-8"),
        file_name="forecast_stack_filtered.csv",
        mime="text/csv",
    )
else:
    st.caption("Configure a natal chart and window in the sidebar, then click **Fetch timeline**.")
