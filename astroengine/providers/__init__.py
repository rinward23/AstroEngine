"""Provider plugin API contracts for AstroEngine.

This module defines the runtime interfaces used by ruleset executors to
communicate with ephemeris backends. Providers are discovered through the
``astroengine.providers`` entry-point group and must implement the
:class:`EphemerisProvider` protocol defined here. The design enforces the
following guarantees:

* Deterministic outputs – repeated queries with identical inputs MUST return
  identical results and determinism hash inputs.
* Cache transparency – providers surface cache metadata and validation hashes;
  the caller never assumes implicit fallbacks.
* Structured error taxonomy – all provider errors are reported using the
  :class:`ProviderError` hierarchy so callers can differentiate retriable vs
  fatal states.

Providers are required to declare their supported bodies, coordinate frames,
precision targets, and cache layout via :class:`ProviderMetadata`. The metadata
structures and result containers defined here are intentionally lightweight so
plugins can be implemented in pure Python or compiled extensions while still
respecting the schema contracts enforced by the engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from ..ephemeris import SwissEphemerisAdapter


class ProviderError(RuntimeError):
    """Base class for provider failures.

    Subclasses MUST populate the ``provider_id`` field so structured logging
    can attribute failures, and SHOULD supply a deterministic ``error_code``
    string that matches documentation in ``docs/providers/registry.md``.
    """

    provider_id: str
    error_code: str
    retriable: bool

    def __init__(self, message: str, *, provider_id: str, error_code: str, retriable: bool) -> None:
        super().__init__(message)
        self.provider_id = provider_id
        self.error_code = error_code
        self.retriable = retriable


class CacheStatus(Enum):
    """Enumerates cache states a provider may report."""

    WARM = "warm"
    COLD = "cold"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(frozen=True)
class CacheInfo:
    """Describes ephemeris cache provenance."""

    cache_path: str
    checksum: str
    generated_at: datetime
    status: CacheStatus


@dataclass(frozen=True)
class ProviderMetadata:
    """Static metadata for provider registration."""

    provider_id: str
    version: str
    supported_bodies: Sequence[str]
    supported_frames: Sequence[str]
    supports_declination: bool
    supports_light_time: bool
    cache_layout: Mapping[str, str]
    extras_required: Sequence[str]
    documentation_url: str | None = None


@dataclass(frozen=True)
class EphemerisVector:
    """Represents a single ephemeris sample."""

    body_id: str
    timestamp: datetime
    frame: str
    position_km: Sequence[float]
    velocity_km_s: Sequence[float]
    longitude_deg: float
    latitude_deg: float
    right_ascension_deg: float
    declination_deg: float
    distance_au: float
    speed_longitude_deg_per_day: float
    data_provenance: Mapping[str, str]


@dataclass(frozen=True)
class EphemerisBatch:
    """Vectorized result returned by :meth:`EphemerisProvider.query`."""

    vectors: Sequence[EphemerisVector]
    cache_info: CacheInfo
    determinism_inputs: Mapping[str, str]


class EphemerisProvider(Protocol):
    """Protocol that all provider plugins must implement."""

    metadata: ProviderMetadata

    def configure(
        self, *, profile_flags: Mapping[str, object], options: Mapping[str, object] | None = None
    ) -> None:
        """Apply profile-specific configuration.

        Implementations MUST be idempotent and only mutate internal caches.
        Raising :class:`ProviderError` signals misconfiguration.
        """

    def prime_cache(
        self, *, start: datetime, end: datetime, bodies: Sequence[str], cadence_hours: float
    ) -> CacheInfo:
        """Warm ephemeris caches for the requested window.

        Providers may download ephemeris files, but MUST verify checksums and
        refuse to continue when validation fails.
        """

    def query(
        self, *, timestamps: Sequence[datetime], bodies: Sequence[str], frame: str
    ) -> EphemerisBatch:
        """Return deterministic vectors for all timestamps/bodies in the requested frame."""

    def query_window(
        self,
        *,
        start: datetime,
        end: datetime,
        bodies: Sequence[str],
        cadence_hours: float,
        frame: str,
    ) -> EphemerisBatch:
        """Return vectors sampled across a regular cadence within ``[start, end]`` inclusive."""

    def close(self) -> None:
        """Release open resources (files, network handles)."""


_BODY_NAME_TO_ID = {
    "sun": 0,
    "moon": 1,
    "mercury": 2,
    "venus": 3,
    "mars": 4,
    "jupiter": 5,
    "saturn": 6,
    "uranus": 7,
    "neptune": 8,
    "pluto": 9,
}


def _parse_iso8601(iso_utc: str) -> datetime:
    moment = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _resolve_body_id(body: str | int) -> int:
    if isinstance(body, int):
        return body
    key = body.lower()
    if key not in _BODY_NAME_TO_ID:
        raise KeyError(f"Unknown body identifier: {body}")
    return _BODY_NAME_TO_ID[key]


class SwissProvider:
    """Minimal Swiss Ephemeris-backed provider for CLI diagnostics."""

    provider_id = "swiss"

    def __init__(self) -> None:
        self._adapter = SwissEphemerisAdapter()

    def positions_ecliptic(self, iso_utc: str, bodies: Sequence[str | int]) -> dict[str, dict[str, float]]:
        """Return ecliptic positions for ``bodies`` at ``iso_utc``."""

        moment = _parse_iso8601(iso_utc)
        jd_ut = self._adapter.julian_day(moment)
        results: dict[str, dict[str, float]] = {}
        for body in bodies:
            body_id = _resolve_body_id(body)
            body_name = body if isinstance(body, str) else str(body_id)
            sample = self._adapter.body_position(jd_ut, body_id, body_name=str(body_name))
            results[str(body_name)] = {
                "longitude": float(sample.longitude),
                "latitude": float(sample.latitude),
                "distance_au": float(sample.distance_au),
            }
        return results


_PROVIDER_FACTORIES: dict[str, type[SwissProvider]] = {
    SwissProvider.provider_id: SwissProvider,
}


def list_providers() -> list[str]:
    """Return available provider identifiers."""

    return sorted(_PROVIDER_FACTORIES)


def get_provider(name: str) -> SwissProvider:
    """Instantiate a provider by identifier."""

    key = name.lower()
    try:
        factory = _PROVIDER_FACTORIES[key]
    except KeyError as exc:
        raise KeyError(f"Unknown provider: {name}") from exc
    return factory()


__all__ = [
    "CacheInfo",
    "CacheStatus",
    "EphemerisBatch",
    "EphemerisProvider",
    "EphemerisVector",
    "ProviderError",
    "ProviderMetadata",
    "SwissProvider",
    "get_provider",
    "list_providers",
]
