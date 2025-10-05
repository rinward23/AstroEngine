from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _to_utc_iso(moment: datetime, tz_name: str) -> str:
    try:
        tzinfo = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone '{tz_name}'") from exc
    localized = moment.replace(tzinfo=tzinfo)
    utc_value = localized.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _api_get(path: str, *, params: dict | None = None, timeout: int = 20) -> dict | list:
    url = f"{API_BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=timeout)
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def _api_post(path: str, payload: dict, *, timeout: int = 30) -> dict:
    url = f"{API_BASE_URL}{path}"
    response = requests.post(url, json=payload, timeout=timeout)
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def _api_put(path: str, payload: dict, *, timeout: int = 30) -> dict:
    url = f"{API_BASE_URL}{path}"
    response = requests.put(url, json=payload, timeout=timeout)
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def _api_delete(path: str, *, timeout: int = 30) -> None:
    url = f"{API_BASE_URL}{path}"
    response = requests.delete(url, timeout=timeout)
    if not response.ok:
        raise RuntimeError(response.text)


st.set_page_config(page_title="AstroEngine — Chart Library", layout="wide")
st.title("🗂️ Chart Library")


with st.expander("Create new chart", expanded=True):
    with st.form("create-chart-form"):
        name = st.text_input("Name", placeholder="Jane Doe")
        col1, col2, col3 = st.columns(3)
        with col1:
            dt_value = st.datetime_input("Date & time (local)", value=datetime.now())
            tz_name = st.text_input("Timezone (IANA)", value="UTC")
        with col2:
            lat = st.number_input("Latitude", value=0.0, format="%.6f")
            lon = st.number_input("Longitude", value=0.0, format="%.6f")
        with col3:
            location = st.text_input("Location label", placeholder="City, Country")
            gender = st.text_input("Gender (optional)")
        tags = st.text_input("Tags", placeholder="client, vip")
        notes = st.text_area("Notes")
        profile = st.text_input("Profile to apply (optional)", placeholder="modern_western")
        narrative_profile = st.text_input("Narrative profile (optional)")
        submitted = st.form_submit_button("Save & compute natal", type="primary", disabled=not name)
    if submitted:
        try:
            dt_iso = _to_utc_iso(dt_value, tz_name)
            payload = {
                "name": name,
                "kind": "natal",
                "dt_utc": dt_iso,
                "tz": tz_name,
                "lat": float(lat),
                "lon": float(lon),
                "location": location or None,
                "gender": gender or None,
                "tags": tags or None,
                "notes": notes or None,
                "profile": profile or None,
                "narrative_profile": narrative_profile or None,
            }
            _api_post("/v1/charts", payload)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.success("Chart saved.")
            st.experimental_rerun()

st.divider()


col_list, col_detail = st.columns([2, 3])

with col_list:
    st.subheader("Stored charts")
    search = st.text_input("Search name")
    kind_filter = st.selectbox(
        "Kind",
        ["any", "natal", "transit", "progressed", "solar_return", "lunar_return", "custom"],
        index=0,
    )
    query_params: dict[str, str] = {}
    if kind_filter != "any":
        query_params["kind"] = kind_filter
    if search:
        query_params["q"] = search
    try:
        items = _api_get("/v1/charts", params=query_params)
        if not isinstance(items, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response shape from /v1/charts")
    except Exception as exc:
        st.error(str(exc))
        items = []
    label_by_id: dict[str, int] = {}
    for entry in items:
        if not isinstance(entry, dict):
            continue
        label = f"{entry.get('name') or entry.get('chart_key')} — {entry.get('kind')}"
        label += f" ({entry.get('dt_utc')})"
        label_by_id[label] = entry.get("id")
    selection = st.selectbox("Select chart", ["(none)"] + list(label_by_id.keys()))
    selected_id = label_by_id.get(selection)

with col_detail:
    st.subheader("Chart details")
    if not selected_id:
        st.info("Select a chart from the list to view details.")
    else:
        try:
            detail = _api_get(f"/v1/charts/{selected_id}")
            if not isinstance(detail, dict):  # pragma: no cover - defensive
                raise RuntimeError("Unexpected response payload from chart detail")
        except Exception as exc:
            st.error(str(exc))
            detail = None

        if detail:
            meta_cols = st.columns(3)
            meta_cols[0].metric("Kind", detail.get("kind", "—"))
            meta_cols[1].metric("Profile", detail.get("profile_applied", "—"))
            meta_cols[2].metric("Narrative", detail.get("narrative_profile", "—"))

            st.markdown("### Metadata")
            st.json({
                "name": detail.get("name"),
                "dt_utc": detail.get("dt_utc"),
                "tz": detail.get("tz"),
                "location": detail.get("location"),
                "lat": detail.get("lat"),
                "lon": detail.get("lon"),
                "tags": detail.get("tags"),
                "gender": detail.get("gender"),
            })

            with st.form(f"update-chart-{selected_id}"):
                st.write("Update metadata")
                name_edit = st.text_input("Name", value=detail.get("name") or "")
                tags_edit = st.text_input("Tags", value=detail.get("tags") or "")
                notes_edit = st.text_area("Notes", value=detail.get("notes") or "")
                gender_edit = st.text_input("Gender", value=detail.get("gender") or "")
                location_edit = st.text_input("Location", value=detail.get("location") or "")
                tz_edit = st.text_input("Timezone", value=detail.get("tz") or "")
                narrative_edit = st.text_input("Narrative profile", value=detail.get("narrative_profile") or "")
                submitted_update = st.form_submit_button("Save changes")
            if submitted_update:
                payload = {
                    "name": name_edit or None,
                    "tags": tags_edit or None,
                    "notes": notes_edit or None,
                    "gender": gender_edit or None,
                    "location": location_edit or None,
                    "tz": tz_edit or None,
                    "narrative_profile": narrative_edit or None,
                }
                try:
                    _api_put(f"/v1/charts/{selected_id}", payload)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success("Chart updated.")
                    st.experimental_rerun()

            st.markdown("### Derive new chart")
            with st.form(f"derive-chart-{selected_id}"):
                derive_kind = st.selectbox(
                    "Derivation",
                    ["transit", "progressed", "solar_return", "lunar_return", "custom"],
                )
                derive_dt = st.datetime_input(
                    "Target datetime (UTC)", value=datetime.now(timezone.utc)
                )
                derive_profile = st.text_input(
                    "Profile override (optional)", key=f"derive-profile-{selected_id}"
                )
                submitted_derive = st.form_submit_button("Run derivation", type="primary")
            if submitted_derive:
                payload = {
                    "kind": derive_kind,
                    "dt_utc": derive_dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
                    "profile": derive_profile or None,
                }
                try:
                    _api_post(f"/v1/charts/{selected_id}/derive", payload)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success("Derived chart saved.")
                    st.experimental_rerun()

            st.markdown("### Computed data")
            tabs = st.tabs(["Bodies", "Houses", "Aspects", "Patterns", "Settings"])
            with tabs[0]:
                st.json(detail.get("bodies"))
            with tabs[1]:
                st.json(detail.get("houses"))
            with tabs[2]:
                st.json(detail.get("aspects"))
            with tabs[3]:
                st.json(detail.get("patterns"))
            with tabs[4]:
                st.json(detail.get("settings_snapshot"))

            export_payload = json.dumps(detail, indent=2, ensure_ascii=False)
            st.download_button(
                "Download JSON export",
                data=export_payload.encode("utf-8"),
                file_name=f"chart_{selected_id}.json",
                mime="application/json",
            )

            if st.button("Delete chart", type="secondary"):
                try:
                    _api_delete(f"/v1/charts/{selected_id}")
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success("Chart deleted.")
                    st.experimental_rerun()

st.caption(
    "Charts are persisted with their computed placements and the settings snapshot used for calculation."
)
