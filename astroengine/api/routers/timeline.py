"""Timeline API router exposing lunations, eclipses, stations, and void-of-course data."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from typing import Any, Iterable, Literal

from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...analysis import (
    VoidOfCourseEvent,
    find_eclipses,
    find_lunations,
    find_stations,
    void_of_course_moon,
)
from ...config import default_settings, load_settings
from ...events import EclipseEvent, LunationEvent, StationEvent
from .._time import ensure_utc_datetime

router = APIRouter()

_ALLOWED_TYPES: dict[str, str] = {
    "lunations": "lunations",
    "lunation": "lunations",
    "eclipses": "eclipses",
    "eclipse": "eclipses",
    "stations": "stations",
    "station": "stations",
    "void_of_course": "void_of_course",
    "void-of-course": "void_of_course",
    "voc": "void_of_course",
}
_DEFAULT_STATION_BODIES: tuple[str, ...] = (
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
)


class TimelineEventModel(BaseModel):
    type: Literal["lunations", "eclipses", "stations", "void_of_course"]
    ts: str
    jd: float
    summary: str
    end_ts: str | None = None
    end_jd: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    events: list[TimelineEventModel]


@lru_cache(maxsize=1)
def _get_settings():
    try:
        return load_settings()
    except Exception:
        return default_settings()


def _serialize_lunations(events: Iterable[LunationEvent]) -> list[TimelineEventModel]:
    payload: list[TimelineEventModel] = []
    for event in events:
        phase_title = event.phase.replace("_", " ").title()
        summary = f"{phase_title} Moon"
        payload.append(
            TimelineEventModel(
                type="lunations",
                ts=event.ts,
                jd=event.jd,
                summary=summary,
                details={
                    "phase": event.phase,
                    "sun_longitude": event.sun_longitude,
                    "moon_longitude": event.moon_longitude,
                },
            )
        )
    return payload


def _serialize_eclipses(events: Iterable[EclipseEvent]) -> list[TimelineEventModel]:
    payload: list[TimelineEventModel] = []
    for event in events:
        eclipse_kind = event.eclipse_type.title()
        phase_title = event.phase.replace("_", " ").title()
        summary = f"{eclipse_kind} Eclipse ({phase_title})"
        payload.append(
            TimelineEventModel(
                type="eclipses",
                ts=event.ts,
                jd=event.jd,
                summary=summary,
                details={
                    "eclipse_type": event.eclipse_type,
                    "phase": event.phase,
                    "sun_longitude": event.sun_longitude,
                    "moon_longitude": event.moon_longitude,
                    "moon_latitude": event.moon_latitude,
                    "is_visible": event.is_visible,
                },
            )
        )
    return payload


def _serialize_stations(events: Iterable[StationEvent]) -> list[TimelineEventModel]:
    payload: list[TimelineEventModel] = []
    for event in events:
        if event.station_type:
            summary = f"{event.body} station {event.station_type}"
        else:
            summary = f"{event.body} station"
        payload.append(
            TimelineEventModel(
                type="stations",
                ts=event.ts,
                jd=event.jd,
                summary=summary,
                details={
                    "body": event.body,
                    "motion": event.motion,
                    "longitude": event.longitude,
                    "speed_longitude": event.speed_longitude,
                    "station_type": event.station_type,
                },
            )
        )
    return payload


def _serialize_voc(event: VoidOfCourseEvent) -> TimelineEventModel:
    details = asdict(event)
    details.pop("ts", None)
    details.pop("jd", None)
    return TimelineEventModel(
        type="void_of_course",
        ts=event.ts,
        jd=event.jd,
        summary=f"Void-of-course Moon in {event.moon_sign}",
        end_ts=event.end_ts,
        end_jd=event.end_jd,
        details=details,
    )


@router.get("/timeline", response_model=TimelineResponse)
def timeline(
    from_: str = Query(..., alias="from", description="Start of the search window (UTC RFC3339)"),
    to: str = Query(..., description="End of the search window (UTC RFC3339)"),
    types: str | None = Query(
        None,
        description="Comma separated list of event types: lunations,eclipses,stations,void_of_course",
    ),
    bodies: str | None = Query(None, description="Optional comma separated list of station bodies"),
    sign_orb: float = Query(0.0, ge=0.0, le=5.0, description="Orb in degrees when extending void-of-course past sign ingress"),
) -> TimelineResponse:
    settings = _get_settings()
    if not settings.timeline_ui:
        raise HTTPException(status_code=404, detail="Timeline endpoint disabled by configuration")

    start_dt = ensure_utc_datetime(from_)
    end_dt = ensure_utc_datetime(to)
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="'to' must be after 'from'")

    swiss_caps = getattr(settings, "swiss_caps", None)
    min_year = getattr(swiss_caps, "min_year", 1800)
    max_year = getattr(swiss_caps, "max_year", 2200)
    min_boundary = datetime(int(min_year), 1, 1, tzinfo=UTC)
    max_boundary = datetime(int(max_year) + 1, 1, 1, tzinfo=UTC)
    if start_dt < min_boundary or end_dt >= max_boundary:
        detail = (
            "Timeline window exceeds Swiss Ephemeris coverage "
            f"({int(min_year)}–{int(max_year)}). Adjust the requested dates or install "
            "additional Swiss ephemeris files and update settings.swiss_caps.*."
        )
        raise HTTPException(status_code=400, detail=detail)

    requested: set[str]
    if types:
        requested = set()
        for token in types.split(","):
            key = token.strip().lower()
            if not key:
                continue
            try:
                resolved = _ALLOWED_TYPES[key]
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=f"Unknown timeline type '{token}'") from exc
            requested.add(resolved)
        if not requested:
            requested = set(_ALLOWED_TYPES.values())
    else:
        requested = {"lunations", "eclipses", "stations"}

    events: list[TimelineEventModel] = []

    if "lunations" in requested:
        events.extend(_serialize_lunations(find_lunations(start_dt, end_dt)))

    if "eclipses" in requested:
        if settings.eclipse_finder:
            try:
                events.extend(_serialize_eclipses(find_eclipses(start_dt, end_dt)))
            except Exception as exc:  # pragma: no cover - runtime-only fallback
                raise HTTPException(status_code=503, detail=str(exc)) from exc
        else:
            requested.discard("eclipses")

    if "stations" in requested:
        if not settings.stations:
            requested.discard("stations")
        else:
            body_list = _DEFAULT_STATION_BODIES
            if bodies:
                parsed = [token.strip() for token in bodies.split(",") if token.strip()]
                if parsed:
                    body_list = tuple(parsed)
            for body in body_list:
                events.extend(_serialize_stations(find_stations(body, start_dt, end_dt)))

    if "void_of_course" in requested:
        try:
            voc_event = void_of_course_moon(start_dt, sign_orb=sign_orb)
        except Exception as exc:  # pragma: no cover - runtime-only fallback
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if voc_event.end_jd >= voc_event.jd:
            events.append(_serialize_voc(voc_event))

    events.sort(key=lambda item: (item.ts, item.type))
    return TimelineResponse(events=events)
