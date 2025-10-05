"""Session-state helpers for the report builder Streamlit app."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from pydantic import BaseModel, Field, ValidationError

DEFAULT_ASPECTS = [0, 30, 45, 60, 72, 90, 120, 135, 144, 150, 180]
DEFAULT_SCOPE = "synastry"
DEFAULT_TEMPLATE_ID = "default"


class ReportFilters(BaseModel):
    profile: str = "balanced"
    top_k: int = 50
    min_score: float = 0.3
    include_tags: List[str] = Field(default_factory=list)
    exclude_tags: List[str] = Field(default_factory=list)
    top_highlights: int = 7


class PairIdentity(BaseModel):
    nameA: str = "Person A"
    nameB: str = "Person B"

    class Config:
        populate_by_name = True


class ReportState(BaseModel):
    pair: PairIdentity = Field(default_factory=PairIdentity)
    aspects: List[int] = Field(default_factory=lambda: list(DEFAULT_ASPECTS))
    filters: ReportFilters = Field(default_factory=ReportFilters)
    rulepack_id: str = ""
    scope: str = DEFAULT_SCOPE
    hits: Optional[List[Dict[str, Any]]] = None
    findings: Optional[Dict[str, Any]] = None
    inputs: Optional[Dict[str, Any]] = None
    markdown: Optional[str] = None
    template_id: str = DEFAULT_TEMPLATE_ID
    project_payload: Optional[Dict[str, Any]] = None


def get_state(store: MutableMapping[str, Any]) -> ReportState:
    raw = store.get("report_state")
    if isinstance(raw, ReportState):  # pragma: no cover - defensive
        return raw
    if isinstance(raw, Mapping):
        try:
            return ReportState.model_validate(raw)
        except ValidationError:
            pass
    state = ReportState()
    store["report_state"] = state.model_dump()
    return state


def update_state(store: MutableMapping[str, Any], **updates: Any) -> ReportState:
    state = get_state(store)
    data = state.model_dump()
    data.update(updates)
    new_state = ReportState.model_validate(data)
    store["report_state"] = new_state.model_dump()
    return new_state


def store_project(store: MutableMapping[str, Any], payload: Dict[str, Any]) -> None:
    """Persist a project payload inside session state."""

    state = get_state(store)
    updated = state.model_copy(update={"project_payload": payload})
    store["report_state"] = updated.model_dump()


def reset_state(store: MutableMapping[str, Any]) -> ReportState:
    state = ReportState()
    store["report_state"] = state.model_dump()
    return state


def load_project(store: MutableMapping[str, Any], payload: Mapping[str, Any]) -> ReportState:
    """Replace the current report builder state with a project payload."""

    state = ReportState.model_validate(payload)
    store["report_state"] = state.model_dump()
    return state


__all__ = [
    "DEFAULT_ASPECTS",
    "DEFAULT_SCOPE",
    "DEFAULT_TEMPLATE_ID",
    "PairIdentity",
    "ReportFilters",
    "ReportState",
    "get_state",
    "update_state",
    "reset_state",
    "store_project",
    "load_project",
]
