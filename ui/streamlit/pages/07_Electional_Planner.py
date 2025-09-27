from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

if __package__ is None or __package__ == "":  # pragma: no cover - runtime import guard
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Electional Planner", page_icon="🗳️", layout="wide")
st.title("Electional Planner 🗳️")
api = APIClient()

DEFAULT_ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile", "quincunx"]
DEFAULT_BODIES = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ics_export(
    windows: Iterable[Dict[str, Any]],
    name: str = "Electional Windows",
    uid_prefix: str = "astroengine",
) -> bytes:
    """Produce a minimal ICS calendar string (UTC).

    Each window becomes a VEVENT with DTSTART/DTEND in UTC and a SUMMARY
    that includes the overall score.
    """

    def iso(dt_str: str) -> str:
        """Normalize ISO 8601 strings to the UTC basic format required by ICS."""

        if not dt_str:
            raise ValueError("Missing datetime string for ICS export")

        parsed = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//astroengine//electional//EN",
        f"X-WR-CALNAME:{name}",
    ]
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for i, window in enumerate(windows, 1):
        start = window.get("start")
        end = window.get("end")
        if not start or not end:
            # Skip malformed windows rather than generating an invalid ICS file.
            continue
        summary = f"Electional window (score {window.get('score', 0):.3f})"
        desc = json.dumps(
            {k: window.get(k) for k in ("avg_score", "samples", "breakdown")},
            ensure_ascii=False,
        )
        uid = f"{uid_prefix}-{i}@astroengine"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{iso(start)}",
            f"DTEND:{iso(end)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def _datetime_input(label: str, value: datetime, key: str) -> datetime:
    """Compose a timezone-aware datetime from date+time inputs."""

    base = value.astimezone(timezone.utc)
    date_val = st.date_input(f"{label} date", base.date(), key=f"{key}_date")
    time_val = st.time_input(
        f"{label} time",
        base.timetz().replace(tzinfo=None),
        key=f"{key}_time",
    )
    # ``datetime.combine`` preserves tzinfo; ensure UTC alignment for downstream payloads.
    return datetime.combine(date_val, time_val, tzinfo=timezone.utc)


def _normalize_window_records(raw_windows: Iterable[MutableMapping[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten nested window payloads and coerce datetimes to UTC ISO strings."""

    normalized: List[Dict[str, Any]] = []
    for window in raw_windows or []:
        # Create a shallow copy to avoid mutating the original payload.
        record: Dict[str, Any] = dict(window)

        nested = record.get("window")
        if isinstance(nested, MutableMapping):
            record.setdefault("start", nested.get("start"))
            record.setdefault("end", nested.get("end"))

        for key in ("start", "end"):
            value = record.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                record[key] = value.astimezone(timezone.utc).isoformat()
                continue
            if isinstance(value, str):
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    # Leave the original value intact so the UI can flag issues later.
                    continue
                record[key] = parsed.astimezone(timezone.utc).isoformat()

        normalized.append(record)

    return normalized


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Scan Window")
    now = datetime.now(timezone.utc)
    start = _datetime_input("Start (UTC)", value=now, key="start")
    end = _datetime_input("End (UTC)", value=now + timedelta(days=30), key="end")
    window_minutes = st.number_input("Candidate window size (minutes)", 15, 60 * 24 * 14, 24 * 60, 15)
    step_minutes = st.slider("Sampling step (minutes)", 5, 360, 60, 5)
    top_k = st.slider("Top K windows", 1, 10, 3)

    st.divider()
    st.header("Filters")
    avoid_voc = st.toggle("Avoid VoC Moon", value=True)
    weekdays = st.multiselect("Allowed weekdays (0=Mon)", list(range(7)), default=[0, 1, 2, 3, 4])
    timeranges_txt = st.text_input("Allowed UTC ranges (HH:MM-HH:MM comma-sep)", value="08:00-22:00")
    allowed_ranges: List[Tuple[str, str]] = []
    for chunk in [x.strip() for x in timeranges_txt.split(",") if x.strip()]:
        try:
            a, b = chunk.split("-")
            allowed_ranges.append((a.strip(), b.strip()))
        except ValueError:
            st.warning(f"Bad time range: {chunk}")

st.subheader("Rules")

# Required aspects builder
with st.expander("Required Aspects", expanded=True):
    if "_req_rows" not in st.session_state:
        st.session_state._req_rows = [
            {"a": "Mars", "b": "Venus", "aspects": ["sextile"], "weight": 1.0, "orb_override": None}
        ]
    cols = st.columns([1, 1, 2, 1, 1])
    a_name = cols[0].selectbox("A body", DEFAULT_BODIES, index=DEFAULT_BODIES.index("Sun"))
    b_name = cols[1].selectbox("B body", DEFAULT_BODIES, index=DEFAULT_BODIES.index("Jupiter"))
    aspects = cols[2].multiselect("Aspects", DEFAULT_ASPECTS, default=["trine"])
    weight = float(cols[3].number_input("Weight", 0.0, 5.0, 0.8, 0.1))
    orb_override = cols[4].number_input("Orb override (°)", 0.0, 15.0, 0.0, 0.1)
    add_req = st.button("➕ Add requirement")
    clear_req = st.button("🧹 Clear requirements")
    if add_req and aspects:
        st.session_state._req_rows.append(
            {
                "a": a_name,
                "b": b_name,
                "aspects": aspects,
                "weight": weight,
                "orb_override": (None if orb_override == 0.0 else float(orb_override)),
            }
        )
        st.experimental_rerun()
    if add_req and not aspects:
        st.warning("Select at least one aspect before adding a requirement.")
    if clear_req:
        st.session_state._req_rows = []
        st.experimental_rerun()
    req_df = pd.DataFrame(st.session_state._req_rows)
    st.dataframe(
        req_df if not req_df.empty else pd.DataFrame([], columns=["a", "b", "aspects", "weight", "orb_override"])
    )

# Forbidden aspects builder
with st.expander("Forbidden Aspects", expanded=True):
    if "_forb_rows" not in st.session_state:
        st.session_state._forb_rows = [
            {"a": "Moon", "b": "Saturn", "aspects": ["opposition"], "penalty": 1.0, "orb_override": None}
        ]
    cols = st.columns([1, 1, 2, 1, 1])
    a2 = cols[0].selectbox("A body ", DEFAULT_BODIES, index=DEFAULT_BODIES.index("Moon"), key="fa")
    b2 = cols[1].selectbox("B body ", DEFAULT_BODIES, index=DEFAULT_BODIES.index("Saturn"), key="fb")
    aspects2 = cols[2].multiselect("Aspects ", DEFAULT_ASPECTS, default=["square"], key="faspects")
    penalty = float(cols[3].number_input("Penalty", 0.0, 5.0, 1.0, 0.1, key="fpen"))
    orb_override2 = cols[4].number_input("Orb override (°) ", 0.0, 15.0, 0.0, 0.1, key="forb_orb")
    add_forb = st.button("➕ Add prohibition")
    clear_forb = st.button("🧹 Clear prohibitions")
    if add_forb and aspects2:
        st.session_state._forb_rows.append(
            {
                "a": a2,
                "b": b2,
                "aspects": aspects2,
                "penalty": penalty,
                "orb_override": (None if orb_override2 == 0.0 else float(orb_override2)),
            }
        )
        st.experimental_rerun()
    if add_forb and not aspects2:
        st.warning("Select at least one aspect before adding a prohibition.")
    if clear_forb:
        st.session_state._forb_rows = []
        st.experimental_rerun()
    forb_df = pd.DataFrame(st.session_state._forb_rows)
    st.dataframe(
        forb_df if not forb_df.empty else pd.DataFrame([], columns=["a", "b", "aspects", "penalty", "orb_override"])
    )

# Orb policy inline
with st.expander("Orb Policy Overrides (inline)", expanded=False):
    c = st.columns(6)
    conj = c[0].number_input("conj", 0.1, 12.0, 8.0, 0.1)
    opp = c[1].number_input("opp", 0.1, 12.0, 7.0, 0.1)
    sq = c[2].number_input("sq", 0.1, 12.0, 6.0, 0.1)
    tri = c[3].number_input("tri", 0.1, 12.0, 6.0, 0.1)
    sex = c[4].number_input("sex", 0.1, 12.0, 3.0, 0.1)
    qcx = c[5].number_input("qcx", 0.1, 12.0, 3.0, 0.1)
    policy = {
        "per_aspect": {
            "conjunction": conj,
            "opposition": opp,
            "square": sq,
            "trine": tri,
            "sextile": sex,
            "quincunx": qcx,
        }
    }

# Preset
with st.expander("Preset: Product Launch (harmonious + no Moon–Saturn hits)", expanded=False):
    if st.button("Load preset"):
        st.session_state._req_rows = [
            {
                "a": "Sun",
                "b": "Jupiter",
                "aspects": ["trine", "sextile"],
                "weight": 0.8,
                "orb_override": None,
            },
            {"a": "Mars", "b": "Venus", "aspects": ["sextile"], "weight": 1.0, "orb_override": None},
        ]
        st.session_state._forb_rows = [
            {
                "a": "Moon",
                "b": "Saturn",
                "aspects": ["square", "opposition"],
                "penalty": 1.0,
                "orb_override": None,
            }
        ]
        st.experimental_rerun()

# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------
if st.button("🔎 Search Best Windows", type="primary"):
    if end <= start:
        st.error("The scan end must be after the start.")
        st.stop()
    req_rules = [r for r in st.session_state.get("_req_rows", []) if r.get("aspects")]
    forb_rules = [r for r in st.session_state.get("_forb_rows", []) if r.get("aspects")]

    payload = {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "window_minutes": int(window_minutes),
        "step_minutes": int(step_minutes),
        "top_k": int(top_k),
        "avoid_voc_moon": bool(avoid_voc),
        "allowed_weekdays": weekdays if weekdays else None,
        "allowed_utc_ranges": allowed_ranges if allowed_ranges else None,
        "orb_policy_inline": policy,
        "required_aspects": req_rules,
        "forbidden_aspects": forb_rules,
    }

    try:
        data = api.electional_search(payload)
    except Exception as exc:  # pragma: no cover - UI surface
        st.error(f"API error: {exc}")
        st.stop()

    windows = _normalize_window_records(data.get("windows", []))
    if not windows:
        st.info("No windows matched — try relaxing rules or enlarging the scan window.")
        st.stop()

    # Table
    df = pd.DataFrame(windows)
    if "score" in df.columns:
        df = df.sort_values(by="score", ascending=False, ignore_index=True)
    windows = df.to_dict(orient="records")
    df.insert(0, "rank", df.index + 1)
    df["window_label"] = df["rank"].apply(lambda idx: f"Window {idx}")
    st.subheader("Ranked Windows")
    table_cols = ["rank", "start", "end", "score", "avg_score", "samples"]
    available_cols = [col for col in table_cols if col in df.columns]
    st.dataframe(
        df[available_cols],
        use_container_width=True,
        hide_index=True,
    )

    # Timeline
    timeline_df = df[["window_label", "start", "end", "score"]].copy()
    timeline_df["start"] = pd.to_datetime(timeline_df["start"], utc=True, errors="coerce")
    timeline_df["end"] = pd.to_datetime(timeline_df["end"], utc=True, errors="coerce")
    invalid = timeline_df["start"].isna() | timeline_df["end"].isna()
    if invalid.any():
        st.warning("Some windows had invalid timestamps and were skipped in the timeline visualization.")
        timeline_df = timeline_df[~invalid]

    if not timeline_df.empty:
        try:
            fig = px.timeline(
                timeline_df,
                x_start="start",
                x_end="end",
                y="window_label",
                color="score",
            )
            fig.update_yaxes(title="Window", autorange="reversed")
            st.plotly_chart(fig, use_container_width=True, theme="streamlit")
        except Exception:  # pragma: no cover - visualization guard
            pass

    # Drilldown: top instants of first window
    with st.expander("Top instants", expanded=True):
        window_options = {
            f"#{row.rank}: {row.start} → {row.end}": idx for idx, row in df.iterrows()
        }
        selection = st.selectbox("Choose a window", list(window_options.keys()))
        selected_window = windows[window_options[selection]]
        top = selected_window.get("top_instants", [])
        if top:
            df_i = pd.DataFrame(top)
            st.dataframe(df_i, use_container_width=True, hide_index=True)
        else:
            st.caption("No instant breakdown available.")

    # Exports
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download CSV",
            df[available_cols].to_csv(index=False).encode("utf-8"),
            file_name="electional_windows.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Download JSON",
            json.dumps(windows, indent=2).encode("utf-8"),
            file_name="electional_windows.json",
            mime="application/json",
        )
    with c3:
        try:
            ics_bytes = _ics_export(windows, name="Electional Windows")
        except ValueError as err:
            st.warning(f"ICS export unavailable: {err}")
            ics_bytes = None

        if ics_bytes:
            st.download_button(
                "Download ICS",
                ics_bytes,
                file_name="electional_windows.ics",
                mime="text/calendar",
            )
