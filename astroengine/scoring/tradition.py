"""Tradition-specific scoring helpers derived from repository data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from ..infrastructure.paths import profiles_dir

__all__ = ["TraditionSpec", "get_tradition_spec", "load_tradition_table"]


@lru_cache(maxsize=1)
def _tradition_policy_path() -> Path:
    return profiles_dir() / "tradition_scoring.json"


@lru_cache(maxsize=1)
def load_tradition_table() -> Mapping[str, object]:
    path = _tradition_policy_path()
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    payload = "\n".join(line for line in raw_lines if not line.strip().startswith("#"))
    return json.loads(payload)


@dataclass(frozen=True)
class TraditionSpec:
    """Wrapper exposing tradition-specific scoring parameters."""

    name: str
    data: Mapping[str, object]

    def drishti_angles(self, body: str) -> tuple[float, ...]:
        entry = self._drishti_entry(body)
        if not entry:
            return ()
        raw_angles = entry.get("angles_deg")
        if isinstance(raw_angles, Sequence):
            return tuple(float(angle) for angle in raw_angles)
        return ()

    def drishti_scalar(self, body: str) -> float:
        entry = self._drishti_entry(body)
        if not entry:
            return 0.0
        scalar = entry.get("severity_scalar")
        try:
            return float(scalar)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return 0.0

    def resonance_bias(self) -> Mapping[str, float]:
        bias = self.data.get("resonance_bias")
        if isinstance(bias, Mapping):
            return {str(key): float(value) for key, value in bias.items()}
        return {}

    def _drishti_entry(self, body: str) -> Mapping[str, object] | None:
        drishti = self.data.get("drishti")
        if isinstance(drishti, Mapping):
            entry = drishti.get(body.lower())
            if isinstance(entry, Mapping):
                return entry
        return None


@lru_cache(maxsize=None)
def get_tradition_spec(name: str) -> TraditionSpec | None:
    table = load_tradition_table()
    traditions = table.get("traditions") if isinstance(table, Mapping) else None
    if not isinstance(traditions, Mapping):
        return None
    entry = traditions.get(name.lower())
    if not isinstance(entry, Mapping):
        return None
    return TraditionSpec(name=name.lower(), data=entry)
