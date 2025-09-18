"""Exporter helpers for AstroEngine outputs."""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["event_to_row", "_event_to_row"]


# >>> AUTO-GEN BEGIN: Exporters Domain Fields v1.0
# When writing SQLite or Parquet, include `elements`, `domains`, `domain_profile` if present on event.
# Example for row dict assembly:

def _event_to_row(event_obj: Any) -> Dict[str, Any]:
    row = getattr(event_obj, "__dict__", {}).copy()
    # Ensure optional fields exist; downstream schemas tolerate absence
    row.setdefault("elements", [])
    row.setdefault("domains", {})
    row.setdefault("domain_profile", None)
    return row


def event_to_row(event_obj: Any) -> Dict[str, Any]:
    """Public wrapper around :func:`_event_to_row` for external exporters."""

    return _event_to_row(event_obj)

# >>> AUTO-GEN END: Exporters Domain Fields v1.0
