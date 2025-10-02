from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Tuple

from dependency_utils import ensure

TEST_DEPENDENCIES: list[tuple[str, str, Tuple[int, ...]]] = [
    ("pyswisseph>=2.10.3.2", "swisseph", (2, 10, 3, 2)),
    ("pymeeus>=0.5.12", "pymeeus", (0, 5, 12)),
    ("PyYAML>=6.0", "yaml", (6, 0, 0)),
    ("pydantic>=2.11", "pydantic", (2, 11)),
    ("fastapi>=0.117,<0.118", "fastapi", (0, 117)),
    ("httpx>=0.28,<0.29", "httpx", (0, 28)),
    ("pandas>=2.2", "pandas", (2, 2)),
    ("alembic>=1.13", "alembic", (1, 13)),
    ("jinja2>=3.1", "jinja2", (3, 1)),
    ("markdown-it-py>=4.0", "markdown_it", (4, 0)),
    ("mdit-py-plugins>=0.5", "mdit_py_plugins", (0, 5)),
]


def _upgrade_pip(quiet: bool) -> None:
    cmd: list[str] = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    kwargs = {}
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    subprocess.check_call(cmd, **kwargs)


def install_test_dependencies(*, install: bool = True, quiet: bool = False) -> None:
    """Ensure the core test dependency set is importable."""

    missing: list[str] = []
    for spec, import_name, minimum in TEST_DEPENDENCIES:
        try:
            ensure(
                spec,
                import_name=import_name,
                minimum=minimum,
                install=install,
                quiet=quiet,
            )
        except ModuleNotFoundError:
            missing.append(f"{import_name} ({spec})")
    if missing:
        formatted = "\n  - ".join([""] + missing)
        raise RuntimeError(
            "Missing required runtime dependencies before tests can execute:"
            f"{formatted}\nRe-run without --check-only to install them automatically."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upgrade-pip",
        action="store_true",
        help="Upgrade pip before verifying dependencies.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify that dependencies are present without installing them.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress pip output when packages are already satisfied.",
    )
    args = parser.parse_args()

    if args.upgrade_pip:
        _upgrade_pip(args.quiet)

    try:
        install_test_dependencies(install=not args.check_only, quiet=args.quiet)
    except RuntimeError as exc:
        parser.exit(status=1, message=f"{exc}\n")


if __name__ == "__main__":
    main()
