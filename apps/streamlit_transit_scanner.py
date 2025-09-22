# >>> AUTO-GEN BEGIN: Streamlit Transit Scanner v1.1
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping

try:
    import streamlit as st
except Exception as exc:
    print("This app requires Streamlit. Install with: pip install streamlit", file=sys.stderr)
    raise

from astroengine.app_api import (
    available_scan_entrypoints,
    canonicalize_events,
    run_scan_or_raise,
)


def _event_to_record(event: Any) -> Dict[str, Any]:
    if isinstance(event, Mapping):
        return dict(event)
    if hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
        except Exception:
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if hasattr(event, "_asdict"):
        try:
            dumped = event._asdict()
        except Exception:
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if is_dataclass(event):
        try:
            return asdict(event)
        except Exception:
            pass
    if hasattr(event, "__dict__"):
        try:
            return dict(vars(event))
        except Exception:
            pass
    try:
        return dict(event)
    except Exception:
        return {"value": repr(event)}


def _events_to_records(events: Iterable[Any]) -> List[Dict[str, Any]]:
    return [_event_to_record(evt) for evt in events]


def _records_to_df(records: List[Dict[str, Any]]):
    if not records:
        return None
    try:
        import pandas as pd  # optional
    except Exception:
        return None
    try:
        return pd.DataFrame(records)
    except Exception:
        return None


def _default_window():
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).replace(microsecond=0)
    end = (now + timedelta(days=1)).replace(microsecond=0)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


st.set_page_config(page_title="AstroEngine — Transit Scanner", layout="wide")
st.title("AstroEngine — Transit Scanner (Minimal App)")

entrypoints = available_scan_entrypoints()
entrypoint_labels = ["Auto (first compatible)"] + [f"{mod}.{fn}" for mod, fn in entrypoints]
entrypoint_lookup = dict(zip(entrypoint_labels[1:], entrypoints))

with st.sidebar:
    st.header("Environment")
    se_path = None
    try:
        from astroengine.ephemeris.utils import get_se_ephe_path

        se_path = get_se_ephe_path()
    except Exception:
        pass
    st.write("**SE_EPHE_PATH**:", os.getenv("SE_EPHE_PATH") or "not set")
    st.write("**ASTROENGINE_SCAN_ENTRYPOINTS**:", os.getenv("ASTROENGINE_SCAN_ENTRYPOINTS") or "not set")
    st.write("**Detected Swiss path**:", se_path or "not found")

    st.header("Scan Settings")
    s, e = _default_window()
    start_utc = st.text_input("Start (UTC, ISO-8601)", value=s)
    end_utc = st.text_input("End (UTC, ISO-8601)", value=e)
    provider = st.selectbox("Provider", options=["auto", "swiss", "pymeeus", "skyfield"], index=0)
    step_minutes = st.slider("Step minutes", min_value=10, max_value=240, value=60, step=10)
    st.caption("Tip: set SE_EPHE_PATH to your Swiss ephemeris folder if using the swiss provider.")
    entrypoint_choice = st.selectbox("Scan entrypoint", entrypoint_labels, index=0)
    st.caption(
        "Select an explicit scan function or leave on Auto to try detected entrypoints in order.\n"
        "Set ASTROENGINE_SCAN_ENTRYPOINTS for custom modules (format: module:function)."
    )

    st.header("Bodies")
    moving = st.multiselect(
        "Transiting bodies",
        ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Node", "Chiron"],
        default=["Sun", "Mars", "Jupiter"],
    )
    targets = st.multiselect(
        "Targets (natal points)",
        ["natal_Sun", "natal_Moon", "natal_Mercury", "natal_Venus", "natal_Mars", "natal_ASC", "natal_MC"],
        default=["natal_Sun", "natal_Moon", "natal_ASC"],
    )
    profile_id = st.text_input("Profile (optional)", value="default")

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


tab_scan, tab_smoke = st.tabs(["Scan Transits", "Swiss Smoketest"])

with tab_scan:
    st.subheader("Run Scan")
    run = st.button("Run scan")
    if run:
        entrypoint_override = entrypoint_lookup.get(entrypoint_choice)
        entrypoint_arg = [entrypoint_override] if entrypoint_override else None
        with st.spinner("Scanning…"):
            try:
                provider_name = None if provider == "auto" else provider
                raw_events, used_entrypoint = run_scan_or_raise(
                    start_utc=start_utc,
                    end_utc=end_utc,
                    moving=moving,
                    targets=targets,
                    provider=provider_name,
                    profile_id=profile_id or None,
                    step_minutes=int(step_minutes),
                    entrypoints=entrypoint_arg,
                    return_used_entrypoint=True,
                )
                events = canonicalize_events(raw_events)
                st.success(f"Scan complete — {len(events)} events")
                st.caption(f"Entrypoint: `{used_entrypoint[0]}.{used_entrypoint[1]}`")
                records = _events_to_records(events)
                df = _records_to_df(records)
                if df is not None:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                elif records:
                    st.json(records)
                else:
                    st.info("Scan completed but returned no events for the selected window.")
                st.markdown("### Export")
                col1, col2 = st.columns(2)
                with col1:
                    to_sqlite = st.text_input("SQLite path", value="runs.db", key="sqlite_path")
                    if st.button("Write to SQLite", key="sqlite_btn"):
                        try:
                            from astroengine.exporters import write_sqlite_canonical

                            rows_written = write_sqlite_canonical(to_sqlite, raw_events)
                            st.success(f"Wrote {rows_written} rows to {to_sqlite}")
                        except Exception as export_exc:
                            st.error(f"SQLite export failed: {export_exc}")
                with col2:
                    to_parquet = st.text_input(
                        "Parquet path (.parquet or dir)", value="runs.parquet", key="parquet_path"
                    )
                    if st.button("Write to Parquet", key="parquet_btn"):
                        try:
                            from astroengine.exporters import write_parquet_canonical

                            rows_written = write_parquet_canonical(to_parquet, raw_events)
                            st.success(f"Wrote {rows_written} rows to {to_parquet}")
                        except Exception as export_exc:
                            st.error(f"Parquet export failed: {export_exc}")
            except Exception as exc:
                st.error(f"Scan failed: {exc}")

with tab_smoke:
    st.subheader("Swiss Smoketest (script)")
    st.write("Runs scripts/swe_smoketest.py with the start time above to validate your Swiss setup.")
    if st.button("Run smoketest"):
        try:
            cmd = [sys.executable, "scripts/swe_smoketest.py", "--utc", start_utc]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if proc.returncode == 0:
                st.success("Smoketest ran successfully")
                st.code(out or "<no output>", language="bash")
            else:
                st.error(f"Smoketest failed (exit {proc.returncode})")
                st.code((out + "\n\n" + err).strip(), language="bash")
        except Exception as exc:
            st.error(f"Failed to run smoketest: {exc}")
# >>> AUTO-GEN END: Streamlit Transit Scanner v1.1
