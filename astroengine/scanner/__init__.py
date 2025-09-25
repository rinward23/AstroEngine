"""Compatibility layer exposing legacy scanner APIs."""

from __future__ import annotations

from .contacts import detect_antiscia_contacts, detect_decl_contacts

__all__ = [
    "detect_antiscia_contacts",
    "detect_decl_contacts",
]
