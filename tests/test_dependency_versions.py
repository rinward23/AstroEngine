from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import Requirement


def _specifier_for(dependency_list: list[str], package: str) -> str:
    for item in dependency_list:
        requirement = Requirement(item)
        if requirement.name == package:
            return str(requirement.specifier)
    raise AssertionError(f"Package {package!r} not found in dependency list")


def test_optional_versions_match_core_dependencies() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())

    project = data["project"]
    core_deps = project["dependencies"]
    optional_deps = project["optional-dependencies"]

    expected_specifiers = {
        package: _specifier_for(core_deps, package)
        for package in ("httpx", "timezonefinder", "tzdata")
    }

    extras_to_validate = {
        "api": ("httpx",),
        "providers": ("timezonefinder", "tzdata"),
        "all": ("httpx", "timezonefinder", "tzdata"),
    }

    for extra_name, packages in extras_to_validate.items():
        extra = optional_deps[extra_name]
        for package in packages:
            expected = expected_specifiers[package]
            assert (
                _specifier_for(extra, package) == expected
            ), f"{extra_name} extra for {package} drifted from core dependencies"
