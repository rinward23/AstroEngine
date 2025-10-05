"""Streamlit UI helpers and global configuration hooks."""

from __future__ import annotations

import logging
import uuid
from typing import Any

try:  # pragma: no cover - import guard for optional dependency
    import streamlit as _st
except ModuleNotFoundError as exc:  # pragma: no cover - defensive
    raise RuntimeError("Streamlit must be available to use ui.streamlit") from exc

_LOG = logging.getLogger("ui.streamlit.errors")


def _render_error_id(container: Any, error_id: str) -> None:
    """Attach a caption/code snippet with the error identifier to ``container``."""

    if container is None:
        return
    try:
        caption = getattr(container, "caption", None)
        code = getattr(container, "code", None)
        if callable(caption):
            caption("Error ID (click to copy):")
        if callable(code):
            code(error_id, language=None)
    except Exception:  # pragma: no cover - UI rendering best-effort
        pass


def _normalize_exc_info(exc_info: Any) -> Any:
    """Convert ``exc_info`` into a ``logging``-friendly shape."""

    if isinstance(exc_info, BaseException):
        return (type(exc_info), exc_info, exc_info.__traceback__)
    return exc_info


def _install_error_wrapper() -> None:
    """Wrap :func:`streamlit.error` with logging + toast instrumentation."""

    if getattr(_st.error, "__astroengine_wrapped__", False):  # pragma: no cover - idempotent
        return

    original_error = _st.error

    def error_with_tracking(
        body: Any,
        icon: str | None = None,
        *,
        logger: logging.Logger | logging.LoggerAdapter | None = None,
        exc_info: Any | None = None,
    ):
        error_id = uuid.uuid4().hex[:12].upper()
        message = "" if body is None else str(body)
        log = logger or _LOG
        log_kwargs = {"extra": {"error_id": error_id}}
        normalized_exc = _normalize_exc_info(exc_info)

        if normalized_exc:
            log.error("Error %s: %s", error_id, message, exc_info=normalized_exc, **log_kwargs)
        else:
            log.error("Error %s: %s", error_id, message, **log_kwargs)

        toast_func = getattr(_st, "toast", None)
        if callable(toast_func):
            toast = toast_func(message or "An unexpected error occurred.", icon=icon or "⚠️")
            _render_error_id(toast, error_id)

        result = original_error(body, icon=icon)
        _render_error_id(result, error_id)

        try:  # pragma: no cover - attribute may not exist on shim
            setattr(result, "error_id", error_id)
        except Exception:
            pass

        return result

    error_with_tracking.__astroengine_wrapped__ = True  # type: ignore[attr-defined]
    error_with_tracking.__wrapped__ = original_error  # type: ignore[attr-defined]
    _st.error = error_with_tracking  # type: ignore[assignment]


_install_error_wrapper()
