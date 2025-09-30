"""Streamlit interface for observational Alt/Az exploration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import streamlit as st

from astroengine.ephemeris import EphemerisAdapter, EphemerisConfig, ObserverLocation
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

try:
    import swisseph as swe
except ModuleNotFoundError:  # pragma: no cover - Streamlit app executed manually
    swe = None

_BODY_CHOICES = {
    "Sun": getattr(swe, "SUN", 0),
    "Moon": getattr(swe, "MOON", 1),
    "Mercury": getattr(swe, "MERCURY", 2),
    "Venus": getattr(swe, "VENUS", 3),
    "Mars": getattr(swe, "MARS", 4),
    "Jupiter": getattr(swe, "JUPITER", 5),
    "Saturn": getattr(swe, "SATURN", 6),
}

_ADAPTER = EphemerisAdapter(EphemerisConfig())


def _observer(lat: float, lon: float, elev: float) -> ObserverLocation:
    return ObserverLocation(latitude_deg=lat, longitude_deg=lon, elevation_m=elev)


def main() -> None:
    st.set_page_config(page_title="Alt/Az Explorer", layout="wide")
    st.title("Topocentric Altitude & Visibility Explorer")

    with st.sidebar:
        st.header("Observer")
        lat = st.number_input("Latitude (deg)", value=40.7128, min_value=-90.0, max_value=90.0, step=0.1)
        lon = st.number_input("Longitude (deg)", value=-74.0060, min_value=-180.0, max_value=180.0, step=0.1)
        elev = st.number_input("Elevation (m)", value=10.0, step=1.0)
        temp = st.number_input("Temperature (°C)", value=10.0, step=1.0)
        press = st.number_input("Pressure (hPa)", value=1010.0, step=1.0)
        refraction = st.checkbox("Apply refraction", value=True)

    col1, col2 = st.columns(2)
    with col1:
        st.header("Target")
        body_label = st.selectbox("Body", list(_BODY_CHOICES.keys()))
        body = _BODY_CHOICES[body_label]
        start_date = st.date_input("Start date", datetime.now(tz=UTC).date())
        start_time = st.time_input("Start time", datetime.now(tz=UTC).time())
        duration_hours = st.slider("Duration (hours)", min_value=1, max_value=24, value=12)
    with col2:
        st.header("Visibility Constraints")
        min_alt = st.slider("Minimum altitude (deg)", min_value=0, max_value=45, value=5)
        sun_alt_max = st.slider("Max Sun altitude (deg)", min_value=-18, max_value=10, value=-12)
        sun_sep = st.slider("Min Sun separation (deg)", min_value=0, max_value=30, value=10)
        moon_alt_max = st.slider("Max Moon altitude (deg)", min_value=-10, max_value=90, value=90)

    start_dt = datetime.combine(start_date, start_time, tzinfo=UTC)
    end_dt = start_dt + timedelta(hours=duration_hours)
    observer = _observer(lat, lon, elev)
    met = MetConditions(temperature_c=temp, pressure_hpa=press)

    st.subheader("Rise / Set / Transit")
    options = EventOptions(refraction=refraction, met=met)
    rise, set_ = rise_set_times(_ADAPTER, body, start_dt, observer, options=options)
    transit = transit_time(_ADAPTER, body, start_dt, observer)
    st.write({
        "rise": rise.isoformat() if rise else None,
        "set": set_.isoformat() if set_ else None,
        "transit": transit.isoformat() if transit else None,
    })

    st.subheader("Visibility Windows")
    constraints = VisibilityConstraints(
        min_altitude_deg=min_alt,
        sun_altitude_max_deg=sun_alt_max,
        sun_separation_min_deg=sun_sep,
        moon_altitude_max_deg=moon_alt_max,
        refraction=refraction,
        met=met,
    )
    windows = visibility_windows(_ADAPTER, body, start_dt, end_dt, observer, constraints)
    if windows:
        st.table(
            {
                "start": [w.start.isoformat() for w in windows],
                "end": [w.end.isoformat() for w in windows],
                "duration_min": [round(w.duration_seconds / 60, 1) for w in windows],
                "max_alt_deg": [round(w.max_altitude_deg, 2) for w in windows],
                "score": [round(w.score, 2) for w in windows],
            }
        )
    else:
        st.info("No windows matched the provided constraints.")

    st.subheader("Heliacal Candidates")
    profile = HeliacalProfile(
        mode="rising",
        min_object_altitude_deg=min_alt,
        sun_altitude_max_deg=sun_alt_max,
        sun_separation_min_deg=sun_sep,
    )
    heliacal = heliacal_candidates(_ADAPTER, body, (start_dt, end_dt), observer, profile)
    st.write([moment.isoformat() for moment in heliacal])

    st.subheader("Alt/Az Diagram")
    diagram = render_altaz_diagram(
        _ADAPTER,
        body,
        start_dt,
        end_dt,
        observer,
        refraction=refraction,
        met=met,
    )
    st.download_button("Download SVG", diagram.svg, file_name="altaz.svg", mime="image/svg+xml")
    if diagram.png:
        st.download_button(
            "Download PNG",
            diagram.png,
            file_name="altaz.png",
            mime="image/png",
        )
        st.image(diagram.png, caption="Time-altitude and polar track", use_column_width=True)

    st.caption("All outputs are topocentric and derived from Swiss Ephemeris data.")


if __name__ == "__main__":
    main()
