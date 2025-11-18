"""Documentation guards for the compatibility matrix."""

from __future__ import annotations

from pathlib import Path

from astroengine.modules import DEFAULT_REGISTRY


def test_matrix_lists_all_modules() -> None:
    """Every registered module must appear in docs/COMPATIBILITY_MATRIX.md."""

    doc_path = Path(__file__).resolve().parents[2] / "docs" / "COMPATIBILITY_MATRIX.md"
    matrix_text = doc_path.read_text(encoding="utf-8")
    missing = [module.name for module in DEFAULT_REGISTRY.iter_modules() if module.name not in matrix_text]
    assert not missing, f"Compatibility matrix missing modules: {missing}"
