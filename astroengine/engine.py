"""High level transit scanning helpers used by the CLI and unit tests."""

from __future__ import annotations

import datetime as dt

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Mapping, MutableMapping

from .core.engine import get_active_aspect_angles
from .detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from .detectors.common import body_lon, delta_deg, iso_to_jd, jd_to_iso, norm360
from .detectors_aspects import AspectHit, detect_aspects
from .exporters import LegacyTransitEvent
from .providers import get_provider
from .scoring import ScoreInputs, compute_score
from .canonical import BodyPosition
from .chart.natal import NatalChart
from .chart.progressions import ProgressedChart, compute_secondary_progressed_chart
from .chart.directions import DirectedChart, compute_solar_arc_chart
from .chart.composite import CompositeChart

# >>> AUTO-GEN BEGIN: engine-feature-flags v1.0
# Feature flags (default OFF to preserve current behavior)
FEATURE_LUNATIONS = False
FEATURE_ECLIPSES = False
FEATURE_STATIONS = False
FEATURE_PROGRESSIONS = False
FEATURE_DIRECTIONS = False
FEATURE_RETURNS = False
FEATURE_PROFECTIONS = False
# >>> AUTO-GEN END: engine-feature-flags v1.0

__all__ = [
    "events_to_dicts",
    "scan_contacts",
    "get_active_aspect_angles",
    "resolve_provider",
    "fast_scan",
    "ScanConfig",
    "TargetFrameResolver",
]

_BODY_CODE_TO_NAME = {
    0: "sun",
    1: "moon",
    2: "mercury",
    3: "venus",
    4: "mars",
    5: "jupiter",
    6: "saturn",
    7: "uranus",
    8: "neptune",
    9: "pluto",
}


class TargetFrameResolver:
    """Resolve target body positions for alternate reference frames."""

    def __init__(
        self,
        frame: str,
        *,
        natal_chart: NatalChart | None = None,
        composite_chart: CompositeChart | None = None,
        static_positions: Mapping[str, float] | None = None,
    ) -> None:
        self.frame = frame.lower()
        self.natal_chart = natal_chart
        self.composite_chart = composite_chart
        self._static_positions: MutableMapping[str, float] = {
            key.lower(): float(value) % 360.0 for key, value in (static_positions or {}).items()
        }
        self._progressed_cache: MutableMapping[str, ProgressedChart] = {}
        self._directed_cache: MutableMapping[str, DirectedChart] = {}

    @staticmethod
    def _normalize_iso(ts: str) -> str:
        dt_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt_utc = dt_obj.astimezone(timezone.utc) if dt_obj.tzinfo else dt_obj.replace(tzinfo=timezone.utc)
        return dt_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def overrides_target(self) -> bool:
        if self.frame == "natal":
            return bool(self._static_positions) or self.natal_chart is not None
        if self.frame in {"progressed", "directed", "composite"}:
            return True
        return False

    @property
    def static_positions(self) -> Mapping[str, float]:
        return dict(self._static_positions)

    def _available_names(self) -> set[str]:
        names: set[str] = set(self._static_positions.keys())
        if self.natal_chart is not None:
            names.update(self.natal_chart.positions.keys())
        if self.composite_chart is not None:
            names.update(self.composite_chart.positions.keys())
        return names

    def _resolve_body_name(self, body: str) -> str:
        body_lower = body.lower()
        for name in self._available_names():
            if name.lower() == body_lower:
                return name
        return body

    def _natal_body(self, body: str) -> BodyPosition | None:
        if self.natal_chart is None:
            return None
        name = self._resolve_body_name(body)
        return self.natal_chart.positions.get(name)

    def _progressed_for(self, iso_ts: str) -> ProgressedChart:
        key = self._normalize_iso(iso_ts)
        cached = self._progressed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Progressed frame requires a natal chart")
        dt_obj = datetime.fromisoformat(key.replace("Z", "+00:00"))
        progressed = compute_secondary_progressed_chart(self.natal_chart, dt_obj)
        self._progressed_cache[key] = progressed
        return progressed

    def _directed_for(self, iso_ts: str) -> DirectedChart:
        key = self._normalize_iso(iso_ts)
        cached = self._directed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Directed frame requires a natal chart")
        dt_obj = datetime.fromisoformat(key.replace("Z", "+00:00"))
        directed = compute_solar_arc_chart(self.natal_chart, dt_obj)
        self._directed_cache[key] = directed
        return directed

    def _static_position(self, body: str) -> Mapping[str, float] | None:
        body_lower = body.lower()
        if body_lower not in self._static_positions:
            return None
        lon = self._static_positions[body_lower]
        return {"lon": lon, "lat": 0.0, "decl": 0.0, "speed_lon": 0.0}

    def position_dict(self, iso_ts: str, body: str) -> Mapping[str, float]:
        frame = self.frame
        if frame == "natal":
            static = self._static_position(body)
            if static is not None:
                return static
            natal = self._natal_body(body)
            if natal is None:
                raise KeyError(f"Body '{body}' not present in natal chart")
            return {
                "lon": natal.longitude % 360.0,
                "lat": natal.latitude,
                "decl": natal.declination,
                "speed_lon": natal.speed_longitude,
            }

        if frame == "progressed":
            progressed = self._progressed_for(iso_ts).chart
            name = self._resolve_body_name(body)
            pos = progressed.positions.get(name)
            if pos is None:
                raise KeyError(f"Body '{body}' not present in progressed chart")
            return {
                "lon": pos.longitude % 360.0,
                "lat": pos.latitude,
                "decl": pos.declination,
                "speed_lon": pos.speed_longitude,
            }

        if frame == "directed":
            directed = self._directed_for(iso_ts)
            name = self._resolve_body_name(body)
            lon = directed.positions.get(name)
            if lon is None:
                raise KeyError(f"Body '{body}' not present in directed chart")
            natal = self._natal_body(body)
            lat = natal.latitude if natal is not None else 0.0
            decl = natal.declination if natal is not None else 0.0
            return {"lon": lon % 360.0, "lat": lat, "decl": decl, "speed_lon": 0.0}

        if frame == "composite":
            if self.composite_chart is None:
                raise ValueError("Composite frame requires a composite chart")
            name = self._resolve_body_name(body)
            pos = self.composite_chart.positions.get(name)
            if pos is None:
                raise KeyError(f"Body '{body}' not present in composite chart")
            return {
                "lon": pos.midpoint_longitude % 360.0,
                "lat": pos.latitude,
                "decl": pos.declination,
                "speed_lon": pos.speed_longitude,
            }

        raise ValueError(f"Unsupported target frame '{self.frame}'")


class FrameAwareProvider:
    """Provider wrapper that injects alternate frame target positions."""

    def __init__(self, provider, target: str, resolver: TargetFrameResolver) -> None:
        self._provider = provider
        self._target = target.lower()
        self._resolver = resolver

    def positions_ecliptic(self, iso_utc: str, bodies: Iterable[str]):
        base = dict(self._provider.positions_ecliptic(iso_utc, bodies))
        if self._resolver.overrides_target():
            for name in bodies:
                if name.lower() == self._target:
                    base[name] = dict(self._resolver.position_dict(iso_utc, name))
        return base

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        if self._resolver.overrides_target() and body.lower() == self._target:
            data = self._resolver.position_dict(ts_utc, body)
            return BodyPosition(
                lon=float(data["lon"]),
                lat=float(data.get("lat", 0.0)),
                dec=float(data.get("decl", 0.0)),
                speed_lon=float(data.get("speed_lon", 0.0)),
            )
        return self._provider.position(body, ts_utc)

    def __getattr__(self, item):  # pragma: no cover - passthrough
        return getattr(self._provider, item)


@dataclass(slots=True)
class ScanConfig:
    body: int
    natal_lon_deg: float
    aspect_angle_deg: float
    orb_deg: float
    tick_minutes: int = 60


def events_to_dicts(events: Iterable[LegacyTransitEvent]) -> List[dict]:
    """Convert :class:`LegacyTransitEvent` objects into JSON-friendly dictionaries."""

    return [event.to_dict() for event in events]


def _iso_ticks(start_iso: str, end_iso: str, *, step_minutes: int) -> Iterable[str]:
    """Yield ISO-8601 timestamps separated by ``step_minutes`` minutes."""

    start_dt = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    end_dt = dt.datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    step = dt.timedelta(minutes=step_minutes)
    current = start_dt
    while current <= end_dt:
        yield current.replace(tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
        current += step


def _score_from_hit(
    kind: str,
    orb_abs: float,
    orb_allow: float,
    moving: str,
    target: str,
    phase: str,
) -> float:
    """Use the scoring policy to assign a score for a detected contact."""

    score_inputs = ScoreInputs(
        kind=kind,
        orb_abs_deg=float(orb_abs),
        orb_allow_deg=float(orb_allow),
        moving=moving,
        target=target,
        applying_or_separating=phase,
    )
    return compute_score(score_inputs).score


def _event_from_decl(hit: CoarseHit, *, orb_allow: float) -> LegacyTransitEvent:
    score = _score_from_hit(
        hit.kind,
        abs(hit.delta),
        orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return LegacyTransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=abs(hit.delta),
        orb_allow=float(orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata={
            "dec_moving": hit.dec_moving,
            "dec_target": hit.dec_target,
        },
    )


def _event_from_aspect(hit: AspectHit) -> LegacyTransitEvent:
    score = _score_from_hit(
        hit.kind,
        hit.orb_abs,
        hit.orb_allow,
        hit.moving,
        hit.target,
        hit.applying_or_separating,
    )
    return LegacyTransitEvent(
        kind=hit.kind,
        timestamp=hit.when_iso,
        moving=hit.moving,
        target=hit.target,
        orb_abs=float(hit.orb_abs),
        orb_allow=float(hit.orb_allow),
        applying_or_separating=hit.applying_or_separating,
        score=score,
        lon_moving=hit.lon_moving,
        lon_target=hit.lon_target,
        metadata={"angle_deg": hit.angle_deg},
    )


def scan_contacts(
    start_iso: str,
    end_iso: str,
    moving: str,
    target: str,
    provider_name: str = "swiss",
    *,
    decl_parallel_orb: float = 0.5,
    decl_contra_orb: float = 0.5,
    antiscia_orb: float = 2.0,
    contra_antiscia_orb: float = 2.0,
    step_minutes: int = 60,
    aspects_policy_path: str | None = None,
    provider: object | None = None,
    target_frame: str = "transit",
    target_resolver: TargetFrameResolver | None = None,
) -> List[LegacyTransitEvent]:
    """Scan for declination, antiscia, and aspect contacts between two bodies."""

    base_provider = provider or get_provider(provider_name)
    frame = (target_frame or "transit").lower()
    resolver = target_resolver
    if resolver is not None and frame != "transit" and resolver.frame != frame:
        resolver = TargetFrameResolver(
            frame,
            natal_chart=target_resolver.natal_chart,
            composite_chart=target_resolver.composite_chart,
            static_positions=target_resolver.static_positions,
        )
    if resolver is not None and resolver.overrides_target():
        provider_obj = FrameAwareProvider(base_provider, target, resolver)
    else:
        provider_obj = base_provider
    ticks = list(_iso_ticks(start_iso, end_iso, step_minutes=step_minutes))

    events: List[LegacyTransitEvent] = []

    for hit in detect_decl_contacts(
        provider_obj,
        ticks,
        moving,
        target,
        decl_parallel_orb,
        decl_contra_orb,
    ):
        allow = decl_parallel_orb if hit.kind == "decl_parallel" else decl_contra_orb
        events.append(_event_from_decl(hit, orb_allow=allow))

    for hit in detect_antiscia_contacts(
        provider_obj,
        ticks,
        moving,
        target,
        antiscia_orb,
        contra_antiscia_orb,
    ):
        allow = antiscia_orb if hit.kind == "antiscia" else contra_antiscia_orb
        events.append(_event_from_decl(hit, orb_allow=allow))

    for aspect_hit in detect_aspects(
        provider_obj,
        ticks,
        moving,
        target,
        policy_path=aspects_policy_path,
    ):
        events.append(_event_from_aspect(aspect_hit))

    events.sort(key=lambda event: (event.timestamp, -event.score))
    return events


def resolve_provider(name: str | None) -> object:
    """Compatibility shim used by external callers."""

    return get_provider(name or "swiss")


def _datetime_to_jd(moment: datetime) -> float:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    else:
        moment = moment.astimezone(timezone.utc)
    iso = moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return iso_to_jd(iso)


def fast_scan(start: datetime, end: datetime, config: ScanConfig) -> List[dict]:
    """Lightweight aspect scanner using Swiss Ephemeris positions."""

    body_name = _BODY_CODE_TO_NAME.get(config.body)
    if body_name is None:
        raise ValueError(f"Unsupported body code: {config.body}")

    start_jd = _datetime_to_jd(start)
    end_jd = _datetime_to_jd(end)
    if end_jd <= start_jd:
        return []

    step_days = config.tick_minutes / (24.0 * 60.0)
    target_lon = norm360(config.natal_lon_deg + config.aspect_angle_deg)

    hits: List[dict] = []
    current = start_jd
    while current <= end_jd:
        lon = body_lon(current, body_name)
        delta = delta_deg(lon, target_lon)
        if abs(delta) <= config.orb_deg:
            hits.append(
                {
                    "timestamp": jd_to_iso(current),
                    "body": body_name,
                    "longitude": lon,
                    "delta": delta,
                }
            )
        current += step_days
    return hits
