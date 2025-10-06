"""Core evaluation engine for interpretation findings."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import cos, pi
from typing import Any

from .loader import Rule, Rulepack, iter_rulepack_rules


@dataclass(slots=True)
class Hit:
    """Normalized relationship aspect hit."""

    bodyA: str
    bodyB: str
    aspect: int
    severity: float
    offset: float | None = None


@dataclass(slots=True)
class Finding:
    """Single interpretation finding."""

    id: str
    title: str
    tags: list[str]
    score: float
    context: dict[str, Any]
    markdown: str | None = None


@dataclass(slots=True)
class EvaluationResult:
    """Aggregate output from the engine."""

    findings: list[Finding]
    totals: dict[str, Any]


def _severity_modifier(name: str, severity: float) -> float:
    if severity <= 0:
        return 0.0
    if name.startswith("cosine"):
        power = 1.0
        if "^" in name:
            try:
                power = float(name.split("^", 1)[1])
            except ValueError:
                power = 1.0
        value = 0.5 * (1 + cos(pi * (1 - severity)))
        return max(0.0, min(1.0, value**power))
    if name == "linear":
        return max(0.0, min(1.0, severity))
    return max(0.0, min(1.0, severity))


def _match(rule: Rule, hit: Hit) -> bool:
    if rule.scope != "synastry":
        return False
    when = rule.when
    if when.bodiesA != "*" and hit.bodyA not in when.bodiesA:
        return False
    if when.bodiesB != "*" and hit.bodyB not in when.bodiesB:
        return False
    if when.aspects != "*" and hit.aspect not in when.aspects:
        return False
    if hit.severity < when.min_severity:
        return False
    return True


def _context_from_hit(hit: Hit) -> dict[str, Any]:
    context = {
        "bodyA": hit.bodyA,
        "bodyB": hit.bodyB,
        "aspect": hit.aspect,
        "severity": hit.severity,
    }
    if hit.offset is not None:
        context["offset"] = hit.offset
    return context


def evaluate(
    rulepack: Rulepack,
    *,
    scope: str,
    hits: Iterable[dict[str, Any]] | None = None,
    positionsA: Any | None = None,
    positionsB: Any | None = None,
    profile: str = "balanced",
    renderer=None,
) -> EvaluationResult:
    """Evaluate *rulepack* against chart data and return scored findings."""

    del positionsA, positionsB  # composite/davison support is planned but not yet implemented.

    tag_weights = rulepack.profile_weights(profile)
    raw_findings: list[Finding] = []

    if scope == "synastry" and hits:
        for hit_data in hits:
            hit = Hit(
                bodyA=hit_data["bodyA"],
                bodyB=hit_data["bodyB"],
                aspect=int(hit_data["aspect"]),
                severity=float(hit_data["severity"]),
                offset=float(hit_data.get("offset")) if hit_data.get("offset") is not None else None,
            )
            for rule in iter_rulepack_rules(rulepack):
                if not _match(rule, hit):
                    continue
                modifier = _severity_modifier(rule.then.score_fn, hit.severity)
                if modifier <= 0:
                    continue
                weights = [tag_weights.get(tag, 1.0) for tag in rule.then.tags]
                weight = sum(weights) / max(1, len(weights))
                score = min(1.0, rule.then.base_score * modifier * weight)
                markdown = None
                if renderer and rule.then.markdown_template:
                    markdown = renderer.render(rule.then.markdown_template, _context_from_hit(hit))
                raw_findings.append(
                    Finding(
                        id=rule.id,
                        title=rule.then.title,
                        tags=list(rule.then.tags),
                        score=score,
                        context=_context_from_hit(hit),
                        markdown=markdown,
                    )
                )

    deduped: dict[tuple[Any, ...], Finding] = {}
    for finding in raw_findings:
        key = (
            finding.id,
            finding.context.get("bodyA"),
            finding.context.get("bodyB"),
            finding.context.get("aspect"),
            tuple(sorted(finding.tags)),
        )
        existing = deduped.get(key)
        if existing is None or finding.score > existing.score:
            deduped[key] = finding

    findings = sorted(deduped.values(), key=lambda f: f.score, reverse=True)

    by_tag: dict[str, float] = {}
    for finding in findings:
        for tag in finding.tags:
            by_tag[tag] = by_tag.get(tag, 0.0) + finding.score

    totals = {
        "by_tag": by_tag,
        "overall": sum(f.score for f in findings),
    }

    return EvaluationResult(findings=findings, totals=totals)


__all__ = ["EvaluationResult", "evaluate"]
