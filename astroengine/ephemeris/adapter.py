"""Swiss Ephemeris adapter with caching and fallback support."""

from __future__ import annotations

import datetime as _dt
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

from ..core.angles import AspectMotion, DeltaLambdaTracker, classify_relative_motion
from ..core.time import TimeConversion, to_tt

try:  # pragma: no cover - import guarded for environments without SWE
    import swisseph as swe

except ModuleNotFoundError:  # pragma: no cover - fallback exercised in tests
    swe = None

_HAS_SWE: Final[bool] = swe is not None

__all__ = [
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefinementError",
    "TimeScaleContext",
]


LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class EphemerisConfig:
    """Ephemeris configuration passed to :class:`EphemerisAdapter`."""

    ephemeris_path: str | None = None
    prefer_moshier: bool = False
    cache_size: int | None = None
    time_scale: "TimeScaleContext" = field(default_factory=lambda: TimeScaleContext())
    topocentric: bool = False
    observer: "ObserverLocation | None" = None
    sidereal: bool = False
    sidereal_mode: str | None = None


@dataclass(frozen=True)
class TimeScaleContext:
    """Describe the input/output time scales used by the adapter."""

    input_scale: str = "UTC"
    ephemeris_scale: str = "TT"

    def __post_init__(self) -> None:
        input_norm = self.input_scale.upper()
        ephem_norm = self.ephemeris_scale.upper()
        if input_norm != "UTC":
            raise ValueError(f"unsupported input time scale: {self.input_scale}")
        if ephem_norm not in {"TT", "UT"}:
            raise ValueError(f"unsupported ephemeris time scale: {self.ephemeris_scale}")
        object.__setattr__(self, "input_scale", input_norm)
        object.__setattr__(self, "ephemeris_scale", ephem_norm)

    def describe(self) -> str:
        return f"{self.input_scale}→{self.ephemeris_scale}"


@dataclass(frozen=True)
class ObserverLocation:
    """Observer location used when topocentric calculations are requested."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.longitude_deg, self.latitude_deg, self.elevation_m)


@dataclass(frozen=True)
class EphemerisSample:
    """Ephemeris sample returned by :class:`EphemerisAdapter`."""

    jd_tt: float
    jd_utc: float
    longitude: float
    latitude: float
    distance: float
    speed_longitude: float
    speed_latitude: float
    speed_distance: float
    right_ascension: float
    declination: float
    speed_right_ascension: float
    speed_declination: float
    delta_t_seconds: float


class RefinementError(RuntimeError):
    """Raised when refinement across a retrograde loop is attempted."""


class EphemerisAdapter:
    """Swiss Ephemeris front-end with deterministic caching."""

    def __init__(self, config: EphemerisConfig | None = None) -> None:
        self._config = config or EphemerisConfig()
        if self._config.topocentric and self._config.observer is None:
            raise ValueError("EphemerisConfig.topocentric requires an observer location")
        self._cache: dict[tuple[float, int, int], EphemerisSample] = {}
        self._cache_order: list[tuple[float, int, int]] = []
        self._use_tt = self._config.time_scale.ephemeris_scale == "TT"
        self._probe_path()
        self._configure_observer()

    # ------------------------------------------------------------------
    # Core public API
    # ------------------------------------------------------------------
    def sample(
        self,
        body: int,
        moment: TimeConversion | _dt.datetime,
        *,
        flags: int | None = None,
    ) -> EphemerisSample:
        """Return an :class:`EphemerisSample` for ``body`` at ``moment``."""

        if not isinstance(moment, TimeConversion):
            if not isinstance(moment, _dt.datetime):
                raise TypeError("moment must be datetime or TimeConversion")
            moment = to_tt(moment)

        flags = self._resolve_flags(flags)
        cache_jd = moment.jd_tt if self._use_tt else moment.jd_utc
        cache_key = (cache_jd, body, flags)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        backend = self._select_backend()
        (
            longitude,
            latitude,
            distance,
            lon_speed,
            lat_speed,
            dist_speed,
            right_ascension,
            declination,
            ra_speed,
            dec_speed,
        ) = backend(moment, body, flags)

        sample = EphemerisSample(
            jd_tt=moment.jd_tt,
            jd_utc=moment.jd_utc,
            longitude=longitude,
            latitude=latitude,
            distance=distance,
            speed_longitude=lon_speed,
            speed_latitude=lat_speed,
            speed_distance=dist_speed,
            right_ascension=right_ascension,
            declination=declination,
            speed_right_ascension=ra_speed,
            speed_declination=dec_speed,
            delta_t_seconds=moment.delta_t_seconds,
        )
        self._store(cache_key, sample)
        return sample

    def sample_at_datetime(self, body: int, moment: _dt.datetime) -> EphemerisSample:
        conversion = to_tt(moment)
        return self.sample(body, conversion)

    def classify_motion(
        self,
        tracker: DeltaLambdaTracker,
        moving: EphemerisSample,
        reference_longitude: float,
        aspect_angle_deg: float,
        *,
        reference_speed_deg_per_day: float = 0.0,
    ) -> AspectMotion:
        separation = tracker.update(moving.longitude, reference_longitude)
        return classify_relative_motion(
            separation,
            aspect_angle_deg,
            moving.speed_longitude,
            reference_speed_deg_per_day,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_flags(self, flags: int | None) -> int:
        if flags is not None:
            return flags
        if not _HAS_SWE:
            return 0
        assert swe is not None
        base = cast(int, swe.FLG_SWIEPH | swe.FLG_SPEED)
        if self._config.topocentric:
            base |= cast(int, swe.FLG_TOPOCTR)
        return base

    def _store(self, key: tuple[float, int, int], sample: EphemerisSample) -> None:
        if self._config.cache_size is None:
            self._cache[key] = sample
            self._cache_order.append(key)
            return

        cache_size = self._config.cache_size
        if cache_size <= 0:
            return
        if key in self._cache:
            return

        if len(self._cache_order) >= cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)
        self._cache[key] = sample
        self._cache_order.append(key)

    def _probe_path(self) -> None:
        if not _HAS_SWE or self._config.prefer_moshier:
            return

        candidate = None
        if self._config.ephemeris_path:
            candidate = Path(self._config.ephemeris_path)
        else:
            for env_var in ("SE_EPHE_PATH", "ASTROENGINE_EPHEMERIS_PATH"):
                value = os.environ.get(env_var)
                if value:
                    candidate = Path(value)
                    break

        if candidate and candidate.exists():
            swe.set_ephe_path(str(candidate))
            LOG.debug("Swiss Ephemeris path configured: %s", candidate)
        else:
            if candidate:
                raise FileNotFoundError(
                    f"Swiss Ephemeris path '{candidate}' does not exist. "
                    "Set SE_EPHE_PATH or provide a valid EphemerisConfig.ephemeris_path."
                )

    def _configure_observer(self) -> None:
        if not _HAS_SWE:
            return
        assert swe is not None
        if not self._config.topocentric or self._config.observer is None:
            swe.set_topo(0.0, 0.0, 0.0)
            return
        lon, lat, elev = self._config.observer.as_tuple()
        swe.set_topo(lon, lat, elev)

    def _select_backend(
        self,
    ) -> Callable[
        [TimeConversion, int, int],
        tuple[float, float, float, float, float, float, float, float, float, float],
    ]:
        if not _HAS_SWE:
            return self._moshier_backend
        if self._config.prefer_moshier:
            return self._moshier_backend
        return self._swiss_ephemeris_backend

    def _swiss_ephemeris_backend(
        self, moment: TimeConversion, body: int, flags: int
    ) -> tuple[float, float, float, float, float, float, float, float, float, float]:
        assert swe is not None
        if self._use_tt:
            jd = moment.jd_tt
            calc_fn = swe.calc
        else:
            jd = moment.jd_utc
            calc_fn = swe.calc_ut
        result, _ = calc_fn(jd, body, flags)
        eq_result, _ = calc_fn(jd, body, flags | swe.FLG_EQUATORIAL)
        longitude, latitude, distance, lon_speed, lat_speed, dist_speed = result
        ra, dec, _, ra_speed, dec_speed, _ = eq_result
        return (
            longitude,
            latitude,
            distance,
            lon_speed,
            lat_speed,
            dist_speed,
            ra,
            dec,
            ra_speed,
            dec_speed,
        )

    def _moshier_backend(
        self, moment: TimeConversion, body: int, flags: int
    ) -> tuple[float, float, float, float, float, float, float, float, float, float]:
        if not _HAS_SWE:
            raise RuntimeError("Moshier fallback requires pyswisseph to be installed")
        assert swe is not None
        if self._use_tt:
            jd = moment.jd_tt
            calc_fn = swe.calc
        else:
            jd = moment.jd_utc
            calc_fn = swe.calc_ut
        moshier_flags = flags | swe.FLG_MOSEPH
        result, _ = calc_fn(jd, body, moshier_flags)
        eq_result, _ = calc_fn(jd, body, moshier_flags | swe.FLG_EQUATORIAL)
        longitude, latitude, distance, lon_speed, lat_speed, dist_speed = result
        ra, dec, _, ra_speed, dec_speed, _ = eq_result
        return (
            longitude,
            latitude,
            distance,
            lon_speed,
            lat_speed,
            dist_speed,
            ra,
            dec,
            ra_speed,
            dec_speed,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def describe_configuration(self) -> dict[str, str | None]:
        """Return a human-readable summary of the adapter configuration."""

        observer_mode = "geocentric"
        observer_summary: str | None = None
        if self._config.topocentric and self._config.observer is not None:
            observer_mode = "topocentric"
            observer_summary = (
                f"lat={self._config.observer.latitude_deg:.4f}°, "
                f"lon={self._config.observer.longitude_deg:.4f}°, "
                f"elev={self._config.observer.elevation_m:.0f} m"
            )
        return {
            "input_scale": self._config.time_scale.input_scale,
            "ephemeris_scale": self._config.time_scale.ephemeris_scale,
            "time_scale": self._config.time_scale.describe(),
            "observer_mode": observer_mode,
            "observer_location": observer_summary,
            "sidereal": "enabled" if self._config.sidereal else "disabled",
        }
