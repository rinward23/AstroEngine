"""Generic environment diagnostics (replaces the old Conda-only doctor)."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from importlib import metadata

__all__ = [
    "EnvironmentReport",
    "collect_environment_report",
    "main",
]


@dataclass
class EnvironmentReport:
    """Snapshot of the local Python environment."""

    python_version: tuple[int, int, int]
    executable: str
    platform: str
    packages: Mapping[str, str]

    def to_dict(self) -> Mapping[str, object]:
        return {
            "python_version": ".".join(map(str, self.python_version)),
            "executable": self.executable,
            "platform": self.platform,
            "packages": dict(self.packages),
        }


def _package_versions(package_names: Iterable[str]) -> MutableMapping[str, str]:
    versions: dict[str, str] = {}
    for name in package_names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "missing"
    return versions


def collect_environment_report(packages: Sequence[str] | None = None) -> EnvironmentReport:
    """Build an :class:`EnvironmentReport` for the current interpreter."""

    python_version = sys.version_info[:3]
    pkg_versions = _package_versions(packages or [])
    return EnvironmentReport(
        python_version=python_version,
        executable=sys.executable,
        platform=platform.platform(),
        packages=pkg_versions,
    )


def _emit_text_report(report: EnvironmentReport) -> None:
    sys.stdout.write("# AstroEngine Environment Report\n")
    sys.stdout.write(f"Python: {'.'.join(map(str, report.python_version))}\n")
    sys.stdout.write(f"Executable: {report.executable}\n")
    sys.stdout.write(f"Platform: {report.platform}\n")
    if report.packages:
        sys.stdout.write("Packages:\n")
        for name, version in sorted(report.packages.items()):
            sys.stdout.write(f"  - {name}: {version}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astroengine.environment",
        description="Inspect the active Python environment without relying on Conda.",
    )
    parser.add_argument(
        "packages",
        nargs="*",
        help="Optional package names to verify (numpy pandas...).",
    )
    parser.add_argument("--as-json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    report = collect_environment_report(args.packages)

    if args.as_json:
        json.dump(report.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _emit_text_report(report)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
