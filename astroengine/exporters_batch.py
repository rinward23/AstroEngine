"""Batch exporters for large AstroEngine analytics workloads."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Dict, Any, List

try:  # pragma: no cover - optional dependency
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore[assignment]

from .engine import events_to_dicts
from .exporters import parquet_available


def _events_to_records(events: Iterable[object], meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    base_meta = {k: v for k, v in (meta or {}).items() if v is not None}
    event_list = list(events)
    records: List[Dict[str, Any]] = []
    if event_list and all(hasattr(event, "to_dict") for event in event_list):
        payloads = events_to_dicts(event_list)  # type: ignore[arg-type]
    else:
        payloads = []
        for event in event_list:
            if isinstance(event, dict):
                payloads.append(dict(event))
            else:
                payloads.append(dict(getattr(event, "__dict__", {})))
    for payload in payloads:
        ts = payload.get("timestamp") or payload.get("when_iso") or payload.get("ts")
        if ts is None:
            raise ValueError("event missing timestamp field")
        payload.setdefault("ts", ts)
        payload.update({k: v for k, v in base_meta.items() if k not in payload})
        records.append(payload)
    return records


def _infer_year(ts: str) -> int:
    # ts like 'YYYY-MM-DDTHH:MM:SSZ'
    return int(ts[:4])


def export_parquet_dataset(events: Iterable[object], dataset_dir: str, meta: Optional[Dict[str, Any]] = None) -> str:
    if not parquet_available():
        raise RuntimeError("pyarrow not available; install extras: [exporters]")
    if pd is None:
        raise RuntimeError("pandas required for Parquet export")
    recs = _events_to_records(events, meta)
    # derive year column for partitioning
    for r in recs:
        r.setdefault('natal_id', 'unknown')
        r['year'] = _infer_year(r['ts'])
    df = pd.DataFrame.from_records(recs)
    out = Path(dataset_dir)
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False, partition_cols=['natal_id','year'])
    return str(out)
# >>> AUTO-GEN END: exporters-batch-parquet-dataset v1.0
