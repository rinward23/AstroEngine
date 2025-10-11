# >>> AUTO-GEN BEGIN: AE Providers Registry v1.0
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Any, Protocol

from ..canonical import BodyPosition
from .se_fixedstars import get_star_lonlat as get_star_lonlat
from .sweph_bridge import ensure_sweph_alias

ensure_sweph_alias()

LOG = logging.getLogger(__name__)

__all__ = [
    "BodyPosition",
    "EphemerisProvider",
    "ProviderError",
    "ProviderMetadata",
    "get_provider",
    "get_provider_metadata",
    "get_provider_metadata_for_name",
    "get_star_lonlat",
    "list_provider_metadata",
    "list_providers",
    "load_entry_point_providers",
    "register_provider",
    "register_provider_metadata",
]


class ProviderError(RuntimeError):
    """Structured error raised when a provider cannot satisfy a request."""

    def __init__(
        self,
        message: str,
        *,
        provider_id: str | None = None,
        error_code: str | None = None,
        retriable: bool = False,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.provider_id = provider_id
        self.error_code = error_code
        self.retriable = retriable
        self.context = dict(context or {})


@dataclass(frozen=True)
class ProviderMetadata:
    """Describes the provenance and capabilities for an ephemeris provider."""

    provider_id: str
    version: str | None
    supported_bodies: Sequence[str]
    supported_frames: Sequence[str]
    supports_declination: bool
    supports_light_time: bool
    cache_layout: Mapping[str, str]
    extras_required: Sequence[str] = ()
    description: str | None = None
    module: str | None = None
    available: bool = True

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable copy of the metadata."""

        return {
            "provider_id": self.provider_id,
            "version": self.version,
            "supported_bodies": list(self.supported_bodies),
            "supported_frames": list(self.supported_frames),
            "supports_declination": self.supports_declination,
            "supports_light_time": self.supports_light_time,
            "cache_layout": dict(self.cache_layout),
            "extras_required": list(self.extras_required),
            "description": self.description,
            "module": self.module,
            "available": self.available,
        }


class EphemerisProvider(Protocol):
    """Provider contract returning canonical body positions."""

    def positions_ecliptic(
        self,
        iso_utc: str,
        bodies: Iterable[str],
    ) -> dict[str, dict[str, float]]:
        """Return mapping body -> {lon, decl, speed_lon?} for the given UTC timestamp."""

        ...

    def position(self, body: str, ts_utc: str) -> BodyPosition:
        """Fetch a canonical body position at the supplied UTC timestamp."""

        ...


_REGISTRY: dict[str, EphemerisProvider] = {}
_METADATA_REGISTRY: dict[str, ProviderMetadata] = {}
_NAME_TO_PROVIDER_ID: dict[str, str] = {}


def _normalize_metadata(
    metadata: ProviderMetadata | Mapping[str, Any] | None,
) -> ProviderMetadata | None:
    if metadata is None:
        return None
    if isinstance(metadata, ProviderMetadata):
        return metadata
    if isinstance(metadata, Mapping):
        return ProviderMetadata(**metadata)
    raise TypeError("metadata must be ProviderMetadata or mapping")


def register_provider_metadata(
    metadata: ProviderMetadata,
    *,
    overwrite: bool = False,
) -> None:
    """Register provider metadata for governance and audit tooling."""

    provider_id = metadata.provider_id
    if not overwrite and provider_id in _METADATA_REGISTRY:
        raise ValueError(f"metadata for provider '{provider_id}' already registered")
    _METADATA_REGISTRY[provider_id] = metadata


def register_provider(
    name: str,
    provider: EphemerisProvider,
    *,
    metadata: ProviderMetadata | Mapping[str, Any] | None = None,
    aliases: Sequence[str] = (),
) -> None:
    """Register ``provider`` under ``name`` and optional ``aliases``."""

    keys = [name, *aliases]
    duplicates = [key for key in keys if key in _REGISTRY]
    if duplicates:
        raise ValueError(f"provider name(s) already registered: {duplicates}")

    for key in keys:
        _REGISTRY[key] = provider

    meta_obj = _normalize_metadata(metadata)
    if meta_obj is not None:
        register_provider_metadata(meta_obj, overwrite=True)
        provider_id = meta_obj.provider_id
    else:
        provider_id = getattr(provider, "provider_id", None)

    if provider_id:
        for key in keys:
            _NAME_TO_PROVIDER_ID[key] = provider_id


def get_provider(name: str = "swiss") -> EphemerisProvider:
    try:
        return _REGISTRY[name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise KeyError(
            f"provider '{name}' not registered; available={list(_REGISTRY)}"
        ) from exc


def list_providers() -> Iterable[str]:
    return sorted(_REGISTRY)


def get_provider_metadata(provider_id: str) -> ProviderMetadata:
    try:
        return _METADATA_REGISTRY[provider_id]
    except KeyError as exc:
        raise KeyError(f"metadata for provider '{provider_id}' not registered") from exc


def get_provider_metadata_for_name(name: str) -> ProviderMetadata:
    provider_id = _NAME_TO_PROVIDER_ID.get(name)
    if provider_id is None:
        raise KeyError(f"no metadata associated with provider '{name}'")
    return get_provider_metadata(provider_id)


def list_provider_metadata() -> Iterable[str]:
    return sorted(_METADATA_REGISTRY)


def _coerce_entrypoint_payload(
    entry_name: str,
    payload: Any,
) -> tuple[EphemerisProvider | None, ProviderMetadata | Mapping[str, Any] | None, Sequence[str]]:
    provider: EphemerisProvider | None = None
    metadata: ProviderMetadata | Mapping[str, Any] | None = None
    aliases: Sequence[str] = ()

    obj = payload() if callable(payload) and not hasattr(payload, "positions_ecliptic") else payload

    if isinstance(obj, tuple) and obj:
        provider = obj[0]  # type: ignore[assignment]
        if len(obj) > 1:
            metadata = obj[1]  # type: ignore[assignment]
        if len(obj) > 2 and isinstance(obj[2], Sequence):
            aliases = obj[2]
    elif hasattr(obj, "positions_ecliptic") and hasattr(obj, "position"):
        provider = obj  # type: ignore[assignment]
        metadata = getattr(obj, "metadata", None)
        aliases = tuple(getattr(obj, "aliases", ()))

    if provider is None:
        LOG.warning(
            "entry point '%s' did not return an EphemerisProvider",
            entry_name,
            extra={"err_code": "PROVIDER_ENTRYPOINT_INVALID"},
        )
        return None, None, ()

    return provider, metadata, aliases


def load_entry_point_providers(group: str = "astroengine.providers") -> list[str]:
    """Load and register providers exposed via entry points."""

    loaded: list[str] = []
    try:
        entry_points = importlib_metadata.entry_points()
    except Exception as exc:  # pragma: no cover - importlib failures are rare
        LOG.warning(
            "failed to enumerate provider entry points",
            extra={"err_code": "PROVIDER_ENTRYPOINT_DISCOVERY"},
            exc_info=exc,
        )
        return loaded

    if hasattr(entry_points, "select"):
        candidates = entry_points.select(group=group)
    else:  # pragma: no cover - legacy importlib
        candidates = [ep for ep in entry_points if getattr(ep, "group", None) == group]

    for entry in candidates:
        try:
            payload = entry.load()
        except Exception as exc:  # pragma: no cover - defensive logging
            LOG.exception(
                "failed to load provider entry point",
                extra={
                    "err_code": "PROVIDER_ENTRYPOINT_LOAD",
                    "entry_point": entry.name,
                },
            )
            continue

        provider, metadata, aliases = _coerce_entrypoint_payload(entry.name, payload)
        if provider is None:
            continue

        metadata_obj = _normalize_metadata(metadata)
        provider_name = getattr(provider, "provider_id", entry.name)

        try:
            register_provider(provider_name, provider, metadata=metadata_obj, aliases=aliases)
        except ValueError:
            LOG.warning(
                "provider '%s' already registered; skipping entry point",
                provider_name,
                extra={"err_code": "PROVIDER_ENTRYPOINT_DUPLICATE"},
            )
            continue

        loaded.append(provider_name)

    return loaded


# Eagerly import built-in providers so they register themselves.
try:  # pragma: no cover
    from . import swiss_provider as _swiss  # noqa: F401
except ImportError:
    LOG.info(
        "swiss provider unavailable",
        extra={"err_code": "PROVIDER_IMPORT", "provider": "swiss"},
        exc_info=True,
    )
except Exception:
    LOG.exception(
        "unexpected provider import failure",
        extra={"err_code": "PROVIDER_IMPORT_UNEXPECTED", "provider": "swiss"},
    )

try:  # pragma: no cover
    from . import skyfield_provider as _skyfield  # noqa: F401
except ImportError:
    LOG.info(
        "skyfield provider unavailable",
        extra={"err_code": "PROVIDER_IMPORT", "provider": "skyfield"},
        exc_info=True,
    )
except Exception:
    LOG.exception(
        "unexpected provider import failure",
        extra={"err_code": "PROVIDER_IMPORT_UNEXPECTED", "provider": "skyfield"},
    )


# >>> AUTO-GEN END: AE Providers Registry v2.0
