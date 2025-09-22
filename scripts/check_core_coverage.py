#!/usr/bin/env python3
"""Validate coverage thresholds for astroengine.core modules."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from fnmatch import fnmatch
from pathlib import Path


def _load_coverage(path: Path, patterns: list[str] | None) -> tuple[int, int]:
    tree = ET.parse(path)
    root = tree.getroot()

    covered = 0
    total = 0
    aggregates: dict[str, tuple[int, int]] = {}

    for cls in root.findall(".//class"):
        filename = cls.get("filename")
        if not filename or not filename.startswith("astroengine/core/"):
            continue
        if patterns and not any(fnmatch(filename, pattern) for pattern in patterns):
            continue
        lines = cls.find("lines")
        if lines is None:
            continue

        hits = 0
        count = 0
        for line in lines.findall("line"):
            count += 1
            if int(line.get("hits", "0")) > 0:
                hits += 1

        previous = aggregates.get(filename)
        if previous is None:
            aggregates[filename] = (hits, count)
        else:
            aggregates[filename] = (previous[0] + hits, previous[1] + count)

    for hits, count in aggregates.values():
        covered += hits
        total += count

    return covered, total


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: check_core_coverage.py COVERAGE_XML THRESHOLD [GLOB ...]",
            file=sys.stderr,
        )
        return 2

    path = Path(argv[1])
    threshold = float(argv[2])
    patterns = argv[3:]

    covered, total = _load_coverage(path, patterns or None)
    if total == 0:
        print("No astroengine/core files found in coverage report", file=sys.stderr)
        return 1

    percent = (covered / total) * 100.0
    if percent < threshold * 100.0:
        print(
            f"astroengine/core coverage {percent:.2f}% below threshold {threshold * 100:.2f}%",
            file=sys.stderr,
        )
        return 1

    print(f"astroengine/core coverage OK: {percent:.2f}% >= {threshold * 100:.2f}%")
    return 0


if __name__ == "__main__":  # pragma: no cover - convenience script
    raise SystemExit(main(sys.argv))
