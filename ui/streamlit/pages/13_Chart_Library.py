from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, List

import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Chart Library", page_icon="🗂️", layout="wide")
st.title("🗂️ Chart Library")

api = APIClient()


def _parse_iso(timestamp: str | None) -> str:
    if not timestamp:
        return "—"
    try:
        value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:  # pragma: no cover - defensive
        return timestamp
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _normalize_tags(text: str) -> List[str]:
    return [chunk.strip().lower() for chunk in text.split(",") if chunk.strip()]


with st.sidebar:
    st.header("Search")
    query = st.text_input("Name contains", placeholder="chart or client name")
    tags_input = st.text_input(
        "Tags (comma separated)", placeholder="natal, client"
    )
    filter_dates = st.checkbox("Filter by creation date")
    created_from_iso = created_to_iso = None
    if filter_dates:
        default_start = date.today() - timedelta(days=90)
        start = st.date_input("Created from", value=default_start)
        end = st.date_input("Created to", value=date.today())
        created_from_iso = start.isoformat()
        created_to_iso = end.isoformat()

tags = _normalize_tags(tags_input)

try:
    charts = api.search_charts(
        query=query or None,
        tags=tags or None,
        created_from=created_from_iso,
        created_to=created_to_iso,
    )
except Exception as exc:  # pragma: no cover - defensive path
    st.error(f"Unable to load charts: {exc}")
    charts = []

st.subheader("Active charts")
if not charts:
    st.info("No charts matched the current filters.")
else:
    for record in charts:
        chart_id = record.get("id")
        chart_key = record.get("chart_key") or f"Chart {chart_id}"
        created_at = _parse_iso(record.get("created_at"))
        st.markdown(f"### {chart_key}  ")
        meta_cols = st.columns(3)
        meta_cols[0].metric("ID", chart_id)
        meta_cols[1].metric("Profile", record.get("profile_key", "—"))
        meta_cols[2].metric("Created", created_at)
        current_tags = ", ".join(record.get("tags") or [])
        tag_value = st.text_input(
            "Tags",
            value=current_tags,
            key=f"chart_tags_{chart_id}",
            help="Tags are stored in lowercase and can be used when filtering charts.",
        )
        button_cols = st.columns([1, 1, 2])
        with button_cols[0]:
            if st.button("Save tags", key=f"save_tags_{chart_id}"):
                try:
                    api.update_chart_tags(chart_id, _normalize_tags(tag_value))
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unable to update tags: {exc}")
                else:
                    st.success("Tags updated")
                    st.experimental_rerun()
        with button_cols[1]:
            if st.button("Delete", key=f"delete_chart_{chart_id}"):
                try:
                    api.soft_delete_chart(chart_id)
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unable to delete chart: {exc}")
                else:
                    st.success("Chart moved to Recently deleted")
                    st.experimental_rerun()
        st.divider()

st.subheader("Recently deleted")
try:
    deleted = api.list_deleted_charts()
except Exception as exc:  # pragma: no cover - defensive
    st.error(f"Unable to load deleted charts: {exc}")
    deleted = []

if not deleted:
    st.caption("No recently deleted charts.")
else:
    for record in deleted:
        chart_id = record.get("id")
        chart_key = record.get("chart_key") or f"Chart {chart_id}"
        deleted_at = _parse_iso(record.get("deleted_at"))
        restore_cols = st.columns([3, 1])
        with restore_cols[0]:
            st.markdown(f"**{chart_key}** — deleted at {deleted_at}")
        with restore_cols[1]:
            if st.button("Restore", key=f"restore_chart_{chart_id}"):
                try:
                    api.restore_chart(chart_id)
                except Exception as exc:  # pragma: no cover - defensive
                    st.error(f"Unable to restore chart: {exc}")
                else:
                    st.success("Chart restored")
                    st.experimental_rerun()
