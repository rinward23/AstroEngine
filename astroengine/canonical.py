# >>> AUTO-GEN BEGIN: Canonical Types & Adapters v1.0
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol

_SQLITE_IMPORT_ERROR: ModuleNotFoundError | None = None

try:  # pragma: no cover - optional storage dependency
    from .infrastructure.storage.sqlite import ensure_sqlite_schema
except ModuleNotFoundError as exc:  # pragma: no cover - allows lightweight imports
    _SQLITE_IMPORT_ERROR = exc

    def ensure_sqlite_schema(*_args, **_kwargs):  # type: ignore

        raise RuntimeError(
            "SQLite storage support unavailable"
        ) from _SQLITE_IMPORT_ERROR



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
    score: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


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


def _extract_profile_id(meta: Mapping[str, Any]) -> str | None:
    candidates = (
        meta.get("profile_id"),
        meta.get("profileId"),
        meta.get("profile"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    profile = meta.get("profile")
    if isinstance(profile, Mapping):
        value = profile.get("id") or profile.get("profile_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_natal_id(meta: Mapping[str, Any]) -> str | None:
    for key in ("natal_id", "natalId", "natal"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    natal = meta.get("natal")
    if isinstance(natal, Mapping):
        for key in ("id", "natal_id"):
            value = natal.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    subject = meta.get("subject")
    if isinstance(subject, Mapping):
        for key in ("natal_id", "id"):
            value = subject.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _event_year(ts: str) -> int:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid ISO timestamp for canonical export: {ts!r}") from exc
    return dt.year


def _event_row(event: TransitEvent) -> dict[str, Any]:
    meta_source = event.meta or {}
    if not isinstance(meta_source, Mapping):
        raise TypeError("TransitEvent.meta must be a mapping for canonical exports")
    meta: dict[str, Any] = dict(meta_source)
    profile_id = _extract_profile_id(meta)
    natal_id = _extract_natal_id(meta)
    if profile_id and "profile_id" not in meta:
        meta["profile_id"] = profile_id
    if natal_id and "natal_id" not in meta:
        meta["natal_id"] = natal_id
    meta_json = json.dumps(meta, sort_keys=True)
    return {
        "ts": event.ts,
        "moving": event.moving,
        "target": event.target,
        "aspect": event.aspect,
        "orb": float(event.orb),
        "orb_abs": float(abs(event.orb)),
        "applying": bool(event.applying),
        "score": None if event.score is None else float(event.score),
        "profile_id": profile_id,
        "natal_id": natal_id,
        "event_year": _event_year(event.ts),
        "meta": meta,
        "meta_json": meta_json,
    }


def event_from_legacy(
    obj: Mapping[str, Any] | _HasAttrs | TransitEvent,
) -> TransitEvent:
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

    if (
        ts is None
        or moving is None
        or target is None
        or aspect_raw is None
        or orb is None
        or applying is None
    ):
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


def events_from_any(
    seq: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent],
) -> list[TransitEvent]:
    """Vector form of :func:`event_from_legacy` with strict conversion."""

    return [event_from_legacy(x) for x in seq]


def sqlite_write_canonical(
    db_path: str, events: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent]
) -> int:
    """Append canonical events to SQLite (table: ``transits_events``)."""

    import sqlite3

    evs = events_from_any(events)
    if not evs:
        return 0

    rows = []
    for e in evs:
        payload = _event_row(e)
        rows.append(
            (
                payload["ts"],
                payload["moving"],
                payload["target"],
                payload["aspect"],
                payload["orb"],
                payload["orb_abs"],
                1 if payload["applying"] else 0,
                payload["score"],
                payload["profile_id"],
                payload["natal_id"],
                payload["event_year"],
                payload["meta_json"],
            )
        )

    ensure_sqlite_schema(db_path)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.executemany(
            """
            INSERT INTO transits_events (
                ts, moving, target, aspect, orb, orb_abs, applying, score,
                profile_id, natal_id, event_year, meta_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        con.commit()
        return len(rows)
    finally:
        con.close()


def sqlite_read_canonical(
    db_path: str,
    *,
    where: str | None = None,
    parameters: Iterable[Any] | None = None,
) -> list[TransitEvent]:
    """Load canonical events from SQLite without losing metadata."""

    import sqlite3

    ensure_sqlite_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        query = (

            "SELECT ts, moving, target, aspect, orb, applying, score, "
            "meta_json, profile_id, natal_id "
            "FROM transits_events"

        )
        if where:
            query += f" WHERE {where}"
        query += " ORDER BY ts"
        params = tuple(parameters or ())
        rows = con.execute(query, params).fetchall()
        events: list[TransitEvent] = []
        for row in rows:
            meta_payload: dict[str, Any]
            raw_meta = row["meta_json"]
            if raw_meta:
                meta_payload = json.loads(raw_meta)
            else:
                meta_payload = {}
            profile_id = row["profile_id"]
            if profile_id and "profile_id" not in meta_payload:
                meta_payload["profile_id"] = profile_id
            natal_id = row["natal_id"]
            if natal_id and "natal_id" not in meta_payload:
                meta_payload["natal_id"] = natal_id
            events.append(
                TransitEvent(
                    ts=row["ts"],
                    moving=row["moving"],
                    target=row["target"],
                    aspect=row["aspect"],
                    orb=float(row["orb"]),
                    applying=bool(row["applying"]),
                    score=None if row["score"] is None else float(row["score"]),
                    meta=meta_payload,
                )
            )
        return events
    finally:
        con.close()


def parquet_write_canonical(
    path: str,
    events: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent],
    *,
    compression: str = "snappy",
) -> int:
    """Write canonical events to a Parquet file or partitioned dataset."""

    try:
        import pyarrow as pa
        import pyarrow.dataset as ds
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "pyarrow is required for Parquet export. Install 'pyarrow' to enable."
        ) from exc

    evs = events_from_any(events)
    if not evs:
        return 0

    rows = [_event_row(e) for e in evs]

    def _string_or_none(value: Any) -> Any:
        if value is None:
            return None
        return str(value)

    table = pa.table(
        {
            "ts": [row["ts"] for row in rows],
            "moving": [row["moving"] for row in rows],
            "target": [row["target"] for row in rows],
            "aspect": [row["aspect"] for row in rows],
            "orb": [row["orb"] for row in rows],
            "orb_abs": [row["orb_abs"] for row in rows],
            "applying": [row["applying"] for row in rows],
            "score": [row["score"] for row in rows],
            "profile_id": [_string_or_none(row["profile_id"]) for row in rows],
            "natal_id": [row["natal_id"] or "unknown" for row in rows],
            "event_year": [row["event_year"] for row in rows],
            "meta_json": [row["meta_json"] for row in rows],
        }
    )
    if path.endswith(".parquet"):
        pq.write_table(table, path, compression=compression)
    else:
        parquet_format = ds.ParquetFileFormat()
        file_options = parquet_format.make_write_options(compression=compression)
        partition_schema = pa.schema(
            [
                ("natal_id", pa.string()),
                ("event_year", pa.int64()),
            ]
        )
        partitioning = ds.HivePartitioning(partition_schema)
        ds.write_dataset(
            table,
            path,
            format=parquet_format,
            partitioning=partitioning,
            existing_data_behavior="overwrite_or_ignore",
            file_options=file_options,
        )
    return len(evs)


# >>> AUTO-GEN END: Canonical Types & Adapters v1.0

__all__ = [
    "AspectName",
    "BodyPosition",
    "TransitEvent",
    "event_from_legacy",
    "events_from_any",
    "sqlite_write_canonical",
    "sqlite_read_canonical",
    "parquet_write_canonical",
]
