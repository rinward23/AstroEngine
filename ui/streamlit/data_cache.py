"""Shared Streamlit cache helpers for heavy catalog datasets."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List

import streamlit as st


def _to_dict(entry: Any) -> Dict[str, Any]:
    """Return a dictionary representation for dataclass-like ``entry``."""

    if is_dataclass(entry):
        return asdict(entry)
    if hasattr(entry, "_asdict"):
        return dict(entry._asdict())  # type: ignore[no-untyped-call]
    if isinstance(entry, dict):
        return dict(entry)
    if hasattr(entry, "__dict__"):
        return {key: value for key, value in vars(entry).items()}
    raise TypeError(f"Unsupported catalog entry type: {type(entry)!r}")


@st.cache_data(show_spinner=False)
def load_fixed_star_catalog(catalog: str = "robson") -> List[Dict[str, Any]]:
    """Load the fixed-star catalog identified by ``catalog`` with caching."""

    from astroengine.analysis.fixed_stars import load_catalog

    stars = load_catalog(catalog)
    return [_to_dict(star) for star in stars]


@st.cache_data(show_spinner=False)
def load_dignities_table() -> List[Dict[str, Any]]:
    """Load the essential dignities table with caching for Streamlit apps."""

    from astroengine.scoring import load_dignities

    records = load_dignities()
    return [_to_dict(record) for record in records]


__all__ = ["load_fixed_star_catalog", "load_dignities_table"]
