"""Streamlit interface for observational Alt/Az exploration."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import streamlit as st

from astroengine.engine.observational import (
    EventOptions,
    HeliacalProfile,
    MetConditions,
    VisibilityConstraints,
    heliacal_candidates,
    render_altaz_diagram,
    rise_set_times,
    transit_time,
    visibility_windows,
)
from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation
from astroengine.ephemeris.swe import has_swe, swe

from .components import location_picker

_HAS_SWE = has_swe()
_SWE_MODULE = swe() if _HAS_SWE else None

_BODY_CHOICES = {
    "Sun": getattr(_SWE_MODULE, "SUN", 0) if _SWE_MODULE else 0,
    "Moon": getattr(_SWE_MODULE, "MOON", 1) if _SWE_MODULE else 1,
    "Mercury": getattr(_SWE_MODULE, "MERCURY", 2) if _SWE_MODULE else 2,
    "Venus": getattr(_SWE_MODULE, "VENUS", 3) if _SWE_MODULE else 3,
    "Mars": getattr(_SWE_MODULE, "MARS", 4) if _SWE_MODULE else 4,
    "Jupiter": getattr(_SWE_MODULE, "JUPITER", 5) if _SWE_MODULE else 5,
    "Saturn": getattr(_SWE_MODULE, "SATURN", 6) if _SWE_MODULE else 6,
}

_TZ_LABEL = "UTC"


@st.cache_resource
def _ephemeris_adapter() -> EphemerisAdapter:
    """Return a cached Swiss Ephemeris adapter instance."""

    return EphemerisAdapter(EphemerisConfig())


@st.cache_data(show_spinner=False)
def _compute_topocentric_payload(
    *,
    body: int,
    start_iso: str,
    end_iso: str,
    tz_label: str,
    observer_tuple: tuple[float, float, float],
    met_tuple: tuple[float, float],
    refraction: bool,
    min_alt: float,
    sun_alt_max: float,
    sun_sep: float,
    moon_alt_max: float,
) -> dict[str, Any]:
    """Compute topocentric data for ``body`` between ``start`` and ``end``.

    Results are cached per ``(body, start/end, tz_label)`` key to keep expensive
    Swiss Ephemeris calls from repeating when users tweak presentation widgets.
    """

    start_dt = datetime.fromisoformat(start_iso)
    end_dt = datetime.fromisoformat(end_iso)
    adapter = _ephemeris_adapter()

    observer = ObserverLocation(
        latitude_deg=observer_tuple[0],
        longitude_deg=observer_tuple[1],
        elevation_m=observer_tuple[2],
    )
    met = MetConditions(temperature_c=met_tuple[0], pressure_hpa=met_tuple[1])
    options = EventOptions(refraction=refraction, met=met)

    rise, set_ = rise_set_times(adapter, body, start_dt, observer, options=options)
    transit = transit_time(adapter, body, start_dt, observer)

    constraints = VisibilityConstraints(
        min_altitude_deg=min_alt,
        sun_altitude_max_deg=sun_alt_max,
        sun_separation_min_deg=sun_sep,
        moon_altitude_max_deg=moon_alt_max,
        refraction=refraction,
        met=met,
    )
    windows = visibility_windows(adapter, body, start_dt, end_dt, observer, constraints)
    heliacal = heliacal_candidates(
        adapter,
        body,
        (start_dt, end_dt),
        observer,
        HeliacalProfile(
            mode="rising",
            min_object_altitude_deg=min_alt,
            sun_altitude_max_deg=sun_alt_max,
            sun_separation_min_deg=sun_sep,
        ),
    )

    diagram = render_altaz_diagram(
        adapter,
        body,
        start_dt,
        end_dt,
        observer,
        refraction=refraction,
        met=met,
    )

    window_rows: list[dict[str, Any]] = [
        {
            "start": w.start.isoformat(),
            "end": w.end.isoformat(),
            "duration_min": round(w.duration_seconds / 60, 1),
            "max_alt_deg": round(w.max_altitude_deg, 2),
            "score": round(w.score, 2),
        }
        for w in windows
    ]

    heliacal_iso = [moment.isoformat() for moment in heliacal]

    return {
        "tz": tz_label,
        "rise": rise.isoformat() if rise else None,
        "set": set_.isoformat() if set_ else None,
        "transit": transit.isoformat() if transit else None,
        "windows": window_rows,
        "heliacal": heliacal_iso,
        "diagram": {
            "svg": diagram.svg,
            "png": diagram.png,
            "metadata": diagram.metadata,
        },
    }


def _stream_partial_windows(
    *,
    rows: list[dict[str, Any]],
    placeholder: st.delta_generator.DeltaGenerator,
    progress_placeholder: st.delta_generator.DeltaGenerator,
) -> None:
    """Incrementally render visibility window rows to the UI."""

    if not rows:
        progress_placeholder.info("No visibility windows matched the given constraints.")
        return

    buffered: list[dict[str, Any]] = []
    total = len(rows)
    for idx, row in enumerate(rows, start=1):
        buffered.append(row)
        progress_placeholder.info(
            f"Rendering visibility window {idx} / {total} (timezone: {_TZ_LABEL})."
        )
        placeholder.dataframe(buffered, use_container_width=True, hide_index=True)

    progress_placeholder.success(
        f"Loaded {total} visibility windows (timezone: {_TZ_LABEL})."
    )


def _init_session_state() -> None:
    if "altaz_params" in st.session_state:
        return

    now = datetime.now(tz=UTC)
    st.session_state.altaz_params = {
        "lat": 40.7128,
        "lon": -74.0060,
        "elev": 10.0,
        "temp": 10.0,
        "press": 1010.0,
        "refraction": True,
        "body_label": "Sun",
        "start": now,
        "duration_hours": 12,
        "min_alt": 5,
        "sun_alt_max": -12,
        "sun_sep": 10,
        "moon_alt_max": 90,
        "tz": _TZ_LABEL,
    }


def _throttled_button(label: str, *, key: str, cooldown: float = 0.5, **kwargs: Any) -> bool:
    """Button helper that debounces rapid clicks using a monotonic clock."""

    pressed = st.button(label, key=key, **kwargs)
    if not pressed:
        return False

    last = st.session_state.get("_altaz_click_clock")
    current = time.monotonic()
    if last and current - last < cooldown:
        st.info("Please wait a moment before re-running the computation.")
        return False

    st.session_state._altaz_click_clock = current
    return True


def _render_results(payload: dict[str, Any]) -> None:
    st.subheader("Rise / Set / Transit")
    metrics = st.columns(3)
    metrics[0].metric("Rise", payload.get("rise", "—") or "—")
    metrics[1].metric("Transit", payload.get("transit", "—") or "—")
    metrics[2].metric("Set", payload.get("set", "—") or "—")

    st.subheader("Visibility Windows")
    window_placeholder = st.empty()
    progress_placeholder = st.empty()
    _stream_partial_windows(
        rows=list(payload.get("windows", [])),
        placeholder=window_placeholder,
        progress_placeholder=progress_placeholder,
    )

    st.subheader("Heliacal Candidates")
    heliacal = payload.get("heliacal", [])
    if heliacal:
        st.write(heliacal)
    else:
        st.info("No heliacal rising candidates within the configured window.")

    st.subheader("Alt/Az Diagram")
    diagram = payload.get("diagram", {})
    svg = diagram.get("svg")
    png = diagram.get("png")
    metadata = diagram.get("metadata", {})

    if svg:
        st.download_button(
            "Download SVG",
            svg,
            file_name="altaz.svg",
            mime="image/svg+xml",
        )
    if png:
        st.download_button(
            "Download PNG",
            png,
            file_name="altaz.png",
            mime="image/png",
        )
        st.image(png, caption="Time-altitude and polar track", use_column_width=True)
    if metadata:
        st.caption(
            "Diagram metadata: "
            + ", ".join(f"{k}={v}" for k, v in metadata.items() if v is not None)
        )

    st.caption("All outputs are topocentric and derived from Swiss Ephemeris data.")


def main() -> None:
    st.set_page_config(page_title="Alt/Az Explorer", layout="wide")
    st.title("Topocentric Altitude & Visibility Explorer")
    _init_session_state()

    params: dict[str, Any] = dict(st.session_state.altaz_params)

    with st.sidebar:
        location_picker(
            "Observer location",
            default_query="New York, United States",
            state_prefix="altaz_observer",
            help="Atlas lookup feeds the observer coordinates and shows DST status.",
        )
        lat_default = float(st.session_state.get("altaz_observer_lat", params["lat"]))
        lon_default = float(st.session_state.get("altaz_observer_lon", params["lon"]))

        with st.form("altaz-controls"):
            st.header("Observer")
            params["lat"] = st.number_input(
                "Latitude (deg)",
                value=lat_default,
                min_value=-90.0,
                max_value=90.0,
                step=0.1,
            )
            params["lon"] = st.number_input(
                "Longitude (deg)",
                value=lon_default,
                min_value=-180.0,
                max_value=180.0,
                step=0.1,
            )
            params["elev"] = st.number_input("Elevation (m)", value=float(params["elev"]), step=1.0)
            params["temp"] = st.number_input("Temperature (°C)", value=float(params["temp"]), step=1.0)
            params["press"] = st.number_input("Pressure (hPa)", value=float(params["press"]), step=1.0)
            params["refraction"] = st.checkbox("Apply refraction", value=bool(params["refraction"]))

            st.subheader("Target")
            params["body_label"] = st.selectbox(
                "Body",
                list(_BODY_CHOICES.keys()),
                index=list(_BODY_CHOICES.keys()).index(params["body_label"]),
            )
            start_default = params["start"].astimezone(UTC)
            params["start_date"] = st.date_input("Start date", start_default.date())
            params["start_time"] = st.time_input("Start time", start_default.time())
            params["duration_hours"] = st.slider(
                "Duration (hours)",
                min_value=1,
                max_value=24,
                value=int(params["duration_hours"]),
                step=1,
            )

            st.subheader("Visibility Constraints")
            params["min_alt"] = st.slider(
                "Minimum altitude (deg)",
                min_value=0,
                max_value=45,
                value=int(params["min_alt"]),
            )
            params["sun_alt_max"] = st.slider(
                "Max Sun altitude (deg)",
                min_value=-18,
                max_value=10,
                value=int(params["sun_alt_max"]),
            )
            params["sun_sep"] = st.slider(
                "Min Sun separation (deg)",
                min_value=0,
                max_value=30,
                value=int(params["sun_sep"]),
            )
            params["moon_alt_max"] = st.slider(
                "Max Moon altitude (deg)",
                min_value=-10,
                max_value=90,
                value=int(params["moon_alt_max"]),
            )

            if st.form_submit_button("Apply inputs", type="secondary"):
                params["start"] = datetime.combine(
                    params.pop("start_date"),
                    params.pop("start_time"),
                    tzinfo=UTC,
                )
                st.session_state.altaz_params.update(params)
                st.session_state["altaz_observer_lat"] = float(params["lat"])
                st.session_state["altaz_observer_lon"] = float(params["lon"])
                st.success("Inputs updated. Use 'Run visibility scan' to compute results.")

    # Use latest persisted parameters for computation.
    params = dict(st.session_state.altaz_params)
    body = _BODY_CHOICES[params["body_label"]]
    start_dt = params["start"]
    end_dt = start_dt + timedelta(hours=int(params["duration_hours"]))

    run_scan = _throttled_button(
        "Run visibility scan",
        key="run-visibility-scan",
        type="primary",
    )

    if run_scan:
        status = st.status("Dispatching Swiss Ephemeris computations…", expanded=True)
        status.write("Caching ephemeris adapter with st.cache_resource…")
        status.write(
            f"Window: {start_dt.isoformat()} → {end_dt.isoformat()} ({params['tz']})"
        )

        payload = _compute_topocentric_payload(
            body=body,
            start_iso=start_dt.isoformat(),
            end_iso=end_dt.isoformat(),
            tz_label=params["tz"],
            observer_tuple=(params["lat"], params["lon"], params["elev"]),
            met_tuple=(params["temp"], params["press"]),
            refraction=bool(params["refraction"]),
            min_alt=float(params["min_alt"]),
            sun_alt_max=float(params["sun_alt_max"]),
            sun_sep=float(params["sun_sep"]),
            moon_alt_max=float(params["moon_alt_max"]),
        )

        status.write("Rendering visibility windows and diagrams…")
        st.session_state.altaz_results = payload
        status.update(label="Computation complete", state="complete", expanded=False)

    if "altaz_results" in st.session_state:
        _render_results(st.session_state.altaz_results)
    else:
        st.caption("Adjust parameters and run the visibility scan to see results.")


if __name__ == "__main__":
    main()
