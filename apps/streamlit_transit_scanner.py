"""Streamlit application for running AstroEngine transit scans."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover - environment guard
    print("This app requires Streamlit. Install with: pip install streamlit", file=sys.stderr)
    raise

from astroengine.app_api import (
    available_scan_entrypoints,
    canonicalize_events,
    run_scan_or_raise,
)
from astroengine.exporters import write_parquet_canonical, write_sqlite_canonical
from astroengine.exporters_ics import ics_bytes_from_events
from astroengine.utils import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    DETECTOR_NAMES,
    TARGET_FRAME_BODIES,
    available_frames,
    expand_targets,
)
from astroengine.chart.config import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    VALID_ZODIAC_SYSTEMS,
)


def _event_to_record(event: Any) -> Dict[str, Any]:
    if isinstance(event, Mapping):
        return dict(event)
    if hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if hasattr(event, "_asdict"):
        try:
            dumped = event._asdict()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if is_dataclass(event):
        try:
            return asdict(event)
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(event, "__dict__"):
        try:
            return dict(vars(event))
        except Exception:  # pragma: no cover - defensive
            pass
    try:
        return dict(event)
    except Exception:  # pragma: no cover - defensive
        return {"value": repr(event)}


def _events_to_records(events: Iterable[Any]) -> List[Dict[str, Any]]:
    return [_event_to_record(evt) for evt in events]


def _records_to_df(records: List[Dict[str, Any]]):
    if not records:
        return None
    try:  # pragma: no cover - optional dependency
        import pandas as pd
    except Exception:  # pragma: no cover - pandas optional
        return None
    try:
        return pd.DataFrame(records)
    except Exception:  # pragma: no cover - defensive
        return None


def _default_window() -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).replace(microsecond=0)
    end = (now + timedelta(days=1)).replace(microsecond=0)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def _sorted_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def _ts_key(record: Mapping[str, Any]) -> str:
        return str(record.get("ts") or record.get("timestamp") or "")

    return sorted(records, key=_ts_key)


def _mark_custom() -> None:
    st.session_state["scan_active_preset"] = "Custom"
    st.session_state["scan_preset"] = "Custom"


def _set_session_default(key: str, value: Any) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


PRESETS: Dict[str, Dict[str, Any]] = {
    "Custom": {},
    "Transit scan — Daily": {
        "window": lambda now: (
            (now - timedelta(hours=12)).isoformat().replace("+00:00", "Z"),
            (now + timedelta(hours=36)).isoformat().replace("+00:00", "Z"),
        ),
        "moving": ["Sun", "Mars", "Jupiter"],
        "frames": ["natal"],
        "targets": ["natal:Sun", "natal:Moon", "natal:ASC"],
        "detectors": ["lunations", "stations", "profections"],
        "provider": "auto",
        "step": 60,
        "sidereal": False,
    },
    "Electional — Week": {
        "window": lambda now: (
            now.isoformat().replace("+00:00", "Z"),
            (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        ),
        "moving": ["Sun", "Venus", "Mars", "Jupiter"],
        "frames": ["natal", "angles"],
        "targets": ["natal:Sun", "natal:Moon", "angles:ASC", "angles:MC"],
        "detectors": ["lunations", "stations", "midpoints", "antiscia"],
        "provider": "swiss",
        "step": 30,
        "sidereal": False,
    },
    "Sidereal natal + dashas": {
        "window": lambda now: (
            (now - timedelta(days=3)).isoformat().replace("+00:00", "Z"),
            (now + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        ),
        "moving": ["Sun", "Moon", "Mercury", "Venus", "Mars"],
        "frames": ["natal", "points"],
        "targets": ["natal:Sun", "natal:Moon", "points:Fortune", "points:Spirit"],
        "detectors": ["timelords", "progressions", "returns"],
        "provider": "swiss",
        "step": 120,
        "sidereal": True,
        "ayanamsha": "lahiri",
    },
}


def _apply_preset(name: str) -> None:
    if name == "Custom":
        return
    now = datetime.now(timezone.utc)
    preset = PRESETS[name]
    start, end = preset.get("window", _default_window)(now)
    st.session_state["scan_start"] = start
    st.session_state["scan_end"] = end
    st.session_state["scan_moving"] = preset.get("moving", ["Sun", "Mars", "Jupiter"])
    st.session_state["scan_frames"] = preset.get("frames", list(DEFAULT_TARGET_FRAMES))
    st.session_state["scan_targets"] = preset.get(
        "targets", [f"natal:{body}" for body in DEFAULT_TARGET_SELECTION]
    )
    st.session_state["scan_detectors"] = preset.get("detectors", [])
    st.session_state["scan_provider"] = preset.get("provider", "auto")
    st.session_state["scan_step"] = preset.get("step", 60)
    st.session_state["scan_sidereal"] = preset.get("sidereal", False)
    if preset.get("sidereal"):
        st.session_state["scan_ayanamsha"] = preset.get("ayanamsha", "lahiri")
    st.session_state["scan_active_preset"] = name


@st.cache_data(show_spinner=False)
def cached_scan(
    start_utc: str,
    end_utc: str,
    moving: Tuple[str, ...],
    targets: Tuple[str, ...],
    provider: Optional[str],
    profile_id: Optional[str],
    step_minutes: int,
    detectors: Tuple[str, ...],
    sidereal: Optional[bool],
    ayanamsha: Optional[str],
    frames: Tuple[str, ...],
    entrypoints: Tuple[str, ...],
) -> Tuple[List[Dict[str, Any]], Sequence[Any], Tuple[str, str]]:
    entrypoint_arg = list(entrypoints) if entrypoints else None
    raw_events, used_entrypoint = run_scan_or_raise(
        start_utc=start_utc,
        end_utc=end_utc,
        moving=list(moving),
        targets=list(targets),
        provider=provider,
        profile_id=profile_id or None,
        step_minutes=step_minutes,
        detectors=list(detectors),
        target_frames=list(frames),
        sidereal=sidereal,
        ayanamsha=ayanamsha,
        entrypoints=entrypoint_arg,
        return_used_entrypoint=True,
    )
    canonical = canonicalize_events(raw_events)
    return list(raw_events), canonical, used_entrypoint


def _ensure_defaults() -> None:
    start, end = _default_window()
    _set_session_default("scan_start", start)
    _set_session_default("scan_end", end)
    _set_session_default("scan_moving", ["Sun", "Mars", "Jupiter"])
    _set_session_default("scan_frames", list(DEFAULT_TARGET_FRAMES))
    _set_session_default(
        "scan_targets", [f"natal:{body}" for body in DEFAULT_TARGET_SELECTION]
    )
    _set_session_default("scan_detectors", [])
    _set_session_default("scan_provider", "auto")
    _set_session_default("scan_profile", "base")
    _set_session_default("scan_step", 60)
    _set_session_default("scan_sidereal", False)
    _set_session_default("scan_ayanamsha", "lahiri")
    _set_session_default("scan_entrypoint", "Auto (first compatible)")
    _set_session_default("scan_preset", "Transit scan — Daily")
    _set_session_default("scan_active_preset", "Transit scan — Daily")
    _set_session_default("scan_initialized", False)
    _set_session_default("scan_ics_title", "AstroEngine Events")
    if not st.session_state.get("scan_initialized", False):
        active = st.session_state.get("scan_active_preset", "Transit scan — Daily")
        if active != "Custom":
            _apply_preset(active)
        st.session_state["scan_initialized"] = True


_ensure_defaults()
st.set_page_config(page_title="AstroEngine — Transit Scanner", layout="wide")
st.title("AstroEngine — Transit Scanner")

entrypoints = available_scan_entrypoints()
entrypoint_labels = ["Auto (first compatible)"] + [f"{mod}.{fn}" for mod, fn in entrypoints]
entrypoint_lookup = dict(zip(entrypoint_labels[1:], entrypoints))

with st.sidebar:
    st.header("Presets & Environment")
    preset_choice = st.selectbox("Preset", list(PRESETS.keys()), key="scan_preset")
    if preset_choice != st.session_state.get("scan_active_preset") and preset_choice != "Custom":
        _apply_preset(preset_choice)
    st.caption("Adjust any field to switch into the Custom preset.")

    se_path = None
    try:
        from astroengine.ephemeris.utils import get_se_ephe_path

        se_path = get_se_ephe_path()
    except Exception:  # pragma: no cover - optional import
        se_path = None

    st.write("**SE_EPHE_PATH**:", os.getenv("SE_EPHE_PATH") or "not set")
    st.write(
        "**ASTROENGINE_SCAN_ENTRYPOINTS**:",
        os.getenv("ASTROENGINE_SCAN_ENTRYPOINTS") or "not set",
    )
    st.write("**Detected Swiss path**:", se_path or "not found")

    st.header("Scan Settings")
    st.text_input("Start (UTC, ISO-8601)", key="scan_start", on_change=_mark_custom)
    st.text_input("End (UTC, ISO-8601)", key="scan_end", on_change=_mark_custom)
    st.selectbox(
        "Provider",
        options=["auto", "swiss", "pymeeus", "skyfield"],
        key="scan_provider",
        on_change=_mark_custom,
    )
    st.slider(
        "Step minutes",
        min_value=10,
        max_value=240,
        value=int(st.session_state.get("scan_step", 60)),
        step=10,
        key="scan_step",
        on_change=_mark_custom,
    )
    entrypoint_choice = st.selectbox(
        "Scan entrypoint",
        entrypoint_labels,
        index=0,
        key="scan_entrypoint",
    )

    st.header("Transiting bodies")
    moving_options = [
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
        "Node",
        "Chiron",
    ]
    st.multiselect(
        "Transiting bodies",
        moving_options,
        default=st.session_state.get("scan_moving", ["Sun", "Mars", "Jupiter"]),
        key="scan_moving",
        on_change=_mark_custom,
    )

    st.header("Frames & Targets")
    frame_options = available_frames()
    target_frames = st.multiselect(
        "Target frames",
        frame_options,
        default=st.session_state.get("scan_frames", list(DEFAULT_TARGET_FRAMES)),
        key="scan_frames",
        on_change=_mark_custom,
    )
    selected_frames = target_frames or list(DEFAULT_TARGET_FRAMES)
    merged_options: List[str] = []
    for frame in selected_frames:
        bodies = TARGET_FRAME_BODIES.get(frame) or DEFAULT_TARGET_SELECTION
        for body in bodies:
            token = f"{frame}:{body}"
            if token not in merged_options:
                merged_options.append(token)
    for existing in st.session_state.get("scan_targets", []):
        if existing not in merged_options:
            merged_options.append(existing)
    default_targets = st.session_state.get(
        "scan_targets", [f"natal:{body}" for body in DEFAULT_TARGET_SELECTION]
    )
    st.multiselect(
        "Targets",
        options=merged_options,
        default=default_targets,
        key="scan_targets",
        on_change=_mark_custom,
    )

    st.header("Toggles")
    detectors = st.multiselect(
        "Detectors",
        options=sorted(DETECTOR_NAMES),
        default=st.session_state.get("scan_detectors", []),
        key="scan_detectors",
        on_change=_mark_custom,
    )
    sidereal = st.checkbox(
        "Use sidereal zodiac",
        value=st.session_state.get("scan_sidereal", False),
        key="scan_sidereal",
        on_change=_mark_custom,
    )
    ayanamsha_value = st.session_state.get("scan_ayanamsha", "lahiri")
    if sidereal:
        ayanamsha_options = sorted(SUPPORTED_AYANAMSHAS)
        default_index = ayanamsha_options.index(DEFAULT_SIDEREAL_AYANAMSHA)
        choice = st.selectbox(
            "Ayanamsha",
            options=ayanamsha_options,
            index=default_index,
            key="scan_ayanamsha_choice",
        )
        if choice != ayanamsha_value:
            st.session_state["scan_ayanamsha"] = choice
    else:
        st.session_state["scan_ayanamsha"] = ayanamsha_value

    st.text_input(
        "Profile (optional)",
        value=st.session_state.get("scan_profile", "base"),
        key="scan_profile",
        on_change=_mark_custom,
    )

    if st.session_state.get("scan_provider") in {"swiss", "auto"} and not se_path:
        st.warning(
            "Swiss Ephemeris path not detected. Set SE_EPHE_PATH to your Swiss ephemeris folder for precision.",
            icon="⚠️",
        )

    st.header("Entrypoints detected")
    if entrypoints:
        st.caption("First compatible entrypoint runs when Auto is selected.")
        for mod, fn in entrypoints:
            st.code(f"{mod}.{fn}", language="python")
    else:
        st.warning(
            "No scan entrypoints discovered. Ensure astroengine is installed or set ASTROENGINE_SCAN_ENTRYPOINTS.",
            icon="⚠️",
        )


col_scan, col_results = st.columns((1, 2))

with col_scan:
    st.subheader("Run Scan")
    run = st.button("Run scan")
    if run:
        entrypoint_override = entrypoint_lookup.get(st.session_state.get("scan_entrypoint"))
        entrypoint_arg = tuple([entrypoint_override]) if entrypoint_override else tuple()
        moving = tuple(st.session_state.get("scan_moving", []))
        frames = tuple(st.session_state.get("scan_frames", list(DEFAULT_TARGET_FRAMES)))
        target_tokens = expand_targets(frames, st.session_state.get("scan_targets", []))
        detectors_tuple = tuple(st.session_state.get("scan_detectors", []))
        cache_key = (
            st.session_state.get("scan_start"),
            st.session_state.get("scan_end"),
            moving,
            tuple(target_tokens),
            st.session_state.get("scan_provider"),
            st.session_state.get("scan_profile"),
            int(st.session_state.get("scan_step", 60)),
            detectors_tuple,
            st.session_state.get("scan_sidereal"),
            st.session_state.get("scan_ayanamsha"),
            frames,
            entrypoint_arg,
        )
        session_cache = st.session_state.setdefault("scan_cache", {})
        from_cache = cache_key in session_cache
        st.session_state["scan_last_cache_hit"] = from_cache
        if from_cache:
            raw_events, canonical_events, used_entrypoint = session_cache[cache_key]
        else:
            raw_events, canonical_events, used_entrypoint = cached_scan(
                st.session_state.get("scan_start"),
                st.session_state.get("scan_end"),
                moving,
                tuple(target_tokens),
                st.session_state.get("scan_provider"),
                st.session_state.get("scan_profile"),
                int(st.session_state.get("scan_step", 60)),
                detectors_tuple,
                st.session_state.get("scan_sidereal"),
                st.session_state.get("scan_ayanamsha"),
                frames,
                entrypoint_arg,
            )
            session_cache[cache_key] = (raw_events, canonical_events, used_entrypoint)
        st.session_state["scan_results"] = (raw_events, canonical_events, used_entrypoint)

with col_results:
    st.subheader("Results")
    results = st.session_state.get("scan_results")
    if not results:
        st.info("Run a scan to see results.")
    else:
        raw_events, canonical_events, used_entrypoint = results
        st.write(f"Used entrypoint: {used_entrypoint[0]}.{used_entrypoint[1]}")
        records = _sorted_records(_events_to_records(canonical_events))
        df = _records_to_df(records)
        if df is not None:
            st.dataframe(df)
        else:
            st.json(records)
        st.caption(
            "Tip: use the export buttons below to save results as SQLite, Parquet, or ICS calendars."
        )

    export_col1, export_col2, export_col3 = st.columns(3)
    if results:
        raw_events, canonical_events, _ = results
        with export_col1:
            if st.button("Export SQLite"):
                path = write_sqlite_canonical(canonical_events)
                st.success(f"Wrote SQLite export to {path}")
        with export_col2:
            if st.button("Export Parquet"):
                path = write_parquet_canonical(canonical_events)
                st.success(f"Wrote Parquet export to {path}")
        with export_col3:
            if st.button("Download ICS"):
                payload = ics_bytes_from_events(
                    canonical_events,
                    title=st.session_state.get("scan_ics_title", "AstroEngine Events"),
                )
                st.download_button(
                    "Download ICS",
                    data=payload,
                    file_name="astroengine_events.ics",
                )


st.caption(
    "This demo caches scan results per parameter set. Repeat the same scan to load cached results instantly."
)
