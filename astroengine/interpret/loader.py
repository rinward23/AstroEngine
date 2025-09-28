"""Utilities for loading interpretation rulepacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .models import Rulepack
from .schema import RULEPACK_SCHEMA


class RulepackValidationError(ValueError):
    """Raised when a rulepack fails schema or model validation."""


class RulepackNotFoundError(FileNotFoundError):
    """Raised when a rulepack path does not exist."""


def _load_file(path: Path) -> Any:
    if not path.exists():
        raise RulepackNotFoundError(f"Rulepack not found: {path}")

    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    if path.suffix.lower() == ".json":
        import json

        return json.loads(text)
    raise RulepackNotFoundError(f"Unsupported rulepack format: {path.suffix}")


def load_rulepack(path: str | Path) -> Rulepack:
    """Load and validate a rulepack from *path*."""

    data = _load_file(Path(path))
    return load_rulepack_from_data(data)


def load_rulepack_from_data(data: Any) -> Rulepack:
    """Validate *data* against the schema and return a :class:`Rulepack`."""

    try:
        jsonschema.validate(instance=data, schema=RULEPACK_SCHEMA)
    except jsonschema.ValidationError as exc:  # pragma: no cover - error path message
        raise RulepackValidationError(str(exc)) from exc

    try:
        return Rulepack.model_validate(data)
    except Exception as exc:  # pragma: no cover - Pydantic detail
        raise RulepackValidationError(str(exc)) from exc


def iter_rulepack_rules(rulepack: Rulepack):
    """Yield rules from *rulepack* preserving author order."""

    yield from rulepack.rules


__all__ = [
    "Rulepack",
    "RulepackNotFoundError",
    "RulepackValidationError",
    "iter_rulepack_rules",
    "load_rulepack",
    "load_rulepack_from_data",
]
