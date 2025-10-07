"""Utilities for loading optional runtime dependencies safely."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from importlib import import_module, util
from types import ModuleType

__all__ = ["dependency_available", "require_dependency"]


def dependency_available(module_name: str) -> bool:
    """Return ``True`` when ``module_name`` can be imported.

    This helper avoids importing heavy modules eagerly while still letting callers
    fast-path code paths that only work when the optional package is present.
    """

    return util.find_spec(module_name) is not None


def require_dependency(
    module_name: str,
    *,
    package: str | None = None,
    extras: str | Sequence[str] | None = None,
    purpose: str | None = None,
) -> ModuleType:
    """Import ``module_name`` or raise a descriptive :class:`ModuleNotFoundError`.

    Parameters
    ----------
    module_name:
        Fully-qualified module path to import.
    package:
        Optional PyPI package name to reference in the error message. Defaults to
        ``module_name`` when omitted.
    extras:
        Optional extra or extras that satisfy the dependency. When provided the
        error explains how to install ``astroengine`` with those extras enabled.
    purpose:
        Optional human friendly description of what the dependency unlocks.
    """

    if dependency_available(module_name):
        return import_module(module_name)

    dependency = package or module_name
    message = f"{dependency} is required"
    if purpose:
        message += f" to {purpose}"
    message += "."

    if extras:
        if isinstance(extras, str):
            extras_tokens: Iterable[str] = [extras]
        else:
            extras_tokens = extras
        joined = ",".join(sorted({extra.strip() for extra in extras_tokens if extra.strip()}))
        if joined:
            message += f" Install with `pip install -e .[{joined}]`."

    raise ModuleNotFoundError(message)

