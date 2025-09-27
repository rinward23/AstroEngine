"""Synastry-related API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Mapping
from typing import Any, Sequence



from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ...chart.natal import DEFAULT_BODIES
from ...core.aspects_plus.harmonics import BASE_ASPECTS
from ...synastry.orchestrator import SynHit, compute_synastry




router = APIRouter()

def _to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


class NatalPayload(BaseModel):

    """Minimal payload describing a natal chart for synastry scans."""

    model_config = ConfigDict(extra="ignore")

    ts: datetime = Field(validation_alias=AliasChoices("ts", "datetime"))
    lat: float
    lon: float

    @field_validator("ts", mode="before")
    def _coerce_timestamp(cls, value: Any) -> datetime:

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

    @field_validator("lat", "lon", mode="before")
    def _coerce_float(cls, value: Any) -> float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return float(str(value))

    def as_payload(self) -> dict[str, Any]:
        return {"ts": _to_iso(self.ts), "lat": float(self.lat), "lon": float(self.lon)}


class SynastryRequest(BaseModel):

    """Request model for synastry aspect computations."""

    subject: NatalPayload
    partner: NatalPayload

    bodies: Sequence[str] | None = None
    aspects: Sequence[Any] | None = None
    orb: float = Field(default=2.0, ge=0.0)


    def resolved_aspects(self) -> list[int]:
        if not self.aspects:
            return [0, 60, 90, 120, 180]
        resolved: list[int] = []
        for entry in self.aspects:
            if isinstance(entry, (int, float)) and not isinstance(entry, bool):
                resolved.append(int(round(float(entry))))
                continue
            key = str(entry).strip().lower()
            angle = BASE_ASPECTS.get(key)
            if angle is not None:
                resolved.append(int(round(float(angle))))
        cleaned = sorted({int(value) for value in resolved})
        return cleaned or [0, 60, 90, 120, 180]

    def resolved_bodies(self) -> list[str] | None:
        if self.bodies is None:
            return None
        lookup = {name.lower(): name for name in DEFAULT_BODIES}
        resolved: list[str] = []
        for entry in self.bodies:
            key = str(entry).strip().lower()
            canonical = lookup.get(key)
            if canonical and canonical not in resolved:
                resolved.append(canonical)
        return resolved or None


class SynastryHitDTO(BaseModel):
    direction: str

    moving: str
    target: str
    aspect: float
    orb: float
    score: float | None = None
    domains: dict[str, float] | None = None


class SynastrySummary(BaseModel):
    method: str = "synastry_aspects"
    count_by_direction: dict[str, int]
    orb: float
    aspects: list[float]
    bodies: list[str] | None = None


class SynastryResponse(BaseModel):
    count: int
    summary: SynastrySummary
    hits: list[SynastryHitDTO]



def _convert_hit(hit: SynHit) -> SynastryHitDTO:
    return SynastryHitDTO(
        direction=hit.direction,
        moving=hit.moving,
        target=hit.target,
        aspect=float(hit.angle_deg),
        orb=float(hit.orb_abs),
        score=float(hit.score) if hit.score is not None else None,
        domains=hit.domains,
    )


@router.post("/aspects", response_model=SynastryResponse)
def api_synastry_aspects(request: SynastryRequest) -> SynastryResponse:
    aspects = request.resolved_aspects()
    orb = float(request.orb)
    body_list = request.resolved_bodies()
    hits = compute_synastry(
        subject=request.subject.as_payload(),
        partner=request.partner.as_payload(),
        aspects=aspects,
        orb_deg=orb,
        subject_bodies=body_list,
        partner_bodies=body_list,
    )

    dto_hits = [_convert_hit(hit) for hit in hits]
    aspect_summary = sorted({float(angle) for angle in aspects})
    summary = SynastrySummary(
        count_by_direction={
            "A->B": sum(1 for h in hits if h.direction == "A->B"),
            "B->A": sum(1 for h in hits if h.direction == "B->A"),
        },
        orb=orb,
        aspects=aspect_summary,
        bodies=body_list,
    )

    return SynastryResponse(count=len(dto_hits), summary=summary, hits=dto_hits)


