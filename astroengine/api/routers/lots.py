"""FastAPI router for Arabic Lots compilation and evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from ...chart.natal import ChartLocation
from ...engine.lots import (
    ChartContext,
    LotsProfile,
    aspects_to_lots,
    compile_program,
    evaluate,
    list_builtin_profiles,
    load_custom_profiles,
    parse_lot_defs,
    save_custom_profile,
)
from ...engine.lots.dsl import CompiledProgram
from ...engine.lots.events import scan_lot_events
from ...ephemeris.adapter import EphemerisAdapter
from ...scoring.policy import load_orb_policy
from ...web.responses import conditional_json_response

router = APIRouter(prefix="/lots", tags=["lots"])


class LotCompileRequest(BaseModel):
    source: str = Field(..., description="DSL text defining lots")


class LotCompileResponse(BaseModel):
    order: list[str]
    dependencies: dict[str, list[str]]


class ChartPoint(BaseModel):
    value: float


class ChartInput(BaseModel):
    positions: dict[str, float]
    angles: dict[str, float] | None = None
    is_day: bool | None = None
    sun_altitude: float | None = None
    moment: UtcDateTime | None = None
    latitude: float | None = None
    longitude: float | None = None
    zodiac: str | None = None
    ayanamsha: str | None = None
    house_system: str | None = None


class LotComputeRequest(BaseModel):
    source: str | None = None
    profile: str | None = Field(
        None, description="Built-in tradition to load when source omitted"
    )
    chart: ChartInput


class LotComputeResponse(BaseModel):
    lots: dict[str, float]
    metadata: dict[str, Any]


class LotPresetPayload(BaseModel):
    profile_id: str
    name: str
    description: str | None = None
    source: str
    zodiac: str = "tropical"
    house_system: str = "Placidus"
    policy_id: str = "standard"
    ayanamsha: str | None = None
    tradition: str | None = None
    source_refs: dict[str, str] | None = None


class AspectScanRequest(BaseModel):
    lots: dict[str, float]
    bodies: dict[str, float]
    harmonics: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 6])
    policy: dict[str, Any] | None = None


class AspectScanResponse(BaseModel):
    hits: list[dict[str, Any]]


class EventScanRequest(BaseModel):
    lot_name: str
    lot_longitude: float
    bodies: list[str]
    start: UtcDateTime
    end: UtcDateTime
    harmonics: list[int] = Field(default_factory=lambda: [1, 2])
    policy: dict[str, Any] | None = None
    step_hours: float | None = None


class EventScanResponse(BaseModel):
    events: list[dict[str, Any]]


def _resolve_program(source: str | None, profile: str | None) -> CompiledProgram:
    if source:
        program = parse_lot_defs(source)
        return compile_program(program)
    if profile:
        builtins = {prof.tradition: prof for prof in list_builtin_profiles() if prof.tradition}
        custom = load_custom_profiles()
        if profile in builtins:
            return builtins[profile].compile()
        if profile in custom:
            return custom[profile].compile()
        raise HTTPException(status_code=404, detail="Unknown profile")
    raise HTTPException(status_code=400, detail="Either source or profile must be provided")


def _chart_context(payload: ChartInput) -> ChartContext:
    location = None
    if payload.latitude is not None and payload.longitude is not None:
        location = ChartLocation(payload.latitude, payload.longitude)
    return ChartContext(
        moment=payload.moment,
        location=location,
        positions=payload.positions,
        angles=payload.angles or {},
        is_day_override=payload.is_day,
        sun_altitude=payload.sun_altitude,
        zodiac=payload.zodiac or "tropical",
        ayanamsha=payload.ayanamsha,
        house_system=payload.house_system,
    )


@router.post("/compile", response_model=LotCompileResponse)
def compile_lots(request: LotCompileRequest) -> LotCompileResponse:
    program = parse_lot_defs(request.source)
    compiled = compile_program(program)
    dependencies = {name: sorted(list(refs)) for name, refs in compiled.dependencies.items()}
    return LotCompileResponse(order=list(compiled.order), dependencies=dependencies)


@router.post("/compute", response_model=LotComputeResponse)
def compute_lots(request: LotComputeRequest) -> LotComputeResponse:
    compiled = _resolve_program(request.source, request.profile)
    chart_ctx = _chart_context(request.chart)
    values = evaluate(compiled, chart_ctx)
    metadata = {
        "zodiac": chart_ctx.zodiac,
        "ayanamsha": chart_ctx.ayanamsha,
        "house_system": chart_ctx.house_system,
    }
    return LotComputeResponse(lots=values, metadata=metadata)


@router.get("/presets", response_model=list[dict[str, Any]])
def list_presets(
    if_none_match: str | None = Header(default=None, alias="If-None-Match")
) -> Response:
    presets = [
        {
            "profile_id": profile.profile_id,
            "name": profile.name,
            "description": profile.description,
            "tradition": profile.tradition,
            "zodiac": profile.zodiac,
            "house_system": profile.house_system,
            "expr_text": profile.expr_text,
            "source_refs": profile.source_refs,
        }
        for profile in list_builtin_profiles()
    ]
    custom = load_custom_profiles()
    for profile in custom.values():
        presets.append(
            {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "description": profile.description,
                "tradition": profile.tradition,
                "zodiac": profile.zodiac,
                "house_system": profile.house_system,
                "expr_text": profile.expr_text,
                "source_refs": profile.source_refs,
            }
        )
    return conditional_json_response(
        presets,
        if_none_match=if_none_match,
        max_age=86400,
    )


@router.post("/presets", response_model=dict)
def save_preset(payload: LotPresetPayload) -> dict[str, Any]:
    profile = LotsProfile(
        profile_id=payload.profile_id,
        name=payload.name,
        description=payload.description or "",
        zodiac=payload.zodiac,
        house_system=payload.house_system,
        policy_id=payload.policy_id,
        expr_text=payload.source,
        source_refs=payload.source_refs or {},
        ayanamsha=payload.ayanamsha,
        tradition=payload.tradition,
    )
    save_custom_profile(profile)
    return {"status": "ok", "profile_id": profile.profile_id}


@router.post("/aspects", response_model=AspectScanResponse)
def scan_aspects(request: AspectScanRequest) -> AspectScanResponse:
    policy = load_orb_policy(overrides=request.policy) if request.policy else load_orb_policy()
    hits = aspects_to_lots(request.lots, request.bodies, policy, request.harmonics)
    return AspectScanResponse(
        hits=[
            {
                "body": hit.body,
                "lot": hit.lot,
                "angle": hit.angle,
                "orb": hit.orb,
                "separation": hit.separation,
                "severity": hit.severity,
                "applying": hit.applying,
            }
            for hit in hits
        ]
    )


from astroengine.ephemeris.swe import has_swe, swe


if has_swe():
    swe_module = swe()
else:
    swe_module = None

_BODY_CODES = {
    "sun": getattr(swe_module, "SUN", None) if swe_module is not None else None,
    "moon": getattr(swe_module, "MOON", None) if swe_module is not None else None,
    "mercury": getattr(swe_module, "MERCURY", None) if swe_module is not None else None,
    "venus": getattr(swe_module, "VENUS", None) if swe_module is not None else None,
    "mars": getattr(swe_module, "MARS", None) if swe_module is not None else None,
    "jupiter": getattr(swe_module, "JUPITER", None) if swe_module is not None else None,
    "saturn": getattr(swe_module, "SATURN", None) if swe_module is not None else None,
    "uranus": getattr(swe_module, "URANUS", None) if swe_module is not None else None,
    "neptune": getattr(swe_module, "NEPTUNE", None) if swe_module is not None else None,
    "pluto": getattr(swe_module, "PLUTO", None) if swe_module is not None else None,
}


class _SwissEphemerisWrapper:
    def __init__(self) -> None:
        if swe is None:
            raise HTTPException(
                status_code=503,
                detail="Swiss Ephemeris not available; install astroengine[ephem]",
            )
        self._adapter = EphemerisAdapter()

    def sample(self, body: str, moment: datetime):
        code = _BODY_CODES.get(body.lower())
        if code is None:
            raise HTTPException(status_code=404, detail=f"Unsupported body {body}")
        return self._adapter.sample(code, moment)


@router.post("/events", response_model=EventScanResponse)
def scan_events(request: EventScanRequest) -> EventScanResponse:
    policy = load_orb_policy(overrides=request.policy) if request.policy else load_orb_policy()
    adapter = _SwissEphemerisWrapper()
    events = scan_lot_events(
        adapter,
        request.lot_longitude,
        request.bodies,
        request.start,
        request.end,
        policy,
        request.harmonics,
        step_hours=request.step_hours or 12.0,
        lot_name=request.lot_name,
    )
    return EventScanResponse(
        events=[
            {
                "lot": event.lot,
                "body": event.body,
                "timestamp": event.timestamp.isoformat(),
                "angle": event.angle,
                "orb": event.orb,
                "severity": event.severity,
                "applying": event.applying,
                "metadata": dict(event.metadata),
            }
            for event in events
        ]
    )
