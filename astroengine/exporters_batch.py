from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable, Sequence


def _normalize_events(events: Iterable[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for event in events:
        if is_dataclass(event):
            normalized.append(asdict(event))
        elif isinstance(event, dict):
            normalized.append(dict(event))
        else:
            normalized.append({"value": event})
    return normalized


def export_parquet_dataset(path: str | Path, events: Sequence[object]) -> int:
    """Write events to a Parquet file using pandas.

    The helper returns the number of rows written.  It intentionally keeps
    dependencies optional; if pandas or pyarrow are unavailable a
    RuntimeError is raised prompting the caller to install the parquet
    extras.
    """

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:  # pragma: no cover - environment specific
        raise RuntimeError(
            "pandas (with pyarrow) is required for Parquet export"
        ) from exc

    data = _normalize_events(events)
    df = pd.DataFrame(data)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)
    return len(df)
