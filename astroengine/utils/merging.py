"""Mapping merge helpers used by profile and policy loaders."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = ["deep_merge"]


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursive merge of ``override`` into ``base``.

    Values in ``override`` replace the corresponding key in ``base`` unless both
    values are mappings, in which case the merge recurses. The original mapping
    objects are not mutated.
    """

    result: dict[str, Any] = {key: value for key, value in base.items()}
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
