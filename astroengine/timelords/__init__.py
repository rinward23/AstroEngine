"""Timelord techniques such as profections."""

from __future__ import annotations

from .dashas import compute_vimshottari_dasha
from .profections import annual_profections
from .zr import compute_zodiacal_releasing

__all__ = [
    "annual_profections",
    "compute_vimshottari_dasha",
    "compute_zodiacal_releasing",
]
