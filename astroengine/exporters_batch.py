"""Batch exporters for derived datasets."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

__all__ = ["export_parquet_dataset"]


def export_parquet_dataset(
    path: str,
    events: Sequence[Mapping[str, object]] | Iterable[Mapping[str, object]] | Iterable[object],
) -> int:
    """Write events to a Parquet dataset.

    The real implementation depends on optional Parquet dependencies. This
    placeholder raises an informative error when those dependencies are not
    installed so that CLI imports continue to work.
    """

    raise RuntimeError(
        "Parquet export requires optional dependencies (pyarrow/fastparquet)."
    )
