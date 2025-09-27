
"""Synastry-related API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Sequence

from fastapi import APIRouter

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ...chart.natal import DEFAULT_BODIES
from ...ephemeris.swisseph_adapter import SwissEphemerisAdapter



router = APIRouter()



def _to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class NatalPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ts: datetime = Field(validation_alias=AliasChoices("ts", "utc"))
    lat: float | None = None
    lon: float | None = None

    @field_validator("ts", mode="before")
    @classmethod
    def _validate_ts(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
        if isinstance(value, dict):
            ts = value.get("ts") or value.get("utc")
            if ts:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
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

    subject: NatalPayload = Field(
        ..., validation_alias=AliasChoices("subject", "a")
    )
    partner: NatalPayload = Field(
        ..., validation_alias=AliasChoices("partner", "b")
    )

    bodies: Sequence[str] | None = None
    aspects: Sequence[int] | None = None
    orb: float = Field(default=2.0, ge=0.0)

    model_config = ConfigDict(extra="ignore")


class SynastryResponse(BaseModel):
    count: int
    summary: dict[str, Any]
    hits: list[Hit]


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



@router.post("/aspects")
def api_synastry_aspects(request: SynastryRequest) -> dict[str, Any]:

    aspects = _scan_synastry(request)
    hits = [
        {
            "ts": item.when_iso,
            "moving": item.moving,
            "target": item.target,
            "aspect": item.aspect,
            "orb": item.orb,
            "lon_moving": item.lon_moving,
            "lon_target": item.lon_target,
            "direction": "partner_to_subject",
        }
        for item in aspects
    ]

    summary = {"method": "synastry_aspects", "pairs": len(hits)}
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

