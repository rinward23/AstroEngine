# >>> AUTO-GEN BEGIN: exporters-batch v1.2
from __future__ import annotations
from typing import Iterable, Optional, List, Dict, Any
import uuid

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

from .exporters import parquet_available

_SQLITE_INIT = """
CREATE TABLE IF NOT EXISTS transit_events (
  ts TEXT NOT NULL,
  event_type TEXT NOT NULL,
  method TEXT, moving_body TEXT, static_body TEXT, aspect INTEGER,
  kind TEXT, body TEXT, sign TEXT, lord TEXT, start_ts TEXT, end_ts TEXT,
  run_id TEXT, natal_id TEXT, profile TEXT, window_start TEXT, window_end TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON transit_events (ts);
CREATE INDEX IF NOT EXISTS idx_events_type_ts ON transit_events (event_type, ts);
CREATE INDEX IF NOT EXISTS idx_events_natal_ts ON transit_events (natal_id, ts);
"""


def _ensure_sqlite_schema(con) -> None:
    cur = con.cursor()
    cur.executescript(_SQLITE_INIT)
    con.commit()


def _extract_attr(event: Any, *names: str) -> Any:
    for name in names:
        if isinstance(event, dict) and name in event:
            return event[name]
        if hasattr(event, name):
            value = getattr(event, name)
            if callable(value):  # tolerate properties implemented as callables
                try:
                    value = value()
                except TypeError:
                    pass
            return value
    return None


def _coerce_timestamp(event: Any) -> Optional[str]:
    cand = _extract_attr(event, "ts", "timestamp", "when_iso", "when", "date", "time")
    if cand is None:
        cand = _extract_attr(event, "start_ts", "start", "window_start")
    if cand is None:
        return None
    return str(cand)


def _infer_event_type(event: Any) -> str:
    explicit = _extract_attr(event, "event_type", "kind", "type")
    if explicit:
        return str(explicit)
    if isinstance(event, dict) and "__type__" in event:
        return str(event["__type__"])
    name = event.__class__.__name__
    return name[:-5].lower() if name.endswith("Event") else name.lower()


def _events_to_records(events: Iterable[object], meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    meta = meta or {}
    run_id = meta.get("run_id") or str(uuid.uuid4())
    meta_defaults = {k: meta.get(k) for k in ("natal_id", "profile", "window_start", "window_end")}

    records: List[Dict[str, Any]] = []
    for event in events:
        ts = _coerce_timestamp(event)
        if not ts:
            continue
        aspect = _extract_attr(event, "aspect", "aspect_angle", "angle")
        if aspect is not None:
            try:
                aspect = int(round(float(aspect)))
            except (TypeError, ValueError):
                aspect = None
        record: Dict[str, Any] = {
            "ts": ts,
            "event_type": _infer_event_type(event),
            "method": _extract_attr(event, "method", "detector", "source"),
            "moving_body": _extract_attr(event, "moving_body", "moving", "body"),
            "static_body": _extract_attr(event, "static_body", "target"),
            "aspect": aspect,
            "kind": _extract_attr(event, "kind", "event_kind"),
            "body": _extract_attr(event, "body"),
            "sign": _extract_attr(event, "sign"),
            "lord": _extract_attr(event, "lord", "ruler"),
            "start_ts": _extract_attr(event, "start_ts", "start"),
            "end_ts": _extract_attr(event, "end_ts", "end"),
            "run_id": run_id,
            "natal_id": meta_defaults.get("natal_id"),
            "profile": meta_defaults.get("profile"),
            "window_start": meta_defaults.get("window_start"),
            "window_end": meta_defaults.get("window_end"),
        }
        records.append(record)
    return records


def export_batch(events: Iterable[object], sqlite_path: Optional[str] = None, parquet_path: Optional[str] = None, ics_path: Optional[str] = None, ics_title: str = "AstroEngine Events", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    recs = _events_to_records(events, meta)
    summary: Dict[str, Any] = {"count": len(recs)}
    if meta and meta.get("run_id"):
        summary["run_id"] = meta["run_id"]

    if sqlite_path:
        if pd is None:
            raise RuntimeError("pandas required for SQLite export")
        import sqlite3
        con = sqlite3.connect(sqlite_path)
        try:
            _ensure_sqlite_schema(con)
            df = pd.DataFrame.from_records(recs)
            df.to_sql('transit_events', con, if_exists='append', index=False)
            summary['sqlite'] = sqlite_path
        finally:
            con.close()

    if parquet_path:
        if not parquet_available():
            raise RuntimeError("pyarrow not available; install extras: [exporters]")
        if pd is None:
            raise RuntimeError("pandas required for Parquet export")
        df = pd.DataFrame.from_records(recs)
        df.to_parquet(parquet_path, index=False)
        summary['parquet'] = parquet_path

    if ics_path:
        from .exporters_ics import write_ics
        write_ics([type('E', (), r) for r in recs], ics_path, title=ics_title)
        summary['ics'] = ics_path

    return summary
# >>> AUTO-GEN END: exporters-batch v1.2
