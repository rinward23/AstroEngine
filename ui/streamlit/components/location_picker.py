"""Location picker component backed by the atlas geocoder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import streamlit as st
from zoneinfo import ZoneInfo

from astroengine.geo import geocode


def location_picker(
    label: str,
    *,
    default_query: str,
    state_prefix: str,
    help: str | None = None,
) -> Dict[str, Any] | None:
    """Render a lookup widget returning a cached location selection.

    Parameters
    ----------
    label:
        Human readable label describing the search input.
    default_query:
        Default text used for the location search box when no session state is
        available.
    state_prefix:
        Prefix used to isolate Streamlit session keys for this picker.
    help:
        Optional tooltip text displayed on the search box.

    Returns
    -------
    Optional[Dict[str, Any]]
        Mapping containing the selected location payload (``name``, ``lat``,
        ``lon``, ``tz``). ``None`` when nothing has been selected yet.
    """

    query_key = f"{state_prefix}_query"
    result_key = f"{state_prefix}_selection"
    lat_key = f"{state_prefix}_lat"
    lon_key = f"{state_prefix}_lon"
    tz_key = f"{state_prefix}_tz"

    container = st.container()
    query_default = st.session_state.get(query_key, default_query)
    query_value = container.text_input(
        f"{label} search",
        value=query_default,
        key=query_key,
        help=help,
    )

    if container.button("Lookup", key=f"{state_prefix}_lookup"):
        trimmed = query_value.strip()
        if not trimmed:
            container.warning("Enter a location to search.")
        else:
            try:
                result = geocode(trimmed)
            except Exception as exc:  # pragma: no cover - user feedback path
                container.error(f"Lookup failed: {exc}")
            else:
                st.session_state[result_key] = result
                st.session_state[query_key] = result["name"]
                st.session_state[lat_key] = float(result["lat"])
                st.session_state[lon_key] = float(result["lon"])
                st.session_state[tz_key] = result["tz"]
                container.success(f"Selected {result['name']}")

    selection = st.session_state.get(result_key)
    if selection:
        tzid = selection.get("tz")
        try:
            zone = ZoneInfo(tzid) if tzid else None
        except Exception:  # pragma: no cover - invalid tz data
            zone = None
        if zone is not None:
            now_utc = datetime.now(timezone.utc)
            local = now_utc.astimezone(zone)
            offset = local.utcoffset() or timedelta(0)
            offset_hours = offset.total_seconds() / 3600.0
            dst_active = bool(local.dst() and local.dst() != timedelta(0))
            container.caption(
                f"{selection['name']} — {tzid} (UTC{offset_hours:+.1f}) • DST {'active' if dst_active else 'inactive'}"
            )
        else:
            container.caption(f"{selection['name']} — {tzid or 'Unknown timezone'}")

    return selection
