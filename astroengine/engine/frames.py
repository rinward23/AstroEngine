"""Resolver utilities that adapt scanning providers to alternate frames."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from datetime import UTC, datetime

from ..canonical import BodyPosition
from ..chart.composite import CompositeChart
from ..chart.directions import DirectedChart, compute_solar_arc_chart
from ..chart.natal import NatalChart
from ..chart.progressions import ProgressedChart, compute_secondary_progressed_chart

__all__ = [
    "TargetFrameResolver",
    "FrameAwareProvider",
]


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
        self._progressed_cache: MutableMapping[str, ProgressedChart] = {}
        self._directed_cache: MutableMapping[str, DirectedChart] = {}
        self._static_positions: MutableMapping[str, float] = {}
        self._natal_chart: NatalChart | None = None
        self._composite_chart: CompositeChart | None = None
        self._name_lookup: dict[str, str] = {}
        self.static_positions = static_positions
        self.natal_chart = natal_chart
        self.composite_chart = composite_chart

    @staticmethod
    def _normalize_iso(ts: str) -> tuple[str, datetime]:
        """Return a normalized ISO string and UTC datetime for ``ts``."""

        dt_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        dt_utc = dt_obj.astimezone(UTC) if dt_obj.tzinfo else dt_obj.replace(tzinfo=UTC)
        dt_utc = dt_utc.replace(microsecond=0)
        normalized = dt_utc.isoformat().replace("+00:00", "Z")
        return normalized, dt_utc

    @property
    def natal_chart(self) -> NatalChart | None:
        return self._natal_chart

    @natal_chart.setter
    def natal_chart(self, chart: NatalChart | None) -> None:
        self._natal_chart = chart
        self._progressed_cache.clear()
        self._directed_cache.clear()
        self._name_lookup = self._build_name_lookup()

    @property
    def composite_chart(self) -> CompositeChart | None:
        return self._composite_chart

    @composite_chart.setter
    def composite_chart(self, chart: CompositeChart | None) -> None:
        self._composite_chart = chart
        self._name_lookup = self._build_name_lookup()

    @property
    def static_positions(self) -> Mapping[str, float]:
        return dict(self._static_positions)

    @static_positions.setter
    def static_positions(self, positions: Mapping[str, float] | None) -> None:
        source = positions or {}
        self._static_positions = {
            str(key).lower(): float(value) % 360.0 for key, value in source.items()
        }
        self._name_lookup = self._build_name_lookup()

    def set_static_position(self, name: str, longitude: float) -> None:
        """Register or update a static longitude override for ``name``."""

        self._static_positions[str(name).lower()] = float(longitude) % 360.0
        self._name_lookup = self._build_name_lookup()

    def remove_static_position(self, name: str) -> None:
        """Remove a static longitude override when present."""

        normalized = str(name).lower()
        if normalized in self._static_positions:
            del self._static_positions[normalized]
            self._name_lookup = self._build_name_lookup()

    def _build_name_lookup(self) -> dict[str, str]:
        """Return mapping from lowercase body names to canonical identifiers."""

        lookup: dict[str, str] = {}

        def _record(names: Iterable[str]) -> None:
            for raw_name in names:
                normalized = str(raw_name).lower()
                lookup.setdefault(normalized, str(raw_name))

        _record(self._static_positions.keys())
        if self.natal_chart is not None:
            _record(self.natal_chart.positions.keys())
        if self.composite_chart is not None:
            _record(self.composite_chart.positions.keys())
        return lookup

    def _resolve_body_name(self, body: str) -> str:
        body_lower = body.lower()
        name = self._name_lookup.get(body_lower)
        if name is not None:
            return name
        self._name_lookup = self._build_name_lookup()
        return self._name_lookup.get(body_lower, body)

    def overrides_target(self) -> bool:
        if self.frame == "natal":
            return bool(self._static_positions) or self.natal_chart is not None
        if self.frame in {"progressed", "directed", "composite"}:
            return True
        return False

    def clear_temporal_caches(self) -> None:
        """Drop progressed/directed caches, forcing recomputation on next access."""

        self._progressed_cache.clear()
        self._directed_cache.clear()

    def _natal_body(self, body: str) -> BodyPosition | None:
        if self.natal_chart is None:
            return None
        name = self._resolve_body_name(body)
        return self.natal_chart.positions.get(name)

    def _progressed_for(self, iso_ts: str) -> ProgressedChart:
        key, moment = self._normalize_iso(iso_ts)
        cached = self._progressed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Progressed frame requires a natal chart")
        progressed = compute_secondary_progressed_chart(self.natal_chart, moment)
        self._progressed_cache[key] = progressed
        return progressed

    def _directed_for(self, iso_ts: str) -> DirectedChart:
        key, moment = self._normalize_iso(iso_ts)
        cached = self._directed_cache.get(key)
        if cached is not None:
            return cached
        if self.natal_chart is None:
            raise ValueError("Directed frame requires a natal chart")
        directed = compute_solar_arc_chart(self.natal_chart, moment)
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
        if not self._resolver.overrides_target():
            return base

        target_lower = self._target
        replaced = False
        for name in list(base.keys()):
            if name.lower() == target_lower:
                base[name] = dict(self._resolver.position_dict(iso_utc, name))
                replaced = True
        if not replaced:
            for requested in bodies:
                if str(requested).lower() == target_lower:
                    base[str(requested)] = dict(
                        self._resolver.position_dict(iso_utc, str(requested))
                    )
                    break
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
