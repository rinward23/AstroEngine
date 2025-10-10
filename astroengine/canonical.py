# >>> AUTO-GEN BEGIN: Canonical Types & Adapters v1.0
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol

_SQLITE_IMPORT_ERROR: ModuleNotFoundError | None = None

try:  # pragma: no cover - optional storage dependency
    from .infrastructure.storage.sqlite import (
        apply_default_pragmas,
        ensure_sqlite_schema,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - allows lightweight imports
    _SQLITE_IMPORT_ERROR = exc

    def ensure_sqlite_schema(*_args, **_kwargs):  # type: ignore

        raise RuntimeError(
            "SQLite storage support unavailable"
        ) from _SQLITE_IMPORT_ERROR

    def apply_default_pragmas(*_args, **_kwargs):  # type: ignore

        raise RuntimeError(
            "SQLite storage support unavailable"
        ) from _SQLITE_IMPORT_ERROR



_CANONICAL_PRECISION = 5


def canonical_round(value: float) -> float:
    """Round ``value`` to the canonical precision used for ephemeris payloads."""

    return round(float(value), _CANONICAL_PRECISION)


def _normalize_longitude(value: float) -> float:
    """Return ``value`` wrapped into ``[0, 360)`` with canonical rounding."""

    lon = float(value) % 360.0
    if lon < 0:
        lon += 360.0
    normalized = canonical_round(lon)
    # Guard against values like 359.9999999999 -> 360.0 due to rounding.
    if normalized >= 360.0:
        return 0.0
    return normalized


def _normalize_declination(value: float) -> float:
    """Clamp declinations to ``[-90, +90]`` and round deterministically."""

    dec = max(-90.0, min(90.0, float(value)))
    return canonical_round(dec)


def normalize_longitude(value: float) -> float:
    """Public wrapper returning ``value`` normalized to ``[0, 360)`` degrees."""

    return _normalize_longitude(value)


def normalize_declination(value: float) -> float:
    """Public wrapper returning ``value`` clamped to ``[-90, +90]`` degrees."""

    return _normalize_declination(value)


def normalize_speed_per_day(value: float) -> float:
    """Return the longitudinal speed normalised to degrees/day precision."""

    return canonical_round(value)


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "lon", _normalize_longitude(self.lon))
        object.__setattr__(self, "lat", canonical_round(self.lat))
        object.__setattr__(self, "dec", _normalize_declination(self.dec))
        object.__setattr__(self, "speed_lon", canonical_round(self.speed_lon))

    def as_mapping(self) -> dict[str, float]:
        """Return the position as a canonical mapping payload."""

        return {
            "lon": self.lon,
            "lat": self.lat,
            "decl": self.dec,
            "speed_lon": self.speed_lon,
        }


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


def iter_events_from_any(
    seq: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent]
) -> Iterator[TransitEvent]:
    """Yield canonical :class:`TransitEvent` objects lazily from ``seq``."""

    for item in seq:
        yield event_from_legacy(item)


def events_from_any(
    seq: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent],
) -> list[TransitEvent]:
    """Vector form of :func:`event_from_legacy` with strict conversion."""

    return list(iter_events_from_any(seq))


_SQLITE_INSERT = """
    INSERT INTO transits_events (
        ts, moving, target, aspect, orb, orb_abs, applying, score,
        profile_id, natal_id, event_year, meta_json
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _row_params(event: TransitEvent) -> tuple[Any, ...]:
    payload = _event_row(event)
    return (
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


def sqlite_write_canonical(
    db_path: str,
    events: Iterable[Mapping[str, Any] | _HasAttrs | TransitEvent],
    *,
    batch_size: int = 512,
) -> int:
    """Append canonical events to SQLite (table: ``transits_events``)."""

    import sqlite3

    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    event_iter = iter_events_from_any(events)
    try:
        first_event = next(event_iter)
    except StopIteration:
        return 0

    ensure_sqlite_schema(db_path)
    con = sqlite3.connect(db_path)
    apply_default_pragmas(con)
    try:
        cur = con.cursor()
        rows: list[tuple[Any, ...]] = [_row_params(first_event)]
        total = 0
        for event in event_iter:
            rows.append(_row_params(event))
            if len(rows) >= batch_size:
                cur.executemany(_SQLITE_INSERT, rows)
                con.commit()
                total += len(rows)
                rows.clear()
        if rows:
            cur.executemany(_SQLITE_INSERT, rows)
            con.commit()
            total += len(rows)
        return total
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
    apply_default_pragmas(con)
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

    def _string_or_none(value: Any) -> Any:
        return None if value is None else str(value)

    def _record_batch_from_rows(batch_rows: list[dict[str, Any]]) -> pa.RecordBatch:
        ts: list[str] = []
        moving: list[str] = []
        target: list[str] = []
        aspect: list[str] = []
        orb: list[float] = []
        orb_abs: list[float] = []
        applying: list[bool] = []
        score: list[float | None] = []
        profile_id: list[str | None] = []
        natal_id: list[str] = []
        event_year: list[int] = []
        meta_json: list[str] = []

        for row in batch_rows:
            ts.append(row["ts"])
            moving.append(row["moving"])
            target.append(row["target"])
            aspect.append(row["aspect"])
            orb.append(float(row["orb"]))
            orb_abs.append(float(row["orb_abs"]))
            applying.append(bool(row["applying"]))
            score.append(None if row["score"] is None else float(row["score"]))
            profile_id.append(_string_or_none(row["profile_id"]))
            natal_id.append((row["natal_id"] or "unknown"))
            event_year.append(int(row["event_year"]))
            meta_json.append(row["meta_json"])

        return pa.record_batch(
            {
                "ts": pa.array(ts, type=pa.string()),
                "moving": pa.array(moving, type=pa.string()),
                "target": pa.array(target, type=pa.string()),
                "aspect": pa.array(aspect, type=pa.string()),
                "orb": pa.array(orb, type=pa.float64()),
                "orb_abs": pa.array(orb_abs, type=pa.float64()),
                "applying": pa.array(applying, type=pa.bool_()),
                "score": pa.array(score, type=pa.float64()),
                "profile_id": pa.array(profile_id, type=pa.string()),
                "natal_id": pa.array(natal_id, type=pa.string()),
                "event_year": pa.array(event_year, type=pa.int64()),
                "meta_json": pa.array(meta_json, type=pa.string()),
            }
        )

    def _iter_record_batches() -> Iterable[pa.RecordBatch]:
        batch: list[dict[str, Any]] = []
        for obj in events:
            event = event_from_legacy(obj)
            batch.append(_event_row(event))
            if len(batch) >= 2048:
                yield _record_batch_from_rows(batch)
                batch = []
        if batch:
            yield _record_batch_from_rows(batch)

    batches = iter(_iter_record_batches())
    try:
        first_batch = next(batches)
    except StopIteration:
        return 0

    total_rows = first_batch.num_rows
    if path.endswith(".parquet"):
        with pq.ParquetWriter(
            path, first_batch.schema, compression=compression
        ) as writer:
            writer.write_batch(first_batch)
            for batch in batches:
                writer.write_batch(batch)
                total_rows += batch.num_rows
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

        def _counting_batches() -> Iterable[pa.RecordBatch]:
            nonlocal total_rows
            yield first_batch
            for batch in batches:
                total_rows += batch.num_rows
                yield batch

        ds.write_dataset(
            _counting_batches(),
            path,
            format=parquet_format,
            partitioning=partitioning,
            existing_data_behavior="overwrite_or_ignore",
            file_options=file_options,
            schema=first_batch.schema,
        )

    return total_rows


# >>> AUTO-GEN END: Canonical Types & Adapters v1.0

__all__ = [
    "canonical_round",
    "normalize_longitude",
    "normalize_declination",
    "normalize_speed_per_day",
    "AspectName",
    "BodyPosition",
    "TransitEvent",
    "event_from_legacy",
    "iter_events_from_any",
    "events_from_any",
    "sqlite_write_canonical",
    "sqlite_read_canonical",
    "parquet_write_canonical",
]
