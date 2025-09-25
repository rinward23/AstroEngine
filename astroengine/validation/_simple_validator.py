"""A tiny JSON-schema-like validator for offline doctor checks.

The implementation supports only the keywords used by the schema
contracts bundled with this repository.  It avoids third-party
requirements so operators can run validations in constrained
offline environments.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

__all__ = ["SimpleValidationError", "SimpleValidator"]


@dataclass
class SimpleValidationError:
    """Represents a validation failure."""

    path: tuple[Any, ...]
    message: str

    @property
    def json_path(self) -> str:
        pointer = "$"
        for part in self.path:
            if isinstance(part, int):
                pointer += f"[{part}]"
            else:
                pointer += f".{part}"
        return pointer


class SimpleValidator:
    """Very small subset of JSON Schema validation."""

    def __init__(self, schema: dict[str, Any]):
        self._schema = schema
        self._defs = schema.get("$defs") or schema.get("definitions") or {}

    def iter_errors(self, value: Any) -> Iterator[SimpleValidationError]:
        yield from self._iter_errors(self._schema, value, ())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _iter_errors(
        self, schema: dict[str, Any], value: Any, path: tuple[Any, ...]
    ) -> Iterable[SimpleValidationError]:
        if "$ref" in schema:
            target = self._resolve_ref(schema["$ref"], path)
            if target is None:
                yield SimpleValidationError(
                    path, f"Unresolvable reference {schema['$ref']}"
                )
            else:
                yield from self._iter_errors(target, value, path)
            return

        schema_type = schema.get("type")
        if schema_type is not None:
            if isinstance(schema_type, list):
                if not any(self._matches_type(t, value) for t in schema_type):
                    yield SimpleValidationError(
                        path,
                        f"Expected type {schema_type} but got {type(value).__name__}",
                    )
                    return
            else:
                if not self._matches_type(schema_type, value):
                    yield SimpleValidationError(
                        path,
                        f"Expected type {schema_type} but got {type(value).__name__}",
                    )
                    return

        if schema_type == "object":
            if not isinstance(value, dict):
                yield SimpleValidationError(path, "Expected object")
                return
            required = schema.get("required", [])
            for key in required:
                if key not in value:
                    yield SimpleValidationError(
                        path + (key,), "Missing required property"
                    )
            props = schema.get("properties", {})
            additional_allowed = schema.get("additionalProperties", True)
            if additional_allowed is False:
                extras = [key for key in value.keys() if key not in props]
                for extra in extras:
                    yield SimpleValidationError(
                        path + (extra,), "Additional properties are not allowed"
                    )
            for key, subschema in props.items():
                if key in value:
                    yield from self._iter_errors(subschema, value[key], path + (key,))
            return

        if schema_type == "array":
            if not isinstance(value, list):
                yield SimpleValidationError(path, "Expected array")
                return
            min_items = schema.get("minItems")
            if min_items is not None and len(value) < min_items:
                yield SimpleValidationError(
                    path, f"Expected at least {min_items} items"
                )
            item_schema = schema.get("items")
            if item_schema:
                for idx, item in enumerate(value):
                    yield from self._iter_errors(item_schema, item, path + (idx,))
            return

        if schema_type == "string":
            if not isinstance(value, str):
                yield SimpleValidationError(path, "Expected string")
                return
            pattern = schema.get("pattern")
            if pattern and not re.fullmatch(pattern, value):
                yield SimpleValidationError(
                    path, f"Value does not match pattern {pattern}"
                )
            if "enum" in schema and value not in schema["enum"]:
                yield SimpleValidationError(
                    path, f"Value {value!r} is not one of {schema['enum']}"
                )
            fmt = schema.get("format")
            if fmt == "date-time" and not _is_datetime(value):
                yield SimpleValidationError(path, "Invalid date-time format")
            return

        if schema_type == "boolean":
            if not isinstance(value, bool):
                yield SimpleValidationError(path, "Expected boolean")
            return

        if schema_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                yield SimpleValidationError(path, "Expected integer")
                return
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and value < minimum:
                yield SimpleValidationError(
                    path, f"Value {value} is less than minimum {minimum}"
                )
            if maximum is not None and value > maximum:
                yield SimpleValidationError(
                    path, f"Value {value} exceeds maximum {maximum}"
                )
            return

        if schema_type == "number":
            if not _is_number(value):
                yield SimpleValidationError(path, "Expected number")
                return
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and value < minimum:
                yield SimpleValidationError(
                    path, f"Value {value} is less than minimum {minimum}"
                )
            if maximum is not None and value > maximum:
                yield SimpleValidationError(
                    path, f"Value {value} exceeds maximum {maximum}"
                )
            return

        if "enum" in schema:
            if value not in schema["enum"]:
                yield SimpleValidationError(
                    path, f"Value {value!r} is not one of {schema['enum']}"
                )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _resolve_ref(self, ref: str, path: tuple[Any, ...]) -> dict[str, Any] | None:
        if ref.startswith("#/$defs/"):
            key = ref.split("/")[-1]
            return self._defs.get(key)
        if ref.startswith("#/definitions/"):
            key = ref.split("/")[-1]
            return self._defs.get(key)
        return None

    @staticmethod
    def _matches_type(expected: str, value: Any) -> bool:
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "string":
            return isinstance(value, str)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return _is_number(value)
        return True


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_datetime(value: str) -> bool:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        _dt.datetime.fromisoformat(value)
        return True
    except Exception:
        return False
