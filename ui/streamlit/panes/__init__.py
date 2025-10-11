"""Utilities for managing Streamlit dashboard panes."""

from .catalog import PaneSpec, load_registered_panes, register_pane

__all__ = ["PaneSpec", "load_registered_panes", "register_pane"]
