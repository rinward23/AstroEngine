from __future__ import annotations

import json
from collections.abc import Sequence

import pandas as pd
import streamlit as st

from astroengine.analysis import DeclinationAspect, declination_aspects, get_declinations
from astroengine.chart.natal import expansions_from_groups
from astroengine.config import settings as runtime_settings
from core.aspects_plus.harmonics import BASE_ASPECTS
from core.viz_plus.aspect_grid import aspect_grid_symbols, render_aspect_grid
from core.viz_plus.wheel_svg import WheelOptions, build_aspect_hits, render_chart_wheel
from ui.streamlit.api import APIClient
from ui.streamlit.data_cache import load_fixed_star_catalog

st.set_page_config(page_title="Chart Wheel & Aspectarian", page_icon="🎡", layout="wide")
st.title("Chart Wheel & Aspectarian 🎡")

api = APIClient()

# --------------------------- Defaults --------------------------------------
DEFAULT_POSITIONS = {
    "Sun": 0.0,
    "Moon": 90.0,
    "Mercury": 15.0,
    "Venus": 70.0,
    "Mars": 180.0,
    "Jupiter": 220.0,
    "Saturn": 300.0,
}
DEFAULT_POLICY = {
    "per_object": {},
    "per_aspect": {
        "conjunction": 8.0,
        "opposition": 7.0,
        "square": 6.0,
        "trine": 6.0,
        "sextile": 4.0,
    },
    "adaptive_rules": {},
}
DEFAULT_ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile"]
AVAILABLE_ASPECTS = sorted(BASE_ASPECTS.keys())
_APP_SETTINGS = runtime_settings.persisted()
_DECL_DEFAULT_ENABLED = bool(getattr(_APP_SETTINGS.declinations, "enabled", True))
_DECL_DEFAULT_ORB = float(getattr(_APP_SETTINGS.declinations, "orb_deg", 0.5))
_BODY_GROUP_DEFAULTS = getattr(getattr(_APP_SETTINGS, "bodies", None), "groups", {})
_EXPANSION_DEFAULTS = expansions_from_groups(_BODY_GROUP_DEFAULTS)

_OPTIONAL_BODY_MAP: dict[str, tuple[str, ...]] = {
    "asteroids": ("Ceres", "Pallas", "Juno", "Vesta"),
    "chiron": ("Chiron",),
    "mean_lilith": ("Black Moon Lilith (Mean)",),
    "true_lilith": ("Black Moon Lilith (True)",),
    "mean_node": ("Mean Node", "Mean South Node", "North Node", "South Node"),
    "true_node": ("True Node", "True South Node"),
    "vertex": ("Vertex", "Anti-Vertex"),
}


def _filter_optional_positions(
    positions: dict[str, float], toggles: dict[str, bool]
) -> dict[str, float]:
    optional_names: set[str] = set()
    allowed: set[str] = set()
    for key, names in _OPTIONAL_BODY_MAP.items():
        optional_names.update(names)
        if toggles.get(key, False):
            allowed.update(names)
    filtered: dict[str, float] = {}
    for name, value in positions.items():
        if name in optional_names and name not in allowed:
            continue
        filtered[name] = value
    return filtered


def _overlay_declination_markers(
    grid: dict[str, dict[str, str]], hits: Sequence[DeclinationAspect]
) -> dict[str, dict[str, str]]:
    """Return a copy of ``grid`` with declination symbols appended per hit."""

    updated: dict[str, dict[str, str]] = {a: dict(row) for a, row in grid.items()}
    for hit in hits:
        marker = "∥" if hit.kind == "parallel" else "⇅"
        for first, second in ((hit.body_a, hit.body_b), (hit.body_b, hit.body_a)):
            cell = updated.setdefault(first, {}).get(second, "")
            if marker not in cell:
                updated[first][second] = f"{cell}{marker}" if cell else marker
    return updated

wheel_tab, aspectarian_tab = st.tabs(["Wheel", "Aspectarian"])

# --------------------------- Sidebar inputs --------------------------------
with st.sidebar:
    st.header("Inputs")
    positions_txt = st.text_area(
        "Positions JSON (name → longitude°)",
        value=json.dumps(DEFAULT_POSITIONS, indent=2),
        height=220,
    )
    try:
        positions: dict[str, float] = {
            str(name): float(lon)
            for name, lon in (json.loads(positions_txt) if positions_txt.strip() else {}).items()
        }
    except Exception as exc:  # pragma: no cover - UI error path
        st.error(f"Invalid positions JSON: {exc}")
        positions = {}
    else:
        if positions:
            positions = _filter_optional_positions(positions, expansion_toggles)

    houses_txt = st.text_area(
        "Houses JSON (12 longitudes, optional)",
        value="",
        height=80,
        help="e.g., [100,130,...] (length 12)",
    )
    houses: list[float] | None = None
    if houses_txt.strip():
        try:
            houses = [float(x) for x in json.loads(houses_txt)]
            if len(houses) != 12:
                st.warning("Provide exactly 12 house cusp longitudes.")
                houses = None
        except Exception as exc:  # pragma: no cover - UI error path
            st.warning(f"Invalid houses JSON: {exc}")
            houses = None

    st.divider()
    st.header("Chart Actions")

    chart_id_input = st.text_input("Chart ID", value="")

    def _parse_chart_id(raw: str) -> int | None:
        raw = raw.strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value > 0 else None

    chart_id = _parse_chart_id(chart_id_input)
    note_text = st.text_area("Note", value="", height=80)
    tags_input = st.text_input("Tags (comma separated)", value="")
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]

    st.divider()
    st.header("Body Expansions")
    col_toggle_a, col_toggle_b = st.columns(2)
    include_asteroids = col_toggle_a.toggle(
        "Major asteroids",
        value=_EXPANSION_DEFAULTS.get("asteroids", False),
        help="Toggle Ceres, Pallas, Juno, and Vesta.",
    )
    include_chiron = col_toggle_b.toggle(
        "Chiron",
        value=_EXPANSION_DEFAULTS.get("chiron", False),
    )
    include_mean_lilith = col_toggle_a.toggle(
        "Mean Lilith",
        value=_EXPANSION_DEFAULTS.get("mean_lilith", False),
    )
    include_true_lilith = col_toggle_b.toggle(
        "True Lilith",
        value=_EXPANSION_DEFAULTS.get("true_lilith", False),
    )
    include_mean_node = col_toggle_a.toggle(
        "Mean Node",
        value=_EXPANSION_DEFAULTS.get("mean_node", False),
        help="Enable mean North/South Node pair.",
    )
    include_true_node = col_toggle_b.toggle(
        "True Node",
        value=_EXPANSION_DEFAULTS.get("true_node", False),
        help="Enable true North/South Node pair.",
    )
    include_vertex = st.toggle(
        "Vertex & Anti-Vertex",
        value=_EXPANSION_DEFAULTS.get("vertex", False),
    )
    expansion_toggles = {
        "asteroids": include_asteroids,
        "chiron": include_chiron,
        "mean_lilith": include_mean_lilith,
        "true_lilith": include_true_lilith,
        "mean_node": include_mean_node,
        "true_node": include_true_node,
        "vertex": include_vertex,
    }

    if st.button("Save note", use_container_width=True):
        if chart_id is None:
            st.warning("Provide a valid chart ID before saving a note.")
        elif not note_text.strip():
            st.warning("Enter note text before saving.")
        else:
            try:
                api.create_note(chart_id, note_text.strip(), tags)
                st.success("Note saved")
                st.session_state["_chart_notes_cache"] = None
            except Exception as exc:  # pragma: no cover - streamlit UI only
                st.error(f"Failed to save note: {exc}")

    if st.button("Export", use_container_width=True):
        try:
            st.session_state["_export_bundle"] = api.export_bundle()
            st.success("Export ready")
        except Exception as exc:  # pragma: no cover - streamlit UI only
            st.error(f"Export failed: {exc}")

    export_bytes = st.session_state.get("_export_bundle")
    if isinstance(export_bytes, (bytes, bytearray)):
        st.download_button(
            "Download export",
            data=export_bytes,
            file_name="astroengine_export.zip",
            mime="application/zip",
            use_container_width=True,
        )

    pdf_enabled = True
    try:
        settings_payload = api.fetch_settings()
        pdf_enabled = bool(settings_payload.get("reports", {}).get("pdf_enabled", True))
    except Exception as exc:  # pragma: no cover - streamlit UI only
        st.info(f"Settings unavailable: {exc}")

    if pdf_enabled and chart_id is not None:
        if st.button("Generate PDF", use_container_width=True):
            try:
                st.session_state["_chart_pdf"] = api.generate_chart_pdf(chart_id)
                st.success("PDF generated")
            except Exception as exc:  # pragma: no cover - streamlit UI only
                st.error(f"PDF generation failed: {exc}")
    elif not pdf_enabled:
        st.caption("PDF generation disabled in settings.")

    pdf_bytes = st.session_state.get("_chart_pdf")
    if isinstance(pdf_bytes, (bytes, bytearray)):
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"chart_{chart_id or 'report'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    notes_records = []
    if chart_id is not None:
        cache_key = "_chart_notes_cache"
        cached = st.session_state.get(cache_key)
        if cached is None:
            try:
                cached = api.list_notes(chart_id)
            except Exception as exc:  # pragma: no cover - streamlit UI only
                st.warning(f"Unable to load notes: {exc}")
                cached = []
            st.session_state[cache_key] = cached
        notes_records = cached

    if notes_records:
        with st.expander("Recent notes", expanded=False):
            for item in notes_records:
                created = item.get("created_at", "")
                tags_fmt = ", ".join(item.get("tags", []))
                st.markdown(f"**{created}** — {item.get('text')}" + (f" _(tags: {tags_fmt})_" if tags_fmt else ""))
    st.header("Aspects & Orbs")
    aspects = st.multiselect(
        "Aspect set",
        options=AVAILABLE_ASPECTS,
        default=[a for a in DEFAULT_ASPECTS if a in AVAILABLE_ASPECTS],
    )

    selected_aspects = aspects or [a for a in DEFAULT_ASPECTS if a in AVAILABLE_ASPECTS]

    policy_per_aspect: dict[str, float] = {}
    if selected_aspects:
        st.caption("Orb overrides (degrees)")
    for asp in selected_aspects:
        default_orb = DEFAULT_POLICY["per_aspect"].get(asp, 3.0)
        policy_per_aspect[asp] = st.number_input(
            f"{asp}",
            min_value=0.1,
            max_value=15.0,
            value=float(default_orb),
            step=0.1,
            key=f"orb_{asp}",
        )

    orb_policy = {
        "per_object": {},
        "per_aspect": policy_per_aspect or DEFAULT_POLICY["per_aspect"].copy(),
        "adaptive_rules": {},
    }

    st.divider()
    st.header("Declination Aspects")
    declination_enabled = st.toggle(
        "Compute declination aspects",
        value=_DECL_DEFAULT_ENABLED,
        help="Detect declination parallels/contraparallels within a configured orb.",
    )
    declination_orb = st.number_input(
        "Declination orb (deg)",
        min_value=0.1,
        max_value=5.0,
        value=float(_DECL_DEFAULT_ORB),
        step=0.1,
    )


# --------------------------- Wheel Tab -------------------------------------
with wheel_tab:
    st.subheader("SVG Chart Wheel")
    size = st.slider("Size (px)", min_value=400, max_value=1200, value=800, step=50)
    show_ticks = st.toggle("Show degree ticks", value=True)
    show_houses = st.toggle("Show house lines", value=True)
    show_aspects = st.toggle("Draw aspect lines", value=True)

    if st.button("Render Wheel", type="primary"):
        if not positions:
            st.warning("Please provide valid positions JSON.")
            st.stop()

        options = WheelOptions(
            size=int(size),
            show_degree_ticks=bool(show_ticks),
            show_house_lines=bool(show_houses),
            show_aspects=bool(show_aspects),
            aspects=selected_aspects,
            policy=orb_policy,
        )
        svg = render_chart_wheel(positions, houses=houses, options=options)
        st.components.v1.html(svg, height=int(size) + 40, scrolling=False)
        st.download_button(
            "Download SVG",
            svg.encode("utf-8"),
            file_name="chart_wheel.svg",
            mime="image/svg+xml",
        )


# --------------------------- Aspectarian Tab -------------------------------
with aspectarian_tab:
    st.subheader("Aspectarian")
    if st.button("Compute Aspects", type="primary"):
        if not positions:
            st.warning("Please provide valid positions JSON.")
            st.stop()

        hits = build_aspect_hits(positions, aspects=selected_aspects, policy=orb_policy)
        if hits:
            df = pd.DataFrame(hits)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Hits CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="aspect_hits.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download Hits JSON",
                json.dumps(hits, indent=2).encode("utf-8"),
                file_name="aspect_hits.json",
                mime="application/json",
            )
        else:
            st.info("No matched aspects with current policy.")

        grid = render_aspect_grid(hits)
        symbol_grid = aspect_grid_symbols(
            positions,
            aspects=selected_aspects,
            policy=orb_policy,
            hits=hits,
        )

        declination_hits: list[DeclinationAspect] = []
        symbol_grid_display = symbol_grid
        if declination_enabled:
            declinations = get_declinations(positions)
            declination_hits = declination_aspects(
                declinations, orb_deg=float(declination_orb)
            )
            st.subheader("Declination Parallels/Contraparallels")
            if declination_hits:
                decl_df = pd.DataFrame(
                    [
                        {
                            "Body A": hit.body_a,
                            "Body B": hit.body_b,
                            "Kind": "Parallel"
                            if hit.kind == "parallel"
                            else "Contraparallel",
                            "Decl A (°)": hit.declination_a,
                            "Decl B (°)": hit.declination_b,
                            "Orb (°)": hit.orb,
                        }
                        for hit in declination_hits
                    ]
                ).round({"Decl A (°)": 2, "Decl B (°)": 2, "Orb (°)": 3})
                st.dataframe(decl_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Declination Aspects CSV",
                    decl_df.to_csv(index=False).encode("utf-8"),
                    file_name="declination_aspects.csv",
                    mime="text/csv",
                )
                st.download_button(
                    "Download Declination Aspects JSON",
                    json.dumps([
                        {
                            "body_a": hit.body_a,
                            "body_b": hit.body_b,
                            "kind": hit.kind,
                            "declination_a": hit.declination_a,
                            "declination_b": hit.declination_b,
                            "orb": hit.orb,
                            "delta": hit.delta,
                        }
                        for hit in declination_hits
                    ], indent=2).encode("utf-8"),
                    file_name="declination_aspects.json",
                    mime="application/json",
                )
                overlay_declination = st.toggle(
                    "Overlay declination markers in aspect grid",
                    value=True,
                    key="declination_overlay_toggle",
                )
                if overlay_declination:
                    symbol_grid_display = _overlay_declination_markers(
                        symbol_grid_display, declination_hits
                    )
            else:
                st.info(
                    f"No declination parallels or contraparallels within {declination_orb:.2f}°.",
                )

        if grid:
            st.subheader("Aspect Grid (names)")
            grid_names_df = pd.DataFrame(grid).fillna("").T
            st.dataframe(grid_names_df, use_container_width=True)
            st.download_button(
                "Download Grid (names) JSON",
                json.dumps(grid, indent=2).encode("utf-8"),
                file_name="aspect_grid_names.json",
                mime="application/json",
            )

        if symbol_grid_display:
            st.subheader("Aspect Grid (symbols)")
            grid_df = pd.DataFrame(symbol_grid_display).fillna("").T
            st.dataframe(grid_df, use_container_width=True)
            st.download_button(
                "Download Grid CSV",
                grid_df.to_csv().encode("utf-8"),
                file_name="aspect_grid.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download Grid JSON",
                json.dumps(symbol_grid, indent=2).encode("utf-8"),
                file_name="aspect_grid.json",
                mime="application/json",
            )

        if not grid and not symbol_grid:
            st.caption("Grid empty — no aspects matched.")

    with st.expander("Fixed star catalog (cached)", expanded=False):
        catalog_rows = load_fixed_star_catalog()
        if catalog_rows:
            star_df = (
                pd.DataFrame(catalog_rows)
                .sort_values("mag")
                .reset_index(drop=True)
            )
            cols = [col for col in ("name", "lon_deg", "lat_deg", "mag") if col in star_df.columns]
            st.dataframe(star_df[cols], use_container_width=True, hide_index=True)
            st.caption(
                "Catalog results are cached with st.cache_data to keep large CSV reads fast during reruns."
            )
        else:
            st.info("Fixed star catalog unavailable.")
