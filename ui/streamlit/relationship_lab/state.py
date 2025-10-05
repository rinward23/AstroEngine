"""Session state utilities for the Relationship Lab Streamlit app."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from .constants import EXTENDED_ASPECTS

SESSION_KEY = "relationship_lab_state"


@dataclass
class RelationshipState:
    mode: str = "api"
    api_base_url: str = "http://localhost:8000"
    aspect_mode: str = "extended"
    aspects: list[str] = field(default_factory=lambda: list(EXTENDED_ASPECTS))
    min_severity: float = 0.0
    weights_profile: str = "default"
    positions_a_text: str = ""
    positions_b_text: str = ""
    last_synastry: Optional[Dict[str, Any]] = None
    last_composite: Optional[Dict[str, Any]] = None
    last_davison: Optional[Dict[str, Any]] = None


def _coerce_state(value: Any) -> RelationshipState:
    if isinstance(value, RelationshipState):
        return value
    if isinstance(value, dict):
        data = dict(value)
        data.setdefault("aspects", list(EXTENDED_ASPECTS))
        return RelationshipState(**data)
    return RelationshipState()


def get_state(st) -> RelationshipState:
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = RelationshipState()
    else:
        st.session_state[SESSION_KEY] = _coerce_state(st.session_state[SESSION_KEY])
    return st.session_state[SESSION_KEY]


def update_state(st, **changes: Any) -> None:
    state = get_state(st)
    for key, value in changes.items():
        setattr(state, key, value)
    st.session_state[SESSION_KEY] = state


def export_state_payload(state: RelationshipState) -> Dict[str, Any]:
    payload = asdict(state)
    # Remove bulky entries not needed for export/import toggles.
    payload.pop("last_synastry", None)
    payload.pop("last_composite", None)
    payload.pop("last_davison", None)
    return payload
