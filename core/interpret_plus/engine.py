from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple
import json

try:  # pragma: no cover - optional dependency for richer rulepacks
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# --------------------------- Data Models -----------------------------------
@dataclass
class Finding:
    """Structured interpretation assembled from a rule match."""

    id: str
    scope: str  # synastry|composite|davison
    title: str
    text: str
    score: float
    tags: List[str]
    meta: Dict[str, Any]


Rule = Dict[str, Any]
Request = Dict[str, Any]
SynastryHit = Dict[str, Any]


# --------------------------- Rule loading ----------------------------------
def load_rules(path: str) -> List[Rule]:
    """Load a rulepack from YAML or JSON."""

    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    if path.endswith(".json") or yaml is None:
        return json.loads(raw)
    return yaml.safe_load(raw)


# --------------------------- Helpers ---------------------------------------
ASPECT_SYMBOLS: Dict[str, str] = {
    "conjunction": "☌",
    "opposition": "☍",
    "trine": "△",
    "square": "□",
    "sextile": "✶",
    "quincunx": "⚻",
}

ARCHETYPES: Dict[str, str] = {
    "Sun": "Core Self",
    "Moon": "Emotional Body",
    "Mercury": "Mind & Speech",
    "Venus": "Relating & Pleasure",
    "Mars": "Drive & Desire",
    "Jupiter": "Growth",
    "Saturn": "Structure & Commitment",
}


def _fmt(template: str, ctx: Dict[str, Any]) -> str:
    """Best-effort format that falls back to template on error."""

    try:
        return template.format(**ctx)
    except Exception:
        return template


def _coerce_bodies(raw: Any) -> Sequence[str]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    return tuple(raw)


# --------------------------- Matching Primitives ---------------------------
def _match_synastry_rule(rule: Rule, hits: Sequence[SynastryHit]) -> List[Tuple[SynastryHit, float]]:
    """Return (hit, strength) pairs that satisfy the synastry rule."""

    cond = rule.get("when", {}) or {}
    bodies = set(_coerce_bodies(cond.get("bodies")))
    aspect_in = {str(name).lower() for name in cond.get("aspect_in", [])}
    min_severity = float(cond.get("min_severity", 0.0))

    matches: List[Tuple[SynastryHit, float]] = []
    for hit in hits:
        a = hit.get("a")
        b = hit.get("b")
        aspect = str(hit.get("aspect", "")).lower()
        if aspect_in and aspect not in aspect_in:
            continue

        if bodies:
            pair = {a, b}
            if len(bodies) == 1:
                if a not in bodies and b not in bodies:
                    continue
            elif pair != bodies:
                continue

        severity = float(hit.get("severity", 0.0))
        if severity < min_severity:
            continue
        matches.append((hit, max(severity, min_severity)))
    return matches


def _match_body_longitude(rule: Rule, positions: Dict[str, float]) -> List[Tuple[str, float]]:
    cond = rule.get("when", {}) or {}
    bodies = _coerce_bodies(cond.get("bodies") or cond.get("body"))
    if not bodies:
        return []

    ranges = cond.get("longitude_ranges") or []
    normalised_ranges = [tuple(map(float, window)) for window in ranges]
    matches: List[Tuple[str, float]] = []
    for body in bodies:
        if body not in positions:
            continue
        longitude = float(positions[body])
        if normalised_ranges:
            in_range = any(lo <= longitude < hi for lo, hi in normalised_ranges)
            if not in_range:
                continue
        matches.append((body, longitude))
    return matches


# --------------------------- Engine ----------------------------------------
def interpret(request: Request, rules: Sequence[Rule]) -> List[Finding]:
    """Evaluate the supplied rules against the request payload."""

    scope = request.get("scope")
    findings: List[Finding] = []

    for rule in rules:
        if rule.get("scope") != scope:
            continue

        base_score = float(rule.get("score", 1.0))
        title = rule.get("title") or rule.get("id", "")
        template = rule.get("text", "")
        tags = list(rule.get("tags", []) or [])

        if scope == "synastry":
            hits = request.get("hits", []) or []
            for hit, strength in _match_synastry_rule(rule, hits):
                a = hit.get("a")
                b = hit.get("b")
                aspect = str(hit.get("aspect", "")).lower()
                ctx = {
                    "a": a,
                    "b": b,
                    "aspect": aspect,
                    "aspect_symbol": ASPECT_SYMBOLS.get(aspect, aspect),
                    "severity": float(hit.get("severity", 0.0)),
                    "a_arch": ARCHETYPES.get(a, a),
                    "b_arch": ARCHETYPES.get(b, b),
                }
                findings.append(
                    Finding(
                        id=rule.get("id", "rule"),
                        scope=scope,
                        title=title,
                        text=_fmt(template, ctx),
                        score=base_score * strength,
                        tags=tags,
                        meta={"hit": hit},
                    )
                )
        else:
            positions = request.get("positions", {}) or {}
            for body, longitude in _match_body_longitude(rule, positions):
                ctx = {
                    "body": body,
                    "longitude": longitude,
                    "arch": ARCHETYPES.get(body, body),
                }
                findings.append(
                    Finding(
                        id=rule.get("id", "rule"),
                        scope=scope,
                        title=title,
                        text=_fmt(template, ctx),
                        score=base_score,
                        tags=tags,
                        meta={"body": body, "longitude": longitude},
                    )
                )

    findings.sort(key=lambda item: (-item.score, item.id))
    return findings


__all__ = [
    "ARCHETYPES",
    "ASPECT_SYMBOLS",
    "Finding",
    "interpret",
    "load_rules",
]
