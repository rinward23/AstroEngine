"""Batch export stubs used by the CLI placeholder."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

__all__ = ["export_parquet_dataset"]


def export_parquet_dataset(events: Iterable[Mapping[str, object]], output_path: str | Path) -> Path:
    """Pretend to export events to Parquet and return the destination path."""

    return Path(output_path)
