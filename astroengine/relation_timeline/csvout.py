"""CSV export helpers for relationship timeline events."""

from __future__ import annotations

import csv
import io
from typing import Iterable

from .engine import Event

__all__ = ["events_to_csv"]


_CSV_COLUMNS: tuple[str, ...] = (
    "type",
    "chart",
    "transiter",
    "target",
    "aspect",
    "exact_utc",
    "start_utc",
    "end_utc",
    "orb",
    "max_severity",
    "score",
)


def events_to_csv(
    events: Iterable[Event],
    *,
    chart_type: str,
) -> str:
    """Return CSV rows encoding ``events``."""

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_COLUMNS)
    for event in events:
        writer.writerow(
            [
                event.type,
                chart_type,
                event.transiter,
                event.target or "",
                event.aspect if event.aspect is not None else "",
                event.exact_utc.replace(tzinfo=None).isoformat() + "Z",
                event.start_utc.replace(tzinfo=None).isoformat() + "Z",
                event.end_utc.replace(tzinfo=None).isoformat() + "Z",
                f"{event.orb:.2f}",
                f"{event.max_severity:.3f}",
                f"{event.score:.3f}",
            ]
        )
    return buffer.getvalue()

