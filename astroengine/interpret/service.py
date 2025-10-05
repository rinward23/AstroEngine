"""Evaluation helpers for relationship interpretations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS
from astroengine.core.aspects_plus.matcher import angular_sep_deg
from astroengine.core.aspects_plus.orb_policy import ASPECT_DEFAULTS, orb_limit
from astroengine.utils.i18n import translate

from .models import (
    Finding,
    FindingsFilters,
    InterpretRequest,
    InterpretResponse,
    ProfileDefinition,
    RuleDefinition,
    RulepackVersionPayload,
)


class InterpretationError(ValueError):
    """Raised when the interpretation request cannot be fulfilled."""


_ASPECT_BY_DEGREE = {int(round(angle)): name for name, angle in BASE_ASPECTS.items()}
_DEFAULT_ASPECT_NAMES = list(BASE_ASPECTS.keys())
_EPS = 1e-9


@dataclass
class _NormalizedHit:
    a: str
    b: str
    aspect: str
    severity: float
    angle: float | None = None
    orb: float | None = None
    limit: float | None = None

    def as_context(self) -> dict[str, Any]:
        ctx = {
            "a": self.a,
            "b": self.b,
            "aspect": self.aspect,
            "severity": self.severity,
        }
        if self.angle is not None:
            ctx["angle"] = self.angle
        if self.orb is not None:
            ctx["orb"] = self.orb
        if self.limit is not None:
            ctx["limit"] = self.limit
        return ctx


def _profile_for(rulepack: RulepackVersionPayload, profile_name: str) -> ProfileDefinition | None:
    profiles = rulepack.profiles or {}
    if profile_name in profiles:
        return profiles[profile_name]
    if "balanced" in profiles:
        return profiles["balanced"]
    if profiles:
        # Return an arbitrary profile to avoid zero multipliers
        key = sorted(profiles)[0]
        return profiles[key]
    return None


def _profile_multiplier(profile: ProfileDefinition | None, rule: RuleDefinition) -> float:
    multiplier = 1.0
    if profile is None:
        return multiplier
    multiplier *= float(profile.base_multiplier)
    rule_weight = profile.rule_weights.get(rule.id)
    if rule_weight is not None:
        multiplier *= float(rule_weight)
    tag_multiplier = 1.0
    for tag in rule.tags:
        weight = profile.tag_weights.get(tag)
        if weight is not None:
            tag_multiplier *= float(weight)
    multiplier *= tag_multiplier
    return multiplier


def _match_bodies(bodies: Sequence[str] | None, a: str, b: str) -> bool:
    if not bodies:
        return True
    normalized = [body.lower() for body in bodies]
    a_key = a.lower()
    b_key = b.lower()
    if len(normalized) == 1:
        target = normalized[0]
        return a_key == target or b_key == target
    return sorted({a_key, b_key}) == sorted({normalized[0], normalized[1]})


def _resolve_aspect_names(aspects: Sequence[int] | None) -> list[str]:
    if not aspects:
        return _DEFAULT_ASPECT_NAMES
    names: list[str] = []
    for value in aspects:
        key = _ASPECT_BY_DEGREE.get(int(value))
        if key:
            names.append(key)
    return names or _DEFAULT_ASPECT_NAMES


def _default_policy() -> dict[str, Any]:
    return {"per_aspect": dict(ASPECT_DEFAULTS)}


def _normalize_hits_from_payload(payload: Sequence[dict[str, Any]]) -> list[_NormalizedHit]:
    hits: list[_NormalizedHit] = []
    for entry in payload:
        a = str(entry.get("a"))
        b = str(entry.get("b"))
        aspect = str(entry.get("aspect"))
        if not a or not b or not aspect:
            continue
        severity = entry.get("severity")
        if severity is None:
            orb = float(entry.get("orb", 0.0))
            limit = float(entry.get("limit", 0.0))
            severity = 0.0 if limit <= 0 else max(0.0, 1.0 - (orb / limit))
        hit = _NormalizedHit(
            a=a,
            b=b,
            aspect=aspect.lower(),
            severity=float(severity),
            angle=float(entry.get("angle")) if entry.get("angle") is not None else None,
            orb=float(entry.get("orb")) if entry.get("orb") is not None else None,
            limit=float(entry.get("limit")) if entry.get("limit") is not None else None,
        )
        hits.append(hit)
    return hits


def _best_aspect_for_pair(
    a_name: str,
    b_name: str,
    delta: float,
    aspects: Sequence[str],
    policy: dict[str, Any],
) -> tuple[str, float, float, float] | None:
    best: tuple[str, float, float, float] | None = None
    for aspect_name in aspects:
        angle = BASE_ASPECTS.get(aspect_name)
        if angle is None:
            continue
        limit = float(orb_limit(a_name, b_name, aspect_name, policy))
        orb = abs(delta - float(angle))
        if orb > limit + _EPS:
            continue
        candidate = (aspect_name, orb, limit, float(angle))
        if best is None or orb < best[1]:
            best = candidate
    return best


def _hits_from_positions(data: dict[str, Any]) -> list[_NormalizedHit]:
    aspects = data.get("aspects")
    policy = data.get("policy") or _default_policy()
    aspect_names = _resolve_aspect_names(aspects)
    positions_a: dict[str, float] = data["positionsA"]
    positions_b: dict[str, float] = data["positionsB"]
    normalized: list[_NormalizedHit] = []
    for a_name, lon_a in positions_a.items():
        for b_name, lon_b in positions_b.items():
            delta = angular_sep_deg(float(lon_a), float(lon_b))
            match = _best_aspect_for_pair(a_name, b_name, delta, aspect_names, policy)
            if not match:
                continue
            aspect, orb, limit, angle = match
            severity = 0.0 if limit <= 0 else max(0.0, 1.0 - (orb / limit))
            normalized.append(
                _NormalizedHit(
                    a=a_name,
                    b=b_name,
                    aspect=aspect,
                    severity=severity,
                    angle=angle,
                    orb=orb,
                    limit=limit,
                )
            )
    normalized.sort(key=lambda hit: (hit.a, hit.b, hit.orb))
    return normalized


def _evaluate_synastry(
    rulepack: RulepackVersionPayload,
    rule: RuleDefinition,
    hits: Sequence[_NormalizedHit],
    profile: ProfileDefinition | None,
) -> Iterable[Finding]:
    cond = rule.when
    aspects = {aspect.lower() for aspect in (cond.aspect_in or [])}
    min_severity = cond.min_severity or 0.0
    multiplier = _profile_multiplier(profile, rule)
    for hit in hits:
        if aspects and hit.aspect not in aspects:
            continue
        if not _match_bodies(cond.bodies, hit.a, hit.b):
            continue
        if hit.severity < min_severity:
            continue
        score = float(rule.score) * hit.severity * multiplier
        if score <= 0:
            continue
        yield Finding(
            id=rule.id,
            title=rule.title,
            tags=list(rule.tags),
            score=score,
            context=hit.as_context(),
        )


def _evaluate_positions(
    rule: RuleDefinition,
    positions: dict[str, float],
    profile: ProfileDefinition | None,
) -> Iterable[Finding]:
    cond = rule.when
    bodies = cond.bodies or ()
    ranges = cond.longitude_ranges or ()
    multiplier = _profile_multiplier(profile, rule)
    for body in bodies:
        value = positions.get(body)
        if value is None:
            continue
        if ranges:
            match = any(float(lo) <= float(value) < float(hi) for lo, hi in ranges)
            if not match:
                continue
        score = float(rule.score) * multiplier
        if score <= 0:
            continue
        yield Finding(
            id=rule.id,
            title=rule.title,
            tags=list(rule.tags),
            score=score,
            context={"body": body, "longitude": float(value)},
        )


def _apply_filters(findings: list[Finding], filters: FindingsFilters) -> list[Finding]:
    results: list[Finding] = []
    include = set(filters.include_tags or [])
    exclude = set(filters.exclude_tags or [])
    for finding in findings:
        if finding.score < filters.min_score:
            continue
        tag_set = set(finding.tags)
        if include and not (tag_set & include):
            continue
        if exclude and (tag_set & exclude):
            continue
        results.append(finding)
    results.sort(key=lambda f: (-f.score, f.id))
    if filters.top_k:
        results = results[: filters.top_k]
    return results


def _aggregate(findings: Sequence[Finding]) -> dict[str, Any]:
    total = sum(f.score for f in findings)
    by_tag: dict[str, float] = {}
    for finding in findings:
        for tag in finding.tags:
            by_tag[tag] = by_tag.get(tag, 0.0) + finding.score
    return {
        "count": len(findings),
        "total_score": total,
        "by_tag": by_tag,
    }


def evaluate_relationship(
    rulepack: RulepackVersionPayload,
    request: InterpretRequest,
) -> InterpretResponse:
    profile = _profile_for(rulepack, request.filters.profile)
    findings: list[Finding] = []

    if request.scope == "synastry":
        if request.synastry is None:
            raise InterpretationError(
                translate("interpret.error.synastry_missing")
            )
        if hasattr(request.synastry, "hits"):
            hits = _normalize_hits_from_payload(request.synastry.hits)
        else:
            hits = _hits_from_positions(request.synastry.model_dump())
        for rule in rulepack.rules:
            if rule.scope != "synastry":
                continue
            findings.extend(_evaluate_synastry(rulepack, rule, hits, profile))
    elif request.scope == "composite":
        if not request.composite:
            raise InterpretationError(
                translate("interpret.error.composite_missing")
            )
        positions = {str(k): float(v) for k, v in request.composite.positions.items()}
        for rule in rulepack.rules:
            if rule.scope != "composite":
                continue
            findings.extend(_evaluate_positions(rule, positions, profile))
    elif request.scope == "davison":
        if not request.davison:
            raise InterpretationError(
                translate("interpret.error.davison_missing")
            )
        positions = {str(k): float(v) for k, v in request.davison.positions.items()}
        for rule in rulepack.rules:
            if rule.scope != "davison":
                continue
            findings.extend(_evaluate_positions(rule, positions, profile))
    else:  # pragma: no cover - guarded by request model
        raise InterpretationError(
            translate(
                "interpret.error.scope_unsupported", scope=request.scope
            )
        )

    filtered = _apply_filters(findings, request.filters)
    totals = _aggregate(filtered)
    return InterpretResponse(findings=filtered, totals=totals, rulepack=rulepack.meta)


__all__ = ["evaluate_relationship", "InterpretationError"]
