from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.schemas.interpret import (
    RulepacksResponse,
    RulepackInfo,
    FindingsRequest,
    FindingsResponse,
    FindingOut,
)
from core.interpret_plus.engine import interpret, load_rules

router = APIRouter(prefix="/interpret", tags=["Interpretations"])

# Directory containing rulepacks (YAML/JSON). Defaults to built-in samples.
RULEPACK_DIR = os.getenv(
    "RULEPACK_DIR",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "core",
            "interpret_plus",
            "samples",
        )
    ),
)


def _discover_rulepacks() -> List[RulepackInfo]:
    items: List[RulepackInfo] = []
    if not os.path.isdir(RULEPACK_DIR):
        return items
    for fn in os.listdir(RULEPACK_DIR):
        if not (fn.endswith(".yaml") or fn.endswith(".yml") or fn.endswith(".json")):
            continue
        rid = os.path.splitext(fn)[0]
        path = os.path.join(RULEPACK_DIR, fn)
        items.append(RulepackInfo(id=rid, path=path, description=None))
    items.sort(key=lambda x: x.id)
    return items


@router.get("/rulepacks", response_model=RulepacksResponse, summary="List available rulepacks")
def list_rulepacks():
    items = _discover_rulepacks()
    return RulepacksResponse(items=items, meta={"count": len(items), "dir": RULEPACK_DIR})


@router.post("/relationship", response_model=FindingsResponse, summary="Run relationship interpretations")
def relationship_findings(req: FindingsRequest):
    # Validate scope payload
    if req.scope == "synastry" and not req.hits:
        raise HTTPException(status_code=400, detail="synastry requires hits[]")
    if req.scope in ("composite", "davison") and not req.positions:
        raise HTTPException(status_code=400, detail="composite/davison require positions{}")

    # Load rules
    if req.rules_inline is not None:
        rules: List[Dict[str, Any]] = req.rules_inline
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

    findings = interpret(ireq, rules)

    # Filters
    if req.min_score is not None:
        findings = [f for f in findings if f.score >= req.min_score]
    if req.top_k is not None and req.top_k > 0:
        findings = findings[: req.top_k]

    return FindingsResponse(
        findings=[FindingOut(**asdict(f)) for f in findings],
        meta={"count": len(findings)},
    )


__all__ = ["router", "list_rulepacks", "relationship_findings"]
