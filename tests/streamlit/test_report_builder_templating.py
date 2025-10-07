from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip(
    "jinja2",
    reason="jinja2 not installed; install extras with `pip install -e .[narrative,reports,ui,streamlit]`.",
)

from ui.streamlit.report_builder.templating import ReportContext, render_markdown


def test_default_template_snapshot() -> None:
    sample = json.loads(
        Path("ui/streamlit/report_builder/samples/findings_sample.json").read_text()
    )
    context = ReportContext(
        findings=sample["findings"],
        rulepack=sample["rulepack"],
        filters=sample["filters"],
        pair=sample["pair"],
        totals=sample["totals"],
        generated_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        top_highlights=2,
        template_id="default",
    )
    markdown = render_markdown(context)
    expected = Path("tests/data/report_builder/default_report.md").read_text()
    assert markdown == expected
