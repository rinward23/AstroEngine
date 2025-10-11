"""Parser utilities for the Markdown-based ruleset DSL."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterator

__all__ = [
    "RulesetDocument",
    "RulesetSection",
    "SectionLine",
    "parse_ruleset_markdown",
]

_SECTION_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9 &()\-_/.'`]+$")
_BULLET_PATTERN = re.compile(r"^([-*])\s+(.*)$")
_ENUM_PATTERN = re.compile(r"^([0-9]+|[a-z])\.(.*)$")


@dataclass(frozen=True)
class SectionLine:
    """Representation of a logical line within a section."""

    raw: str
    text: str
    indent: int
    marker: str | None = None

    @classmethod
    def from_raw(cls, raw: str) -> "SectionLine":
        stripped = raw.lstrip(" ")
        indent = len(raw) - len(stripped)
        if not stripped:
            return cls(raw=raw, text="", indent=indent, marker=None)

        match = _BULLET_PATTERN.match(stripped)
        marker: str | None = None
        text = stripped
        if match:
            marker = match.group(1)
            text = match.group(2).strip()
        else:
            enum_match = _ENUM_PATTERN.match(stripped)
            if enum_match:
                marker = enum_match.group(1)
                text = enum_match.group(2).strip()

        return cls(raw=raw, text=text, indent=indent, marker=marker)


@dataclass(frozen=True)
class RulesetSection:
    """Structured representation of a Markdown section."""

    name: str
    lines: tuple[SectionLine, ...]

    def iter_keyword_lines(self, keyword: str) -> Iterator[SectionLine]:
        kw = keyword.lower()
        for line in self.lines:
            if kw in line.text.lower():
                yield line


@dataclass(frozen=True)
class RulesetDocument:
    """Parsed representation of a ruleset Markdown document."""

    module_path: str
    sections: tuple[RulesetSection, ...]
    trailing_newline: bool = True

    def to_markdown(self) -> str:
        lines = [f"```AUTO-GEN[{self.module_path}]"]
        for section in self.sections:
            lines.append(section.name)
            lines.extend(line.raw for line in section.lines)
        lines.append("```")
        result = "\n".join(lines)
        if self.trailing_newline:
            result += "\n"
        return result

    def find_section(self, name: str) -> RulesetSection | None:
        target = name.upper()
        for section in self.sections:
            if section.name.upper() == target:
                return section
        return None

    def iter_keyword_lines(self, keyword: str) -> Iterator[SectionLine]:
        for section in self.sections:
            yield from section.iter_keyword_lines(keyword)

    def all_lines(self) -> Iterator[str]:
        yield f"```AUTO-GEN[{self.module_path}]"
        for section in self.sections:
            yield section.name
            for line in section.lines:
                yield line.raw
        yield "```"

    def body_text(self) -> str:
        return "\n".join(self.all_lines())


def _is_section_header(line: str) -> bool:
    if not line:
        return False
    if line.startswith("-") or line.startswith("*"):
        return False
    if line.startswith("```"):
        return False
    return bool(_SECTION_PATTERN.fullmatch(line))


def parse_ruleset_markdown(text: str) -> RulesetDocument:
    """Parse a Markdown ruleset document into a structured representation."""

    trailing_newline = text.endswith("\n")
    stripped = text.rstrip("\n")
    lines = stripped.split("\n")
    if not lines or not lines[0].startswith("```AUTO-GEN["):
        raise ValueError("Ruleset must begin with ```AUTO-GEN[...] header")
    header = lines[0]
    if not header.endswith("]"):
        raise ValueError("Ruleset AUTO-GEN header is malformed")
    module_path = header[len("```AUTO-GEN[") : -1]
    if not module_path:
        raise ValueError("Ruleset AUTO-GEN header must include module path")

    if len(lines) < 2 or lines[-1] != "```":
        raise ValueError("Ruleset must terminate with ``` fence")

    sections: list[RulesetSection] = []
    current_name: str | None = None
    current_lines: list[SectionLine] = []

    for raw_line in lines[1:-1]:
        line = raw_line.rstrip("\r")
        stripped_line = line.strip()
        if _is_section_header(stripped_line):
            if current_name is not None:
                sections.append(
                    RulesetSection(name=current_name, lines=tuple(current_lines))
                )
            current_name = stripped_line
            current_lines = []
            continue
        if current_name is None:
            raise ValueError("Encountered content before first section header")
        current_lines.append(SectionLine.from_raw(line))

    if current_name is None:
        raise ValueError("Ruleset contains no sections")

    sections.append(RulesetSection(name=current_name, lines=tuple(current_lines)))
    return RulesetDocument(
        module_path=module_path,
        sections=tuple(sections),
        trailing_newline=trailing_newline,
    )
