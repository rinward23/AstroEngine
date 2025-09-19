"""Swiss Ephemeris adapter with caching and fallback support."""

from __future__ import annotations

import datetime as _dt
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from ..core.angles import AspectMotion, DeltaLambdaTracker, classify_relative_motion
from ..core.time import TimeConversion, to_tt

try:  # pragma: no cover - import guarded for environments without SWE
    import swisseph as swe

except ModuleNotFoundError:  # pragma: no cover - fallback exercised in tests
    swe = None

_HAS_SWE: Final[bool] = swe is not None

__all__ = ["EphemerisAdapter", "EphemerisConfig", "EphemerisSample", "RefinementError"]


LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class EphemerisConfig:
    """Ephemeris configuration passed to :class:`EphemerisAdapter`."""

    ephemeris_path: str | None = None
    prefer_moshier: bool = False
    cache_size: int | None = None


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
    delta_t_seconds: float


class RefinementError(RuntimeError):
    """Raised when refinement across a retrograde loop is attempted."""


class EphemerisAdapter:
    """Swiss Ephemeris front-end with deterministic caching."""

    def __init__(self, config: EphemerisConfig | None = None) -> None:
        self._config = config or EphemerisConfig()
        self._cache: dict[tuple[float, int, int], EphemerisSample] = {}
        self._cache_order: list[tuple[float, int, int]] = []
        self._probe_path()

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
        cache_key = (moment.jd_tt, body, flags)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        backend = self._select_backend()
        longitude, latitude, distance, lon_speed, lat_speed, dist_speed = backend(
            moment, body, flags
        )

        sample = EphemerisSample(
            jd_tt=moment.jd_tt,
            jd_utc=moment.jd_utc,
            longitude=longitude,
            latitude=latitude,
            distance=distance,
            speed_longitude=lon_speed,
            speed_latitude=lat_speed,
            speed_distance=dist_speed,
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
        return cast(int, swe.FLG_SWIEPH | swe.FLG_SPEED)

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

    def _select_backend(
        self,
    ) -> Callable[[TimeConversion, int, int], tuple[float, float, float, float, float, float]]:
        if not _HAS_SWE:
            return self._moshier_backend
        if self._config.prefer_moshier:
            return self._moshier_backend
        return self._swiss_ephemeris_backend

    def _swiss_ephemeris_backend(
        self, moment: TimeConversion, body: int, flags: int
    ) -> tuple[float, float, float, float, float, float]:
        assert swe is not None
        result, _ = swe.calc_ut(moment.jd_utc, body, flags)
        longitude, latitude, distance, lon_speed, lat_speed, dist_speed = result
        return (longitude, latitude, distance, lon_speed, lat_speed, dist_speed)

    def _moshier_backend(
        self, moment: TimeConversion, body: int, flags: int
    ) -> tuple[float, float, float, float, float, float]:
        if not _HAS_SWE:
            raise RuntimeError("Moshier fallback requires pyswisseph to be installed")
        assert swe is not None
        result, _ = swe.calc_ut(moment.jd_utc, body, flags | swe.FLG_MOSEPH)
        longitude, latitude, distance, lon_speed, lat_speed, dist_speed = result
        return (longitude, latitude, distance, lon_speed, lat_speed, dist_speed)
