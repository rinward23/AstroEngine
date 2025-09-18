from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Mapping, Protocol

import pandas as pd


class DatasetConnector(Protocol):
    """Protocol for connectors that load tabular data into pandas."""

    def __call__(self, location: Path) -> pd.DataFrame:  # pragma: no cover - protocol definition
        ...


@dataclass
class ConnectorRegistry:
    """Registry mapping connector names to callables.

    The registry ships with connectors for CSV, Parquet, and SQLite (via pandas). Additional
    connectors can be supplied at engine construction time.
    """

    connectors: Mapping[str, DatasetConnector]

    def resolve(self, name: str) -> DatasetConnector:
        try:
            return self.connectors[name]
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise KeyError(f"Connector '{name}' is not registered") from exc

    def with_overrides(self, overrides: Mapping[str, DatasetConnector]) -> "ConnectorRegistry":
        merged: Dict[str, DatasetConnector] = dict(self.connectors)
        merged.update(overrides)
        return ConnectorRegistry(merged)


def csv_connector(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def parquet_connector(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def sqlite_connector(path: Path) -> pd.DataFrame:
    import sqlite3

    with sqlite3.connect(path) as conn:
        # Expecting a table named "data"; callers can copy views as needed.
        return pd.read_sql("SELECT * FROM data", conn)


DEFAULT_CONNECTORS = ConnectorRegistry(
    {
        "csv": csv_connector,
        "parquet": parquet_connector,
        "sqlite": sqlite_connector,
    }
)
