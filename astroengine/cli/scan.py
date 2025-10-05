"""Transit scanning command integration for the modular CLI."""

from __future__ import annotations

from .channels.transit.scan import add_subparser, run

__all__ = ["add_subparser", "run"]
