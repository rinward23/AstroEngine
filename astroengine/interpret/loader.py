
"""Rulepack loading and validation helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError as PydanticValidationError

from .models import RulepackDocument, RulepackLintResult


class RulepackValidationError(Exception):
    """Raised when a rulepack fails schema or semantic validation."""

    def __init__(self, message: str, *, errors: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass(frozen=True)
class LoadedRulepack:
    """Parsed rulepack document alongside its raw content."""

    document: RulepackDocument
    content: dict[str, Any]


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


def load_rulepack(raw: str | bytes, *, source: str | None = None) -> LoadedRulepack:
    """Parse and validate a rulepack document."""

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    content = _parse_raw(raw, source=source)
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

    return LoadedRulepack(document=document, content=content)


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

