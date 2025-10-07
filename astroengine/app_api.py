# >>> AUTO-GEN BEGIN: App Scan Wrapper v1.1
from __future__ import annotations

import importlib
import inspect
import logging
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import asdict, is_dataclass
from typing import Any

# Canonical adapters; tolerate absence if CP not yet applied
LOG = logging.getLogger(__name__)

try:
    from .canonical import events_from_any
except Exception as exc:  # pragma: no cover
    LOG.debug("Falling back to passthrough events_from_any: %s", exc)

    def events_from_any(seq: Iterable[Any]) -> list[Any]:
        return list(seq)


ScanCandidate = tuple[str, str]  # (module, function)
ScanSpec = ScanCandidate | str

try:  # pragma: no cover - optional OpenTelemetry dependency
    from opentelemetry import trace as _scan_trace
    from opentelemetry.trace import Status, StatusCode
except Exception as exc:  # pragma: no cover - otel not installed
    LOG.debug("OpenTelemetry tracer unavailable: %s", exc)
    _scan_trace = None
    Status = None  # type: ignore[assignment]
    StatusCode = None  # type: ignore[assignment]
SCAN_ENTRYPOINT_ENV = "ASTROENGINE_SCAN_ENTRYPOINTS"
DEFAULT_SCAN_ENTRYPOINTS: tuple[ScanCandidate, ...] = (
    ("astroengine.core.transit_engine", "scan_window"),
    ("astroengine.core.transit_engine", "scan_contacts"),
    ("astroengine.engine", "scan_window"),
    ("astroengine.engine", "scan_contacts"),
)


def _scan_tracer():
    if _scan_trace is None:
        return None
    return _scan_trace.get_tracer("astroengine.app.scan")


def _start_scan_span(name: str, attributes: dict[str, Any] | None = None):
    tracer = _scan_tracer()
    if tracer is None:
        return nullcontext(None)
    return tracer.start_as_current_span(name, attributes=attributes or {})


def _record_span_error(span: Any, exc: Exception) -> None:
    if span is None:
        return
    if hasattr(span, "record_exception"):
        span.record_exception(exc)
    if Status is not None and StatusCode is not None:
        try:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
        except Exception as span_exc:  # pragma: no cover - defensive guard
            LOG.debug("Unable to tag tracing span with error: %s", span_exc)


def _parse_entrypoint_spec(spec: str) -> ScanCandidate | None:
    raw = spec.strip()
    if not raw:
        return None
    if "#" in raw:
        raw = raw.split("#", 1)[0].strip()
    if not raw:
        return None
    if ":" in raw:
        mod, fn = raw.split(":", 1)
    elif "." in raw:
        mod, fn = raw.rsplit(".", 1)
    else:
        return None
    mod = mod.strip()
    fn = fn.strip()
    if not mod or not fn:
        return None
    return mod, fn


def _normalize_entrypoints(
    entrypoints: Iterable[ScanSpec] | None,
) -> list[ScanCandidate]:
    normalized: list[ScanCandidate] = []
    if not entrypoints:
        return normalized
    for item in entrypoints:
        candidate: ScanCandidate | None
        if isinstance(item, tuple) and len(item) == 2:
            candidate = (str(item[0]), str(item[1]))
        elif isinstance(item, str):
            candidate = _parse_entrypoint_spec(item)
        else:
            candidate = None
        if not candidate:
            continue
        mod, fn = candidate
        mod = mod.strip()
        fn = fn.strip()
        if mod and fn:
            normalized.append((mod, fn))
    return normalized


def _env_entrypoints() -> list[ScanCandidate]:
    raw = os.getenv(SCAN_ENTRYPOINT_ENV, "")
    if not raw:
        return []
    parts = [p for p in re.split(r"[\s,;]+", raw) if p]
    return [c for part in parts if (c := _parse_entrypoint_spec(part))]


def _candidate_order(
    entrypoints: Iterable[ScanSpec] | None = None,
) -> list[ScanCandidate]:
    ordered: list[ScanCandidate] = []
    seen: set[ScanCandidate] = set()

    def add_candidates(cands: Iterable[ScanCandidate]) -> None:
        for cand in cands:
            if cand in seen:
                continue
            ordered.append(cand)
            seen.add(cand)

    add_candidates(_normalize_entrypoints(entrypoints))
    add_candidates(_env_entrypoints())
    add_candidates(DEFAULT_SCAN_ENTRYPOINTS)
    return ordered


def available_scan_entrypoints(
    entrypoints: Iterable[ScanSpec] | None = None,
) -> list[ScanCandidate]:
    """Discover scan functions across old/new engine layouts and env overrides."""

    found: list[ScanCandidate] = []
    for mod, fn in _candidate_order(entrypoints):
        try:
            module = importlib.import_module(mod)
        except Exception:
            continue
        attr = getattr(module, fn, None)
        if callable(attr):
            found.append((mod, fn))
    return found


def _filter_kwargs_for(fn, proposed: dict[str, Any]) -> dict[str, Any]:
    """
    Pass only kwargs the function actually accepts.
    Supports common alias keys for start/end/provider/profile fields.
    """
    sig = inspect.signature(fn)
    params = set(sig.parameters.keys())

    alias_map = {
        "start_utc": ["start", "start_ts", "start_time", "window_start", "utc_start"],
        "end_utc": ["end", "end_ts", "end_time", "window_end", "utc_end"],
        "moving": ["moving", "movers", "bodies", "transiting"],
        "targets": ["targets", "natal", "static"],
        "provider": ["provider", "provider_name"],
        "profile_id": ["profile", "profile_id"],
        "step_minutes": ["step_minutes", "step_min", "step"],
        "sidereal": ["sidereal", "use_sidereal", "sidereal_flag"],
        "ayanamsha": ["ayanamsha", "ayanamsa", "sidereal_ayanamsha"],
        "detectors": ["detectors", "detector_flags", "features", "feature_flags"],
        "target_frames": ["target_frames", "target_frame", "frames", "target_contexts"],
    }

    final: dict[str, Any] = {}
    expanded: dict[str, Any] = dict(proposed)
    for key, aliases in alias_map.items():
        if key in proposed:
            for alias in aliases:
                expanded.setdefault(alias, proposed[key])

    for key in list(expanded.keys()):
        if key in params:
            final[key] = expanded[key]
    return final


def _event_like_to_dict(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, Mapping):
        return dict(obj)
    if hasattr(obj, "model_dump"):
        try:
            dumped = obj.model_dump()
        except Exception:
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if hasattr(obj, "_asdict"):
        try:
            dumped = obj._asdict()
        except Exception:
            dumped = None
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            return None
    if hasattr(obj, "__dict__"):
        try:
            return dict(vars(obj))
        except Exception:
            return None
    try:
        return dict(obj)  # type: ignore[arg-type]
    except Exception:
        return None


def _normalize_result_payload(result: Any) -> list[dict[str, Any]] | None:
    if result is None:
        return None
    payload: Any = result
    if isinstance(payload, Mapping):
        items: Sequence[Any] = [payload]
    else:
        events_attr = getattr(payload, "events", None)
        if events_attr is not None:
            payload = events_attr() if callable(events_attr) else events_attr
        if isinstance(payload, Mapping):
            items = [payload]
        elif isinstance(payload, list | tuple):
            items = list(payload)
        else:
            if isinstance(payload, str | bytes):
                return None
            try:
                items = list(payload)
            except TypeError:
                return None
    normalized: list[dict[str, Any]] = []
    for item in items:
        event_dict = _event_like_to_dict(item)
        if event_dict is None:
            return None
        normalized.append(event_dict)
    return normalized


def _format_run_failure(errors: Sequence[str]) -> str:
    base = "No usable scan entrypoint found."
    if not errors:
        detail = " No candidate modules could be imported."
    else:
        detail = " Tried:\n- " + "\n- ".join(errors)
    if os.getenv(SCAN_ENTRYPOINT_ENV):
        detail += f"\nCandidates include overrides from ${SCAN_ENTRYPOINT_ENV}."
    return base + detail


def run_scan_or_raise(
    start_utc: str,
    end_utc: str,
    moving: Iterable[str],
    targets: Iterable[str],
    provider: str | None = None,
    profile_id: str | None = None,
    step_minutes: int = 60,
    detectors: Iterable[str] | None = None,
    target_frames: Iterable[str] | None = None,
    sidereal: bool | None = None,
    ayanamsha: str | None = None,
    entrypoints: Iterable[ScanSpec] | None = None,
    return_used_entrypoint: bool = False,
    zodiac: str | None = None,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], ScanCandidate]:
    """
    Try known scan entrypoints, call the first that matches a compatible signature,
    and return a plain list of event dicts (canonicalizable).

    When ``return_used_entrypoint`` is ``True`` the return value is a tuple of
    ``(events, (module, function))`` describing the entrypoint that produced the
    events.
    """

    moving_list = list(moving)
    target_list = list(targets)
    detectors_list = list(detectors) if detectors else []
    target_frames_list = list(target_frames) if target_frames else []
    candidates = _candidate_order(entrypoints)
    errors: list[str] = []

    run_attrs: dict[str, Any] = {
        "astroengine.scan.entrypoint_count": len(candidates),
        "astroengine.scan.moving_count": len(moving_list),
        "astroengine.scan.target_count": len(target_list),
    }
    if provider:
        run_attrs["astroengine.scan.provider"] = provider
    if profile_id:
        run_attrs["astroengine.scan.profile_id"] = profile_id
    if sidereal is not None:
        run_attrs["astroengine.scan.sidereal"] = bool(sidereal)
    if ayanamsha:
        run_attrs["astroengine.scan.ayanamsha"] = ayanamsha
    if detectors_list:
        run_attrs["astroengine.scan.detector_count"] = len(detectors_list)
    if target_frames_list:
        run_attrs["astroengine.scan.target_frame_count"] = len(target_frames_list)

    with _start_scan_span("astroengine.scan.run", run_attrs) as run_span:
        for mod, fn_name in candidates:
            try:
                module = importlib.import_module(mod)
            except Exception as exc:  # pragma: no cover - import failure surfaces in UI
                errors.append(f"{mod}.{fn_name}: import failed ({exc})")
                if run_span is not None and hasattr(run_span, "add_event"):
                    run_span.add_event(
                        "astroengine.scan.import_failed",
                        {
                            "module": mod,
                            "function": fn_name,
                            "error": str(exc),
                        },
                    )
                continue
            fn = getattr(module, fn_name, None)
            if not callable(fn):
                errors.append(f"{mod}.{fn_name}: attribute is not callable")
                if run_span is not None and hasattr(run_span, "add_event"):
                    run_span.add_event(
                        "astroengine.scan.invalid_entrypoint",
                        {"module": mod, "function": fn_name},
                    )
                continue
            kwargs: dict[str, Any] = dict(
                start_utc=start_utc,
                end_utc=end_utc,
                moving=list(moving_list),
                targets=list(target_list),
                provider=provider,
                step_minutes=step_minutes,
                zodiac=zodiac,
                ayanamsha=ayanamsha,
            )
            optional_kwargs: dict[str, Any] = {}
            if profile_id is not None:
                optional_kwargs["profile_id"] = profile_id
            if detectors_list:
                optional_kwargs["detectors"] = list(detectors_list)
            if target_frames_list:
                optional_kwargs["target_frames"] = list(target_frames_list)
            if sidereal is not None:
                optional_kwargs["sidereal"] = bool(sidereal)
            if ayanamsha:
                optional_kwargs["ayanamsha"] = ayanamsha
            kwargs.update(optional_kwargs)
            call_kwargs = _filter_kwargs_for(fn, kwargs)
            entry_attrs: dict[str, Any] = {
                "astroengine.scan.entrypoint": f"{mod}.{fn_name}",
                "astroengine.scan.call_arg_count": len(call_kwargs),
            }
            if detectors_list:
                entry_attrs["astroengine.scan.detector_count"] = len(detectors_list)
            if target_frames_list:
                entry_attrs["astroengine.scan.target_frame_count"] = len(
                    target_frames_list
                )
            with _start_scan_span(
                "astroengine.scan.entrypoint", entry_attrs
            ) as entry_span:
                try:
                    result = fn(**call_kwargs)  # type: ignore[arg-type]
                except Exception as exc:
                    errors.append(f"{mod}.{fn_name}: {exc}")
                    _record_span_error(entry_span, exc)
                    if run_span is not None and hasattr(run_span, "add_event"):
                        run_span.add_event(
                            "astroengine.scan.entrypoint_error",
                            {
                                "module": mod,
                                "function": fn_name,
                                "error": str(exc),
                            },
                        )
                    continue
            events = _normalize_result_payload(result)
            if events is not None:
                event_count = len(events)
                if entry_span is not None and hasattr(entry_span, "set_attribute"):
                    entry_span.set_attribute("astroengine.scan.event_count", event_count)
                if run_span is not None and hasattr(run_span, "set_attribute"):
                    run_span.set_attribute(
                        "astroengine.scan.used_entrypoint",
                        f"{mod}.{fn_name}",
                    )
                    run_span.set_attribute("astroengine.scan.event_count", event_count)
                return (events, (mod, fn_name)) if return_used_entrypoint else events
            errors.append(f"{mod}.{fn_name}: returned no events")
            if entry_span is not None:
                if hasattr(entry_span, "set_attribute"):
                    entry_span.set_attribute("astroengine.scan.event_count", 0)
                if hasattr(entry_span, "add_event"):
                    entry_span.add_event(
                        "astroengine.scan.no_events",
                        {"module": mod, "function": fn_name},
                    )
        if run_span is not None and hasattr(run_span, "set_attribute"):
            run_span.set_attribute("astroengine.scan.error_count", len(errors))
    raise RuntimeError(_format_run_failure(errors))


def canonicalize_events(objs: Iterable[Any]):
    """Return canonical :class:`TransitEvent` instances when adapters exist."""

    try:
        return events_from_any(objs)
    except Exception:
        return list(objs)


__all__ = [
    "available_scan_entrypoints",
    "run_scan_or_raise",
    "canonicalize_events",
]
# >>> AUTO-GEN END: App Scan Wrapper v1.1
