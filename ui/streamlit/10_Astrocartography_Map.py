"""Streamlit panel for astrocartography line exploration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pydeck as pdk
import streamlit as st

from astroengine.analysis import compute_astrocartography_lines
from astroengine.config import settings as runtime_settings
from astroengine.ephemeris import SwissEphemerisAdapter
from astroengine.ephemeris.swe import has_swe
from astroengine.userdata.vault import list_natals, load_natal

if not has_swe():  # pragma: no cover - Streamlit runtime only
    swisseph = None
else:
    swisseph = "available"

st.set_page_config(page_title="Astrocartography Explorer", layout="wide")

settings = runtime_settings.persisted()
cfg = settings.astrocartography

st.title("Astrocartography Explorer")
st.write(
    "Visualize angular lines for stored natal charts. All calculations rely on the"
    " Swiss Ephemeris adapter bundled with AstroEngine — the map is driven entirely"
    " by observed planetary positions."
)


@st.cache_resource(show_spinner=False)
def _adapter() -> SwissEphemerisAdapter:
    return SwissEphemerisAdapter.get_default_adapter()


@st.cache_data(show_spinner=False)
def _load_lines(
    natal_id: str,
    bodies: tuple[str, ...],
    kinds: tuple[str, ...],
    lat_step: float,
    simplify: float,
    parans: bool,
) -> dict[str, Any]:
    natal = load_natal(natal_id)
    moment = datetime.fromisoformat(natal.utc.replace("Z", "+00:00"))
    moment = moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)
    result = compute_astrocartography_lines(
        moment,
        bodies=bodies,
        adapter=_adapter(),
        lat_step=lat_step,
        line_types=kinds,
        simplify_tolerance=simplify,
        show_parans=parans,
    )
    return {
        "moment": moment,
        "lines": result.lines,
        "parans": result.parans,
    }


with st.sidebar:
    st.header("Inputs")
    natal_ids = list_natals()
    selected_natal = st.selectbox("Natal chart", options=natal_ids, index=0 if natal_ids else None)

    default_bodies = tuple(cfg.bodies)
    default_kinds = tuple(cfg.line_types)

    body_options = sorted({*default_bodies, "uranus", "neptune", "pluto"})
    selected_bodies = st.multiselect(
        "Bodies",
        options=body_options,
        default=default_bodies,
        help="Pick the planets to render on the map.",
    )
    selected_kinds = st.multiselect(
        "Line types",
        options=["ASC", "DSC", "MC", "IC"],
        default=default_kinds,
        help="Toggle horizon (ASC/DSC) or meridian (MC/IC) lines.",
    )
    lat_step = st.slider(
        "Latitude sampling step (degrees)",
        min_value=0.5,
        max_value=10.0,
        value=float(cfg.lat_step_deg),
        step=0.5,
    )
    simplify_tol = st.slider(
        "Simplification tolerance (degrees)",
        min_value=0.0,
        max_value=5.0,
        value=float(cfg.simplify_tolerance_deg),
        step=0.1,
    )
    parans = st.toggle("Show parans", value=cfg.show_parans, help="Include paran markers when available.")

if swisseph is None:
    st.error(
        "Swiss Ephemeris is not available. Install astroengine[locational] to render"
        " astrocartography maps."
    )
    st.stop()

if not selected_natal:
    st.info("No natal charts found. Create one using the natals API before exploring maps.")
    st.stop()

if not selected_bodies:
    st.warning("Select at least one body to compute linework.")
    st.stop()

if not selected_kinds:
    st.warning("Select at least one line type to compute linework.")
    st.stop()

payload = _load_lines(
    selected_natal,
    tuple(selected_bodies),
    tuple(selected_kinds),
    float(lat_step),
    float(simplify_tol),
    bool(parans),
)

lines = payload["lines"]
parans_payload = payload["parans"]
moment = payload["moment"]

if not lines:
    st.warning("No linework produced for the selected configuration.")
    st.stop()

line_rows: list[dict[str, Any]] = []
map_rows: list[dict[str, Any]] = []
line_colors = {
    "MC": [52, 152, 219],
    "IC": [41, 128, 185],
    "ASC": [231, 76, 60],
    "DSC": [241, 196, 15],
}

for line in lines:
    coords = [[lon, lat] for lon, lat in line.coordinates]
    color = line_colors.get(line.kind, [255, 255, 255])
    line_rows.append(
        {
            "Body": line.body.title(),
            "Line": line.kind,
            "Points": len(coords),
            "RA (deg)": round(float(line.metadata.get("ra_deg", 0.0)), 3),
            "Decl (deg)": round(float(line.metadata.get("decl_deg", 0.0)), 3),
        }
    )
    map_rows.append(
        {
            "body": line.body,
            "kind": line.kind,
            "path": coords,
            "color": color,
        }
    )

layer = pdk.Layer(
    "Path",
    map_rows,
    get_path="path",
    get_color="color",
    width_scale=1000,
    width_min_pixels=2,
)

view_state = pdk.ViewState(latitude=0.0, longitude=0.0, zoom=1.2)
deck = pdk.Deck(
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    layers=[layer],
    initial_view_state=view_state,
)

st.subheader(f"Lines rendered for {moment.isoformat().replace('+00:00', 'Z')}")
st.pydeck_chart(deck)

st.subheader("Line details")
st.dataframe(line_rows, use_container_width=True)

if parans and parans_payload:
    st.subheader("Parans")
    st.json([dict(entry) for entry in parans_payload])
elif parans:
    st.info("No parans detected for the current configuration.")
