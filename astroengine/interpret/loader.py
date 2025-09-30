
"""Rulepack loading and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from astroengine.core.aspects_plus.harmonics import BASE_ASPECTS

from .models import (
    LoadedRulepack,
    Rule,
    RuleDefinition,
    RuleThen,
    RuleWhen,
    Rulepack,
    RulepackDocument,
    RulepackHeader,
    RulepackLintResult,
)


class RulepackValidationError(Exception):
    """Raised when a rulepack fails schema or semantic validation."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "interpret_rulepack.schema.json"
_VALIDATOR = Draft202012Validator(json.loads(_SCHEMA_PATH.read_text(encoding="utf-8")))


def _parse_raw(content: str, *, source: str | None = None) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:  # pragma: no cover - PyYAML parses broad cases
            raise RulepackValidationError(
                f"failed to parse rulepack {source or ''}: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise RulepackValidationError("rulepack must be a JSON/YAML object")
        return parsed


def _validate_schema(payload: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for err in _VALIDATOR.iter_errors(payload):
        errors.append(
            {
                "path": list(err.path),
                "message": err.message,
                "validator": err.validator,
            }
        )
    return errors


def _ensure_header(document: RulepackDocument) -> RulepackDocument:
    header = document.meta or RulepackHeader()
    identifier = document.rulepack or header.id or header.name
    if identifier is None:
        raise RulepackValidationError("rulepack missing identifier metadata")
    updates: dict[str, Any] = {}
    if header.id is None:
        updates["id"] = identifier
    if header.name is None:
        updates["name"] = identifier
    if header.title is None:
        updates["title"] = header.name or identifier
    if updates:
        header = header.model_copy(update=updates)
    doc_updates: dict[str, Any] = {"meta": header}
    if document.rulepack is None:
        doc_updates["rulepack"] = header.id
    if document.version is None:
        version = header.version or 1
        doc_updates["version"] = int(version)
    if doc_updates:
        document = document.model_copy(update=doc_updates)
    return document


def _to_rule(definition: RuleDefinition) -> Rule:
    cond = definition.when

    bodies = tuple(cond.bodies or ())
    default_a: tuple[str, ...] = ()
    default_b: tuple[str, ...] = ()
    if len(bodies) >= 1:
        default_a = (bodies[0],)
        default_b = (bodies[0],)
    if len(bodies) >= 2:
        default_b = (bodies[1],)

    def _resolve_side(value: tuple[str, ...] | str | None, default: tuple[str, ...]) -> tuple[str, ...] | str:
        if value == "*":
            return "*"
        if value is None:
            return tuple(default) if default else "*"
        if isinstance(value, tuple):
            return tuple(str(item) for item in value)
        if isinstance(value, str):
            return (value,)
        return tuple(str(item) for item in value)

    def _resolve_aspects(value: tuple[Any, ...] | str | None) -> tuple[int, ...] | str:
        if value is None or value == "*":
            raw = tuple(cond.aspect_in or ())
        else:
            raw = value
        parsed: list[int] = []
        for item in raw:
            try:
                parsed.append(int(round(float(item))))
            except (TypeError, ValueError):
                try:
                    parsed.append(int(str(item)))
                except (TypeError, ValueError):
                    angle = BASE_ASPECTS.get(str(item).lower())
                    if angle is not None:
                        parsed.append(int(round(float(angle))))
        return tuple(parsed) if parsed else "*"

    bodiesA = _resolve_side(cond.bodiesA, default_a)
    bodiesB = _resolve_side(cond.bodiesB, default_b)
    aspects = _resolve_aspects(cond.aspects)
    min_severity = float(cond.min_severity or 0.0)

    when = RuleWhen(bodiesA=bodiesA, bodiesB=bodiesB, aspects=aspects, min_severity=min_severity)
    outcome = definition.then
    then = RuleThen(
        title=outcome.title,
        tags=tuple(str(tag) for tag in outcome.tags),
        base_score=float(outcome.base_score),
        score_fn=str(outcome.score_fn),
        markdown_template=outcome.markdown_template,
    )
    return Rule(id=definition.id, scope=str(definition.scope), when=when, then=then)


def _build_loaded_rulepack(document: RulepackDocument, content: dict[str, Any]) -> LoadedRulepack:
    document = _ensure_header(document)
    rules = tuple(_to_rule(rule_def) for rule_def in document.rules)
    archetypes = {key: tuple(value) for key, value in (document.archetypes or {}).items()}
    metadata = (
        document.meta.model_dump(exclude_none=True)
        if document.meta is not None
        else {}
    )
    return LoadedRulepack(
        id=str(document.rulepack),
        version=int(document.version or 1),
        profiles=dict(document.profiles),
        rules=rules,
        archetypes=archetypes,
        metadata=metadata,
        document=document,
        content=content,
    )


def load_rulepack_from_data(data: dict[str, Any], *, source: str | None = None) -> LoadedRulepack:
    """Validate *data* and return a runtime rulepack."""

    errors = _validate_schema(data)
    if errors:
        raise RulepackValidationError("rulepack failed schema validation", errors=errors)
    try:
        document = RulepackDocument.model_validate(data)
    except PydanticValidationError as exc:
        raise RulepackValidationError(
            f"rulepack failed model validation{f' ({source})' if source else ''}",
            errors=exc.errors(),
        ) from exc
    return _build_loaded_rulepack(document, data)


def load_rulepack(raw: str | bytes | Path, *, source: str | None = None) -> LoadedRulepack:
    """Parse content from *raw* (path, bytes, or text) into a rulepack."""

    path: Path | None = None
    if isinstance(raw, Path):
        path = raw
    elif isinstance(raw, str):
        if "\n" not in raw and len(raw) < 256:
            candidate = Path(raw)
            try:
                if candidate.exists() and candidate.is_file():
                    path = candidate
            except OSError:
                path = None
    if path is not None:
        text = path.read_text(encoding="utf-8")
        source = source or str(path)
        data = _parse_raw(text, source=source)
    else:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not isinstance(raw, str):
            raise TypeError("rulepack payload must be path, str, or bytes")
        data = _parse_raw(raw, source=source)
    return load_rulepack_from_data(data, source=source)


def iter_rulepack_rules(rulepack: Rulepack) -> Iterator[Rule]:
    """Yield rules in definition order."""

    yield from rulepack.rules


def lint_rulepack(raw: str | bytes | Path, *, source: str | None = None) -> RulepackLintResult:
    """Return lint diagnostics for a rulepack payload without persisting it."""

    try:
        loaded = load_rulepack(raw, source=source)
    except RulepackValidationError as exc:
        return RulepackLintResult(ok=False, errors=exc.errors, warnings=[], meta={"source": source})

    return RulepackLintResult(
        ok=True,
        errors=[],
        warnings=[],
        meta={
            "id": loaded.rulepack,
            "version": loaded.version,
            "rule_count": len(loaded.rules),
        },
    )


__all__ = [
    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
    "RulepackValidationError",
]

