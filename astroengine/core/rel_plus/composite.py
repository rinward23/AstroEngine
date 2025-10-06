"""Composite and Davison chart utilities."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from astroengine.ephemeris.cache import calc_ut_cached

TAU = 360.0


class EphemerisError(RuntimeError):
    """Raised when an ephemeris provider cannot return the requested data."""


class Body(str):
    """Identifier for a chart body (planets, points, etc.)."""


class NodePolicy(str):
    """Selects the lunar node variant returned by ephemeris providers."""

    TRUE = "true"
    MEAN = "mean"


@dataclass(frozen=True, slots=True)
class EclipticPos:
    """Ecliptic position expressed in tropical geocentric coordinates."""

    lon: float
    lat: float
    dist: float | None = None
    speed_lon: float | None = None
    retrograde: bool | None = None


ChartPositions = dict[Body, EclipticPos]


@dataclass(frozen=True, slots=True)
class BirthEvent:
    """Birth event descriptor used for Davison calculations."""

    when: datetime
    lat: float
    lon: float

    def __post_init__(self) -> None:
        _validate_datetime(self.when)
        _validate_latitude(self.lat)
        _validate_longitude(self.lon)


class Ephemeris(Protocol):
    """Protocol satisfied by ephemeris adapters used for Davison charts."""

    def positions_at(
        self,
        when: datetime,
        lat: float,
        lon: float,
        bodies: Iterable[Body],
        node_policy: NodePolicy,
    ) -> ChartPositions:
        ...


def wrap_degrees(value: float) -> float:
    """Return ``value`` wrapped to the ``[0, 360)`` interval."""

    res = math.fmod(value, TAU)
    if res < 0.0:
        res += TAU
    # Guard against rounding errors that could push exactly 360.0
    return 0.0 if math.isclose(res, TAU, rel_tol=0.0, abs_tol=1e-12) else res


def angular_difference(delta: float) -> float:
    """Return the signed smallest angular difference in ``(-180, 180]`` degrees."""

    wrapped = math.fmod(delta + 180.0, TAU)
    if wrapped < 0.0:
        wrapped += TAU
    return wrapped - 180.0


def circular_midpoint(a_deg: float, b_deg: float) -> float:
    """Return the midpoint between two angles measured along the shorter arc."""

    if math.isnan(a_deg) or math.isnan(b_deg):
        raise ValueError("Angles must be finite numbers")
    diff = angular_difference(b_deg - a_deg)
    return wrap_degrees(a_deg + diff / 2.0)


def _validate_datetime(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")


def _validate_latitude(lat: float) -> None:
    if not math.isfinite(lat) or lat < -90.0 or lat > 90.0:
        raise ValueError("Latitude must be within [-90, 90] degrees")


def _validate_longitude(lon: float) -> None:
    if not math.isfinite(lon):
        raise ValueError("Longitude must be a finite number")


def midpoint_time(a: datetime, b: datetime) -> datetime:
    """Return the UTC midpoint between two timezone-aware datetimes."""

    _validate_datetime(a)
    _validate_datetime(b)
    a_utc = a.astimezone(UTC)
    b_utc = b.astimezone(UTC)
    # operate on POSIX timestamps to avoid DST ambiguities
    mid_ts = (a_utc.timestamp() + b_utc.timestamp()) / 2.0
    return datetime.fromtimestamp(mid_ts, tz=UTC)


def _sph_to_cart(lat_rad: float, lon_rad: float) -> tuple[float, float, float]:
    cos_lat = math.cos(lat_rad)
    return (
        cos_lat * math.cos(lon_rad),
        cos_lat * math.sin(lon_rad),
        math.sin(lat_rad),
    )


def geodesic_midpoint(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
) -> tuple[float, float]:
    """Return the midpoint along the great-circle between two locations."""

    _validate_latitude(lat1_deg)
    _validate_latitude(lat2_deg)
    _validate_longitude(lon1_deg)
    _validate_longitude(lon2_deg)

    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    lat2 = math.radians(lat2_deg)
    lon2 = math.radians(lon2_deg)

    u = _sph_to_cart(lat1, lon1)
    v = _sph_to_cart(lat2, lon2)

    dot = max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1] + u[2] * v[2]))
    omega = math.acos(dot)
    eps_same = 1e-9
    eps_anti = 1e-8
    if omega < eps_same:
        return (lat1_deg, _wrap_longitude(lon1_deg))
    if abs(math.pi - omega) < eps_anti:
        # Antipodal: perturb v slightly along east of u
        ex, ey, ez = -u[1], u[0], 0.0
        scale = 1e-6
        v = _normalize((v[0] + scale * ex, v[1] + scale * ey, v[2] + scale * ez))
        dot = max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1] + u[2] * v[2]))
        omega = math.acos(dot)

    sin_omega = math.sin(omega)
    if sin_omega == 0.0:
        return (lat1_deg, _wrap_longitude(lon1_deg))

    k1 = math.sin((1.0 - 0.5) * omega) / sin_omega
    k2 = math.sin(0.5 * omega) / sin_omega
    midpoint_vec = (
        k1 * u[0] + k2 * v[0],
        k1 * u[1] + k2 * v[1],
        k1 * u[2] + k2 * v[2],
    )
    midpoint_vec = _normalize(midpoint_vec)
    lat = math.degrees(math.asin(midpoint_vec[2]))
    lon = math.degrees(math.atan2(midpoint_vec[1], midpoint_vec[0]))
    return (lat, _wrap_longitude(lon))


def _normalize(vec: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
    if mag == 0.0:
        raise ValueError("Cannot normalise zero-length vector")
    return (vec[0] / mag, vec[1] / mag, vec[2] / mag)


def _wrap_longitude(lon: float) -> float:
    wrapped = math.fmod(lon + 180.0, TAU)
    if wrapped < 0.0:
        wrapped += TAU
    return wrapped - 180.0


def composite_midpoints(
    pos_a: Mapping[Body, EclipticPos],
    pos_b: Mapping[Body, EclipticPos],
    bodies: Iterable[Body],
) -> ChartPositions:
    """Return composite midpoints for the requested ``bodies``."""

    result: ChartPositions = {}
    for body in bodies:
        if body not in pos_a:
            raise KeyError(f"Body '{body}' missing from first chart")
        if body not in pos_b:
            raise KeyError(f"Body '{body}' missing from second chart")
        pa = pos_a[body]
        pb = pos_b[body]
        if math.isnan(pa.lon) or math.isnan(pb.lon):
            raise ValueError(f"Body '{body}' has NaN longitude")
        lat = (pa.lat + pb.lat) / 2.0
        lon = circular_midpoint(pa.lon, pb.lon)
        result[Body(body)] = EclipticPos(lon=lon, lat=lat)
    return result


@dataclass(frozen=True, slots=True)
class DavisonResult:
    """Davison chart metadata and computed positions."""

    mid_when: datetime
    mid_lat: float
    mid_lon: float
    positions: ChartPositions


def davison_chart(
    a: BirthEvent,
    b: BirthEvent,
    bodies: Iterable[Body],
    eph: Ephemeris,
    node_policy: NodePolicy = NodePolicy.TRUE,
) -> DavisonResult:
    """Return the Davison chart for ``a`` and ``b`` using ``eph``."""

    mid_when = midpoint_time(a.when, b.when)
    mid_lat, mid_lon = geodesic_midpoint(a.lat, a.lon, b.lat, b.lon)
    try:
        positions = eph.positions_at(mid_when, mid_lat, mid_lon, bodies, node_policy)
    except EphemerisError:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard for providers
        raise EphemerisError(str(exc)) from exc
    return DavisonResult(mid_when=mid_when, mid_lat=mid_lat, mid_lon=mid_lon, positions=positions)


# ---------------------------------------------------------------------------
# Compatibility helpers retained for legacy callers expecting bare longitudes
# ---------------------------------------------------------------------------

Positions = dict[str, float]
PositionProvider = Callable[[datetime], Mapping[str, float]]


def composite_midpoint_positions(
    pos_a: Mapping[str, float],
    pos_b: Mapping[str, float],
    objects: Iterable[str],
) -> dict[str, float]:
    """Compatibility wrapper returning midpoint longitudes only."""

    chart_a: MutableMapping[Body, EclipticPos] = {}
    chart_b: MutableMapping[Body, EclipticPos] = {}
    for key, val in pos_a.items():
        chart_a[Body(key)] = EclipticPos(lon=float(val), lat=0.0)
    for key, val in pos_b.items():
        chart_b[Body(key)] = EclipticPos(lon=float(val), lat=0.0)
    mids = composite_midpoints(chart_a, chart_b, [Body(name) for name in objects])
    return {str(body): pos.lon for body, pos in mids.items()}


def davison_positions(
    objects: Iterable[str],
    dt_a: datetime,
    dt_b: datetime,
    provider: PositionProvider,
    *,
    lat_a: float = 0.0,
    lon_a: float = 0.0,
    lat_b: float = 0.0,
    lon_b: float = 0.0,
) -> dict[str, float]:
    """Return Davison longitudes using a callable position ``provider``."""

    event_a = BirthEvent(when=dt_a, lat=lat_a, lon=lon_a)
    event_b = BirthEvent(when=dt_b, lat=lat_b, lon=lon_b)

    class _CallableEphemeris:
        def positions_at(
            self,
            when: datetime,
            lat: float,
            lon: float,
            bodies: Iterable[Body],
            node_policy: NodePolicy,
        ) -> ChartPositions:
            del lat, lon, node_policy  # legacy providers are geocentric only
            data = provider(when)
            result: ChartPositions = {}
            for body in bodies:
                if str(body) not in data:
                    raise EphemerisError(f"Provider missing position for {body}")
                result[body] = EclipticPos(lon=wrap_degrees(float(data[str(body)])), lat=0.0)
            return result

    eph = _CallableEphemeris()
    res = davison_chart(event_a, event_b, [Body(name) for name in objects], eph)
    return {str(body): pos.lon for body, pos in res.positions.items()}


class SwissEphemerisAdapter:
    """Ephemeris backed by :mod:`pyswisseph` (Swiss Ephemeris)."""

    def __init__(self, ephemeris_path: str | None = None) -> None:
        from astroengine.ephemeris.swe import has_swe, swe

        if not has_swe():  # pragma: no cover - optional dependency
            raise EphemerisError("Swiss Ephemeris (pyswisseph) is not available")

        swe_module = swe()
        self._swe = swe_module
        if ephemeris_path:
            swe_module.set_ephe_path(ephemeris_path)
        self._flags = swe_module.SEFLG_SWIEPH | swe_module.SEFLG_SPEED
        self._body_codes = {
            "sun": swe_module.SUN,
            "moon": swe_module.MOON,
            "mercury": swe_module.MERCURY,
            "venus": swe_module.VENUS,
            "mars": swe_module.MARS,
            "jupiter": swe_module.JUPITER,
            "saturn": swe_module.SATURN,
            "uranus": swe_module.URANUS,
            "neptune": swe_module.NEPTUNE,
            "pluto": swe_module.PLUTO,
            "chiron": swe_module.CHIRON,
        }

    def _julian_day(self, when: datetime) -> float:
        ts = when.astimezone(UTC)
        frac = (
            ts.hour
            + ts.minute / 60.0
            + ts.second / 3600.0
            + ts.microsecond / 3_600_000_000.0
        )
        return self._swe.julday(ts.year, ts.month, ts.day, frac)

    def _resolve_body(self, body: Body, node_policy: NodePolicy) -> int:
        key = str(body).lower()
        if key in self._body_codes:
            return self._body_codes[key]
        if key in {"node", "lunar_node", "true node", "mean node"}:
            if node_policy == NodePolicy.MEAN:
                return self._swe.MEAN_NODE
            return self._swe.TRUE_NODE
        raise EphemerisError(f"Swiss Ephemeris does not support body '{body}'")

    def positions_at(
        self,
        when: datetime,
        lat: float,
        lon: float,
        bodies: Iterable[Body],
        node_policy: NodePolicy,
    ) -> ChartPositions:
        _validate_datetime(when)
        _validate_latitude(lat)
        _validate_longitude(lon)

        jd = self._julian_day(when)
        result: ChartPositions = {}
        for body in bodies:
            code = self._resolve_body(body, node_policy)
            try:
                values, ret_flag = calc_ut_cached(jd, code, self._flags)
            except Exception as exc:
                raise EphemerisError(str(exc)) from exc
            if ret_flag < 0:
                raise EphemerisError(
                    f"Swiss ephemeris returned error code {ret_flag}"
                )
            lon_deg = wrap_degrees(values[0])
            lat_deg = values[1]
            dist = values[2]
            speed_lon = values[3] if len(values) > 3 else None
            retrograde = speed_lon is not None and speed_lon < 0
            result[Body(body)] = EclipticPos(
                lon=lon_deg,
                lat=lat_deg,
                dist=dist,
                speed_lon=speed_lon,
                retrograde=retrograde,
            )
        return result


class SkyfieldAdapter:
    """Ephemeris backed by :mod:`skyfield` and JPL ephemeris kernels."""

    def __init__(
        self,
        kernel: object | None = None,
        *,
        loader_path: str | None = None,
        kernel_name: str = "de421.bsp",
    ) -> None:
        try:  # pragma: no cover - optional dependency import guard
            from skyfield.api import Loader, load
            from skyfield.framelib import ecliptic_frame
        except Exception as exc:  # pragma: no cover - optional dependency
            raise EphemerisError("Skyfield is not available") from exc

        self._frame = ecliptic_frame

        if kernel is None:
            if loader_path:
                loader = Loader(loader_path)
                self._kernel = loader(kernel_name)
                self._timescale = loader.timescale()
            else:
                self._kernel = load(kernel_name)
                self._timescale = load.timescale()
        else:
            self._kernel = kernel
            if loader_path:
                loader = Loader(loader_path)
                self._timescale = loader.timescale()
            else:
                # load provides a module-level Loader with a default data path
                self._timescale = load.timescale()

        self._earth = self._kernel["earth"]
        self._targets = {
            "sun": "sun",
            "moon": "moon",
            "mercury": "mercury",
            "venus": "venus",
            "mars": "mars",
            "jupiter": "jupiter barycenter",
            "saturn": "saturn barycenter",
            "uranus": "uranus barycenter",
            "neptune": "neptune barycenter",
            "pluto": "pluto barycenter",
        }

    def _time(self, when: datetime):
        return self._timescale.from_datetime(when.astimezone(UTC))

    def _resolve_body(self, body: Body) -> str:
        key = str(body).lower()
        if key in self._targets:
            return self._targets[key]
        raise EphemerisError(f"Skyfield adapter does not support body '{body}'")

    def _mean_node(self, t) -> float:
        T = (t.tt - 2451545.0) / 36525.0
        omega = 125.04455501 - 1934.13626197 * T + 0.00207614 * T**2 + T**3 / 450000.0
        return wrap_degrees(omega)

    def _true_node(self, t) -> float:
        moon = self._kernel["moon"]
        astrom = self._earth.at(t).observe(moon)
        pos, vel = astrom.frame_xyz_and_velocity(self._frame)
        rx, ry, rz = pos.au
        vx, vy, vz = vel.au_per_d
        hx = ry * vz - rz * vy
        hy = rz * vx - rx * vz
        n = (-hy, hx, 0.0)
        if math.isclose(n[0], 0.0, abs_tol=1e-16) and math.isclose(n[1], 0.0, abs_tol=1e-16):
            return 0.0
        return wrap_degrees(math.degrees(math.atan2(n[1], n[0])))

    def _node(self, t, policy: NodePolicy) -> tuple[float, float]:
        lon = self._true_node(t) if policy == NodePolicy.TRUE else self._mean_node(t)
        delta_days = 1e-3
        t_delta = t + delta_days
        lon_next = (
            self._true_node(t_delta)
            if policy == NodePolicy.TRUE
            else self._mean_node(t_delta)
        )
        speed = angular_difference(lon_next - lon) / delta_days
        return lon, speed

    def positions_at(
        self,
        when: datetime,
        lat: float,
        lon: float,
        bodies: Iterable[Body],
        node_policy: NodePolicy,
    ) -> ChartPositions:
        _validate_datetime(when)
        _validate_latitude(lat)
        _validate_longitude(lon)

        t = self._time(when)
        result: ChartPositions = {}
        for body in bodies:
            key = str(body).lower()
            if key in {"node", "lunar_node", "true node", "mean node"}:
                lon_deg, speed = self._node(t, node_policy)
                result[Body(body)] = EclipticPos(
                    lon=lon_deg,
                    lat=0.0,
                    dist=None,
                    speed_lon=speed,
                    retrograde=speed < 0.0,
                )
                continue
            target_key = self._resolve_body(body)
            target = self._kernel[target_key]
            astrom = self._earth.at(t).observe(target).apparent()
            lon_lat_dist = astrom.frame_latlon_and_rates(self._frame)
            lon_angle, lat_angle, distance, dlon_dt, _, _ = lon_lat_dist
            lon_deg = wrap_degrees(lon_angle.degrees)
            lat_deg = lat_angle.degrees
            dist_au = distance.au
            speed_lon = dlon_dt.degrees_per_day
            retrograde = speed_lon < 0.0
            result[Body(body)] = EclipticPos(
                lon=lon_deg,
                lat=lat_deg,
                dist=dist_au,
                speed_lon=speed_lon,
                retrograde=retrograde,
            )
        return result


__all__ = [
    "Body",
    "BirthEvent",
    "ChartPositions",
    "DavisonResult",
    "Ephemeris",
    "EphemerisError",
    "EclipticPos",
    "NodePolicy",
    "Positions",
    "PositionProvider",
    "angular_difference",
    "circular_midpoint",
    "composite_midpoints",
    "composite_midpoint_positions",
    "davison_chart",
    "davison_positions",
    "geodesic_midpoint",
    "midpoint_time",
    "SkyfieldAdapter",
    "SwissEphemerisAdapter",
    "wrap_degrees",
]
