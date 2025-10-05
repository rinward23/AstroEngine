from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Response

from app.schemas.interpret import (
    RulepacksResponse,
    RulepackInfo,
    FindingsRequest,
    FindingsResponse,
    FindingOut,
)
from core.interpret_plus.engine import interpret, load_rules

from astroengine.web.responses import conditional_json_response

router = APIRouter(prefix="/interpret", tags=["Interpretations"])

# Directory roots containing rulepacks (YAML/JSON).
if env_dir := os.getenv("RULEPACK_DIR"):
    RULEPACK_DIRS: List[str] = [os.path.abspath(env_dir)]
else:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    RULEPACK_DIRS = [
        os.path.join(base, "interpret-packs", "packs"),
        os.path.join(base, "interpret-packs", "meta"),
        os.path.join(base, "core", "interpret_plus", "samples"),
    ]


def _load_pack_info(path: str) -> Optional[RulepackInfo]:
    try:
        pack = load_rules(path)
    except Exception:
        return None
    rid = pack.get("rulepack") or os.path.splitext(os.path.basename(path))[0]
    desc = pack.get("description")
    return RulepackInfo(id=str(rid), path=path, description=desc)


def _discover_rulepacks() -> List[RulepackInfo]:
    items: List[RulepackInfo] = []
    for directory in RULEPACK_DIRS:
        if not os.path.isdir(directory):
            continue
        for fn in os.listdir(directory):
            if not (fn.endswith(".yaml") or fn.endswith(".yml") or fn.endswith(".json")):
                continue
            path = os.path.join(directory, fn)
            info = _load_pack_info(path)
            if info:
                items.append(info)
    items.sort(key=lambda x: x.id)
    return items


@router.get("/rulepacks", response_model=RulepacksResponse, summary="List available rulepacks")
def list_rulepacks(
    if_none_match: str | None = Header(default=None, alias="If-None-Match")
) -> Response:
    items = _discover_rulepacks()
    payload = RulepacksResponse(
        items=items,
        meta={
            "count": len(items),
            "dirs": [directory for directory in RULEPACK_DIRS if os.path.isdir(directory)],
        },
    )
    return conditional_json_response(
        payload.model_dump(mode="json"),
        if_none_match=if_none_match,
        max_age=600,
    )


@router.post("/relationship", response_model=FindingsResponse, summary="Run relationship interpretations")
def relationship_findings(req: FindingsRequest):
    # Validate scope payload
    if req.scope == "synastry" and not req.hits:
        raise HTTPException(status_code=400, detail="synastry requires hits[]")
    if req.scope in ("composite", "davison") and not req.positions:
        raise HTTPException(status_code=400, detail="composite/davison require positions{}")

    # Load rules
    if req.rules_inline is not None:
        if isinstance(req.rules_inline, dict):
            rules: Any = req.rules_inline
        else:
            rules = req.rules_inline
    else:
        rp = req.rulepack_id or "relationship_basic"  # default built-in
        match = next((r for r in _discover_rulepacks() if r.id == rp), None)
        if not match:
            raise HTTPException(status_code=404, detail=f"rulepack not found: {rp}")
        rules = load_rules(match.path)

    # Build request for engine
    ireq: Dict[str, Any] = {"scope": req.scope}
    if req.scope == "synastry":
        ireq["hits"] = req.hits
    else:
        ireq["positions"] = req.positions
        if req.houses is not None:
            ireq["houses"] = req.houses
        if req.angles is not None:
            ireq["angles"] = req.angles
    if req.profile is not None:
        ireq["profile"] = req.profile

    findings = interpret(ireq, rules)

    # Filters
    if req.min_score is not None:
        findings = [f for f in findings if f.score >= req.min_score]
    if req.top_k is not None and req.top_k > 0:
        findings = findings[: req.top_k]

    pack_id = rules.get("rulepack") if isinstance(rules, dict) else None

    return FindingsResponse(
        findings=[FindingOut(**asdict(f)) for f in findings],
        meta={"count": len(findings), "rulepack": pack_id, "profile": req.profile},
    )


__all__ = ["router", "list_rulepacks", "relationship_findings"]
