"""Streamlit view helpers for the Relationship Lab."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
import streamlit as st

from .constants import ASPECTS, FAMILY_LABELS


def filter_hits(hits: Iterable[Mapping[str, Any]], min_severity: float) -> list[Mapping[str, Any]]:
    return [hit for hit in hits if float(hit.get("severity", 0.0)) >= min_severity]


def _aspect_symbol(aspect: str) -> str:
    info = ASPECTS.get(aspect)
    return info.symbol if info else aspect[:2].upper()


def render_hits_table(hits: Iterable[Mapping[str, Any]], *, min_severity: float) -> pd.DataFrame | None:
    filtered = filter_hits(hits, min_severity)
    if not filtered:
        st.info("No aspect hits under the current filters.")
        return None
    frame = pd.DataFrame(filtered)
    frame = frame.rename(columns={"a": "Chart A", "b": "Chart B"})
    frame["symbol"] = frame["aspect"].map(lambda key: _aspect_symbol(str(key)))
    frame = frame[["Chart A", "Chart B", "aspect", "symbol", "delta", "orb", "severity"]]
    frame = frame.sort_values(by="severity", ascending=False)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    return frame


def render_grid(grid: Mapping[str, Mapping[str, str]]) -> pd.DataFrame | None:
    if not grid:
        st.info("Aspect grid unavailable for the current result set.")
        return None
    data: dict[str, dict[str, str]] = {}
    for a_body, row in grid.items():
        data[a_body] = {}
        for b_body, aspect in row.items():
            symbol = _aspect_symbol(str(aspect))
            data[a_body][b_body] = symbol
    frame = pd.DataFrame(data).fillna("").sort_index(axis=0).sort_index(axis=1)
    st.dataframe(frame, use_container_width=True)
    return frame


def _summarise_families(hits: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {key: 0.0 for key in FAMILY_LABELS}
    for hit in hits:
        aspect = str(hit.get("aspect"))
        severity = float(hit.get("severity", 0.0))
        family = ASPECTS.get(aspect).family if aspect in ASPECTS else "neutral"
        totals[family] = totals.get(family, 0.0) + severity
    return totals


def _summarise_bodies(hits: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    per_side = {"Chart A": {}, "Chart B": {}}
    for hit in hits:
        severity = float(hit.get("severity", 0.0))
        body_a = str(hit.get("a"))
        body_b = str(hit.get("b"))
        per_side["Chart A"][body_a] = per_side["Chart A"].get(body_a, 0.0) + severity
        per_side["Chart B"][body_b] = per_side["Chart B"].get(body_b, 0.0) + severity
    return per_side


def render_scores(hits: Iterable[Mapping[str, Any]], *, overall: float | None = None) -> dict[str, Any]:
    hit_list = list(hits)
    total = overall if overall is not None else sum(float(hit.get("severity", 0.0)) for hit in hit_list)
    families = _summarise_families(hit_list)
    bodies = _summarise_bodies(hit_list)

    st.metric("Overall score", f"{total:.2f}")

    fam_df = pd.DataFrame(
        {FAMILY_LABELS.get(key, key.title()): [value] for key, value in families.items() if value > 0.0}
    ).T
    if not fam_df.empty:
        st.bar_chart(fam_df.rename(columns={0: "Severity"}))

    body_tabs = st.tabs(list(bodies.keys()))
    for tab, (label, values) in zip(body_tabs, bodies.items(), strict=False):
        with tab:
            if values:
                df = pd.DataFrame(sorted(values.items(), key=lambda kv: kv[1], reverse=True), columns=[label, "Severity"])
                st.bar_chart(df.set_index(label))
            else:
                st.info("No bodies met the severity threshold.")

    return {"total": total, "families": families, "bodies": bodies}



def render_overlay_table(overlay: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame | None:
    if not overlay:
        st.info("Overlay data unavailable for the current result set.")
        return None
    rows: list[dict[str, Any]] = []
    for body, data in overlay.items():
        row = {"Body": body}
        if "A" in data:
            row["Chart A"] = data["A"]
        if "B" in data:
            row["Chart B"] = data["B"]
        if "delta" in data:
            row["Delta"] = data["delta"]
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(by="Body")
    st.dataframe(frame, use_container_width=True, hide_index=True)
    return frame


def build_summary_markdown(
    title: str,
    hits: Iterable[Mapping[str, Any]],
    score_summary: Mapping[str, Any],
    *,
    top_n: int = 5,
) -> str:
    hit_list = sorted(hits, key=lambda item: float(item.get("severity", 0.0)), reverse=True)
    lines = [f"## {title}", "", f"**Overall score:** {score_summary.get('total', 0.0):.2f}"]
    families = score_summary.get("families", {})
    if families:
        lines.append("\n### Aspect families")
        for key, label in FAMILY_LABELS.items():
            value = float(families.get(key, 0.0))
            if value > 0.0:
                lines.append(f"- {label}: {value:.2f}")
    if hit_list:
        lines.append("\n### Top hits")
        for hit in hit_list[:top_n]:
            aspect = str(hit.get("aspect"))
            symbol = _aspect_symbol(aspect)
            a = hit.get("a")
            b = hit.get("b")
            sev = float(hit.get("severity", 0.0))
            orb = float(hit.get("orb", 0.0))
            lines.append(f"- {a} {symbol} {b} — severity {sev:.2f}, orb {orb:.2f}°")
    return "\n".join(lines)


def render_markdown_copy(markdown: str) -> None:
    text = markdown
    html = f"""
    <div style='position: relative;'>
        <textarea id='rel-copy' style='width:100%; min-height: 220px;'>{text}</textarea>
        <button style='position:absolute; top:6px; right:6px;' onclick="navigator.clipboard.writeText(document.getElementById('rel-copy').value);">Copy</button>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
