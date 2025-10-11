"""Tests for the Markdown ruleset DSL parser and linter."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from astroengine.core.ruleset_dsl import (
    lint_ruleset_documents,
    lint_ruleset_path,
    parse_ruleset_markdown,
)
from astroengine.infrastructure.paths import rulesets_dir


def _expected_module_path(path: Path, base: Path) -> str:
    relative = path.relative_to(base)
    parts = list(relative.parts)
    last = parts[-1]
    assert last.endswith(".ruleset.md"), last
    parts[-1] = last[: -len(".ruleset.md")]
    return ".".join(parts)


@pytest.mark.parametrize("ruleset_path", sorted((rulesets_dir() / "transit").glob("*.ruleset.md")))
def test_ruleset_roundtrip_preserves_module_and_metrics(ruleset_path: Path) -> None:
    source = ruleset_path.read_text(encoding="utf-8")
    document = parse_ruleset_markdown(source)

    expected_module = _expected_module_path(ruleset_path, rulesets_dir())
    assert document.module_path == expected_module

    regenerated = document.to_markdown()
    assert regenerated == source

    reparsed = parse_ruleset_markdown(regenerated)
    assert reparsed.module_path == document.module_path

    def collect_metrics(doc, keyword: str):
        matches = []
        for section in doc.sections:
            for line in section.lines:
                if keyword in line.text.lower():
                    numbers = tuple(re.findall(r"-?\d+(?:\.\d+)?", line.text))
                    matches.append((section.name, line.text.strip(), numbers))
        return matches

    severity_data = collect_metrics(document, "severity")
    orb_data = collect_metrics(document, "orb")

    assert severity_data, "expected severity references in ruleset"
    assert orb_data, "expected orb references in ruleset"

    assert severity_data == collect_metrics(reparsed, "severity")
    assert orb_data == collect_metrics(reparsed, "orb")


def test_ruleset_linter_accepts_repository_rulesets() -> None:
    issues = lint_ruleset_path(rulesets_dir() / "transit")
    assert not issues


def test_ruleset_linter_detects_missing_dataset(tmp_path: Path) -> None:
    ruleset_root = tmp_path / "rulesets"
    ruleset_root.mkdir(parents=True)
    ruleset_path = ruleset_root / "test" / "example.ruleset.md"
    ruleset_path.parent.mkdir(parents=True)
    ruleset_path.write_text(
        """```AUTO-GEN[test.example]
SUMMARY
  - Reference profiles/missing.csv and determinism hash for provenance.
VALIDATION
  - Determinism hash recorded alongside provider identifiers.
```
""",
        encoding="utf-8",
    )

    document = parse_ruleset_markdown(ruleset_path.read_text(encoding="utf-8"))
    issues = lint_ruleset_documents(
        [(ruleset_path, document)],
        project=tmp_path,
        rulesets_root=ruleset_root,
    )

    assert any(issue.code == "dataset-missing" for issue in issues)
