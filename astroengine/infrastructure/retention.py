"""Retention policy utilities for AstroEngine derived artefacts."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .home import ae_home

POLICY_FILE_NAME = "retention_policy.json"
DERIVATIVE_DIR = "derivatives"


def _policy_path() -> Path:
    path = ae_home() / POLICY_FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _derivative_root() -> Path:
    root = ae_home() / DERIVATIVE_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_policy() -> dict[str, Any]:
    path = _policy_path()
    if not path.exists():
        return {"temporary_derivatives_days": 7}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"temporary_derivatives_days": 7}


def save_policy(policy: dict[str, Any]) -> None:
    path = _policy_path()
    path.write_text(json.dumps(policy, indent=2), encoding="utf-8")


def _remove_empty_dirs(root: Path) -> int:
    removed = 0
    for dirpath, _, _ in os.walk(root, topdown=False):
        dir_path = Path(dirpath)
        if dir_path == root:
            continue
        try:
            dir_path.rmdir()
            removed += 1
        except OSError:
            continue
    return removed


def purge_temporary_derivatives(
    *,
    now: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = load_policy()
    retention_days = policy.get("temporary_derivatives_days")
    result: dict[str, Any] = {
        "policy_days": retention_days,
        "dry_run": dry_run,
        "eligible": 0,
        "deleted": 0,
        "scanned": 0,
        "root": str(_derivative_root()),
        "cutoff": None,
    }

    if not retention_days or retention_days <= 0:
        return result

    root = _derivative_root()
    current_time = now if now is not None else time.time()
    cutoff = current_time - (float(retention_days) * 86400)
    result["cutoff"] = cutoff

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        result["scanned"] += 1
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            result["eligible"] += 1
            if not dry_run:
                try:
                    path.unlink()
                    result["deleted"] += 1
                except OSError:
                    continue

    if not dry_run:
        result["directories_removed"] = _remove_empty_dirs(root)
    else:
        result["directories_removed"] = 0

    return result


__all__ = ["load_policy", "save_policy", "purge_temporary_derivatives"]

