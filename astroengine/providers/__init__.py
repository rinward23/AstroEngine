# >>> AUTO-GEN BEGIN: AE Providers Registry v1.0
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Protocol

from ..canonical import BodyPosition
from .se_fixedstars import get_star_lonlat as get_star_lonlat
from .sweph_bridge import ensure_sweph_alias

ensure_sweph_alias()

LOG = logging.getLogger(__name__)


class EphemerisProvider(Protocol):
    """Provider contract returning canonical body positions.

    Implementations continue to expose the legacy :meth:`positions_ecliptic` batch API,
    while :meth:`position` offers a canonical :class:`~astroengine.canonical.BodyPosition`
    view for single-body sampling.
    """

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


def register_provider(name: str, provider: EphemerisProvider) -> None:
    _REGISTRY[name] = provider


def get_provider(name: str = "swiss") -> EphemerisProvider:
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(
            f"provider '{name}' not registered; available={list(_REGISTRY)}"
        ) from e


def list_providers() -> Iterable[str]:
    return sorted(_REGISTRY)


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


# >>> AUTO-GEN END: AE Providers Registry v1.0
