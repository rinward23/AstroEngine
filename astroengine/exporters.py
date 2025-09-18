"""Exporter helpers for AstroEngine."""

from __future__ import annotations


def _event_to_row(event_obj):
    """Return a dictionary representation of ``event_obj`` suitable for persistence."""

    row = getattr(event_obj, "__dict__", {}).copy()
    row.setdefault("elements", [])
    row.setdefault("domains", {})
    row.setdefault("domain_profile", None)
    return row


__all__ = ["_event_to_row"]
