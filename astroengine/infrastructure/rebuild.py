"""Utilities to rebuild the AstroEngine virtual environment from scratch.

The routines here provide a *safe* wrapper around Python's ``venv`` module
and ``pip`` so developers can reset their environment without manually
invoking shell commands.  A dry-run mode is available for inspection and
tests rely on it to avoid mutating the filesystem during CI runs.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "RebuildStep",
    "build_rebuild_plan",
    "execute_plan",
    "rebuild_virtualenv",
    "main",
]


Command = Sequence[str]


@dataclass(frozen=True)
class RebuildStep:
    """Represents a single action in the environment rebuild workflow."""

    description: str
    command: tuple[str, ...] | None = None


def _pip_executable(venv_path: Path) -> Path:
    """Return the path to the ``pip`` executable inside ``venv_path``."""

    if os.name == "nt":
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


def _format_extras(extras: Iterable[str] | None) -> str:
    if not extras:
        return "."
    extras_list = [part.strip() for part in extras if part.strip()]
    if not extras_list:
        return "."
    return f".[{','.join(sorted(extras_list))}]"


def build_rebuild_plan(
    *,
    venv_path: Path = Path(".venv"),
    python_executable: str | None = None,
    extras: Iterable[str] | None = ("dev",),
    upgrade_pip: bool = True,
) -> list[RebuildStep]:
    """Construct a list of steps needed to rebuild ``venv_path``.

    The steps describe what will happen; they do not perform any side effects
    so the plan can be shown to the user before executing it.
    """

    python_executable = python_executable or sys.executable
    plan: list[RebuildStep] = []

    if venv_path.exists():
        plan.append(RebuildStep(description=f"Remove existing environment at {venv_path}"))

    plan.append(
        RebuildStep(
            description=f"Create virtual environment at {venv_path}",
            command=(python_executable, "-m", "venv", str(venv_path)),
        )
    )

    pip_path = _pip_executable(venv_path)
    if upgrade_pip:
        plan.append(
            RebuildStep(
                description="Upgrade pip inside the virtual environment",
                command=(str(pip_path), "install", "--upgrade", "pip"),
            )
        )

    plan.append(
        RebuildStep(
            description="Install AstroEngine into the virtual environment",
            command=(str(pip_path), "install", "--upgrade", "-e", _format_extras(extras)),
        )
    )

    return plan


def execute_plan(
    plan: Sequence[RebuildStep],
    *,
    venv_path: Path,
    upgrade_pip: bool = True,
    remove_existing: bool = True,
    runner: Callable[[Command], None] | None = None,
) -> None:
    """Execute each command in ``plan`` using ``runner``.

    ``remove_existing`` controls whether an existing directory is deleted.
    ``upgrade_pip`` mirrors :func:`build_rebuild_plan` so the caller can ensure
    consistent behaviour when the plan was generated earlier.
    """

    runner = runner or (lambda cmd: subprocess.run(cmd, check=True))

    if remove_existing and venv_path.exists():
        shutil.rmtree(venv_path)

    for step in plan:
        if step.command is None:
            continue
        runner(step.command)


def rebuild_virtualenv(
    *,
    venv_path: Path = Path(".venv"),
    python_executable: str | None = None,
    extras: Iterable[str] | None = ("dev",),
    upgrade_pip: bool = True,
    dry_run: bool = False,
    runner: Callable[[Command], None] | None = None,
) -> list[RebuildStep]:
    """Recreate a virtual environment and reinstall AstroEngine.

    The function returns the plan that was used.  When ``dry_run`` is true the
    plan is returned without executing the commands, making it suitable for
    previews or unit tests.
    """

    plan = build_rebuild_plan(
        venv_path=venv_path,
        python_executable=python_executable,
        extras=extras,
        upgrade_pip=upgrade_pip,
    )

    if not dry_run:
        execute_plan(
            plan,
            venv_path=venv_path,
            upgrade_pip=upgrade_pip,
            remove_existing=True,
            runner=runner,
        )

    return plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astroengine.environment-rebuild",
        description="Rebuild the AstroEngine virtual environment.",
    )
    parser.add_argument(
        "--path",
        default=".venv",
        help="Target directory for the virtual environment (default: .venv).",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Python executable to use for the virtual environment (default: current interpreter).",
    )
    parser.add_argument(
        "--extras",
        default="dev",
        help="Comma separated extras to install (default: dev).  Use an empty string to disable.",
    )
    parser.add_argument(
        "--no-upgrade-pip",
        action="store_true",
        help="Skip upgrading pip inside the virtual environment.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the rebuild plan after printing it.",
    )
    args = parser.parse_args(argv)

    extras = tuple(filter(None, (part.strip() for part in args.extras.split(","))))
    upgrade_pip = not args.no_upgrade_pip

    plan = rebuild_virtualenv(
        venv_path=Path(args.path),
        python_executable=args.python,
        extras=extras,
        upgrade_pip=upgrade_pip,
        dry_run=not args.run,
    )

    for step in plan:
        if step.command is None:
            print(f"- {step.description}")
        else:
            printable = " ".join(step.command)
            print(f"- {step.description}: $ {printable}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
