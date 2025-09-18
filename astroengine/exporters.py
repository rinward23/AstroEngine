"""Exporter helpers for AstroEngine runtimes."""

from __future__ import annotations

from typing import Any, Dict


# >>> AUTO-GEN BEGIN: Exporters Domain Fields v1.0


def _event_to_row(event_obj: Any) -> Dict[str, Any]:
    row = getattr(event_obj, "__dict__", {}).copy()
    row.setdefault("elements", [])
    row.setdefault("domains", {})
    row.setdefault("domain_profile", None)
    return row


# >>> AUTO-GEN END: Exporters Domain Fields v1.0


__all__ = ["_event_to_row"]

