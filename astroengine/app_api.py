# >>> AUTO-GEN BEGIN: App Scan Wrapper v1.1
from __future__ import annotations

import importlib
import inspect
import os
import re
from dataclasses import asdict, is_dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

# Canonical adapters; tolerate absence if CP not yet applied
try:
    from .canonical import events_from_any
except Exception:  # pragma: no cover
    def events_from_any(seq: Iterable[Any]) -> List[Any]:
        return list(seq)


ScanCandidate = Tuple[str, str]  # (module, function)
ScanSpec = Union[ScanCandidate, str]
SCAN_ENTRYPOINT_ENV = "ASTROENGINE_SCAN_ENTRYPOINTS"
DEFAULT_SCAN_ENTRYPOINTS: Tuple[ScanCandidate, ...] = (
    ("astroengine.core.transit_engine", "scan_window"),
    ("astroengine.core.transit_engine", "scan_contacts"),
    ("astroengine.engine", "scan_window"),
    ("astroengine.engine", "scan_contacts"),
)


def _parse_entrypoint_spec(spec: str) -> Optional[ScanCandidate]:
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


def _normalize_entrypoints(entrypoints: Optional[Iterable[ScanSpec]]) -> List[ScanCandidate]:
    normalized: List[ScanCandidate] = []
    if not entrypoints:
        return normalized
    for item in entrypoints:
        candidate: Optional[ScanCandidate]
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


def _env_entrypoints() -> List[ScanCandidate]:
    raw = os.getenv(SCAN_ENTRYPOINT_ENV, "")
    if not raw:
        return []
    parts = [p for p in re.split(r"[\s,;]+", raw) if p]
    return [c for part in parts if (c := _parse_entrypoint_spec(part))]


def _candidate_order(entrypoints: Optional[Iterable[ScanSpec]] = None) -> List[ScanCandidate]:
    ordered: List[ScanCandidate] = []
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


def available_scan_entrypoints(entrypoints: Optional[Iterable[ScanSpec]] = None) -> List[ScanCandidate]:
    """Discover scan functions across old/new engine layouts and env overrides."""

    found: List[ScanCandidate] = []
    for mod, fn in _candidate_order(entrypoints):
        try:
            module = importlib.import_module(mod)
        except Exception:
            continue
        attr = getattr(module, fn, None)
        if callable(attr):
            found.append((mod, fn))
    return found


def _filter_kwargs_for(fn, proposed: Dict[str, Any]) -> Dict[str, Any]:
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
    }

    final: Dict[str, Any] = {}
    expanded: Dict[str, Any] = dict(proposed)
    for key, aliases in alias_map.items():
        if key in proposed:
            for alias in aliases:
                expanded.setdefault(alias, proposed[key])

    for key in list(expanded.keys()):
        if key in params:
            final[key] = expanded[key]
    return final


def _event_like_to_dict(obj: Any) -> Optional[Dict[str, Any]]:
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


def _normalize_result_payload(result: Any) -> Optional[List[Dict[str, Any]]]:
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
        elif isinstance(payload, (list, tuple)):
            items = list(payload)
        else:
            if isinstance(payload, (str, bytes)):
                return None
            try:
                items = list(payload)
            except TypeError:
                return None
    normalized: List[Dict[str, Any]] = []
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
    provider: Optional[str] = None,
    profile_id: Optional[str] = None,
    step_minutes: int = 60,
    entrypoints: Optional[Iterable[ScanSpec]] = None,
    return_used_entrypoint: bool = False,
) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], ScanCandidate]]:
    """
    Try known scan entrypoints, call the first that matches a compatible signature,
    and return a plain list of event dicts (canonicalizable).

    When ``return_used_entrypoint`` is ``True`` the return value is a tuple of
    ``(events, (module, function))`` describing the entrypoint that produced the
    events.
    """

    errors: List[str] = []
    for mod, fn_name in _candidate_order(entrypoints):
        try:
            module = importlib.import_module(mod)
        except Exception as exc:  # pragma: no cover - import failure surfaces in UI
            errors.append(f"{mod}.{fn_name}: import failed ({exc})")
            continue
        fn = getattr(module, fn_name, None)
        if not callable(fn):
            errors.append(f"{mod}.{fn_name}: attribute is not callable")
            continue
        kwargs = dict(
            start_utc=start_utc,
            end_utc=end_utc,
            moving=list(moving),
            targets=list(targets),
            provider=provider,
            profile_id=profile_id or None,
            step_minutes=step_minutes,
        )
        call_kwargs = _filter_kwargs_for(fn, kwargs)
        try:
            result = fn(**call_kwargs)  # type: ignore[arg-type]
        except Exception as exc:
            errors.append(f"{mod}.{fn_name}: {exc}")
            continue
        events = _normalize_result_payload(result)
        if events is not None:
            return (events, (mod, fn_name)) if return_used_entrypoint else events
        errors.append(f"{mod}.{fn_name}: returned no events")
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
