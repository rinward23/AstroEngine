"""Compatibility loader for interpretation rulepacks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .models import Rule, RuleThen, RuleWhen, Rulepack, RulepackDocument, RulepackLintResult


class RulepackValidationError(Exception):
    """Raised when rulepack parsing or validation fails."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass(frozen=True)
class LoadedRulepack:
    """Loaded rulepack with compatibility helpers for legacy consumers."""

    runtime: Rulepack
    document: RulepackDocument
    content: dict[str, Any]

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - delegation helper
        return getattr(self.runtime, item)


def _parse_raw(raw: str, *, source: str | None = None) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            raise RulepackValidationError(
                f"failed to parse rulepack {source or ''}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise RulepackValidationError("rulepack must decode to a mapping")
        return data


def _ensure_sequence(value: Any) -> tuple[Any, ...]:
    if value is None:
        return tuple()
    if isinstance(value, (str, bytes)):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)
    return (value,)


def _legacy_rules(data: dict[str, Any]) -> tuple[Rule, ...]:
    rules: list[Rule] = []
    for entry in data.get("rules", []):
        if not isinstance(entry, dict):
            continue
        rid = str(entry.get("id"))
        scope = str(entry.get("scope", "synastry"))
        when = entry.get("when") or {}
        then = entry.get("then") or {}
        bodies_a = when.get("bodiesA")
        bodies_b = when.get("bodiesB")
        aspects = when.get("aspects")
        rule = Rule(
            id=rid,
            scope=scope,
            when=RuleWhen(
                bodiesA="*" if bodies_a in (None, "*") else tuple(str(x) for x in _ensure_sequence(bodies_a)),
                bodiesB="*" if bodies_b in (None, "*") else tuple(str(x) for x in _ensure_sequence(bodies_b)),
                aspects="*"
                if aspects in (None, "*")
                else tuple(int(float(x)) for x in _ensure_sequence(aspects)),
                min_severity=float(when.get("min_severity", 0.0)),
            ),
            then=RuleThen(
                title=str(then.get("title") or rid),
                tags=tuple(str(tag) for tag in _ensure_sequence(then.get("tags"))),
                base_score=float(then.get("base_score", 1.0)),
                score_fn=str(then.get("score_fn", "linear")),
                markdown_template=then.get("markdown_template"),
            ),
        )
        rules.append(rule)
    return tuple(rules)


def _normalize_for_document(data: dict[str, Any]) -> dict[str, Any]:
    if "meta" in data and isinstance(data["meta"], dict) and "id" in data["meta"]:
        return data
    pack_id = data.get("rulepack")
    if not pack_id:
        raise RulepackValidationError("rulepack id missing")
    meta_src = data.get("meta") or {}
    meta = {
        "id": str(pack_id),
        "name": str(meta_src.get("name") or pack_id),
        "title": str(meta_src.get("title") or meta_src.get("name") or pack_id),
        "description": meta_src.get("description"),
        "version": int(data.get("version", 1)),
        "mutable": bool(meta_src.get("mutable", False)),
    }
    profiles = {}
    for name, payload in (data.get("profiles") or {}).items():
        if isinstance(payload, dict):
            tags = payload.get("tags") or {}
            profiles[str(name)] = {
                "base_multiplier": 1.0,
                "tag_weights": {str(k): float(v) for k, v in tags.items()},
                "rule_weights": {},
            }
    rules = []
    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RulepackValidationError("rulepack must contain at least one rule")
    for entry in raw_rules:
        if not isinstance(entry, dict):
            continue
        then = entry.get("then") or {}
        when = entry.get("when") or {}
        rules.append(
            {
                "id": str(entry.get("id")),
                "scope": str(entry.get("scope", "synastry")),
                "title": str(then.get("title") or entry.get("id")),
                "text": str(then.get("markdown_template") or ""),
                "score": float(then.get("base_score", 1.0)),
                "tags": list(then.get("tags") or []),
                "when": {
                    "bodies": tuple(str(x) for x in _ensure_sequence(when.get("bodiesA"))) or None,
                    "aspect_in": tuple(str(x) for x in _ensure_sequence(when.get("aspects"))) or None,
                    "min_severity": when.get("min_severity"),
                },
            }
        )
    return {"meta": meta, "profiles": profiles, "rules": rules}


def _read_input(raw: str | bytes | Path | dict[str, Any], *, source: str | None = None) -> tuple[dict[str, Any], str | None]:
    if isinstance(raw, dict):
        return raw, source
    if isinstance(raw, Path):
        source = source or str(raw)
        return _parse_raw(raw.read_text(encoding="utf-8"), source=source), source
    if isinstance(raw, bytes):
        return _parse_raw(raw.decode("utf-8"), source=source), source
    if isinstance(raw, str):
        if "\n" in raw or raw.lstrip().startswith("{") or raw.lstrip().startswith("["):
            return _parse_raw(raw, source=source), source
        candidate = Path(raw)
        if candidate.exists():
            source = source or str(candidate)
            return _parse_raw(candidate.read_text(encoding="utf-8"), source=source), source
        return _parse_raw(raw, source=source), source
    raise TypeError("unsupported rulepack input type")


def load_rulepack(raw: str | bytes | Path | dict[str, Any], *, source: str | None = None) -> LoadedRulepack:
    """Load a rulepack from disk or raw bytes."""

    content, src = _read_input(raw, source=source)
    legacy_rules = _legacy_rules(content)
    identifier = str(content.get("rulepack") or content.get("meta", {}).get("id"))
    if not identifier:
        raise RulepackValidationError("rulepack id missing")
    profiles = {
        str(name): payload if isinstance(payload, dict) else {}
        for name, payload in (content.get("profiles") or {}).items()
    }
    normalized = _normalize_for_document(content)
    try:
        document = RulepackDocument.model_validate(normalized)
    except Exception as exc:  # pragma: no cover - delegated to tests
        raise RulepackValidationError("rulepack failed validation") from exc
    runtime = Rulepack(rulepack=identifier, profiles=profiles, rules=legacy_rules, source=src)
    return LoadedRulepack(runtime=runtime, document=document, content=content)


def load_rulepack_from_data(data: dict[str, Any], *, source: str | None = None) -> LoadedRulepack:
    return load_rulepack(data, source=source)


def iter_rulepack_rules(rulepack: LoadedRulepack | Rulepack) -> tuple[Rule, ...]:
    if isinstance(rulepack, LoadedRulepack):
        return rulepack.runtime.rules
    return rulepack.rules


def lint_rulepack(raw: str | bytes | Path | dict[str, Any], *, source: str | None = None) -> RulepackLintResult:
    try:
        loaded = load_rulepack(raw, source=source)
    except RulepackValidationError as exc:
        return RulepackLintResult(ok=False, errors=exc.errors or [{"message": str(exc)}], warnings=[], meta={"source": source})
    return RulepackLintResult(
        ok=True,
        errors=[],
        warnings=[],
        meta={"id": loaded.rulepack, "rule_count": len(loaded.rules), "source": loaded.source},
    )


__all__ = [
    "LoadedRulepack",
    "RulepackValidationError",
    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
]
