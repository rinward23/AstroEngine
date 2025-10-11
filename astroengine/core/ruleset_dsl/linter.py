"""Linting utilities for the Markdown ruleset DSL."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Iterator

from astroengine.infrastructure.paths import project_root, rulesets_dir

from .parser import RulesetDocument, parse_ruleset_markdown

__all__ = [
    "LintIssue",
    "lint_ruleset_documents",
    "lint_ruleset_path",
]

_DATASET_PATTERN = re.compile(
    r"(?P<path>(?:profiles|datasets|schemas|docs|registry|generated)/[A-Za-z0-9_./\-]+)"
)
_PROVENANCE_KEYWORDS = ("provenance", "determinism", "checksum", "hash")


@dataclass(frozen=True)
class LintIssue:
    """Structured representation of a lint finding."""

    path: Path
    code: str
    message: str


def _iter_ruleset_paths(target: Path) -> Iterator[Path]:
    if target.is_dir():
        yield from sorted(target.rglob("*.ruleset.md"))
    elif target.suffix == ".md" and target.name.endswith(".ruleset.md"):
        yield target
    else:
        raise FileNotFoundError(f"No ruleset Markdown documents found under {target}")


def _expected_module_path(path: Path, base: Path | None) -> str | None:
    if base is not None:
        try:
            relative = path.relative_to(base)
        except ValueError:
            pass
        else:
            parts = list(relative.parts)
            if not parts:
                return None
            stem = parts[-1]
            if not stem.endswith(".ruleset.md"):
                return None
            parts[-1] = stem[: -len(".ruleset.md")]
            return ".".join(parts)
    stem = path.name
    if stem.endswith(".ruleset.md"):
        return stem[: -len(".ruleset.md")]
    return None


def _validate_module_path(doc: RulesetDocument, path: Path, base: Path | None) -> list[LintIssue]:
    expected = _expected_module_path(path, base)
    issues: list[LintIssue] = []
    if expected:
        if doc.module_path != expected:
            issues.append(
                LintIssue(
                    path=path,
                    code="module-path",
                    message=f"Module path '{doc.module_path}' does not match expected '{expected}'",
                )
            )
    segments = doc.module_path.split(".")
    if any(not segment or not segment.replace("_", "").isalnum() for segment in segments):
        issues.append(
            LintIssue(
                path=path,
                code="identifier",
                message="Module path must consist of dot-separated alphanumeric identifiers",
            )
        )
    return issues


def _validate_datasets(doc: RulesetDocument, path: Path, root: Path) -> list[LintIssue]:
    text = doc.body_text()
    issues: list[LintIssue] = []
    seen: set[str] = set()
    for match in _DATASET_PATTERN.finditer(text):
        raw = match.group("path")
        candidate = raw.rstrip(".,)")
        if candidate in seen:
            continue
        seen.add(candidate)
        dataset_path = root / candidate
        if not dataset_path.exists():
            issues.append(
                LintIssue(
                    path=path,
                    code="dataset-missing",
                    message=f"Referenced dataset '{candidate}' does not exist",
                )
            )
    return issues


def _validate_provenance(doc: RulesetDocument, path: Path) -> list[LintIssue]:
    text = doc.body_text().lower()
    if any(keyword in text for keyword in _PROVENANCE_KEYWORDS):
        return []
    return [
        LintIssue(
            path=path,
            code="provenance",
            message="Ruleset must mention provenance, determinism, or checksum requirements",
        )
    ]


def lint_ruleset_documents(
    docs: Iterable[tuple[Path, RulesetDocument]],
    *,
    project: Path | None = None,
    rulesets_root: Path | None = None,
) -> list[LintIssue]:
    """Run lint validation over the provided ruleset documents."""

    project_root_path = project or project_root()
    rulesets_root_path = rulesets_root or rulesets_dir()
    issues: list[LintIssue] = []
    for path, doc in docs:
        issues.extend(_validate_module_path(doc, path, rulesets_root_path))
        issues.extend(_validate_datasets(doc, path, project_root_path))
        issues.extend(_validate_provenance(doc, path))
    return issues


def lint_ruleset_path(target: Path) -> list[LintIssue]:
    """Lint all ruleset Markdown files under the provided path."""

    paths = list(_iter_ruleset_paths(target))
    docs: list[tuple[Path, RulesetDocument]] = []
    for path in paths:
        try:
            doc = parse_ruleset_markdown(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return [LintIssue(path=path, code="parse", message=f"Failed to parse: {exc}")]
        docs.append((path, doc))
    return lint_ruleset_documents(docs)
