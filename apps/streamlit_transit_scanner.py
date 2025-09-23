"""Streamlit UI for running AstroEngine transit scans interactively."""


from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # pragma: no cover - Streamlit import guarded for test environments
    import streamlit as st
except Exception as exc:  # pragma: no cover - surfacing missing dependency
    print("This app requires Streamlit. Install with: pip install streamlit", file=sys.stderr)
    raise

from astroengine.app_api import (
    available_scan_entrypoints,
    canonicalize_events,
    run_scan_or_raise,
)
from astroengine.chart.config import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    VALID_ZODIAC_SYSTEMS,
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
    try:  # pragma: no cover - pandas optional dependency
        import pandas as pd
    except Exception:  # pragma: no cover - gracefully degrade
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

        "targets",
        [f"natal:{body}" for body in DEFAULT_TARGET_SELECTION],

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
    zodiac: str,
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
        zodiac=zodiac,
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
    _set_session_default("scan_ayanamsha", DEFAULT_SIDEREAL_AYANAMSHA)
    _set_session_default("scan_entrypoint", "Auto (first compatible)")
    _set_session_default("scan_preset", "Transit scan — Daily")
    _set_session_default("scan_active_preset", "Transit scan — Daily")
    _set_session_default("scan_initialized", False)
    _set_session_default("scan_ics_title", "AstroEngine Events")

    _set_session_default("scan_cache", {})
    _set_session_default("scan_last_cache_key", None)
    _set_session_default("scan_last_cache_hit", False)
    _set_session_default("scan_preset_initialized", False)
    if st.session_state["scan_active_preset"] != "Custom":
        if not st.session_state["scan_preset_initialized"]:
            _apply_preset(st.session_state["scan_active_preset"])
            st.session_state["scan_preset_initialized"] = True


_ensure_defaults()
st.set_page_config(page_title="AstroEngine — Transit Scanner", layout="wide")
st.title("AstroEngine — Transit Scanner")

entrypoints = available_scan_entrypoints()
entrypoint_labels = ["Auto (first compatible)"] + [f"{mod}.{fn}" for mod, fn in entrypoints]
entrypoint_lookup = dict(zip(entrypoint_labels[1:], entrypoints))

with st.sidebar:
    st.header("Presets & Environment")
    preset_choice = st.selectbox("Preset", list(PRESETS.keys()), key="scan_preset")
    if (
        preset_choice != st.session_state.get("scan_active_preset")
        and preset_choice != "Custom"
    ):
        _apply_preset(preset_choice)
    st.caption("Adjust any field to switch into the Custom preset.")

    se_path = None
    try:  # pragma: no cover - optional swiss info
        from astroengine.ephemeris.utils import get_se_ephe_path

        se_path = get_se_ephe_path()
    except Exception:  # pragma: no cover - best-effort
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

    zodiac_choice = st.selectbox(
        "Zodiac",
        options=sorted(VALID_ZODIAC_SYSTEMS),
        index=0,
        key="scan_zodiac",
        on_change=_mark_custom,
    )
    ayanamsha_choice = None
    if zodiac_choice == "sidereal":
        ayanamsha_options = sorted(SUPPORTED_AYANAMSHAS)
        default_index = ayanamsha_options.index(DEFAULT_SIDEREAL_AYANAMSHA)
        ayanamsha_choice = st.selectbox(
            "Ayanāṁśa",
            options=ayanamsha_options,
            index=default_index,
            key="scan_ayanamsha_choice",
            on_change=_mark_custom,
        )
        st.session_state["scan_ayanamsha"] = ayanamsha_choice
    step_minutes = st.slider(

        "Step minutes",
        min_value=10,
        max_value=240,
        value=int(st.session_state.get("scan_step", 60)),
        step=10,
        key="scan_step",
        on_change=_mark_custom,
    )
    detector_selection = st.multiselect(
        "Detectors",
        options=sorted(DETECTOR_NAMES),
        default=st.session_state.get("scan_detectors", []),
        key="Detectors",
        on_change=_mark_custom,
    )
    st.session_state["scan_detectors"] = detector_selection
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
    moving = st.multiselect(
        "Transiting bodies",
        moving_options,
        default=st.session_state.get("scan_moving", ["Sun", "Mars", "Jupiter"]),
        key="scan_moving",
        on_change=_mark_custom,
    )

    st.header("Frames & Targets")
    frame_options = available_frames()
    frame_selection = st.multiselect(
        "Target frames",
        frame_options,
        default=st.session_state.get("scan_frames", list(DEFAULT_TARGET_FRAMES)),
        key="scan_frames",
        on_change=_mark_custom,
    )
    selected_frames = frame_selection or list(DEFAULT_TARGET_FRAMES)
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

    targets = st.multiselect(
        "Targets",
        options=merged_options,
        default=st.session_state.get(
            "scan_targets", [f"natal:{body}" for body in DEFAULT_TARGET_SELECTION]
        ),
        key="scan_targets",
        on_change=_mark_custom,
    )

    st.header("Toggles")
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
            "Swiss Ephemeris path not detected. Set SE_EPHE_PATH for precise Swiss calculations.",
            icon="⚠️",
        )

    st.header("Entrypoints detected")
    if entrypoints:
        st.caption("First compatible entrypoint runs when Auto is selected.")
        for mod, fn in entrypoints:
            st.code(f"{mod}.{fn}", language="python")
    else:
        st.warning(
            "No scan entrypoints discovered. Set ASTROENGINE_SCAN_ENTRYPOINTS to register custom modules.",
            icon="⚠️",
        )

    st.caption(
        "Select an explicit scan function or leave on Auto to try detected entrypoints in order.\n"
        "Set ASTROENGINE_SCAN_ENTRYPOINTS for custom modules (format: module:function)."
    )


tab_run, tab_smoke = st.tabs(["Run scan", "Swiss smoketest"])

with tab_run:
    st.subheader("Run scan")
    st.caption("Adjust settings in the sidebar, then run the scan to view results below.")
    run_clicked = st.button("Run scan", key="Run scan")

    last_key = st.session_state.get("scan_last_cache_key")
    cache_key = (
        st.session_state.get("scan_start"),
        st.session_state.get("scan_end"),
        tuple(st.session_state.get("scan_moving", [])),
        tuple(st.session_state.get("scan_targets", [])),
        st.session_state.get("scan_provider"),
        st.session_state.get("scan_profile"),
        int(st.session_state.get("scan_step", 60)),
        tuple(st.session_state.get("scan_detectors", [])),
        bool(st.session_state.get("scan_sidereal")),
        st.session_state.get("scan_ayanamsha"),
        tuple(st.session_state.get("scan_frames", [])),
        st.session_state.get("scan_entrypoint"),
        st.session_state.get("scan_zodiac"),
    )

    if run_clicked:
        entrypoint_arg: Tuple[str, ...]
        if st.session_state.get("scan_entrypoint") == entrypoint_labels[0]:
            entrypoint_arg = tuple(entrypoint_lookup.values())
        else:
            entrypoint_arg = (st.session_state["scan_entrypoint"],)
        session_cache = st.session_state.setdefault("scan_cache", {})
        cached_tuple = session_cache.get(cache_key)
        from_cache = cached_tuple is not None
        cache_hit = from_cache or (last_key == cache_key)
        st.session_state["scan_last_cache_hit"] = cache_hit
        progress = st.progress(0, text="Preparing scan…")
        status = st.status("Checking cache…", expanded=False)
        if cached_tuple is not None:
            raw_events, canonical_events, used_entrypoint = cached_tuple
            progress.progress(100, text="Loaded cached results")
            status.update(label="Cache hit — reused previous run", state="complete")
        else:
            progress.progress(30, text="Running detectors…")
            try:
                raw_events, canonical_events, used_entrypoint = cached_scan(
                    start_utc=st.session_state.get("scan_start"),
                    end_utc=st.session_state.get("scan_end"),
                    moving=tuple(st.session_state.get("scan_moving", [])),
                    targets=tuple(st.session_state.get("scan_targets", [])),
                    provider=None
                    if st.session_state.get("scan_provider") == "auto"
                    else st.session_state.get("scan_provider"),
                    profile_id=st.session_state.get("scan_profile"),
                    step_minutes=int(st.session_state.get("scan_step", 60)),
                    detectors=tuple(st.session_state.get("scan_detectors", [])),
                    sidereal=st.session_state.get("scan_sidereal"),
                    ayanamsha=st.session_state.get("scan_ayanamsha"),
                    frames=tuple(st.session_state.get("scan_frames", [])),
                    entrypoints=entrypoint_arg,
                    zodiac=st.session_state.get("scan_zodiac", "tropical"),
                )
                session_cache[cache_key] = (raw_events, canonical_events, used_entrypoint)
                progress.progress(100, text="Scan complete")
                status.update(label="Scan complete", state="complete")
            except Exception as exc:  # pragma: no cover - runtime failure surfaced to user
                status.update(label=f"Scan failed: {exc}", state="error")
                st.error(f"Scan failed: {exc}")
                raw_events = canonical_events = []
                used_entrypoint = ("?", "?")
        st.session_state["scan_cache"] = session_cache
        st.session_state["scan_last_cache_key"] = cache_key
        if canonical_events:
            st.success(f"Scan complete — {len(canonical_events)} events")

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
            st.session_state.get("scan_zodiac"),
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
                st.session_state.get("scan_zodiac", "tropical"),
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


        st.markdown("### Export")
        col_sqlite, col_parquet, col_download = st.columns(3)
        with col_sqlite:
            sqlite_path = st.text_input("SQLite path", value="runs.db", key="scan_sqlite_path")
            if st.button("Save SQLite", key="scan_sqlite_btn") and canonical_events:
                try:
                    rows_written = write_sqlite_canonical(sqlite_path, canonical_events)
                    st.success(f"Wrote {rows_written} rows to {sqlite_path}")
                except Exception as export_exc:
                    st.error(f"SQLite export failed: {export_exc}")
        with col_parquet:
            parquet_path = st.text_input(
                "Parquet path (.parquet or dir)",
                value="runs.parquet",
                key="scan_parquet_path",
            )
            if st.button("Save Parquet", key="scan_parquet_btn") and canonical_events:
                try:
                    rows_written = write_parquet_canonical(parquet_path, canonical_events)
                    st.success(f"Wrote {rows_written} rows to {parquet_path}")
                except Exception as export_exc:
                    st.error(f"Parquet export failed: {export_exc}")
        with col_download:
            json_payload = json.dumps(records, indent=2, ensure_ascii=False)
            st.download_button(
                "Download JSON",
                json_payload,
                file_name="transits.json",
                mime="application/json",
                disabled=not records,
            )
            ics_title = st.text_input(
                "ICS title",
                value=st.session_state.get("scan_ics_title", "AstroEngine Events"),
                key="scan_ics_title",
            )
            ics_bytes = ics_bytes_from_events(
                canonical_events,
                calendar_name=ics_title or "AstroEngine Events",
            )
            st.download_button(
                "Download ICS",
                ics_bytes,
                file_name="transits.ics",
                mime="text/calendar",
                disabled=not canonical_events,
            )
    else:
        st.info("Configure the scan in the sidebar and click **Run scan** to generate events.")

with tab_smoke:
    st.subheader("Swiss Smoketest (script)")
    st.write(
        "Runs scripts/swe_smoketest.py with the selected start time to validate your Swiss setup."
    )
    if st.button("Run smoketest", key="Run smoketest"):
        try:
            cmd = [
                sys.executable,
                "scripts/swe_smoketest.py",
                "--utc",
                st.session_state.get("scan_start"),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if proc.returncode == 0:
                st.success("Smoketest ran successfully")
                st.code(out or "<no output>", language="bash")
            else:
                st.error(f"Smoketest failed (exit {proc.returncode})")
                st.code((out + "\n\n" + err).strip(), language="bash")
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Failed to run smoketest: {exc}")


