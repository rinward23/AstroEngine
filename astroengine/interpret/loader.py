
"""Rulepack loading and validation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Mapping

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from .models import (
    ProfileDefinition,
    Rule,
    RuleThenRuntime,
    RuleWhen,
    Rulepack,
    RulepackDocument,
    RulepackLintResult,
)


class RulepackValidationError(Exception):
    """Raised when a rulepack fails schema or semantic validation."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass(frozen=True)
class LoadedRulepack:
    """Parsed rulepack document alongside its raw content and runtime view."""

    document: RulepackDocument
    content: dict[str, Any]
    runtime: Rulepack

    @property
    def rulepack(self) -> str:
        return self.runtime.id

    @property
    def profiles(self) -> dict[str, ProfileDefinition]:
        return self.runtime.profiles

    @property
    def rules(self) -> list[Rule]:
        return self.runtime.rules

    def profile_weights(self, profile: str) -> dict[str, float]:
        return self.runtime.profile_weights(profile)

    @property
    def archetypes(self) -> dict[str, list[str]]:
        return self.runtime.archetypes


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


def _build_runtime(document: RulepackDocument) -> Rulepack:
    rules: list[Rule] = []
    for rule_def in document.rules:
        cond = rule_def.when
        bodies_a = cond.bodiesA if cond.bodiesA is not None else "*"
        bodies_b = cond.bodiesB if cond.bodiesB is not None else "*"
        aspects = cond.aspects if cond.aspects is not None else "*"
        when = RuleWhen(
            bodiesA=bodies_a,
            bodiesB=bodies_b,
            aspects=aspects,
            min_severity=float(cond.min_severity or 0.0),
        )
        then = RuleThenRuntime(
            title=rule_def.then.title,
            tags=tuple(rule_def.then.tags),
            base_score=float(rule_def.then.base_score),
            score_fn=rule_def.then.score_fn,
            markdown_template=rule_def.then.markdown_template,
        )
        rules.append(Rule(id=rule_def.id, scope=rule_def.scope, when=when, then=then))
    return Rulepack(
        id=document.rulepack,
        version=int(document.version),
        profiles=document.profiles,
        archetypes=document.archetypes,
        rules=rules,
    )


def load_rulepack(raw: Any, *, source: str | None = None) -> LoadedRulepack:
    """Parse and validate a rulepack document from content or a filesystem path."""

    if isinstance(raw, Path):
        potential_path = raw
        if potential_path.exists() and potential_path.is_file():
            text = potential_path.read_text(encoding="utf-8")
            return load_rulepack(text, source=str(potential_path))
    elif isinstance(raw, str):
        stripped = raw.strip()
        # Treat as path only when it resembles a filesystem reference.
        if "\n" not in raw and not stripped.startswith("{") and not stripped.startswith("["):
            potential_path = Path(raw)
            if potential_path.exists() and potential_path.is_file():
                text = potential_path.read_text(encoding="utf-8")
                return load_rulepack(text, source=str(potential_path))
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        content = _parse_raw(raw, source=source)
    elif isinstance(raw, Mapping):
        content = dict(raw)
    else:
        raise RulepackValidationError("rulepack payload must be string, bytes, mapping, or path")
    return load_rulepack_from_data(content, source=source)


def load_rulepack_from_data(data: Mapping[str, Any], *, source: str | None = None) -> LoadedRulepack:
    """Validate a pre-parsed rulepack mapping."""

    content = dict(data)
    errors: list[dict[str, Any]] = []
    for err in _VALIDATOR.iter_errors(content):
        errors.append(
            {
                "path": list(err.path),
                "message": err.message,
                "validator": err.validator,
            }
        )
    if errors:
        raise RulepackValidationError("rulepack failed schema validation", errors=errors)

    try:
        document = RulepackDocument.model_validate(content)
    except PydanticValidationError as exc:
        raise RulepackValidationError("rulepack failed model validation", errors=exc.errors()) from exc

    runtime = _build_runtime(document)
    normalized = document.model_dump(mode="python")
    return LoadedRulepack(document=document, content=normalized, runtime=runtime)


def lint_rulepack(raw: str | bytes, *, source: str | None = None) -> RulepackLintResult:
    """Return lint diagnostics for a rulepack payload without persisting it."""

    try:
        loaded = load_rulepack(raw, source=source)
    except RulepackValidationError as exc:
        return RulepackLintResult(ok=False, errors=exc.errors, warnings=[], meta={"source": source})

    return RulepackLintResult(
        ok=True,
        errors=[],
        warnings=[],
        meta={"id": loaded.document.meta.id, "rule_count": len(loaded.document.rules)},
    )


def iter_rulepack_rules(rulepack: Rulepack | LoadedRulepack) -> Generator[Rule, None, None]:
    """Yield rules from either a runtime rulepack or a loaded wrapper."""

    runtime = rulepack.runtime if isinstance(rulepack, LoadedRulepack) else rulepack
    for rule in runtime.rules:
        yield rule


__all__ = [
    "LoadedRulepack",
    "RulepackValidationError",
    "iter_rulepack_rules",
    "lint_rulepack",
    "load_rulepack",
    "load_rulepack_from_data",
]

