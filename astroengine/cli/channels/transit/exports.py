"""Canonical export helpers shared by transit CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from ....plugins import ExportContext, get_plugin_manager


def add_canonical_export_args(parser: argparse.ArgumentParser) -> None:
    """Augment *parser* with standard canonical export options."""

    group = parser.add_argument_group("canonical export")
    group.add_argument(
        "--sqlite", help="Path to SQLite DB; writes into table transits_events"
    )
    group.add_argument(
        "--parquet",
        help="Path to Parquet file or dataset directory",
    )
    group.add_argument(
        "--parquet-compression",
        default="snappy",
        help="Compression codec for Parquet exports (snappy, gzip, brotli, ...)",
    )


def write_sqlite_canonical(path: str, events: Sequence[Any]) -> int:
    from ....exporters import write_sqlite_canonical as _impl

    return _impl(path, events)


def write_parquet_canonical(path: str, events: Sequence[Any]) -> int:
    from ....exporters import write_parquet_canonical as _impl

    return _impl(path, events)


def export_canonical_datasets(
    args: argparse.Namespace, events: Sequence[Any]
) -> dict[str, int]:
    """Execute configured canonical exports and return a mapping of counts."""

    written: dict[str, int] = {}
    if getattr(args, "sqlite", None):
        written["sqlite"] = write_sqlite_canonical(args.sqlite, events)
    if getattr(args, "parquet", None):
        written["parquet"] = write_parquet_canonical(args.parquet, events)

    runtime = get_plugin_manager()
    runtime.post_export(
        ExportContext(
            destinations=dict(written),
            events=tuple(events),
            arguments=dict(vars(args)),
        )
    )

    return written


__all__ = [
    "add_canonical_export_args",
    "export_canonical_datasets",
    "write_parquet_canonical",
    "write_sqlite_canonical",
]
