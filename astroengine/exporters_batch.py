"""Batch exporters for derived datasets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from .canonical import events_from_any, parquet_write_canonical

__all__ = ["export_parquet_dataset"]


def export_parquet_dataset(
    path: str,
    events: (
        Sequence[Mapping[str, object]]
        | Iterable[Mapping[str, object]]
        | Iterable[object]
    ),
) -> int:
    """Write canonical events to a Parquet file or dataset directory.

    Parameters
    ----------
    path:
        Destination path. If the path ends with ``.parquet`` a single file is
        written, otherwise a partitioned dataset directory is created.
    events:
        Iterable of mappings or objects consumable by
        :func:`astroengine.canonical.events_from_any`.
    """

    canonical = events_from_any(events)
    return parquet_write_canonical(path, canonical)
