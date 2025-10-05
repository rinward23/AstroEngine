"""Location picker component backed by the atlas geocoder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import streamlit as st
from zoneinfo import ZoneInfo

from astroengine.geo import geocode


def _offset_signature(zone: ZoneInfo, moment: datetime) -> Tuple[timedelta, timedelta]:
    local = moment.astimezone(zone)
    offset = local.utcoffset() or timedelta(0)
    dst = local.dst() or timedelta(0)
    return offset, dst


def _refine_transition(
    zone: ZoneInfo,
    start: datetime,
    end: datetime,
    start_signature: Tuple[timedelta, timedelta],
) -> datetime:
    current_start = start
    current_signature = start_signature
    while (end - current_start) > timedelta(minutes=1):
        midpoint = current_start + (end - current_start) / 2
        mid_signature = _offset_signature(zone, midpoint)
        if mid_signature == current_signature:
            current_start = midpoint
            current_signature = mid_signature
        else:
            end = midpoint
    return end


def _collect_dst_transitions(zone: ZoneInfo, reference: datetime) -> List[Dict[str, Any]]:
    window_start = reference - timedelta(days=730)
    window_end = reference + timedelta(days=365)
    step = timedelta(days=30)
    transitions: List[Dict[str, Any]] = []

    current = window_start
    previous_signature = _offset_signature(zone, current)
    while current < window_end:
        next_point = min(current + step, window_end)
        next_signature = _offset_signature(zone, next_point)
        if next_signature != previous_signature:
            transition_instant = _refine_transition(zone, current, next_point, previous_signature)
            transitions.append(
                {
                    "instant": transition_instant,
                    "offset": next_signature[0],
                    "is_dst": bool(next_signature[1] and next_signature[1] != timedelta(0)),
                }
            )
            previous_signature = next_signature
        current = next_point

    return transitions


def _format_transition(zone: ZoneInfo, entry: Dict[str, Any]) -> str:
    local_instant = entry["instant"].astimezone(zone)
    offset_hours = entry["offset"].total_seconds() / 3600.0
    status = "DST active" if entry["is_dst"] else "Standard time"
    return f"- {local_instant.strftime('%Y-%m-%d %H:%M')} — {status} (UTC{offset_hours:+.1f})"


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
            transitions = _collect_dst_transitions(zone, now_utc)
            if transitions:
                history_lines: List[str] = []
                past_lines = [
                    _format_transition(zone, entry)
                    for entry in transitions
                    if entry["instant"] <= now_utc
                ][-3:]
                upcoming_lines = [
                    _format_transition(zone, entry)
                    for entry in transitions
                    if entry["instant"] > now_utc
                ][:2]
                if past_lines:
                    history_lines.append("**Recent DST transitions**")
                    history_lines.extend(past_lines)
                if upcoming_lines:
                    history_lines.append("**Upcoming DST transitions**")
                    history_lines.extend(upcoming_lines)
                if history_lines:
                    container.markdown("\n".join(history_lines))
        else:
            container.caption(f"{selection['name']} — {tzid or 'Unknown timezone'}")

    return selection
