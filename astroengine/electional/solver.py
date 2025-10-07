"""Constraint-based electional search utilities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from ..astro.declination import DEFAULT_ANTISCIA_AXIS
from ..chart.config import ChartConfig
from ..chart.natal import DEFAULT_BODIES
from ..core.bodies import canonical_name
from ..detectors import CoarseHit, detect_antiscia_contacts, detect_decl_contacts
from ..detectors_aspects import AspectHit, detect_aspects
from ..ephemeris import BodyPosition, SwissEphemerisAdapter
from ..utils.angles import delta_angle, norm360


@dataclass(slots=True)
class ElectionalConstraintEvaluation:
    """Outcome of a single constraint evaluation."""

    constraint: str
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None


@dataclass(slots=True)
class ElectionalCandidate:
    """Candidate instant satisfying all configured constraints."""

    ts: datetime
    score: float
    evaluations: Sequence[ElectionalConstraintEvaluation]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "score": self.score,
            "evaluations": [
                {
                    "constraint": ev.constraint,
                    "passed": ev.passed,
                    "detail": dict(ev.detail),
                    **({"reason": ev.reason} if ev.reason else {}),
                }
                for ev in self.evaluations
            ],
        }


@dataclass(slots=True)
class ElectionalSearchParams:
    """Normalized parameters describing a constraint search."""

    start: datetime
    end: datetime
    step_minutes: int
    constraints: Sequence[Mapping[str, Any]]
    latitude: float
    longitude: float
    limit: int | None = None


@dataclass(slots=True)
class SampleContext:
    """Positions and axes for a single timestamp."""

    ts: datetime
    iso: str
    positions: Mapping[str, BodyPosition]
    axes: Mapping[str, float]
    _provider: SingleSampleProvider | None = None

    @property
    def provider(self) -> SingleSampleProvider:
        if self._provider is None:
            self._provider = SingleSampleProvider(self)
        return self._provider


class ElectionalSampleProvider(Protocol):
    """Protocol returning :class:`SampleContext` for a timestamp."""

    def context(self, ts: datetime) -> SampleContext:
        ...


class SingleSampleProvider:
    """Adapter exposing :class:`SampleContext` data to detector helpers."""

    def __init__(self, ctx: SampleContext) -> None:
        self._ctx = ctx

    def positions_ecliptic(self, iso_utc: str, bodies: Iterable[str]) -> dict[str, dict[str, float]]:
        if iso_utc != self._ctx.iso:
            raise ValueError("Sample provider only supports the bound timestamp")
        out: dict[str, dict[str, float]] = {}
        for name in bodies:
            if name in self._ctx.positions:
                pos = self._ctx.positions[name]
                out[name] = {
                    "lon": float(pos.longitude),
                    "lat": float(pos.latitude),
                    "declination": float(pos.declination),
                    "speed_lon": float(pos.speed_longitude),
                }
                continue
            lowered = name.lower()
            if lowered in self._ctx.axes:
                lon = float(self._ctx.axes[lowered]) % 360.0
                out[name] = {
                    "lon": lon,
                    "declination": 0.0,
                    "speed_lon": 0.0,
                }
        return out


class SwissElectionalProvider:
    """Swiss Ephemeris-backed provider for electional scans."""

    def __init__(
        self,
        *,
        start: datetime,
        end: datetime,
        latitude: float,
        longitude: float,
        bodies: Sequence[str],
        chart_config: ChartConfig | None = None,
    ) -> None:
        self._start = start
        self._end = end
        self._lat = float(latitude)
        self._lon = float(longitude)
        self._chart = chart_config or ChartConfig()
        self._adapter = SwissEphemerisAdapter.from_chart_config(self._chart)
        self._body_codes: dict[str, int] = {}
        for name in bodies:
            if name not in DEFAULT_BODIES:
                raise ValueError(f"Unsupported body for electional search: {name}")
            self._body_codes[name] = DEFAULT_BODIES[name]

    def context(self, ts: datetime) -> SampleContext:
        if ts < self._start or ts > self._end:
            raise ValueError("timestamp outside configured scan window")
        jd = self._adapter.julian_day(ts)
        positions: dict[str, BodyPosition] = self._adapter.compute_bodies_many(
            jd, self._body_codes
        )
        houses = self._adapter.houses(jd, self._lat, self._lon, system=self._chart.house_system)
        asc = norm360(houses.ascendant)
        mc = norm360(houses.midheaven)
        axes = {
            "asc": asc,
            "mc": mc,
            "desc": norm360(asc + 180.0),
            "ic": norm360(mc + 180.0),
        }
        iso = ts.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return SampleContext(ts=ts, iso=iso, positions=positions, axes=axes)


class Constraint(Protocol):
    """Runtime constraint contract."""

    def required_bodies(self) -> Sequence[str]:
        ...

    def required_axes(self) -> Sequence[str]:
        ...

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        ...


_ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "square": 90.0,
    "trine": 120.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisquare": 45.0,
    "sesquisquare": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}

_MAJOR_ASPECTS = ("conjunction", "sextile", "square", "trine", "opposition")

_AXES_ALIASES: dict[str, str] = {
    "ascendant": "asc",
    "asc": "asc",
    "dsc": "desc",
    "desc": "desc",
    "dc": "desc",
    "mc": "mc",
    "midheaven": "mc",
    "ic": "ic",
    "imum_coeli": "ic",
    "imumcoeli": "ic",
}

_CANONICAL_TO_DISPLAY: dict[str, str] = {
    canonical_name(name): name for name in DEFAULT_BODIES
}


def _resolve_body(name: str) -> str:
    canonical = canonical_name(name)
    display = _CANONICAL_TO_DISPLAY.get(canonical)
    if not display:
        raise ValueError(f"Unsupported body '{name}'")
    return display


def _resolve_axis(name: str) -> str:
    key = name.lower().strip()
    if key in _AXES_ALIASES:
        return _AXES_ALIASES[key]
    raise ValueError(f"Unsupported chart angle '{name}'")


def _resolve_aspect(name: str) -> tuple[str, float]:
    key = name.lower().strip()
    if key not in _ASPECT_ANGLES:
        raise ValueError(f"Unknown aspect type '{name}'")
    return key, _ASPECT_ANGLES[key]


def _minute_delta(step_minutes: int) -> timedelta:
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")
    return timedelta(minutes=int(step_minutes))


class AspectConstraint:
    def __init__(
        self,
        *,
        body: str,
        target: str,
        aspect: str,
        angle: float,
        max_orb: float | None = None,
        target_is_axis: bool = False,
    ) -> None:
        self.body = body
        self.target = target
        self.aspect = aspect
        self.angle = angle
        self.max_orb = float(max_orb) if max_orb is not None else None
        self.target_is_axis = target_is_axis

    def required_bodies(self) -> Sequence[str]:
        names = [self.body]
        if not self.target_is_axis:
            names.append(self.target)
        return names

    def required_axes(self) -> Sequence[str]:
        return [self.target] if self.target_is_axis else []

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        detail: dict[str, Any] = {
            "body": self.body,
            "target": self.target,
            "aspect": self.aspect,
        }
        if self.body not in ctx.positions:
            return ElectionalConstraintEvaluation(
                "aspect",
                False,
                detail,
                reason="body_position_missing",
            )
        if self.target_is_axis:
            target_key = self.target
            axes = ctx.axes
            if target_key not in axes:
                return ElectionalConstraintEvaluation(
                    "aspect",
                    False,
                    detail,
                    reason="axis_missing",
                )
            lon_body = float(ctx.positions[self.body].longitude)
            lon_target = float(axes[target_key])
            separation = norm360(lon_body - lon_target)
            delta = abs(delta_angle(separation, self.angle))
            detail.update({"orb": delta, "angle": self.angle})
            allow = self.max_orb if self.max_orb is not None else 3.0
            passed = delta <= allow
            detail["orb_allow"] = allow
            strength = max(0.0, 1.0 - delta / allow) if allow > 0 else 0.0
            detail["strength"] = strength if passed else 0.0
            return ElectionalConstraintEvaluation(
                "aspect",
                passed,
                detail,
                None if passed else "orb_exceeded",
            )

        hits = detect_aspects(
            ctx.provider,
            [ctx.iso],
            self.body,
            self.target,
        )
        chosen: AspectHit | None = None
        for hit in hits:
            if getattr(hit, "kind", "").endswith(self.aspect):
                orb = float(getattr(hit, "orb_abs", 0.0))
                if self.max_orb is None or orb <= self.max_orb + 1e-9:
                    chosen = hit
                    break
        if chosen is None:
            detail["orb_allow"] = self.max_orb
            return ElectionalConstraintEvaluation(
                "aspect",
                False,
                detail,
                reason="aspect_not_in_orb",
            )
        orb = float(getattr(chosen, "orb_abs", 0.0))
        allow = float(self.max_orb) if self.max_orb is not None else float(
            getattr(chosen, "orb_allow", orb)
        )
        strength = 0.0
        if allow > 0:
            strength = max(0.0, 1.0 - orb / allow)
        detail.update(
            {
                "orb": orb,
                "orb_allow": allow,
                "angle": float(getattr(chosen, "angle_deg", self.angle)),
                "strength": strength,
                "delta": float(getattr(chosen, "offset_deg", 0.0)),
                "motion": getattr(chosen, "applying_or_separating", None),
            }
        )
        return ElectionalConstraintEvaluation("aspect", True, detail)


class MoonVoidConstraint:
    def __init__(
        self,
        *,
        require_void: bool,
        bodies: Sequence[str],
        max_orb: float,
    ) -> None:
        self.require_void = require_void
        self.bodies = tuple(dict.fromkeys(bodies))
        self.max_orb = max(0.0, float(max_orb))

    def required_bodies(self) -> Sequence[str]:
        names = ["Moon"]
        names.extend(body for body in self.bodies if body != "Moon")
        return names

    def required_axes(self) -> Sequence[str]:
        return []

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        detail: dict[str, Any] = {
            "require_void": self.require_void,
            "max_orb": self.max_orb,
        }
        moon = ctx.positions.get("Moon")
        if moon is None:
            return ElectionalConstraintEvaluation(
                "moon",
                False,
                detail,
                reason="moon_position_missing",
            )
        moon_lon = float(moon.longitude)
        best: tuple[str, float] | None = None
        for name in self.bodies:
            if name == "Moon":
                continue
            pos = ctx.positions.get(name)
            if pos is None:
                continue
            lon = float(pos.longitude)
            separation = norm360(moon_lon - lon)
            for aspect in _MAJOR_ASPECTS:
                angle = _ASPECT_ANGLES[aspect]
                delta = abs(delta_angle(separation, angle))
                if delta <= self.max_orb:
                    if best is None or delta < best[1]:
                        best = (f"Moon-{name}:{aspect}", delta)
        is_void = best is None
        detail["is_void"] = is_void
        if best is not None:
            detail["closest"] = {"label": best[0], "orb": best[1]}
        passed = is_void if self.require_void else not is_void
        if passed:
            detail["strength"] = 1.0
        else:
            detail["strength"] = 0.0
        reason = None
        if not passed:
            reason = "void_expected" if self.require_void else "void_detected"
        return ElectionalConstraintEvaluation("moon", passed, detail, reason)


class MaleficAnglesConstraint:
    def __init__(self, *, allow_contact: bool, max_orb: float) -> None:
        self.allow_contact = bool(allow_contact)
        self.max_orb = max(0.0, float(max_orb))
        self._malefics = ("Mars", "Saturn")
        self._angles = ("asc", "desc", "mc", "ic")

    def required_bodies(self) -> Sequence[str]:
        return list(self._malefics)

    def required_axes(self) -> Sequence[str]:
        return list(self._angles)

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        detail: dict[str, Any] = {
            "allow_contact": self.allow_contact,
            "max_orb": self.max_orb,
        }
        min_delta = None
        closest = None
        for body_name in self._malefics:
            pos = ctx.positions.get(body_name)
            if pos is None:
                continue
            lon = float(pos.longitude)
            for axis_name in self._angles:
                axis_lon = ctx.axes.get(axis_name)
                if axis_lon is None:
                    continue
                delta = abs(delta_angle(norm360(lon), norm360(axis_lon)))
                delta = min(delta, abs(360.0 - delta))
                if min_delta is None or delta < min_delta:
                    min_delta = delta
                    closest = (body_name, axis_name, delta)
        if min_delta is None:
            return ElectionalConstraintEvaluation(
                "malefic_to_angles",
                True,
                detail,
            )
        assert closest is not None  # narrow for type checking
        closest_body, closest_axis, closest_orb = closest
        detail["closest"] = {
            "body": closest_body,
            "axis": closest_axis,
            "orb": closest_orb,
        }
        contact = min_delta <= self.max_orb
        passed = contact if self.allow_contact else not contact
        detail["contact"] = contact
        detail["strength"] = 1.0 if passed else 0.0
        reason = None
        if not passed:
            reason = "contact_forbidden" if not self.allow_contact else "contact_missing"
        return ElectionalConstraintEvaluation(
            "malefic_to_angles",
            passed,
            detail,
            reason,
        )


class AntisciaConstraint:
    def __init__(
        self,
        *,
        body: str,
        target: str,
        max_orb: float,
        kind: str,
        axis: str,
    ) -> None:
        self.body = body
        self.target = target
        self.max_orb = max(0.0, float(max_orb))
        self.kind = "contra_antiscia" if kind.lower().startswith("contra") else "antiscia"
        self.axis = axis or DEFAULT_ANTISCIA_AXIS

    def required_bodies(self) -> Sequence[str]:
        return [self.body, self.target]

    def required_axes(self) -> Sequence[str]:
        return []

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        hits = detect_antiscia_contacts(
            ctx.provider,
            [ctx.iso],
            self.body,
            self.target,
            orb_deg_antiscia=self.max_orb if self.kind == "antiscia" else 0.0,
            orb_deg_contra=self.max_orb if self.kind == "contra_antiscia" else 0.0,
            axis=self.axis,
        )
        detail: dict[str, Any] = {
            "body": self.body,
            "target": self.target,
            "kind": self.kind,
            "axis": self.axis,
            "max_orb": self.max_orb,
        }
        selected: CoarseHit | None = None
        for hit in hits:
            if hit.kind == self.kind and abs(hit.delta) <= self.max_orb + 1e-9:
                selected = hit
                break
        if selected is None:
            return ElectionalConstraintEvaluation(
                "antiscia",
                False,
                detail,
                reason="no_contact",
            )
        delta = abs(float(selected.delta))
        strength = 0.0
        if self.max_orb > 0:
            strength = max(0.0, 1.0 - delta / self.max_orb)
        detail.update(
            {
                "orb": delta,
                "orb_allow": float(selected.orb_allow or self.max_orb),
                "strength": strength,
                "mirror_lon": float(selected.mirror_lon or 0.0),
            }
        )
        return ElectionalConstraintEvaluation("antiscia", True, detail)


class DeclinationConstraint:
    def __init__(
        self,
        *,
        body: str,
        target: str,
        kind: str,
        max_orb: float,
    ) -> None:
        self.body = body
        self.target = target
        self.kind = "decl_contra" if kind.lower().startswith("contra") else "decl_parallel"
        self.max_orb = max(0.0, float(max_orb))

    def required_bodies(self) -> Sequence[str]:
        return [self.body, self.target]

    def required_axes(self) -> Sequence[str]:
        return []

    def evaluate(self, ctx: SampleContext) -> ElectionalConstraintEvaluation:
        hits = detect_decl_contacts(
            ctx.provider,
            [ctx.iso],
            self.body,
            self.target,
            orb_deg_parallel=self.max_orb if self.kind == "decl_parallel" else 0.0,
            orb_deg_contra=self.max_orb if self.kind == "decl_contra" else 0.0,
        )
        detail: dict[str, Any] = {
            "body": self.body,
            "target": self.target,
            "kind": self.kind,
            "max_orb": self.max_orb,
        }
        chosen: CoarseHit | None = None
        for hit in hits:
            if hit.kind == self.kind and abs(hit.delta) <= self.max_orb + 1e-9:
                chosen = hit
                break
        if chosen is None:
            return ElectionalConstraintEvaluation(
                "declination",
                False,
                detail,
                reason="no_contact",
            )
        delta = abs(float(chosen.delta))
        strength = 0.0
        if self.max_orb > 0:
            strength = max(0.0, 1.0 - delta / self.max_orb)
        detail.update(
            {
                "orb": delta,
                "orb_allow": float(chosen.orb_allow or self.max_orb),
                "strength": strength,
            }
        )
        return ElectionalConstraintEvaluation("declination", True, detail)


def _normalize_constraints(payload: Sequence[Mapping[str, Any]]) -> tuple[list[Constraint], set[str], set[str]]:
    constraints: list[Constraint] = []
    bodies: set[str] = set()
    axes: set[str] = set()
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise ValueError("each constraint must be a mapping")
        if "aspect" in entry:
            spec = entry["aspect"]
            if not isinstance(spec, Mapping):
                raise ValueError("aspect constraint must be an object")
            body = _resolve_body(str(spec.get("body")))
            target_raw = spec.get("target")
            if target_raw is None:
                raise ValueError("aspect constraint missing target")
            try:
                target = _resolve_body(str(target_raw))
                target_is_axis = False
            except ValueError:
                target = _resolve_axis(str(target_raw))
                target_is_axis = True
            aspect_name, angle = _resolve_aspect(str(spec.get("type")))
            max_orb = spec.get("max_orb")
            constraints.append(
                AspectConstraint(
                    body=body,
                    target=target,
                    aspect=aspect_name,
                    angle=angle,
                    max_orb=None if max_orb is None else float(max_orb),
                    target_is_axis=target_is_axis,
                )
            )
            bodies.add(body)
            if target_is_axis:
                axes.add(target)
            else:
                bodies.add(target)
            continue
        if "moon" in entry:
            spec = entry["moon"]
            if not isinstance(spec, Mapping):
                raise ValueError("moon constraint must be an object")
            require = bool(spec.get("void_of_course", False))
            orb = float(spec.get("max_orb", 6.0))
            bodies_list = spec.get("bodies")
            if isinstance(bodies_list, Sequence):
                resolved = []
                for name in bodies_list:
                    resolved.append(_resolve_body(str(name)))
            else:
                resolved = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
            constraints.append(
                MoonVoidConstraint(
                    require_void=require,
                    bodies=resolved,
                    max_orb=orb,
                )
            )
            bodies.add("Moon")
            bodies.update(resolved)
            continue
        if "malefic_to_angles" in entry:
            spec = entry["malefic_to_angles"]
            if isinstance(spec, Mapping):
                allow = bool(spec.get("allow", False))
                orb = float(spec.get("max_orb", 3.0))
            else:
                allow = bool(spec)
                orb = 3.0
            constraints.append(
                MaleficAnglesConstraint(allow_contact=allow, max_orb=orb)
            )
            bodies.update(["Mars", "Saturn"])
            axes.update(["asc", "desc", "mc", "ic"])
            continue
        if "antiscia" in entry:
            spec = entry["antiscia"]
            if not isinstance(spec, Mapping):
                raise ValueError("antiscia constraint must be an object")
            body = _resolve_body(str(spec.get("body")))
            target = _resolve_body(str(spec.get("target")))
            kind = str(spec.get("type", "antiscia"))
            axis = str(spec.get("axis", DEFAULT_ANTISCIA_AXIS))
            orb = float(spec.get("max_orb", 2.0))
            constraints.append(
                AntisciaConstraint(
                    body=body,
                    target=target,
                    max_orb=orb,
                    kind=kind,
                    axis=axis,
                )
            )
            bodies.update([body, target])
            continue
        if "declination" in entry:
            spec = entry["declination"]
            if not isinstance(spec, Mapping):
                raise ValueError("declination constraint must be an object")
            body = _resolve_body(str(spec.get("body")))
            target = _resolve_body(str(spec.get("target")))
            kind = str(spec.get("type", "parallel"))
            orb = float(spec.get("max_orb", 1.0))
            constraints.append(
                DeclinationConstraint(
                    body=body,
                    target=target,
                    kind=kind,
                    max_orb=orb,
                )
            )
            bodies.update([body, target])
            continue
        raise ValueError("unknown constraint type")
    if not constraints:
        raise ValueError("at least one constraint must be supplied")
    return constraints, bodies, axes


def _score_evaluations(evaluations: Sequence[ElectionalConstraintEvaluation]) -> float:
    score = 0.0
    for ev in evaluations:
        if not ev.passed:
            return 0.0
        strength = ev.detail.get("strength")
        if isinstance(strength, (int, float)) and not isinstance(strength, bool):
            score += float(strength)
        else:
            score += 1.0
    return score


def search_constraints(
    params: ElectionalSearchParams,
    *,
    chart_config: ChartConfig | None = None,
    provider: ElectionalSampleProvider | None = None,
) -> list[ElectionalCandidate]:
    """Search for instants satisfying the supplied constraint payload."""

    if params.start > params.end:
        raise ValueError("start must precede end")
    step_delta = _minute_delta(int(params.step_minutes))
    constraints, bodies, axes = _normalize_constraints(params.constraints)
    sorted_bodies = sorted(bodies)
    if provider is None:
        provider = SwissElectionalProvider(
            start=params.start,
            end=params.end,
            latitude=params.latitude,
            longitude=params.longitude,
            bodies=sorted_bodies,
            chart_config=chart_config,
        )
    candidates: list[ElectionalCandidate] = []
    cursor = params.start
    limit = params.limit
    while cursor <= params.end:
        ctx = provider.context(cursor)
        evaluations = [constraint.evaluate(ctx) for constraint in constraints]
        if all(ev.passed for ev in evaluations):
            score = _score_evaluations(evaluations)
            candidates.append(ElectionalCandidate(ts=cursor, score=score, evaluations=evaluations))
            if limit is not None and len(candidates) >= limit:
                break
        cursor += step_delta
    return candidates


__all__ = [
    "ElectionalCandidate",
    "ElectionalConstraintEvaluation",
    "ElectionalSearchParams",
    "SwissElectionalProvider",
    "search_constraints",
]
