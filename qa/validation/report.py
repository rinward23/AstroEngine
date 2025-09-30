"""Reporting helpers for cross-engine validation outputs."""

from __future__ import annotations

from pathlib import Path

from .cross_engine import MatrixResult, render_markdown, write_report_json

__all__ = ["write_artifacts"]


def write_artifacts(result: MatrixResult, directory: Path) -> None:
    """Persist JSON + Markdown reports into ``directory``."""

    directory.mkdir(parents=True, exist_ok=True)
    write_report_json(result, directory / "cross_engine.json")
    render_markdown(result, directory / "cross_engine.md")
