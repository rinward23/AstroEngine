"""Client helpers for Relationship Lab data sources."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Mapping, MutableMapping, Optional, Protocol

import requests

try:  # FastAPI router utilities are optional at runtime
    from app.routers import aspects as aspects_module  # type: ignore
except Exception:  # pragma: no cover - optional dependency for local mode
    aspects_module = None  # type: ignore[assignment]

from core.relationship_plus.composite import (
    Geo,
    composite_positions,
    davison_midpoints,
    davison_positions,
)
from core.relationship_plus.synastry import (
    SynastryHit,
    overlay_positions,
    synastry_grid,
    synastry_hits,
    synastry_score,
)


class RelationshipBackend(Protocol):
    """Protocol describing the operations required by the UI layer."""

    def synastry(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        ...

    def composite(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        ...

    def davison(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class RelationshipAPI(RelationshipBackend):
    """HTTP client against the relationship endpoints exposed by B-003."""

    base_url: str
    timeout_synastry: int = 60
    timeout_composite: int = 30
    timeout_davison: int = 60

    def _post(self, path: str, payload: Mapping[str, Any], *, timeout: int) -> Dict[str, Any]:
        root = self.base_url.rstrip("/")
        url = f"{root}{path}" if path.startswith("/") else f"{root}/{path}"
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise RuntimeError("API returned a non-JSON payload") from exc
        if not isinstance(data, MutableMapping):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response type from relationship API")
        return dict(data)

    def synastry(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return self._post("/relationship/synastry", payload, timeout=self.timeout_synastry)

    def composite(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return self._post("/relationship/composite", payload, timeout=self.timeout_composite)

    def davison(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return self._post("/relationship/davison", payload, timeout=self.timeout_davison)


@dataclass(frozen=True)
class RelationshipInProcess(RelationshipBackend):
    """In-process adapter that mirrors the behaviour of the HTTP API."""

    def synastry(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        pos_a = _require_mapping(payload.get("posA"), "posA")
        pos_b = _require_mapping(payload.get("posB"), "posB")
        aspects = list(payload.get("aspects") or [])
        policy = payload.get("orb_policy_inline") or {}
        per_aspect_weight = payload.get("per_aspect_weight")
        per_pair_weight = payload.get("per_pair_weight")

        hits = synastry_hits(
            pos_a,
            pos_b,
            aspects=aspects,
            policy=policy,
            per_aspect_weight=per_aspect_weight,
            per_pair_weight=per_pair_weight,
        )
        grid = synastry_grid(hits)
        overlay = overlay_positions(pos_a, pos_b)
        scores = synastry_score(hits)
        return {
            "hits": [_hit_to_dict(hit) for hit in hits],
            "grid": grid,
            "overlay": overlay,
            "scores": scores,
            "meta": {"count": len(hits)},
        }

    def composite(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        pos_a = _require_mapping(payload.get("posA"), "posA")
        pos_b = _require_mapping(payload.get("posB"), "posB")
        bodies = payload.get("bodies")
        positions = composite_positions(pos_a, pos_b, bodies=bodies)
        return {"positions": positions, "meta": {"bodies": list(positions.keys())}}

    def davison(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if aspects_module is None:
            raise RuntimeError(
                "Local Davison computation requires the API aspects module to resolve providers."
            )
        provider = aspects_module._get_provider()  # type: ignore[attr-defined]
        dt_a = payload.get("dtA")
        dt_b = payload.get("dtB")
        if isinstance(dt_a, str):
            dt_a = datetime.fromisoformat(dt_a)
        if isinstance(dt_b, str):
            dt_b = datetime.fromisoformat(dt_b)
        if dt_a is None or dt_b is None:
            raise RuntimeError("Davison payload requires 'dtA' and 'dtB' timestamps")
        loc_a_raw = payload.get("locA")
        loc_b_raw = payload.get("locB")
        loc_a = _require_mapping(loc_a_raw, "locA")
        loc_b = _require_mapping(loc_b_raw, "locB")
        geo_a = Geo(lat_deg=float(loc_a["lat_deg"]), lon_deg_east=float(loc_a["lon_deg_east"]))
        geo_b = Geo(lat_deg=float(loc_b["lat_deg"]), lon_deg_east=float(loc_b["lon_deg_east"]))
        bodies = payload.get("bodies")
        positions = davison_positions(provider, dt_a, geo_a, dt_b, geo_b, bodies=bodies)
        mid_dt, mid_lat, mid_lon = davison_midpoints(dt_a, geo_a, dt_b, geo_b)
        return {
            "positions": positions,
            "midpoint_time_utc": mid_dt.isoformat() if hasattr(mid_dt, "isoformat") else mid_dt,
            "midpoint_geo": {"lat_deg": mid_lat, "lon_deg_east": mid_lon},
            "meta": {"bodies": list(positions.keys())},
        }


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"Expected '{label}' to be a mapping of names to values")
    return value


def _hit_to_dict(hit: SynastryHit) -> Dict[str, Any]:
    return {
        "a": hit.a,
        "b": hit.b,
        "aspect": hit.aspect,
        "angle": hit.angle,
        "delta": hit.delta,
        "orb": hit.orb,
        "limit": hit.limit,
        "severity": hit.severity,
    }


def build_backend(mode: str, *, base_url: Optional[str] = None) -> RelationshipBackend:
    """Return a backend implementation based on ``mode``."""

    if mode == "api":
        if not base_url:
            raise RuntimeError("API mode requires a base URL")
        return RelationshipAPI(base_url)
    if mode == "local":
        return RelationshipInProcess()
    raise ValueError(f"Unknown backend mode: {mode}")
