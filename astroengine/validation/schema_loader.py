"""Schema loading and validation utilities.

The validation helpers keep the I/O responsibilities out of
the core modules so that the underlying astrology engines can
be swapped without touching the schema contracts.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

from astroengine.data.schemas import (
    SCHEMA_REGISTRY,
    SchemaNotFoundError,
    list_schema_keys,
    load_schema_document,
)
from ._simple_validator import SimpleValidator

__all__ = [
    "SchemaValidationError",
    "available_schema_keys",
    "get_validator",
    "validate_payload",
]


class SchemaValidationError(RuntimeError):
    """Raised when a payload fails schema validation."""

    def __init__(self, errors: Iterable[str]):
        self.errors: List[str] = list(errors)
        super().__init__("; ".join(self.errors))


@lru_cache(maxsize=None)
def get_validator(schema_key: str) -> SimpleValidator:
    """Return a cached validator instance for ``schema_key``."""

    if schema_key not in SCHEMA_REGISTRY:
        raise SchemaNotFoundError(schema_key)
    schema = load_schema_document(schema_key)
    if not isinstance(schema, dict):
        raise TypeError(f"Schema '{schema_key}' is not a JSON object")
    return SimpleValidator(schema)


def available_schema_keys(kind: str | None = None) -> List[str]:
    """List schema keys known to the registry."""

    return sorted(list_schema_keys(kind))


def validate_payload(schema_key: str, payload: object) -> None:
    """Validate ``payload`` against ``schema_key``.

    Raises
    ------
    SchemaValidationError
        If validation fails.  The exception message contains a
        semicolon separated list of human-readable errors.
    """

    validator = get_validator(schema_key)
    failures = []
    for error in validator.iter_errors(payload):
        failures.append(f"{error.json_path}: {error.message}")
    if failures:
        raise SchemaValidationError(failures)
