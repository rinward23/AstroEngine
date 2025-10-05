"""Validation pipeline invoked after developer mode patches."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Iterable

DEFAULT_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pytest", ("pytest", "-q")),
)


def _run_command(command: Iterable[str], *, cwd: Path) -> tuple[int, str, str]:
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


def pipeline(root: str | Path = ".") -> dict:
    """Execute the validation pipeline, returning structured results."""

    worktree = Path(root)
    steps: list[tuple[str, tuple[str, ...]]] = list(DEFAULT_STEPS)
    override = os.environ.get("DEV_VALIDATE_COMMANDS")
    if override:
        steps = []
        for chunk in override.split(";;"):
            chunk = chunk.strip()
            if not chunk:
                continue
            steps.append((chunk, tuple(shlex.split(chunk))))
    results: list[dict[str, object]] = []
    overall_ok = True
    for name, args in steps:
        code, stdout, stderr = _run_command(args, cwd=worktree)
        success = code == 0
        results.append(
            {
                "step": name,
                "command": list(args),
                "returncode": code,
                "ok": success,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        if not success:
            overall_ok = False
            break
    return {"ok": overall_ok, "results": results}
