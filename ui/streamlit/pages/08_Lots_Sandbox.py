from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.streamlit.api import APIClient

st.set_page_config(page_title="Arabic Lots Sandbox", page_icon="🪄", layout="wide")
st.title("Arabic Lots — Viewer & Formula Sandbox 🪄")
api = APIClient()

CUSTOM_LOTS_KEY = "lots_sandbox_custom_lots"
RESULTS_STATE_KEY = "lots_sandbox_results"
CATALOG_MESSAGE_KEY = "lots_sandbox_catalog_msg"

# Built-in fallback metadata used when the backend catalog is unavailable so that
# dependency hints and the default selection remain meaningful.
FALLBACK_LOTS = {
    "Fortune": {
        "name": "Fortune",
        "day": "Asc + Moon - Sun",
        "night": "Asc + Sun - Moon",
        "description": "Part of Fortune (Tyche)",
    },
    "Spirit": {
        "name": "Spirit",
        "day": "Asc + Sun - Moon",
        "night": "Asc + Moon - Sun",
        "description": "Part of Spirit (Daimon)",
    },
}


def _ensure_custom_state() -> list[dict[str, Any]]:
    if CUSTOM_LOTS_KEY not in st.session_state:
        st.session_state[CUSTOM_LOTS_KEY] = [
            {
                "name": "LotOfTest",
                "day": "Asc + 15 - Sun",
                "night": "Asc + 15 - Sun",
                "description": "Example",
                "register": False,
            }
        ]
    return st.session_state[CUSTOM_LOTS_KEY]


def _normalize_longitude(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) % 360.0
    except (TypeError, ValueError):
        return None


def _extract_symbols(expr: str) -> set[str]:
    symbols: set[str] = set()
    for raw in expr.replace("+", " ").replace("-", " ").split():
        token = raw.strip()
        if not token:
            continue
        try:
            float(token)
        except ValueError:
            if token.replace("_", "").isalnum():
                symbols.add(token)
    return symbols


def _sanitize_custom_lots(
    custom_lots: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    valid: list[dict[str, Any]] = []
    issues: list[str] = []
    for idx, lot in enumerate(custom_lots):
        name = str(lot.get("name", "")).strip()
        day_expr = str(lot.get("day", "")).strip()
        night_expr_raw = lot.get("night", "")
        night_expr = str(night_expr_raw if night_expr_raw not in (None, "") else day_expr).strip()
        description = str(lot.get("description", "")).strip()
        register = bool(lot.get("register", False))

        if not name or not day_expr:
            issues.append(name or f"Custom {idx + 1}")
            continue

        valid.append(
            {
                "name": name,
                "day": day_expr,
                "night": night_expr,
                "description": description,
                "register": register,
            }
        )

    return valid, issues


def _coerce_lot_values(response: dict[str, Any]) -> dict[str, Any]:
    """Normalize arbitrary API payloads into a name→longitude mapping."""

    def from_sequence(rows: Sequence[Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for entry in rows:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name") or entry.get("lot") or entry.get("id")
            if not name:
                continue
            value = (
                entry.get("longitude")
                if "longitude" in entry
                else entry.get("value")
            )
            normalized[str(name)] = value
        return normalized

    candidate: Any = (
        response.get("lots")
        or response.get("positions")
        or response.get("results")
        or response
    )
    if isinstance(candidate, dict):
        return candidate
    if isinstance(candidate, (list, tuple)):
        return from_sequence(candidate)
    return {}


def _collect_required_symbols(
    lot_names: Iterable[str],
    sect: str,
    catalog_map: dict[str, dict[str, Any]],
) -> set[str]:
    expr_field = "day" if sect == "day" else "night"
    required: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            return
        visiting.add(name)
        lot = catalog_map.get(name)
        if not lot:
            return
        expr = lot.get(expr_field, "")
        for symbol in _extract_symbols(expr):
            if symbol in catalog_map:
                visit(symbol)
            else:
                required.add(symbol)

    for lot_name in lot_names:
        visit(lot_name)

    return required


def _render_results(result_state: dict[str, Any]) -> None:
    values: dict[str, float | None] = result_state.get("values", {})
    if not values:
        st.info(
            "No output — check that required symbols exist in Positions JSON (e.g., Asc, Sun, Moon)."
        )
        return

    df = pd.DataFrame(
        {
            "lot": list(values.keys()),
            "longitude": [values.get(k) for k in values.keys()],
        }
    )
    df = df.dropna(subset=["longitude"]).sort_values("lot").reset_index(drop=True)

    st.subheader("Results")
    computed_at: str | None = result_state.get("computed_at")
    if computed_at:
        st.caption(f"Computed at {computed_at}")

    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Polar plot", expanded=True):
        theta = df["longitude"].to_numpy()
        r = np.ones_like(theta)
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                theta=theta,
                r=r,
                mode="markers+text",
                text=df["lot"],
                textposition="top center",
            )
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=False)),
            showlegend=False,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    json_bytes = json.dumps(values, indent=2).encode("utf-8")
    with c1:
        st.download_button(
            "Download CSV",
            csv_bytes,
            file_name="lots.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Download JSON",
            json_bytes,
            file_name="lots.json",
            mime="application/json",
        )



# ---------------------------------------------------------------------------
# Load catalog
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def _load_catalog() -> list[dict[str, Any]]:
    try:
        data = api.lots_catalog()
        return data.get("lots", [])
    except Exception as e:
        st.error(f"Failed to load catalog: {e}")
        return []

custom_state = _ensure_custom_state()
catalog = _load_catalog()
catalog_map: dict[str, dict[str, Any]] = {item["name"]: item for item in catalog}
for name, meta in FALLBACK_LOTS.items():
    catalog_map.setdefault(name, meta)

sanitized_custom, custom_issues = _sanitize_custom_lots(custom_state)
effective_catalog_map = dict(catalog_map)
for lot in sanitized_custom:
    effective_catalog_map[lot["name"]] = lot

if msg := st.session_state.pop(CATALOG_MESSAGE_KEY, None):
    st.success(msg)

with st.sidebar:
    st.header("Catalog")
    st.caption("Built-in & registered Lots")
    sidebar_table: list[dict[str, Any]] = catalog if catalog else list(FALLBACK_LOTS.values())
    if sidebar_table:
        st.dataframe(
            pd.DataFrame(sidebar_table),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No catalog loaded.")

if custom_issues:
    st.warning(
        "Skipped incomplete custom lot definitions: "
        + ", ".join(custom_issues)
    )


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
DEFAULT_POS = {
    "Asc": 100.0,
    "Sun": 10.0,
    "Moon": 70.0,
    "Mercury": 15.0,
    "Venus": 20.0,
    "Jupiter": 200.0,
}

st.subheader("Positions & Sect")
col1, col2 = st.columns([3, 1])
with col1:
    txt = st.text_area(
        "Positions JSON (symbol → longitude°)",
        value=json.dumps(DEFAULT_POS, indent=2),
        height=180,
    )
    positions_error = False
    try:
        positions = {
            str(k): float(v)
            for k, v in (json.loads(txt) if txt.strip() else {}).items()
        }
    except Exception as e:
        st.error(f"Invalid JSON: {e}")
        positions = {}
        positions_error = True
with col2:
    sect = st.radio("Sect", ["day", "night"], index=0)

lot_options = sorted(effective_catalog_map.keys()) or ["Fortune", "Spirit"]
default_selection = [name for name in ("Fortune", "Spirit") if name in lot_options]
if not default_selection and lot_options:
    default_selection = lot_options[: min(2, len(lot_options))]
lots_selected = st.multiselect(
    "Lots to compute",
    options=lot_options,
    default=default_selection,
)

required_symbols: set[str] = set()
if lots_selected:
    required_symbols = _collect_required_symbols(
        lots_selected, sect, effective_catalog_map
    )
missing_symbols = sorted(sym for sym in required_symbols if sym not in positions)
if missing_symbols:
    st.warning(
        "Missing positions for: " + ", ".join(missing_symbols)
    )

positions_ready = bool(positions) and not positions_error and not missing_symbols
lots_ready = bool(lots_selected)


# ---------------------------------------------------------------------------
# Custom lots editor
# ---------------------------------------------------------------------------
st.subheader("Custom Lots (inline)")
with st.expander("Add/Edit Custom Lots", expanded=False):
    edited: list[dict[str, Any]] = []
    removal_requested: set[int] = set()
    for i, row in enumerate(custom_state):
        st.markdown(f"**Custom {i + 1}**")
        c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 1, 1])
        name = c1.text_input("Name", value=row.get("name", ""), key=f"name_{i}")
        day = c2.text_input("Day expr", value=row.get("day", ""), key=f"day_{i}")
        night = c3.text_input("Night expr", value=row.get("night", ""), key=f"night_{i}")
        register = c4.checkbox(
            "Register", value=bool(row.get("register", False)), key=f"reg_{i}"
        )
        desc = st.text_input(
            "Description", value=row.get("description", ""), key=f"desc_{i}"
        )
        remove = c5.button("Remove", key=f"remove_{i}")
        if remove:
            removal_requested.add(i)
        edited.append(
            {
                "name": name,
                "day": day,
                "night": night,
                "description": desc,
                "register": register,
            }
        )
        st.divider()
    if removal_requested:
        st.session_state[CUSTOM_LOTS_KEY] = [
            entry for idx, entry in enumerate(edited) if idx not in removal_requested
        ]
        st.experimental_rerun()
    else:
        st.session_state[CUSTOM_LOTS_KEY] = edited
    if st.button("➕ Add custom lot", key="add_custom_lot"):
        st.session_state[CUSTOM_LOTS_KEY].append(
            {"name": "", "day": "", "night": "", "description": "", "register": False}
        )
        st.experimental_rerun()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
colA, colB = st.columns([1, 3])
with colA:
    go_compute = st.button(
        "Compute Lots",
        type="primary",
        disabled=not (positions_ready and lots_ready),
    )
with colB:
    st.caption("Tip: Asc, Sun, Moon are commonly needed for Fortune/Spirit")

result_state: dict[str, Any] | None = st.session_state.get(RESULTS_STATE_KEY)

if go_compute:
    if not positions_ready:
        st.error("Positions JSON must include at least one numeric entry before computing.")
    elif not lots_ready:
        st.error("Select at least one lot to compute.")
    else:
        sanitized_custom, custom_issues = _sanitize_custom_lots(
            st.session_state[CUSTOM_LOTS_KEY]
        )
        payload = {
            "positions": positions,
            "lots": sorted(lots_selected),
            "sect": sect,
            "custom_lots": sanitized_custom or None,
        }
        if custom_issues:
            st.warning(
                "Skipped incomplete custom lot definitions: "
                + ", ".join(custom_issues)
            )
        try:
            resp = api.lots_compute(payload)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

        raw_vals = _coerce_lot_values(resp)
        normalized = {
            name: _normalize_longitude(value) for name, value in raw_vals.items()
        }
        result_state = {
            "values": normalized,
            "raw_response": resp,
            "payload": payload,
            "computed_at": datetime.now(UTC).isoformat(),
        }
        st.session_state[RESULTS_STATE_KEY] = result_state

        if any(cl.get("register") for cl in (payload.get("custom_lots") or [])):
            _load_catalog.clear()
            st.session_state[CATALOG_MESSAGE_KEY] = (
                "Custom lot(s) registered — catalog refreshed."
            )
            st.experimental_rerun()

if result_state:
    _render_results(result_state)
