"""Synastry-related API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any, Sequence

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from ...chart.natal import DEFAULT_BODIES
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter


router = APIRouter()


def _to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class NatalPayload(BaseModel):
    ts: datetime

    @validator("ts", pre=True)
    def _validate_ts(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        raise TypeError("expected ISO-8601 timestamp")

    def positions(
        self, body_names: Sequence[str] | None, adapter: SwissEphemerisAdapter
    ) -> dict[str, float]:
        mapping = _body_map(body_names)
        if not mapping:
            return {}
        jd = adapter.julian_day(self.ts)
        samples = adapter.body_positions(jd, mapping)
        return {name: float(pos.longitude % 360.0) for name, pos in samples.items()}


class SynastryRequest(BaseModel):
    subject: NatalPayload
    partner: NatalPayload
    bodies: Sequence[str] | None = None
    aspects: Sequence[int] | None = None
    orb: float = Field(default=2.0, ge=0.0)


@dataclass
class _SynastryAspect:
    when_iso: str
    moving: str
    target: str
    aspect: int
    orb: float
    lon_moving: float
    lon_target: float


def _scan_synastry(request: SynastryRequest) -> list[_SynastryAspect]:
    adapter = SwissEphemerisAdapter.get_default_adapter()
    aspects = request.aspects or [0, 60, 90, 120, 180]
    orb = float(request.orb)

    hits: list[_SynastryAspect] = []
    bodies = request.bodies

    subject_positions = request.subject.positions(bodies, adapter)
    partner_positions = request.partner.positions(bodies, adapter)

    if not subject_positions or not partner_positions:
        return hits

    if bodies is None:
        names = [name for name in partner_positions.keys() if name in subject_positions]
    else:
        names = [
            name
            for name in bodies
            if name in partner_positions and name in subject_positions
        ]

    if not names:
        return hits

    iso = _to_iso(request.partner.ts)

    for name in names:
        moving = float(partner_positions[name])
        target = float(subject_positions[name])
        separation = abs((moving - target) % 360.0)
        if separation > 180.0:
            separation = 360.0 - separation
        for angle in aspects:
            delta = abs(separation - float(angle))
            if delta <= orb:
                hits.append(
                    _SynastryAspect(
                        when_iso=iso,
                        moving=name,
                        target=f"natal_{name}",
                        aspect=int(angle),
                        orb=float(delta),
                        lon_moving=moving,
                        lon_target=target,
                    )
                )
                break

    return hits


def _normalize_synastry_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    subject = data.get("subject") or data.get("a")
    partner = data.get("partner") or data.get("b")
    if subject is None or partner is None:
        raise HTTPException(status_code=422, detail="subject and partner payloads are required")

    normalized: dict[str, Any] = {"subject": subject, "partner": partner}
    for key in ("bodies", "aspects", "orb"):
        if key in data and data[key] is not None:
            normalized[key] = data[key]
    return normalized


@router.post("/aspects")
def api_synastry_aspects(payload: dict[str, Any]) -> dict[str, Any]:
    request = SynastryRequest(**_normalize_synastry_payload(payload))
    aspects = _scan_synastry(request)
    hits: list[dict[str, Any]] = []
    for item in aspects:
        hits.append(
            {
                "direction": "partner→subject",
                "moving": item.moving,
                "target": item.target,
                "aspect": item.aspect,
                "orb": item.orb,
                "lon_moving": item.lon_moving,
                "lon_target": item.lon_target,
                "ts": item.when_iso,
            }
        )

    summary = {
        "method": "synastry_aspects",
        "orb": float(request.orb),
        "bodies": list(request.bodies) if request.bodies else "default",
    }

    return {"count": len(hits), "summary": summary, "hits": hits}


def _body_map(names: Sequence[str] | None) -> dict[str, int]:
    if not names:
        return {name: int(code) for name, code in DEFAULT_BODIES.items()}
    lookup = {name.lower(): (name, int(code)) for name, code in DEFAULT_BODIES.items()}
    resolved: dict[str, int] = {}
    for entry in names:
        key = str(entry).lower()
        if key in lookup:
            canonical, code = lookup[key]
            resolved[canonical] = code
    return resolved
