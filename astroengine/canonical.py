# >>> AUTO-GEN BEGIN: Canonical Types & Adapters v1.0
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Protocol, Union

AspectName = Literal[
    "conjunction",
    "sextile",
    "square",
    "trine",
    "opposition",
    "semi-sextile",
    "semi-square",
    "sesquiquadrate",
    "quincunx",
]


@dataclass(frozen=True)
class BodyPosition:
    """Canonical instantaneous position returned/consumed across the engine.

    Attributes
    ----------
    lon:
        Ecliptic longitude in degrees in the range ``[0, 360)``.
    lat:
        Ecliptic latitude in degrees in the range ``[-90, +90]``.
    dec:
        Equatorial declination in degrees in the range ``[-90, +90]``.
    speed_lon:
        Instantaneous longitudinal motion in degrees per day.
    """

    lon: float
    lat: float
    dec: float
    speed_lon: float


@dataclass(frozen=True)
class TransitEvent:
    """Canonical transit event used by engine, exporters, and CLI.

    Attributes
    ----------
    ts:
        ISO-8601 UTC timestamp describing the instant of the transit.
    moving:
        Symbol describing the moving body, e.g. ``"Mars"``.
    target:
        Symbol describing the static body or chart point, e.g. ``"natal_Venus"``.
    aspect:
        Canonical aspect name captured by :data:`AspectName`.
    orb:
        Signed orb in degrees. Negative values denote an applying contact.
    applying:
        ``True`` when the moving body is applying at ``ts``.
    score:
        Optional composite score supplied by profiles or detectors.
    meta:
        Free-form metadata dictionary propagated across adapters/exporters.
    """

    ts: str
    moving: str
    target: str
    aspect: AspectName
    orb: float
    applying: bool
    score: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class _HasAttrs(Protocol):
    """Minimal attribute surface read from legacy classes."""

    ts: Any
    moving: Any
    target: Any
    aspect: Any
    orb: Any
    applying: Any
    score: Any
    meta: Any


def _get(d: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return default


def _coerce_aspect(val: Any) -> AspectName:
    if isinstance(val, str):
        v = val.strip().lower().replace(" ", "").replace("-", "")
        table = {
            "conjunction": "conjunction",
            "sextile": "sextile",
            "square": "square",
            "trine": "trine",
            "opposition": "opposition",
            "semisextile": "semi-sextile",
            "semisquare": "semi-square",
            "sesquiquadrate": "sesquiquadrate",
            "quincunx": "quincunx",
            "inconjunct": "quincunx",
        }
        if v in table:
            return table[v]  # type: ignore[return-value]
    raise ValueError(f"Unknown aspect name for canonicalization: {val!r}")


def event_from_legacy(obj: Union[Mapping[str, Any], _HasAttrs, TransitEvent]) -> TransitEvent:
    """Convert dicts/legacy classes into the canonical :class:`TransitEvent`."""

    if isinstance(obj, TransitEvent):
        return obj

    if hasattr(obj, "__dict__") and not isinstance(obj, dict):
        d = {
            "ts": getattr(obj, "ts", None),
            "moving": getattr(obj, "moving", None),
            "target": getattr(obj, "target", None),
            "aspect": getattr(obj, "aspect", getattr(obj, "kind", None)),
            "orb": getattr(obj, "orb", getattr(obj, "orb_abs", None)),
            "applying": getattr(obj, "applying", None),
            "score": getattr(obj, "score", None),
            "meta": getattr(obj, "meta", {}) or {},
        }
    else:
        d = dict(obj)  # shallow copy of mapping/dict

    ts = _get(d, "ts", "timestamp", "time", default=None)
    moving = _get(d, "moving", "mover", "transiting", default=None)
    target = _get(d, "target", "natal", "static", default=None)
    aspect_raw = _get(d, "aspect", "kind", default=None)
    orb = _get(d, "orb", "orb_abs", default=None)
    applying = _get(d, "applying", "is_applying", default=None)
    score = _get(d, "score", "severity", default=None)
    meta = _get(d, "meta", default={}) or {}

    if ts is None or moving is None or target is None or aspect_raw is None or orb is None or applying is None:
        raise ValueError(f"Cannot canonicalize event; missing required keys: {d}")

    return TransitEvent(
        ts=str(ts),
        moving=str(moving),
        target=str(target),
        aspect=_coerce_aspect(aspect_raw),
        orb=float(orb),
        applying=bool(applying),
        score=None if score is None else float(score),
        meta=dict(meta),
    )


def events_from_any(seq: Iterable[Union[Mapping[str, Any], _HasAttrs, TransitEvent]]) -> List[TransitEvent]:
    """Vector form of :func:`event_from_legacy` with strict conversion."""

    return [event_from_legacy(x) for x in seq]


def sqlite_write_canonical(db_path: str, events: Iterable[Union[Mapping[str, Any], _HasAttrs, TransitEvent]]) -> int:
    """Append canonical events to SQLite (table: ``transits_events``)."""

    import sqlite3

    evs = events_from_any(events)
    rows = [
        (
            e.ts,
            e.moving,
            e.target,
            e.aspect,
            e.orb,
            abs(e.orb),
            int(e.applying),
            e.score,
            e.meta.get("profile_id"),
        )
        for e in evs
    ]
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transits_events (
                ts TEXT NOT NULL,
                moving TEXT NOT NULL,
                target TEXT NOT NULL,
                aspect TEXT NOT NULL,
                orb REAL NOT NULL,
                orb_abs REAL NOT NULL,
                applying INTEGER NOT NULL,
                score REAL,
                profile_id TEXT
            )
            """
        )
        cur.executemany(
            "INSERT INTO transits_events (ts, moving, target, aspect, orb, orb_abs, applying, score, profile_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        con.commit()
        return len(rows)
    finally:
        con.close()


def parquet_write_canonical(path: str, events: Iterable[Union[Mapping[str, Any], _HasAttrs, TransitEvent]]) -> int:
    """Write canonical events to a Parquet file or dataset path."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pyarrow is required for Parquet export. Install 'pyarrow' to enable.") from exc

    evs = events_from_any(events)
    data = {
        "ts": [e.ts for e in evs],
        "moving": [e.moving for e in evs],
        "target": [e.target for e in evs],
        "aspect": [e.aspect for e in evs],
        "orb": [e.orb for e in evs],
        "orb_abs": [abs(e.orb) for e in evs],
        "applying": [e.applying for e in evs],
        "score": [e.score for e in evs],
        "profile_id": [e.meta.get("profile_id") for e in evs],
    }
    table = pa.table(data)
    if path.endswith(".parquet"):
        pq.write_table(table, path)
    else:
        pq.write_to_dataset(table, path)
    return len(evs)


# >>> AUTO-GEN END: Canonical Types & Adapters v1.0

__all__ = [
    "AspectName",
    "BodyPosition",
    "TransitEvent",
    "event_from_legacy",
    "events_from_any",
    "sqlite_write_canonical",
    "parquet_write_canonical",
]
