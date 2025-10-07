"""Streamlit application providing a traditional timing lab."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from core.lots_plus.catalog import Sect as LotSect
from core.lots_plus.catalog import compute_lots

from ...chart.natal import ChartLocation, compute_natal_chart
from ...engine.traditional import (
    Interval,
    apply_loosing_of_bond,
    build_chart_context,
    find_alcocoden,
    find_hyleg,
    flag_peaks_fortune,
    load_traditional_profiles,
    profection_year_segments,
    sect_info,
    zr_periods,
)
from ...engine.traditional.models import ChartCtx, LifeProfile
from ...engine.traditional.zr import SIGN_ORDER
from ..components import location_picker


def _parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - user input driven
        raise ValueError(f"Invalid ISO datetime: {value}") from exc


def _build_ctx(moment: datetime, latitude: float, longitude: float, house_system: str) -> ChartCtx:
    location = ChartLocation(latitude=latitude, longitude=longitude)
    chart = compute_natal_chart(moment, location)
    sect = sect_info(moment, location)
    lots = compute_lots(["Fortune", "Spirit"], _lot_positions(chart), LotSect.DAY if sect.is_day else LotSect.NIGHT)
    return build_chart_context(chart=chart, sect=sect, lots=lots, house_system=house_system)


def _lot_positions(chart) -> dict[str, float]:
    positions = {name: pos.longitude for name, pos in chart.positions.items()}
    positions["Asc"] = chart.houses.ascendant
    return positions


def _profection_dataframe(segments) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        note = segment.notes[0] if segment.notes else ""
        kind = "year" if note.startswith("age=") else "month"
        rows.append(
            {
                "kind": kind,
                "start": segment.start,
                "end": segment.end,
                "house": segment.house,
                "sign": segment.sign,
                "year_lord": segment.year_lord,
                "co_rulers": segment.co_rulers,
                "notes": list(segment.notes),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["start"] = pd.to_datetime(df["start"], utc=True)
        df["end"] = pd.to_datetime(df["end"], utc=True)
    return df


def _zr_dataframe(timeline) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for period in timeline.flatten():
        metadata = dict(period.metadata)
        rows.append(
            {
                "level": period.level,
                "start": period.start,
                "end": period.end,
                "sign": period.sign,
                "ruler": period.ruler,
                "lb": bool(period.lb),
                "lb_from": period.lb_from,
                "lb_to": period.lb_to,
                "peak": metadata.get("peak"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["start"] = pd.to_datetime(df["start"], utc=True)
        df["end"] = pd.to_datetime(df["end"], utc=True)
    return df


def _fortune_sign(ctx: ChartCtx) -> str | None:
    degree = ctx.lot("Fortune")
    if degree is None:
        return None
    return SIGN_ORDER[int(degree % 360.0 // 30.0)]


def _life_profile(include_fortune: bool) -> LifeProfile:
    base_profile: LifeProfile = load_traditional_profiles()["life"]["profile"]
    return LifeProfile(
        house_candidates=base_profile.house_candidates,
        include_fortune=include_fortune,
        dignity_weights=base_profile.dignity_weights,
        lifespan_years=base_profile.lifespan_years,
        bounds_scheme=base_profile.bounds_scheme,
        notes=base_profile.notes,
    )


def _export_dataframe(df: pd.DataFrame, name: str) -> None:
    if df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {name} CSV",
        data=csv_bytes,
        file_name=f"{name}.csv",
        mime="text/csv",
    )
    json_bytes = df.to_json(orient="records", date_format="iso").encode("utf-8")
    st.download_button(
        label=f"Download {name} JSON",
        data=json_bytes,
        file_name=f"{name}.json",
        mime="application/json",
    )


def _export_chart_png(chart: alt.Chart) -> None:
    try:
        import altair_saver  # type: ignore  # noqa: F401
        from altair_saver import save  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        st.info("Install altair-saver[kaleido] to enable PNG export.")
        return
    try:
        buffer = io.BytesIO()
        save(chart, fp=buffer, fmt="png")
        buffer.seek(0)
    except Exception as exc:  # pragma: no cover - optional dependency issues
        st.warning(f"PNG export failed: {exc}")
        return
    st.download_button(
        label="Download bands chart PNG",
        data=buffer.read(),
        file_name="traditional_bands.png",
        mime="image/png",
    )


def _timeline_chart(df: pd.DataFrame, overlays: pd.DataFrame | None = None) -> alt.Chart:
    base = alt.Chart(df).encode(x="start:T", x2="end:T", tooltip=["sign", "ruler", "level", "lb", "peak"])
    level1 = base.transform_filter(alt.datum.level == 1).mark_bar(size=18).encode(y=alt.value(0), color=alt.value("#1f77b4"))
    level2 = base.transform_filter(alt.datum.level == 2).mark_bar(size=12, opacity=0.6).encode(y=alt.value(22), color=alt.value("#ff7f0e"))
    chart = alt.layer(level1, level2).properties(height=120, width=800)
    if overlays is not None and not overlays.empty:
        overlay = (
            alt.Chart(overlays)
            .mark_tick(color="red", thickness=2, size=40)
            .encode(x="moment:T", tooltip=["label", "kind"])
        )
        chart = alt.layer(chart, overlay)
    return chart


def render() -> None:
    st.set_page_config(page_title="Traditional Lab", layout="wide")
    st.title("Traditional Timing Lab")

    with st.sidebar:
        st.header("Natal Configuration")
        birth_iso = st.text_input("Birth moment (ISO)", "1990-01-01T12:00:00+00:00")
        location_picker(
            "Birth location",
            default_query="New York, United States",
            state_prefix="traditional_lab_location",
            help="Atlas lookup pre-populates coordinates and shows timezone daylight status.",
        )
        lat_default = float(st.session_state.get("traditional_lab_location_lat", 40.7128))
        lon_default = float(st.session_state.get("traditional_lab_location_lon", -74.0060))
        latitude = st.number_input("Latitude", value=lat_default, format="%.4f")
        longitude = st.number_input("Longitude", value=lon_default, format="%.4f")
        st.session_state["traditional_lab_location_lat"] = float(latitude)
        st.session_state["traditional_lab_location_lon"] = float(longitude)
        house_system = st.selectbox("House system", options=["whole_sign", "placidus", "koch"], index=0)
        range_start_iso = st.text_input("Timeline start", "2023-01-01T00:00:00+00:00")
        range_end_iso = st.text_input("Timeline end", "2025-01-01T00:00:00+00:00")
        include_fortune = st.checkbox("Include Lot of Fortune for Hyleg", value=False)
        run_button = st.button("Generate timelines")

    if not run_button:
        st.info("Provide chart details and click 'Generate timelines'.")
        return

    try:
        birth_moment = _parse_iso(birth_iso)
        start = _parse_iso(range_start_iso)
        end = _parse_iso(range_end_iso)
        if end <= start:
            raise ValueError("Timeline end must be after start.")
        ctx = _build_ctx(birth_moment, latitude, longitude, house_system)
        interval = Interval(start=start.astimezone(UTC), end=end.astimezone(UTC))
        prof_segments = profection_year_segments(ctx, interval)
        timeline = zr_periods(
            lot_sign=_fortune_sign(ctx) or SIGN_ORDER[int(ctx.natal.houses.ascendant % 360.0 // 30.0)],
            start=start.astimezone(UTC),
            end=end.astimezone(UTC),
            levels=2,
        )
        timeline = apply_loosing_of_bond(timeline)
        fortune_sign = _fortune_sign(ctx)
        if fortune_sign:
            flag_peaks_fortune(timeline, fortune_sign)
        life_profile = _life_profile(include_fortune)
        hyleg = find_hyleg(ctx, life_profile)
        alcocoden = find_alcocoden(ctx, hyleg, life_profile)
    except Exception as exc:  # pragma: no cover - user interaction path
        st.error(f"Unable to generate timelines: {exc}")
        return

    prof_df = _profection_dataframe(prof_segments)
    zr_df = _zr_dataframe(timeline)

    tab_profections, tab_zr, tab_life, tab_overlays = st.tabs(
        ["Profections", "Zodiacal Releasing", "Sect/Hyleg", "Overlays & Export"]
    )

    with tab_profections:
        st.subheader("Annual & Monthly Profections")
        kind_filter = st.multiselect("Filter kinds", options=sorted(prof_df["kind"].unique()), default=list(prof_df["kind"].unique()))
        filtered = prof_df[prof_df["kind"].isin(kind_filter)] if kind_filter else prof_df
        st.dataframe(filtered)
        _export_dataframe(filtered, "profections")

    with tab_zr:
        st.subheader("Zodiacal Releasing Levels 1-2")
        sign_filter = st.multiselect("Signs", options=sorted(zr_df["sign"].unique()), default=list(zr_df["sign"].unique()))
        lb_only = st.checkbox("Loosing of the Bond only", value=False)
        peaks_only = st.checkbox("Peaks only", value=False)
        filtered = zr_df
        if sign_filter:
            filtered = filtered[filtered["sign"].isin(sign_filter)]
        if lb_only:
            filtered = filtered[filtered["lb"]]
        if peaks_only:
            filtered = filtered[filtered["peak"].notna()]
        st.dataframe(filtered)
        _export_dataframe(filtered, "zr_periods")

    with tab_life:
        st.subheader("Sect, Hyleg, Alcocoden")
        st.markdown(
            f"**Sect:** {'Day' if ctx.sect.is_day else 'Night'} — Luminary: {ctx.sect.luminary_of_sect} — Benefic of sect: {ctx.sect.benefic_of_sect}"
        )
        st.json(
            {
                "hyleg": {
                    "body": hyleg.body,
                    "degree": round(hyleg.degree, 2),
                    "sign": hyleg.sign,
                    "house": hyleg.house,
                    "score": round(hyleg.score, 2),
                    "notes": list(hyleg.notes),
                    "trace": list(hyleg.trace),
                },
                "alcocoden": {
                    "body": alcocoden.body,
                    "method": alcocoden.method,
                    "indicative_years": (
                        {
                            "minor": alcocoden.indicative_years.minor_years,
                            "mean": alcocoden.indicative_years.mean_years,
                            "major": alcocoden.indicative_years.major_years,
                        }
                        if alcocoden.indicative_years
                        else None
                    ),
                    "confidence": alcocoden.confidence,
                    "notes": list(alcocoden.notes),
                    "trace": list(alcocoden.trace),
                },
            }
        )

    with tab_overlays:
        st.subheader("Timeline Bands & Overlays")
        uploaded = st.file_uploader("Upload overlay CSV (columns: moment,label,kind)")
        overlay_df: pd.DataFrame | None = None
        if uploaded:
            try:
                overlay_df = pd.read_csv(uploaded)
                overlay_df["moment"] = pd.to_datetime(overlay_df["moment"], utc=True)
            except Exception as exc:  # pragma: no cover - user upload path
                st.warning(f"Could not parse overlay CSV: {exc}")
                overlay_df = None
        chart = _timeline_chart(zr_df, overlay_df)
        st.altair_chart(chart, use_container_width=True)
        _export_chart_png(chart)
        st.markdown("### Raw payload")
        st.code(json.dumps(timeline.to_table(), indent=2), language="json")


__all__ = ["render"]
