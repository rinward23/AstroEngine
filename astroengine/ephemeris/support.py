
"""Ephemeris capability probing helpers."""


from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SupportIssue:
    """Represents an unsupported body probe against a provider."""


    body: str
    reason: str



def _probe_timestamp(provider) -> str:
    value = getattr(provider, "probe_timestamp", None)
    if isinstance(value, str):
        return value
    return "2000-01-01T12:00:00Z"  # J2000 epoch


def filter_supported(bodies: Iterable[str], provider) -> tuple[list[str], list[SupportIssue]]:
    """Return (supported, issues) for ``bodies`` against ``provider``."""

    probe = getattr(provider, "position", None)
    if probe is None or not callable(probe):  # legacy providers may lack single-body API
        unique = []
        seen: set[str] = set()
        for body in bodies:
            name = str(body)
            if name not in seen:
                seen.add(name)
                unique.append(name)
        return unique, []

    supported: list[str] = []
    issues: list[SupportIssue] = []
    probe_ts = _probe_timestamp(provider)
    seen: set[str] = set()
    for body in bodies:
        name = str(body)
        if name in seen:
            continue
        seen.add(name)
        try:
            provider.position(name, probe_ts)
        except Exception as exc:  # pragma: no cover - defensive guard
            issues.append(SupportIssue(body=name, reason=str(exc)))
        else:
            supported.append(name)
    return supported, issues


__all__ = ["SupportIssue", "filter_supported"]

