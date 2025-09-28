"""Core channel for synastry engine computations."""

from __future__ import annotations

from . import matrix as _matrix
from .matrix import *  # noqa: F401,F403

__all__ = list(_matrix.__all__)

del _matrix

