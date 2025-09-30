"""Compatibility layer for JSON serialization with optional orjson support."""

from __future__ import annotations

from typing import Any

import json as _json

try:  # pragma: no cover - depends on optional dependency
    import orjson as _orjson  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - pure Python fallback path
    _HAS_ORJSON = False

    OPT_SORT_KEYS = 1
    JSONDecodeError = _json.JSONDecodeError

    def dumps(value: Any, *, option: int | None = None) -> bytes:
        """Serialize *value* to UTF-8 encoded JSON bytes.

        Only the :data:`OPT_SORT_KEYS` flag is honoured to keep behaviour close to
        :mod:`orjson`. Other option values raise :class:`TypeError` so callers do
        not silently proceed with unsupported flags.
        """

        if option not in (None, OPT_SORT_KEYS):
            raise TypeError(f"unsupported option {option!r} for json fallback")
        sort_keys = option == OPT_SORT_KEYS
        return _json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=sort_keys,
            separators=(",", ":"),
        ).encode("utf-8")

    def loads(data: bytes | bytearray | str) -> Any:
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")
        return _json.loads(data)

    def has_orjson() -> bool:
        return False

else:  # pragma: no cover - exercised when orjson is available
    _HAS_ORJSON = True

    OPT_SORT_KEYS = _orjson.OPT_SORT_KEYS
    JSONDecodeError = _orjson.JSONDecodeError
    dumps = _orjson.dumps
    loads = _orjson.loads

    def has_orjson() -> bool:
        return True


__all__ = [
    "JSONDecodeError",
    "OPT_SORT_KEYS",
    "dumps",
    "has_orjson",
    "loads",
]
