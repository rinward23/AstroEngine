
"""Rulepack loading and validation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import RulepackLintResult


class RulepackValidationError(Exception):
    """Raised when rulepack parsing or validation fails."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []



@dataclass(slots=True)
class Profile:
    """Profile weighting configuration."""

    name: str
    base_multiplier: float
    tag_weights: dict[str, float]
    rule_weights: dict[str, float]


@dataclass(slots=True)
class RuleCondition:
    """Condition block for a rule."""

    bodiesA: tuple[str, ...] | str
    bodiesB: tuple[str, ...] | str
    aspects: tuple[int, ...] | str
    min_severity: float
    longitude_ranges: tuple[tuple[float, float], ...]


@dataclass(slots=True)
class RuleOutcome:
    """Outcome configuration for a rule."""

    title: str
    tags: tuple[str, ...]
    base_score: float
    score_fn: str
    markdown_template: str | None


@dataclass(slots=True)
class Rule:
    """Single interpretation rule."""

    id: str
    scope: str
    when: RuleCondition
    then: RuleOutcome


@dataclass(slots=True)
class Rulepack:
    """Parsed rulepack document."""

    rulepack: str
    version: int
    profiles: dict[str, Profile]
    rules: tuple[Rule, ...]
    archetypes: dict[str, tuple[str, ...]]
    meta: dict[str, Any]
    content: dict[str, Any]
    source: str | None = None


    def profile_weights(self, profile_name: str) -> dict[str, float]:
        """Return tag weights for *profile_name* with sensible fallbacks."""


        profile = self.profiles.get(profile_name) or self.profiles.get("balanced")
        if profile is None:
            return {}
        weights = {tag: float(weight) * profile.base_multiplier for tag, weight in profile.tag_weights.items()}
        if not weights and profile.base_multiplier != 1.0:
            return {"__base__": profile.base_multiplier}
        return weights


def _parse_raw(raw: str, *, source: str | None = None) -> dict[str, Any]:
    try:
        return yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - PyYAML may raise various subclasses
        raise RulepackValidationError(f"failed to parse rulepack {source or ''}: {exc}") from exc


def _normalize_sequence(value: Any, *, allow_star: bool = True) -> tuple[str, ...] | str:
    if value is None:
        return "*" if allow_star else tuple()
    if allow_star and value == "*":
        return "*"
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8") if isinstance(value, bytes) else value
        if allow_star and text == "*":
            return "*"
        return (text,)
    if isinstance(value, Sequence):
        items = [str(item) for item in value]
        if not items:
            if allow_star:
                return "*"
            raise ValueError("sequence must not be empty")
        return tuple(items)
    raise ValueError("expected sequence or '*' value")


def _normalize_aspects(value: Any) -> tuple[int, ...] | str:
    if value is None:
        return "*"
    if value == "*":
        return "*"
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8") if isinstance(value, bytes) else value
        if text == "*":
            return "*"
        try:
            return (int(round(float(text))),)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError("aspect entries must be numeric") from exc
    if isinstance(value, Sequence):
        aspects: list[int] = []
        for entry in value:
            try:
                aspects.append(int(round(float(entry))))
            except (TypeError, ValueError) as exc:
                raise ValueError("aspect entries must be numeric") from exc
        if not aspects:
            return "*"
        return tuple(aspects)
    raise ValueError("expected sequence or '*' value")


def _normalize_ranges(value: Any) -> tuple[tuple[float, float], ...]:
    if value is None:
        return tuple()
    ranges: list[tuple[float, float]] = []
    if not isinstance(value, Sequence):
        raise ValueError("longitude_ranges must be an array")
    for entry in value:
        if not isinstance(entry, Sequence) or len(entry) != 2:
            raise ValueError("longitude range must contain two numeric values")
        lo, hi = entry
        try:
            ranges.append((float(lo), float(hi)))
        except (TypeError, ValueError) as exc:
            raise ValueError("longitude range values must be numeric") from exc
    return tuple(ranges)


def _normalize_tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, (str, bytes)):
        text = value.decode("utf-8") if isinstance(value, bytes) else value
        return (text,)
    if isinstance(value, Sequence):
        return tuple(str(entry) for entry in value)
    raise ValueError("tags must be a string or sequence of strings")


def _load_profile(name: str, payload: Mapping[str, Any]) -> Profile:
    try:
        base = float(payload.get("base_multiplier", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("base_multiplier must be numeric") from exc
    tags_raw = payload.get("tags") or payload.get("tag_weights") or {}
    if not isinstance(tags_raw, Mapping):
        raise ValueError("tags must be a mapping of tag weights")
    tag_weights = {str(tag): float(weight) for tag, weight in tags_raw.items()}
    rule_weights_raw = payload.get("rule_weights") or {}
    if not isinstance(rule_weights_raw, Mapping):
        raise ValueError("rule_weights must be a mapping")
    rule_weights = {str(rule): float(weight) for rule, weight in rule_weights_raw.items()}
    return Profile(name=str(name), base_multiplier=base, tag_weights=tag_weights, rule_weights=rule_weights)


def _load_rule(payload: Mapping[str, Any]) -> Rule:
    if "id" not in payload:
        raise ValueError("rule id is required")
    rule_id = str(payload["id"]) or None
    if not rule_id:
        raise ValueError("rule id must be a non-empty string")
    scope = str(payload.get("scope") or "synastry")
    when_payload = payload.get("when")
    if not isinstance(when_payload, Mapping):
        raise ValueError("rule when must be a mapping")
    try:
        bodies_a = _normalize_sequence(when_payload.get("bodiesA"))
        bodies_b = _normalize_sequence(when_payload.get("bodiesB"))
        aspects = _normalize_aspects(when_payload.get("aspects"))
        min_severity = float(when_payload.get("min_severity", 0.0))
        longitude_ranges = _normalize_ranges(when_payload.get("longitude_ranges"))
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc
    then_payload = payload.get("then")
    if not isinstance(then_payload, Mapping):
        raise ValueError("rule then must be a mapping")
    title = str(then_payload.get("title") or "").strip()
    if not title:
        raise ValueError("rule then.title is required")
    try:
        tags = _normalize_tags(then_payload.get("tags"))
        base_score = float(then_payload.get("base_score", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc
    score_fn = str(then_payload.get("score_fn") or "linear")
    markdown_template = then_payload.get("markdown_template")
    if markdown_template is not None:
        markdown_template = str(markdown_template)
    return Rule(
        id=rule_id,
        scope=scope,
        when=RuleCondition(
            bodiesA=bodies_a,
            bodiesB=bodies_b,
            aspects=aspects,
            min_severity=float(min_severity),
            longitude_ranges=longitude_ranges,
        ),
        then=RuleOutcome(
            title=title,
            tags=tags,
            base_score=base_score,
            score_fn=score_fn,
            markdown_template=markdown_template,
        ),
    )


def _load_archetypes(data: Any) -> dict[str, tuple[str, ...]]:
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError("archetypes must be a mapping")
    archetypes: dict[str, tuple[str, ...]] = {}
    for name, entries in data.items():
        if entries is None:
            archetypes[str(name)] = tuple()
            continue
        if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
            archetypes[str(name)] = tuple(str(item) for item in entries)
            continue
        raise ValueError("archetype entries must be arrays of strings")
    return archetypes


def load_rulepack_from_data(data: Mapping[str, Any], *, source: str | None = None) -> Rulepack:
    errors: list[dict[str, Any]] = []

    def add_error(path: Iterable[Any], message: str) -> None:
        errors.append({"path": list(path), "message": message})

    if not isinstance(data, Mapping):
        raise RulepackValidationError("rulepack payload must be an object")

    rulepack_id = data.get("rulepack")
    if not isinstance(rulepack_id, str) or not rulepack_id.strip():
        add_error(["rulepack"], "rulepack identifier is required")
    version_raw = data.get("version", 1)
    try:
        version = int(version_raw)
    except (TypeError, ValueError):
        add_error(["version"], "version must be an integer")
        version = 0

    profiles: dict[str, Profile] = {}
    try:
        profiles_data = data.get("profiles", {})
        if profiles_data:
            if not isinstance(profiles_data, Mapping):
                raise ValueError("profiles must be a mapping")
            for name, payload in profiles_data.items():
                try:
                    profiles[str(name)] = _load_profile(str(name), payload or {})
                except ValueError as exc:
                    add_error(["profiles", name], str(exc))
        else:
            profiles = {}
    except ValueError as exc:
        add_error(["profiles"], str(exc))

    rules: list[Rule] = []
    rules_payload = data.get("rules")
    if not isinstance(rules_payload, Sequence) or isinstance(rules_payload, (str, bytes)):
        add_error(["rules"], "rules must be a non-empty array")
    else:
        if not rules_payload:
            add_error(["rules"], "rules must be a non-empty array")
        for index, payload in enumerate(rules_payload):
            if not isinstance(payload, Mapping):
                add_error(["rules", index], "rule entries must be objects")
                continue
            try:
                rules.append(_load_rule(payload))
            except ValueError as exc:
                add_error(["rules", index], str(exc))

    archetypes: dict[str, tuple[str, ...]] = {}
    try:
        archetypes = _load_archetypes(data.get("archetypes"))
    except ValueError as exc:
        add_error(["archetypes"], str(exc))

    meta: dict[str, Any] = {}
    if data.get("meta") is not None:
        if not isinstance(data["meta"], Mapping):
            add_error(["meta"], "meta must be a mapping")
        else:
            meta = {str(k): v for k, v in data["meta"].items()}

    if errors:
        raise RulepackValidationError("rulepack failed validation", errors=errors)

    content = deepcopy(dict(data))
    return Rulepack(
        rulepack=str(rulepack_id),
        version=version,
        profiles=profiles,
        rules=tuple(rules),
        archetypes=archetypes,
        meta=meta,
        content=content,
        source=source,
    )


def load_rulepack(raw: str | bytes | Path, *, source: str | None = None) -> Rulepack:
    """Load a rulepack from *raw* text or a filesystem path."""

    text: str
    actual_source = source
    if isinstance(raw, Path):
        text = raw.read_text(encoding="utf-8")
        actual_source = actual_source or str(raw)
    elif isinstance(raw, bytes):
        text = raw.decode("utf-8")
    elif isinstance(raw, str):
        if "\n" not in raw and "\r" not in raw:
            candidate = Path(raw)
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8")
                actual_source = actual_source or raw
            else:
                text = raw
        else:
            text = raw
    else:
        raise TypeError("rulepack loader expects text, bytes, or a Path")
    data = _parse_raw(text, source=actual_source)
    return load_rulepack_from_data(data, source=actual_source)


def lint_rulepack(raw: str | bytes | Path, *, source: str | None = None) -> RulepackLintResult:
    """Return lint diagnostics for a rulepack payload without persisting it."""


def iter_rulepack_rules(rulepack: LoadedRulepack | Rulepack) -> tuple[Rule, ...]:
    if isinstance(rulepack, LoadedRulepack):
        return rulepack.runtime.rules
    return rulepack.rules



def lint_rulepack(raw: str | bytes | Path | dict[str, Any], *, source: str | None = None) -> RulepackLintResult:
    try:
        if isinstance(raw, Mapping):
            load_rulepack_from_data(raw, source=source)
        else:
            load_rulepack(raw, source=source)
    except RulepackValidationError as exc:

        return RulepackLintResult(ok=False, errors=exc.errors or [{"message": str(exc)}], warnings=[], meta={"source": source})
    return RulepackLintResult(
        ok=True,
        errors=[],
        warnings=[],

        meta={"rulepack": loaded.rulepack, "version": loaded.version, "source": loaded.source},
    )


def iter_rulepack_rules(rulepack: Rulepack) -> Iterable[Rule]:
    """Yield rules from *rulepack* in the order they were declared."""

    yield from rulepack.rules


__all__ = [
    "Profile",
    "Rule",
    "RuleCondition",
    "RuleOutcome",
    "Rulepack",

    "RulepackValidationError",
    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
]

