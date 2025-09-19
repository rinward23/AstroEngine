"""Schema registry and loaders.

The registry keeps track of JSON schema files used by
validation/doctor tooling.  All files live in the top-level
``schemas`` directory so operators can inspect them without
packing everything into the Python module.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, MutableMapping
from functools import cache
from pathlib import Path

from . import SCHEMA_DIR

__all__ = [
    "SCHEMA_REGISTRY",
    "SchemaNotFoundError",
    "load_schema_document",
    "list_schema_keys",
]


class SchemaNotFoundError(KeyError):
    """Raised when an unknown schema key is requested."""


SchemaMetadata = Mapping[str, str]

SCHEMA_REGISTRY: dict[str, SchemaMetadata] = {
    "result_v1": {"filename": "result_schema_v1.json", "kind": "jsonschema"},
    "result_v1_with_domains": {
        "filename": "result_schema_v1_with_domains.json",
        "kind": "jsonschema",
    },
    "contact_gate_v2": {
        "filename": "contact_gate_schema_v2.json",
        "kind": "jsonschema",
    },
    "orbs_policy": {"filename": "orbs_policy.json", "kind": "data"},
    "natal_input_v1_ext": {
        "filename": "natal_input_v1_ext.json",
        "kind": "jsonschema",
    },
}


def _schema_path(metadata: Mapping[str, str]) -> Path:
    filename = metadata.get("filename")
    if not filename:
        raise ValueError("Schema metadata missing filename field")
    return SCHEMA_DIR / filename


@cache
def load_schema_document(key: str) -> MutableMapping[str, object]:
    """Return the JSON payload for the requested schema key.

    Parameters
    ----------
    key:
        Identifier registered in :data:`SCHEMA_REGISTRY`.
    """

    if key not in SCHEMA_REGISTRY:
        raise SchemaNotFoundError(key)
    metadata = SCHEMA_REGISTRY[key]
    path = _schema_path(metadata)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def list_schema_keys(kind: str | None = None) -> Iterable[str]:
    """Yield the registered schema keys filtered by kind."""

    for name, metadata in SCHEMA_REGISTRY.items():
        if kind is None or metadata.get("kind") == kind:
            yield name
