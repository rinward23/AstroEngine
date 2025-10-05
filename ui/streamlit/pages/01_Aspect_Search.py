from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Aspect Search", page_icon="✨", layout="wide")
st.title("Aspect Search ✨")

api = APIClient()

# ------------------------------- Sidebar -----------------------------------
st.sidebar.header("Search Parameters")

DEFAULT_OBJECTS = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune","Pluto"]
DEFAULT_ASPECTS = [
    "conjunction",
    "opposition",
    "square",
    "trine",
    "sextile",
    "quincunx",
    "antiscia",
    "contra_antiscia",
]

objects: List[str] = st.sidebar.multiselect("Objects", DEFAULT_OBJECTS, default=["Sun","Moon","Mars","Venus"])
aspects: List[str] = st.sidebar.multiselect("Aspects", DEFAULT_ASPECTS, default=["sextile","trine","square"])
harmonics_str = st.sidebar.text_input("Harmonics (comma-sep)", value="5,7,13")

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start (UTC)", value=datetime.now(timezone.utc).date())
end_date = col2.date_input("End (UTC)", value=(datetime.now(timezone.utc) + timedelta(days=90)).date())

step_minutes = st.sidebar.slider("Step (minutes)", min_value=5, max_value=240, value=60, step=5)
order_by = st.sidebar.selectbox("Order by", options=["time","severity","orb"], index=0)
limit = st.sidebar.slider("Limit", min_value=50, max_value=2000, value=500, step=50)
offset = st.sidebar.number_input("Offset", min_value=0, value=0, step=100)

pair_source = objects if len(objects) >= 2 else DEFAULT_OBJECTS
pair_options: Dict[str, Tuple[str, str]] = {
    f"{a}–{b}": (a, b) for a, b in combinations(pair_source, 2)
}
selected_pairs = st.sidebar.multiselect(
    "Restrict to pairs (optional)",
    options=list(pair_options.keys()),
    default=[],
    help="If set, only matches from the selected pairs will be returned."
)

with st.sidebar.expander("Orb Policy (inline)", expanded=False):
    sextile = st.number_input("sextile orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
    square = st.number_input("square orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1)
    trine = st.number_input("trine orb", min_value=0.1, max_value=10.0, value=6.0, step=0.1)
    conj = st.number_input("conjunction orb", min_value=0.1, max_value=10.0, value=8.0, step=0.1)
    quincunx = st.number_input("quincunx orb", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
    adaptive_lum = st.slider("luminaries_factor", 0.5, 1.5, 0.9, 0.05)
    adaptive_out = st.slider("outers_factor", 0.5, 1.5, 1.1, 0.05)
    adaptive_minor = st.slider("minor_aspect_factor", 0.5, 1.5, 0.9, 0.05)

harmonics: List[int] = []
harmonics_parse_error = False
if harmonics_str.strip():
    try:
        harmonics = [int(x.strip()) for x in harmonics_str.split(',') if x.strip()]
    except ValueError:
        harmonics = []
        harmonics_parse_error = True
        st.sidebar.error("Invalid harmonics list; use comma-separated integers.")

start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
end_dt = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc)

validation_errors: List[str] = []
if len(objects) < 2:
    validation_errors.append("Select at least two objects.")
if not aspects:
    validation_errors.append("Select at least one aspect.")
if start_dt >= end_dt:
    validation_errors.append("End date must be after start date.")
if harmonics_parse_error:
    validation_errors.append("Fix the harmonics list before running the search.")

def _safe_dataframe(rows: List[Dict[str, object]] | List[object]) -> pd.DataFrame | None:
    """Build a DataFrame from arbitrary rows, returning ``None`` on schema errors."""

    if not rows:
        return pd.DataFrame()

    try:
        return pd.DataFrame(rows)
    except (TypeError, ValueError) as exc:
        st.error(f"Unable to display results: {exc}")
        return None


pairs_payload: List[Tuple[str, str]] | None = None
if selected_pairs:
    valid_labels = [label for label in selected_pairs if label in pair_options]
    if valid_labels:
        pairs_payload = [pair_options[label] for label in valid_labels]

payload = {
    "objects": objects,
    "aspects": aspects,
    "harmonics": harmonics,
    "window": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
    "orb_policy_inline": {
        "per_aspect": {
            "sextile": sextile,
            "square": square,
            "trine": trine,
            "conjunction": conj,
            "quincunx": quincunx,
        },
        "adaptive_rules": {
            "luminaries_factor": adaptive_lum,
            "outers_factor": adaptive_out,
            "minor_aspect_factor": adaptive_minor,
        }
    },
    "step_minutes": step_minutes,
    "limit": limit,
    "offset": offset,
    "order_by": order_by,
    "pairs": None,
}

if pairs_payload:
    payload["pairs"] = [list(pair) for pair in pairs_payload]

# ------------------------------- Action ------------------------------------
colA, colB = st.columns([1,3])
with colA:
    go = st.button("Search", type="primary")
with colB:
    st.caption("Tip: set a narrow window first (e.g., 1–3 months) and widen as needed.")

# ------------------------------ Results ------------------------------------
if go:
    if validation_errors:
        for msg in validation_errors:
            st.error(msg)
        st.stop()

    try:
        data = api.aspects_search(payload)
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

    if not isinstance(data, dict):
        st.error("API returned an unexpected payload; expected a JSON object.")
        st.stop()

    hits = data.get("hits", [])
    bins = data.get("bins", [])
    paging_raw = data.get("paging")

    if isinstance(paging_raw, dict):
        paging = paging_raw
    else:
        paging = {"total": len(hits)}
        if paging_raw is not None:
            st.warning("API paging payload was malformed; showing basic totals only.")

    if not isinstance(hits, list):
        st.error("API returned an unexpected hits payload; expected a list.")
        st.stop()
    if bins is not None and not isinstance(bins, list):
        st.error("API returned an unexpected bins payload; expected a list.")
        st.stop()

    st.subheader("Results")
    st.write(f"**Total hits (unpaged):** {paging.get('total', len(hits))}  |  **Returned:** {len(hits)}")

    if hits:
        df = _safe_dataframe(hits)
        if df is None:
            st.stop()

        if df.empty:
            st.info("No hits returned in the current page.")
            st.stop()

        sort_columns = {"time": "exact_time", "severity": "severity", "orb": "orb"}
        sort_field = sort_columns.get(order_by, "exact_time")
        if sort_field in df.columns:
            ascending = order_by != "severity"
            df = df.sort_values(sort_field, ascending=ascending)

        if {"a", "b"}.issubset(df.columns):
            df["pair"] = df.apply(lambda r: f"{r['a']}–{r['b']}", axis=1)
        elif "pair" not in df.columns:
            df["pair"] = ""

        # Show main table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Pair × Aspect grid (counts)
        with st.expander("Pair × Aspect grid (counts)", expanded=True):
            if {"pair", "aspect"}.issubset(df.columns):
                grid = pd.pivot_table(
                    df,
                    index="pair",
                    columns="aspect",
                    aggfunc="size",
                ).fillna(0)
                if not grid.empty:
                    grid = grid.astype(int)
                st.dataframe(grid, use_container_width=True)
            else:
                st.info("Pair/aspect columns were missing from the response; grid not available.")

        # Day bins
        with st.expander("Day bins (count / avg severity)", expanded=False):
            if bins:
                df_bins = _safe_dataframe(bins)
                if df_bins is None:
                    st.stop()
                if "score" in df_bins.columns and "avg_severity" not in df_bins.columns:
                    df_bins = df_bins.rename(columns={"score": "avg_severity"})
                st.dataframe(df_bins, use_container_width=True, hide_index=True)
            else:
                st.info("No day bins returned for this query.")

        # Exports
        c1, c2 = st.columns(2)
        with c1:
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Hits CSV", csv_bytes, file_name="aspect_hits.csv", mime="text/csv")
        with c2:
            st.download_button("Download JSON", json.dumps(data, default=str).encode("utf-8"), file_name="aspect_search.json", mime="application/json")
    else:
        st.info("No hits found for the given parameters.")
else:
    st.caption("Set parameters on the left and click **Search** to begin.")
