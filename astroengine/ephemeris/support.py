"""Support probing helpers for ephemeris providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from ..core.bodies import canonical_name

__all__ = ["SupportIssue", "filter_supported"]


@dataclass(slots=True)
class SupportIssue:
    """Represents a provider capability issue for a specific body."""

    body: str
    reason: str


def _probe_position(provider, body: str, iso_utc: str) -> None:
    """Attempt to fetch a position for ``body`` at ``iso_utc``."""

    if hasattr(provider, "position"):
        provider.position(body, iso_utc)
    else:  # pragma: no cover - fallback path for legacy providers
        provider.positions_ecliptic(iso_utc, [body])


def filter_supported(
    bodies: Iterable[str],
    provider,
    *,
    probe_iso: str | None = None,
) -> Tuple[List[str], List[SupportIssue]]:
    """Partition ``bodies`` into supported and unsupported lists for ``provider``."""

    seen: set[str] = set()
    ok: List[str] = []
    issues: List[SupportIssue] = []
    probe_time = probe_iso or getattr(provider, "probe_time_iso", None) or "2000-01-01T00:00:00Z"

    for name in bodies:
        if not name:
            continue
        canonical = canonical_name(name)
        identity = canonical or name
        if identity in seen:
            continue
        seen.add(identity)
        attempts = []
        if canonical:
            attempts.append(canonical)
        if name not in attempts:
            attempts.insert(0, name)
        last_error: Exception | None = None
        for attempt in attempts:
            try:
                _probe_position(provider, attempt, probe_time)
            except Exception as exc:  # pragma: no cover - defensive logging
                last_error = exc
                continue
            else:
                ok.append(canonical_name(attempt) or attempt)
                break
        else:
            reason = str(last_error) if last_error else "unsupported"
            issues.append(SupportIssue(body=identity, reason=reason))
    return ok, issues
