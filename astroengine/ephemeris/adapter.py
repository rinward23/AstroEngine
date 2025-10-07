"""Swiss Ephemeris adapter with caching and fallback support."""

from __future__ import annotations

import datetime as _dt
import logging
import os
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Final, cast

from astroengine.ephemeris.swe import has_swe, swe

from ..core.angles import AspectMotion, DeltaLambdaTracker, classify_relative_motion
from ..core.time import TimeConversion, to_tt
from ..observability import (
    COMPUTE_ERRORS,
    EPHEMERIS_CACHE_COMPUTE_DURATION,
    EPHEMERIS_CACHE_HITS,
    EPHEMERIS_CACHE_MISSES,
)
from .sidereal import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    normalize_ayanamsha_name,
)
from .swisseph_adapter import swe_calc

_HAS_SWE: Final[bool] = has_swe()

if _HAS_SWE:
    _SIDEREAL_MODE_MAP: dict[str, int] = {}
    swe_module = swe()
    for key, attr in (
        ("lahiri", "SIDM_LAHIRI"),
        ("fagan_bradley", "SIDM_FAGAN_BRADLEY"),
        ("krishnamurti", "SIDM_KRISHNAMURTI"),
        ("raman", "SIDM_RAMAN"),
        ("deluce", "SIDM_DELUCE"),
    ):
        value = getattr(swe_module, attr, None)
        if value is not None:
            _SIDEREAL_MODE_MAP[key] = int(value)
else:
    _SIDEREAL_MODE_MAP: dict[str, int] = {}

__all__ = [
    "EphemerisAdapter",
    "EphemerisConfig",
    "EphemerisSample",
    "ObserverLocation",
    "RefinementError",
    "TimeScaleContext",
]


LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EphemerisConfig:
    """Ephemeris configuration passed to :class:`EphemerisAdapter`."""

    ephemeris_path: str | None = None
    prefer_moshier: bool = False
    cache_size: int | None = None
    time_scale: TimeScaleContext = field(default_factory=lambda: TimeScaleContext())
    topocentric: bool = False
    observer: ObserverLocation | None = None
    sidereal: bool = False
    sidereal_mode: str | None = None


@dataclass(frozen=True, slots=True)
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
            raise ValueError(
                f"unsupported ephemeris time scale: {self.ephemeris_scale}"
            )
        object.__setattr__(self, "input_scale", input_norm)
        object.__setattr__(self, "ephemeris_scale", ephem_norm)

    def describe(self) -> str:
        return f"{self.input_scale}→{self.ephemeris_scale}"


@dataclass(frozen=True, slots=True)
class ObserverLocation:
    """Observer location used when topocentric calculations are requested."""

    latitude_deg: float
    longitude_deg: float
    elevation_m: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.longitude_deg, self.latitude_deg, self.elevation_m)


@dataclass(frozen=True, slots=True)
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

    _DEFAULT_CACHE_SIZE: Final[int] = 2048

    def __init__(self, config: EphemerisConfig | None = None) -> None:
        initial_config = config or EphemerisConfig()
        if initial_config.topocentric and initial_config.observer is None:
            raise ValueError(
                "EphemerisConfig.topocentric requires an observer location"
            )
        self._cache: OrderedDict[tuple[float, int, int], EphemerisSample] = (
            OrderedDict()
        )
        self._cache_capacity: int = 0
        self._config = initial_config
        self._use_tt = False
        self._sidereal_mode_code: int | None = None
        self._sidereal_mode_key: str | None = None
        self.reconfigure(initial_config)

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
        adapter_label = self.__class__.__name__
        if self._cache_capacity > 0:
            try:
                cached = self._cache[cache_key]
            except KeyError:
                cached = None
            else:
                self._cache.move_to_end(cache_key)
                EPHEMERIS_CACHE_HITS.labels(adapter=adapter_label).inc()
                return cached
        else:
            cached = None

        backend = self._select_backend()
        EPHEMERIS_CACHE_MISSES.labels(adapter=adapter_label).inc()
        start = perf_counter()
        try:
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
        except Exception as exc:
            COMPUTE_ERRORS.labels(
                component="ephemeris_backend",
                error=exc.__class__.__name__,
            ).inc()
            raise
        finally:
            duration = perf_counter() - start
            EPHEMERIS_CACHE_COMPUTE_DURATION.labels(
                adapter=adapter_label, body=str(body)
            ).observe(duration)

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
        swe_module = swe()
        base = cast(int, swe_module.FLG_SWIEPH | swe_module.FLG_SPEED)
        if self._config.topocentric:
            base |= cast(int, swe_module.FLG_TOPOCTR)
        if self._config.sidereal:
            base |= cast(int, swe_module.FLG_SIDEREAL)
        return base

    def _store(self, key: tuple[float, int, int], sample: EphemerisSample) -> None:
        if self._cache_capacity <= 0:
            return
        if key in self._cache:
            self._cache[key] = sample
            self._cache.move_to_end(key)
            return
        self._cache[key] = sample
        if len(self._cache) > self._cache_capacity:
            self._cache.popitem(last=False)

    def _apply_config(self, config: EphemerisConfig) -> None:
        self._config = config
        self._cache_capacity = self._resolve_cache_capacity(config.cache_size)
        self._use_tt = self._config.time_scale.ephemeris_scale == "TT"
        self._probe_path()
        self._configure_observer()
        self._configure_sidereal()

    def _resolve_cache_capacity(self, requested: int | None) -> int:
        if requested is None:
            return self._DEFAULT_CACHE_SIZE
        if requested <= 0:
            return 0
        return int(requested)

    def reconfigure(self, config: EphemerisConfig) -> None:
        """Apply ``config`` to the adapter, resetting caches if needed."""

        if (
            config == self._config
            and self._cache_capacity == self._resolve_cache_capacity(config.cache_size)
        ):
            return
        self._cache.clear()
        self._cache = OrderedDict()
        self._apply_config(config)

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
            swe().set_ephe_path(str(candidate))
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
        swe_module = swe()
        if not self._config.topocentric or self._config.observer is None:
            swe_module.set_topo(0.0, 0.0, 0.0)
            return
        lon, lat, elev = self._config.observer.as_tuple()
        swe_module.set_topo(lon, lat, elev)

    def _configure_sidereal(self) -> None:
        self._sidereal_mode_code = None
        self._sidereal_mode_key = None
        if not self._config.sidereal:
            return
        if not _HAS_SWE:
            raise RuntimeError(
                "Sidereal calculations require pyswisseph to be installed"
            )
        desired = self._config.sidereal_mode or DEFAULT_SIDEREAL_AYANAMSHA
        key = normalize_ayanamsha_name(desired)
        if key not in SUPPORTED_AYANAMSHAS:
            options = ", ".join(sorted(SUPPORTED_AYANAMSHAS))
            raise ValueError(
                f"Unsupported sidereal mode '{desired}'. Supported options: {options}"
            )
        try:
            mode_code = _SIDEREAL_MODE_MAP[key]
        except (
            KeyError
        ) as exc:  # pragma: no cover - defensive guard for incomplete SWE builds
            raise ValueError(
                f"Swiss Ephemeris does not expose a sidereal constant for '{key}'"
            ) from exc
        swe().set_sid_mode(mode_code, 0.0, 0.0)
        self._sidereal_mode_code = mode_code
        self._sidereal_mode_key = key

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
        jd = moment.jd_tt if self._use_tt else moment.jd_utc
        result, _, serr = swe_calc(
            jd_ut=jd, planet_index=body, flag=flags, use_tt=self._use_tt
        )
        if serr:
            raise RuntimeError(serr)
        eq_result, _, serr_eq = swe_calc(
            jd_ut=jd,
            planet_index=body,
            flag=flags | swe().FLG_EQUATORIAL,
            use_tt=self._use_tt,
        )
        if serr_eq:
            raise RuntimeError(serr_eq)
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
        jd = moment.jd_tt if self._use_tt else moment.jd_utc
        moshier_flags = flags | swe().FLG_MOSEPH
        result, _, serr = swe_calc(
            jd_ut=jd,
            planet_index=body,
            flag=moshier_flags,
            use_tt=self._use_tt,
        )
        if serr:
            raise RuntimeError(serr)
        eq_result, _, serr_eq = swe_calc(
            jd_ut=jd,
            planet_index=body,
            flag=moshier_flags | swe().FLG_EQUATORIAL,
            use_tt=self._use_tt,
        )
        if serr_eq:
            raise RuntimeError(serr_eq)
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
            "sidereal_mode": self._sidereal_mode_key,
        }

    def signature(self) -> tuple[object, ...]:
        """Return a stable signature describing the adapter configuration."""

        observer = None
        if self._config.observer is not None:
            observer = self._config.observer.as_tuple()
        return (
            "EphemerisAdapter",
            bool(self._config.prefer_moshier),
            bool(self._config.topocentric),
            observer,
            bool(self._config.sidereal),
            self._sidereal_mode_key,
            self._config.time_scale.input_scale,
            self._config.time_scale.ephemeris_scale,
            self._config.time_scale.describe(),
            self._config.ephemeris_path,
            self._use_tt,
        )
