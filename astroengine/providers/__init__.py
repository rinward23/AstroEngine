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

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping, Optional, Protocol, Sequence


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
    documentation_url: Optional[str] = None


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

    def configure(self, *, profile_flags: Mapping[str, object], options: Optional[Mapping[str, object]] = None) -> None:
        """Apply profile-specific configuration.

        Implementations MUST be idempotent and only mutate internal caches.
        Raising :class:`ProviderError` signals misconfiguration.
        """

    def prime_cache(self, *, start: datetime, end: datetime, bodies: Sequence[str], cadence_hours: float) -> CacheInfo:
        """Warm ephemeris caches for the requested window.

        Providers may download ephemeris files, but MUST verify checksums and
        refuse to continue when validation fails.
        """

    def query(self, *, timestamps: Sequence[datetime], bodies: Sequence[str], frame: str) -> EphemerisBatch:
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


__all__ = [
    "CacheInfo",
    "CacheStatus",
    "EphemerisBatch",
    "EphemerisProvider",
    "EphemerisVector",
    "ProviderError",
    "ProviderMetadata",
]
