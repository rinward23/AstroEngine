"""Canonicalization helpers for relationship caching."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, Iterable, Mapping, MutableMapping

import hashlib

from astroengine.utils import json as json_utils

_POS_PRECISION = 8
_FLOAT_PRECISION = 8


@dataclass(frozen=True)
class CanonicalPayload:
    payload: Mapping[str, Any]
    serialized: bytes
    digest: str


def _round_float(value: float, precision: int = _FLOAT_PRECISION) -> float:
    return round(float(value), precision)


def _normalize_longitude(value: float) -> float:
    lon = float(value) % 360.0
    if lon < 0:
        lon += 360.0
    return _round_float(lon, _POS_PRECISION)


def _normalize_mapping(values: Mapping[str, Any], *, value_fn) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key in sorted(values):
        normalized[key] = value_fn(values[key])
    return normalized


def canonicalize_positions(pos: Mapping[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key in sorted(pos):
        value = pos[key]
        normalized[key] = None if value is None else _normalize_longitude(value)
    return normalized


def _normalize_policy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _normalize_mapping(value, value_fn=_normalize_policy_value)
    if isinstance(value, (list, tuple, set)):
        return [_normalize_policy_value(v) for v in value]
    if isinstance(value, (int, float)):
        return _round_float(float(value))
    return value


def canonicalize_policy(policy: Mapping[str, Any]) -> Dict[str, Any]:
    return _normalize_mapping(policy, value_fn=_normalize_policy_value)


def canonicalize_aspects(aspects: Iterable[str]) -> list[str]:
    unique = {asp.strip().lower() for asp in aspects}
    return sorted(unique)


def canonicalize_synastry_payload(
    positions_a: Mapping[str, Any],
    positions_b: Mapping[str, Any],
    aspects: Iterable[str],
    orb_policy: Mapping[str, Any],
    *,
    weights: Mapping[str, Any] | None = None,
    gamma: float | None = None,
    node_policy: Any | None = None,
) -> CanonicalPayload:
    payload: Dict[str, Any] = {
        "positionsA": canonicalize_positions(positions_a),
        "positionsB": canonicalize_positions(positions_b),
        "aspects": canonicalize_aspects(aspects),
        "orbPolicy": canonicalize_policy(orb_policy),
    }
    if weights is not None:
        payload["weights"] = canonicalize_policy(weights)
    if gamma is not None:
        payload["gamma"] = _round_float(float(gamma))
    if node_policy is not None:
        payload["nodePolicy"] = node_policy
    return _freeze_payload(payload, namespace="syn")


def canonicalize_composite_payload(
    positions_a: Mapping[str, Any],
    positions_b: Mapping[str, Any],
    objects: Iterable[str],
    *,
    node_policy: Any | None = None,
) -> CanonicalPayload:
    payload: Dict[str, Any] = {
        "positionsA": canonicalize_positions(positions_a),
        "positionsB": canonicalize_positions(positions_b),
        "objects": sorted({obj.strip() for obj in objects}),
    }
    if node_policy is not None:
        payload["nodePolicy"] = node_policy
    return _freeze_payload(payload, namespace="comp")


def canonicalize_davison_payload(
    objects: Iterable[str],
    dt_a: datetime,
    dt_b: datetime,
    *,
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
    node_policy: Any | None = None,
) -> CanonicalPayload:
    payload: Dict[str, Any] = {
        "objects": sorted({obj.strip() for obj in objects}),
        "dtA": dt_a.astimezone(UTC).isoformat(),
        "dtB": dt_b.astimezone(UTC).isoformat(),
        "latA": _round_float(lat_a),
        "lonA": _round_float(lon_a),
        "latB": _round_float(lat_b),
        "lonB": _round_float(lon_b),
    }
    if node_policy is not None:
        payload["nodePolicy"] = node_policy
    return _freeze_payload(payload, namespace="dav")


def _freeze_payload(payload: MutableMapping[str, Any], *, namespace: str) -> CanonicalPayload:
    serialized = json_utils.dumps(payload, option=json_utils.OPT_SORT_KEYS)
    digest = hashlib.sha256(serialized).hexdigest()[:32]
    return CanonicalPayload(payload=dict(payload), serialized=serialized, digest=f"{namespace}:v1:{digest}")


def make_cache_key(namespace: str, payload: Mapping[str, Any]) -> CanonicalPayload:
    serialized = json_utils.dumps(payload, option=json_utils.OPT_SORT_KEYS)
    digest = hashlib.sha256(serialized).hexdigest()[:32]
    return CanonicalPayload(payload=dict(payload), serialized=serialized, digest=f"{namespace}:v1:{digest}")
