from __future__ import annotations

import os
from pathlib import Path

from astroengine.infrastructure import rebuild_virtualenv
from astroengine.infrastructure.rebuild import build_rebuild_plan


def _expected_pip_path(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "pip.exe"
    return venv_path / "bin" / "pip"


def test_build_rebuild_plan_includes_all_steps(tmp_path: Path) -> None:
    venv_path = tmp_path / "existing"
    venv_path.mkdir()

    plan = build_rebuild_plan(
        venv_path=venv_path,
        python_executable="python3",
        extras=["dev"],
        upgrade_pip=True,
    )

    assert plan[0].description.startswith("Remove existing environment")
    assert plan[0].command is None
    assert plan[1].command == ("python3", "-m", "venv", str(venv_path))

    pip_path = str(_expected_pip_path(venv_path))
    assert plan[2].command == (pip_path, "install", "--upgrade", "pip")
    assert plan[3].command == (pip_path, "install", "--upgrade", "-e", ".[dev]")


def test_rebuild_virtualenv_dry_run(tmp_path: Path) -> None:
    venv_path = tmp_path / "preview"

    plan = rebuild_virtualenv(
        venv_path=venv_path,
        python_executable="python3",
        extras=["dev", "docs"],
        dry_run=True,
    )

    assert not venv_path.exists(), "dry run should not create the environment"
    assert plan[-1].command[-1] == ".[dev,docs]"


def test_rebuild_virtualenv_executes_commands(tmp_path: Path) -> None:
    venv_path = tmp_path / "actual"
    recorded: list[tuple[str, ...]] = []

    def runner(cmd: tuple[str, ...]) -> None:
        recorded.append(tuple(cmd))

    plan = rebuild_virtualenv(
        venv_path=venv_path,
        python_executable="python3",
        extras=["dev"],
        dry_run=False,
        runner=runner,
    )

    assert [step.command for step in plan if step.command] == recorded
    assert len(recorded) == 3
    assert recorded[0][0] == "python3"

