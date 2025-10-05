from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping

import pandas as pd
import streamlit as st
from streamlit import components

from . import sections
from .client import APIError, RelationshipClient
from .state import (
    DEFAULT_ASPECTS,
    DEFAULT_TEMPLATE_ID,
    ReportFilters,
    ReportState,
    get_state,
    load_project,
    reset_state,
    store_project,
    update_state,
)
from .templating import ReportContext, build_scores_table, render_markdown

FALLBACK_RULEPACKS = [
    {"id": "synastry-basic", "title": "Synastry Essentials", "version": "1.0"}
]
DEFAULT_REL_BASE = "http://localhost:8000"


def _read_sample(path: str) -> str:
    from importlib import resources

    return resources.files("ui.streamlit.report_builder.samples").joinpath(path).read_text(
        "utf-8"
    )


def _collect_tags(payload: Mapping[str, Any] | None) -> List[str]:
    tags: set[str] = set()
    if isinstance(payload, Mapping):
        findings = payload.get("findings")
        if isinstance(findings, Iterable):
            for item in findings:
                if not isinstance(item, Mapping):
                    continue
                for tag in item.get("tags", []) or []:
                    if isinstance(tag, str):
                        tags.add(tag)
    return sorted(tags)


def _finding_snippet(item: Mapping[str, Any]) -> str:
    snippet = item.get("snippet") if isinstance(item, Mapping) else None
    if isinstance(snippet, str) and snippet.strip():
        return snippet.strip()
    rendered = item.get("rendered_markdown") if isinstance(item, Mapping) else None
    if isinstance(rendered, str) and rendered.strip():
        return rendered.strip().splitlines()[0]
    return ""


def _inputs_summary(hits: Iterable[Mapping[str, Any]] | None) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    if hits:
        for hit in hits:
            if not isinstance(hit, Mapping):
                continue
            record = {
                "aspect": hit.get("aspect"),
                "score": hit.get("score"),
                "orb": hit.get("orb"),
            }
            bodies = hit.get("bodies")
            if isinstance(bodies, Mapping):
                record["body_a"] = bodies.get("a")
                record["body_b"] = bodies.get("b")
            records.append(record)
    return pd.DataFrame(records)


def _theme_styles(theme: str) -> str:
    theme = theme.lower()
    if theme == "dark":
        bg, fg, border = "#0f172a", "#e2e8f0", "#1f2937"
    elif theme == "light":
        bg, fg, border = "#f8fafc", "#0f172a", "#cbd5f5"
    else:
        bg, fg, border = "#f5f5f4", "#111827", "#d4d4d8"
    return f"""
    <style>
    .report-preview {{
        font-family: 'Fira Code', 'JetBrains Mono', 'SFMono-Regular', monospace;
        background-color: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 0.75rem;
        padding: 1.5rem;
        white-space: pre-wrap;
        word-wrap: break-word;
    }}
    .report-preview textarea {{
        font-family: inherit;
    }}
    </style>
    """


def _copy_to_clipboard_button(markdown: str) -> None:
    payload = json.dumps(markdown)
    components.v1.html(
        f"""
        <button id=\"copy-md\">Copy Markdown</button>
        <script>
        const btn = document.getElementById('copy-md');
        if (btn) {{
            btn.addEventListener('click', async () => {{
                try {{
                    await navigator.clipboard.writeText({payload});
                    btn.innerText = 'Copied!';
                    setTimeout(() => btn.innerText = 'Copy Markdown', 1500);
                }} catch (err) {{
                    console.error(err);
                    btn.innerText = 'Copy failed';
                }}
            }});
        }}
        </script>
        """,
        height=60,
    )


def _project_download(state: ReportState) -> tuple[str, str] | None:
    if not state.findings:
        return None
    payload = state.model_dump()
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    return "report_project.json", json.dumps(payload, indent=2, ensure_ascii=False)


def _build_filters(state: ReportState) -> ReportFilters:
    return ReportFilters.model_validate(state.filters.model_dump())


def _ensure_rulepack_selection(state: ReportState, rulepacks: List[Mapping[str, Any]]) -> str:
    current = state.rulepack_id or (rulepacks[0]["id"] if rulepacks else "")
    return current


def _render_markdown(state: ReportState, generated_at: datetime) -> str:
    findings_payload = state.findings or {}
    filters = _build_filters(state)
    filters_payload = filters.model_dump()
    filters_payload.pop("top_highlights", None)
    context = ReportContext(
        findings=list(findings_payload.get("findings", [])),
        rulepack=findings_payload.get("rulepack") or {"id": state.rulepack_id},
        filters={**findings_payload.get("filters", {}), **filters_payload},
        pair=state.pair.model_dump(),
        totals=findings_payload.get("totals") or {},
        generated_at=generated_at,
        top_highlights=state.filters.top_highlights,
        template_id=state.template_id or DEFAULT_TEMPLATE_ID,
    )
    return render_markdown(context)


def main() -> None:  # pragma: no cover - Streamlit entrypoint
    st.set_page_config(page_title="Relationship Report Builder", layout="wide")
    state = get_state(st.session_state)

    with st.sidebar:
        st.title("Report Builder")
        rel_base = st.text_input("Relationship API base", value=st.session_state.get("relationship_base", DEFAULT_REL_BASE))
        int_base = st.text_input("Interpret API base", value=st.session_state.get("interpret_base", rel_base))
        st.session_state["relationship_base"] = rel_base
        st.session_state["interpret_base"] = int_base
        theme = st.selectbox("Preview theme", options=["System", "Light", "Dark"], index=0)
        st.markdown(_theme_styles(theme), unsafe_allow_html=True)

        if st.button("Reset session"):
            state = reset_state(st.session_state)
            st.experimental_rerun()

        project_file = st.file_uploader("Import project", type=["json"], accept_multiple_files=False)
        if project_file is not None:
            try:
                payload = json.loads(project_file.getvalue().decode("utf-8"))
                state = load_project(st.session_state, payload)
                if state.markdown:
                    st.session_state["markdown_preview"] = state.markdown
                st.success("Project loaded")
            except Exception as exc:  # pragma: no cover - user input
                st.error(f"Failed to load project: {exc}")

        export = _project_download(state)
        if export:
            filename, data = export
            st.download_button(
                "Export project", data=data, file_name=filename, mime="application/json"
            )

    st.title("Relationship Report Builder")
    st.caption("Convert synastry, composite, or davison findings into polished Markdown.")

    tabs = st.tabs(["Compute Hits", "Use Existing Hits"])
    with tabs[0]:
        default_a = _read_sample("positions_A.json")
        default_b = _read_sample("positions_B.json")
        col_a, col_b = st.columns(2)
        text_a = col_a.text_area("ChartPositions A (JSON)", value=st.session_state.get("positionsA_text", default_a), height=220)
        text_b = col_b.text_area("ChartPositions B (JSON)", value=st.session_state.get("positionsB_text", default_b), height=220)
        aspects = st.multiselect(
            "Aspects",
            DEFAULT_ASPECTS,
            default=state.aspects or DEFAULT_ASPECTS,
        )
        if aspects != state.aspects:
            state = update_state(st.session_state, aspects=aspects)
        if st.button("Compute hits"):
            try:
                positions_a = json.loads(text_a)
                positions_b = json.loads(text_b)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON payload: {exc}")
            else:
                payload = {
                    "positionsA": {"__root__": positions_a},
                    "positionsB": {"__root__": positions_b},
                    "aspects": aspects or DEFAULT_ASPECTS,
                }
                client = RelationshipClient(rel_base, int_base)
                try:
                    response = client.synastry(payload)
                except APIError as exc:
                    st.error(str(exc))
                else:
                    hits = response.get("hits", [])
                    state = update_state(
                        st.session_state,
                        hits=hits,
                        inputs={"positionsA": positions_a, "positionsB": positions_b, "aspects": aspects},
                        findings=None,
                        markdown=None,
                    )
                    st.session_state["markdown_preview"] = ""
                    st.session_state["positionsA_text"] = text_a
                    st.session_state["positionsB_text"] = text_b
                    st.success(f"Captured {len(hits)} hits from synastry computation.")

    with tabs[1]:
        default_hits = _read_sample("hits_sample.json")
        hits_text = st.text_area("Paste hits JSON", value=st.session_state.get("hits_text", default_hits), height=280)
        upload = st.file_uploader("…or upload hits.json", type=["json"])
        if upload is not None:
            hits_text = upload.getvalue().decode("utf-8")
        if st.button("Use pasted hits"):
            try:
                hits_payload = json.loads(hits_text)
            except json.JSONDecodeError as exc:
                st.error(f"Invalid JSON payload: {exc}")
            else:
                hits = hits_payload.get("hits") if isinstance(hits_payload, Mapping) else None
                if not isinstance(hits, list):
                    st.error("Expected {\"hits\": [...]} in uploaded payload")
                else:
                    state = update_state(
                        st.session_state,
                        hits=hits,
                        inputs={"hits": hits},
                        findings=None,
                        markdown=None,
                    )
                    st.session_state["markdown_preview"] = ""
                    st.session_state["hits_text"] = hits_text
                    st.success(f"Loaded {len(hits)} hits from provided data.")

    hits_df = _inputs_summary(state.hits)
    if not hits_df.empty:
        with st.expander("Hits summary"):
            st.dataframe(hits_df, use_container_width=True)

    st.subheader("Interpretation settings")
    try:
        client = RelationshipClient(rel_base, int_base)
        rulepacks = client.list_rulepacks()
        if not rulepacks:
            rulepacks = FALLBACK_RULEPACKS
    except APIError as exc:
        st.warning(f"Failed to fetch rulepacks: {exc}")
        rulepacks = FALLBACK_RULEPACKS

    rulepack_ids = [pack["id"] for pack in rulepacks]
    current_rulepack = _ensure_rulepack_selection(state, rulepacks) if rulepacks else ""
    default_index = rulepack_ids.index(current_rulepack) if current_rulepack in rulepack_ids else 0
    selected_rulepack = st.selectbox(
        "Rulepack",
        options=rulepack_ids,
        format_func=lambda value: next((f"{item['title']} ({item['version']})" for item in rulepacks if item["id"] == value), value),
        index=default_index if rulepack_ids else 0,
    )

    pair_col1, pair_col2 = st.columns(2)
    name_a = pair_col1.text_input("Name A", value=state.pair.nameA)
    name_b = pair_col2.text_input("Name B", value=state.pair.nameB)

    filters_dict = state.filters.model_dump()
    profile_options = sorted({"balanced", "chemistry_plus", filters_dict.get("profile", "balanced")})
    current_profile = filters_dict.get("profile", "balanced")
    filters_dict["profile"] = st.selectbox(
        "Profile",
        options=profile_options,
        index=profile_options.index(current_profile),
    )
    filters_dict["min_score"] = st.slider("Minimum score", 0.0, 1.0, float(filters_dict.get("min_score", 0.3)), 0.05)
    filters_dict["top_k"] = st.number_input("Top-k findings", min_value=10, max_value=500, value=int(filters_dict.get("top_k", 50)), step=5)
    filters_dict["top_highlights"] = st.slider("Highlights displayed", 1, 20, int(filters_dict.get("top_highlights", 7)))

    available_tags = sorted(set(_collect_tags(state.findings)) | set(filters_dict.get("include_tags", [])) | set(filters_dict.get("exclude_tags", [])))
    include_selection = st.multiselect("Include tags", options=available_tags, default=filters_dict.get("include_tags", []))
    exclude_selection = st.multiselect("Exclude tags", options=available_tags, default=filters_dict.get("exclude_tags", []))
    filters_dict["include_tags"] = include_selection
    filters_dict["exclude_tags"] = exclude_selection

    pending_updates: Dict[str, Any] = {}
    if name_a != state.pair.nameA or name_b != state.pair.nameB:
        pending_updates["pair"] = {"nameA": name_a, "nameB": name_b}
    if selected_rulepack != state.rulepack_id:
        pending_updates["rulepack_id"] = selected_rulepack
    if filters_dict != state.filters.model_dump():
        pending_updates["filters"] = filters_dict
    if pending_updates:
        state = update_state(st.session_state, **pending_updates)

    st.markdown("---")
    st.subheader("Generate report")
    scope = st.selectbox("Interpretation scope", options=["synastry", "composite", "davison"], index=["synastry", "composite", "davison"].index(state.scope if state.scope in {"synastry", "composite", "davison"} else "synastry"))
    if scope != state.scope:
        state = update_state(st.session_state, scope=scope)

    if st.button("Run interpretation", type="primary"):
        if not state.hits and scope == "synastry":
            st.error("Provide hits before running the interpretation.")
        else:
            payload = {
                "rulepack_id": selected_rulepack,
                "scope": scope,
                "filters": {
                    "profile": filters_dict["profile"],
                    "min_score": float(filters_dict["min_score"]),
                    "top_k": int(filters_dict["top_k"]),
                    "include_tags": include_selection or None,
                    "exclude_tags": exclude_selection or None,
                },
                "pair": {"nameA": name_a, "nameB": name_b},
            }
            if scope == "synastry":
                payload["synastry"] = {"hits": state.hits or []}
            elif scope == "composite":
                payload["composite"] = state.inputs or {}
            elif scope == "davison":
                payload["davison"] = state.inputs or {}

            client = RelationshipClient(rel_base, int_base)
            try:
                result = client.interpret(payload)
            except APIError as exc:
                st.error(str(exc))
            else:
                generated_at = datetime.now(timezone.utc)
                state = update_state(st.session_state, findings=result, markdown=None)
                markdown = _render_markdown(state, generated_at)
                state = update_state(st.session_state, markdown=markdown)
                st.session_state["markdown_preview"] = markdown
                store_project(st.session_state, state.model_dump())
                st.success("Interpretation complete. Preview available below.")

    if state.findings:
        st.subheader("Report preview")
        markdown_value = state.markdown or _render_markdown(state, datetime.now(timezone.utc))
        edited_markdown = st.text_area(
            "Markdown", value=markdown_value, height=400, key="markdown_preview"
        )
        if edited_markdown != state.markdown:
            state = update_state(st.session_state, markdown=edited_markdown)

        _copy_to_clipboard_button(edited_markdown)

        st.download_button(
            "Download report.md",
            data=edited_markdown,
            file_name="relationship_report.md",
            mime="text/markdown",
        )

        st.download_button(
            "Download findings.json",
            data=json.dumps(state.findings, indent=2, ensure_ascii=False),
            file_name="relationship_findings.json",
            mime="application/json",
        )

        totals = state.findings.get("totals", {}) if isinstance(state.findings, Mapping) else {}
        score_table = build_scores_table(sections.summarise_scores(totals))
        with st.expander("Score breakdown", expanded=True):
            st.dataframe(score_table, use_container_width=True)

        findings_list = state.findings.get("findings", []) if isinstance(state.findings, Mapping) else []
        with st.expander("Grouped findings"):
            groups = sections.group_by_primary_tag(findings_list)
            for group in groups:
                st.markdown(f"### {group.tag.title()}")
                for item in group.items:
                    snippet = _finding_snippet(item)
                    score_val = item.get("score") if isinstance(item, Mapping) else None
                    try:
                        score_fmt = f"{float(score_val):.2f}"
                    except (TypeError, ValueError):
                        score_fmt = "n/a"
                    title = item.get("title") if isinstance(item, Mapping) else "Finding"
                    st.write(f"- **{title}** ({score_fmt}) {snippet}")

        with st.expander("Raw payload"):
            st.json(state.findings)


if __name__ == "__main__":  # pragma: no cover
    main()
