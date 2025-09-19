"""Profile loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_profile_json(path: str | Path) -> dict[str, Any]:
    """Load a profile JSON document and return a dictionary."""

    profile_path = Path(path)
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "id" not in data:
        raise ValueError("Invalid profile json: must be an object with 'id'")
    return data


def profile_into_ctx(ctx: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Merge profile keys into an engine context dictionary."""

    ctx = dict(ctx or {})
    ctx.setdefault("profile_id", profile.get("id"))

    aspects = profile.get("aspects", {})
    orbs = profile.get("orbs", {})
    flags = profile.get("flags", {})
    domain = profile.get("domain", {})

    ctx["aspects"] = aspects
    ctx["orbs"] = orbs
    ctx["flags"] = flags
    ctx["domain_profile"] = domain.get("profile_key", ctx.get("domain_profile", "vca_neutral"))
    ctx["domain_scorer"] = domain.get("scorer", ctx.get("domain_scorer", "weighted"))
    ctx["domain_temperature"] = domain.get("temperature", ctx.get("domain_temperature", 8.0))
    return ctx


__all__ = ["load_profile_json", "profile_into_ctx"]
