# >>> AUTO-GEN BEGIN: tests-parquet-guard v1.0
from __future__ import annotations

from astroengine.exporters import parquet_available


def test_parquet_guard_imports():
    assert isinstance(parquet_available(), bool)


# >>> AUTO-GEN END: tests-parquet-guard v1.0
