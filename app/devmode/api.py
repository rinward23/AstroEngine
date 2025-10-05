"""FastAPI endpoints supporting the in-app developer mode."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .gitops import GitOps
from .history import Entry, append_changelog, append_history, read_history
from .backups import (
    cancel_backup_schedule,
    create_backup_zip,
    list_backups,
    restore_backup_zip,
    schedule_backups,
    schedule_status,
)
from astroengine.infrastructure import retention
from .security import is_allowed, is_blocked, is_protected
from .validate import pipeline

router = APIRouter(prefix="/v1/dev", tags=["dev"], include_in_schema=False)

CONFIRM_PHRASE = os.environ.get(
    "DEV_CORE_EDIT_CONFIRM", "I UNDERSTAND THIS MAY BREAK THE APP"
)


class PatchRequest(BaseModel):
    diff: str
    message: str | None = None
    allow_core_edits: bool | None = False
    confirm_phrase: str | None = None
    user: str | None = "anonymous"


class RestoreRequest(BaseModel):
    commit: str


class BackupScheduleRequest(BaseModel):
    interval_hours: float
    start_in_hours: float | None = None


class BackupRestoreRequest(BaseModel):
    archive_path: str


class RetentionRequest(BaseModel):
    temporary_derivatives_days: int | None = None
    run_purge: bool | None = True


@router.get("/history")
async def history() -> list[dict]:
    """Return dev history entries."""

    return read_history(".")


@router.post("/validate")
async def dev_validate() -> dict:
    """Run the validation pipeline without applying a patch."""

    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    return pipeline()


@router.post("/apply")
async def dev_apply(req: PatchRequest) -> dict:
    """Apply a unified diff via the dev mode pipeline."""

    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")

    if not req.diff.strip():
        raise HTTPException(status_code=400, detail="diff payload is empty")

    touched: list[str] = []
    for line in req.diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            parts = line.split()
            if len(parts) < 2:
                continue
            path = parts[-1]
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            if path and path != "/dev/null" and path not in touched:
                touched.append(path)

    if not touched:
        raise HTTPException(status_code=400, detail="no files referenced in diff")

    for path in touched:
        if is_blocked(path):
            raise HTTPException(status_code=400, detail=f"file blocked by policy: {path}")
        if not is_allowed(path):
            raise HTTPException(
                status_code=400, detail=f"file outside editable areas: {path}"
            )

    core_touched = any(is_protected(path) for path in touched)
    if core_touched:
        if not req.allow_core_edits:
            raise HTTPException(
                status_code=400,
                detail="core files targeted; set allow_core_edits=true and provide confirm_phrase",
            )
        if req.confirm_phrase != CONFIRM_PHRASE:
            raise HTTPException(
                status_code=400,
                detail=f"confirmation phrase mismatch. Type exactly: {CONFIRM_PHRASE}",
            )

    git = GitOps(".")
    git.ensure_repo()
    previous_commit = git.current_commit() if (git.root / ".git").exists() else "HEAD"

    snapshot = git.backup_zip()
    git.new_branch("devmode/patch")
    ok, result = git.apply_diff(req.diff)
    if not ok:
        raise HTTPException(status_code=400, detail=f"git apply failed: {result}")

    report = pipeline()
    if not report.get("ok"):
        git.restore_commit(previous_commit)
        raise HTTPException(
            status_code=400,
            detail={"error": "validation failed; rolled back", "report": report},
        )

    commit = git.current_commit()
    entry = Entry(
        ts=time.time(),
        user=req.user or "anonymous",
        commit=commit,
        message=req.message or "devmode patch",
        snapshot=snapshot,
        touched_files=touched,
        core_edited=core_touched,
    )
    append_history(entry)
    append_changelog(entry.message, commit)

    response: dict[str, object] = {
        "status": "applied",
        "commit": commit,
        "core_edited": core_touched,
        "backup": snapshot,
    }
    if core_touched:
        response["warning"] = (
            "Core files edited. If the app becomes unstable, reinstall or restore a previous version."
        )
    return response


@router.post("/restore")
async def dev_restore(req: RestoreRequest) -> dict:
    """Restore a previous commit recorded in the dev history."""

    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")

    git = GitOps(".")
    ok, message = git.restore_commit(req.commit)
    if not ok:
        raise HTTPException(status_code=400, detail=f"restore failed: {message}")
    return {"status": "restored", "commit": req.commit}


@router.get("/backups")
async def dev_backups() -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    schedule = schedule_status()
    backups = list_backups()
    retention_policy = retention.load_policy()
    retention_preview = retention.purge_temporary_derivatives(dry_run=True)
    return {
        "schedule": schedule,
        "backups": backups,
        "retention_policy": retention_policy,
        "retention_preview": retention_preview,
    }


@router.post("/backups/run")
async def dev_run_backup() -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    archive = create_backup_zip(".")
    return {"status": "created", "archive": str(archive)}


@router.post("/backups/schedule")
async def dev_schedule_backup(req: BackupScheduleRequest) -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    start_at: float | None = None
    if req.start_in_hours is not None and req.start_in_hours > 0:
        start_at = time.time() + (req.start_in_hours * 3600)
    schedule = schedule_backups(
        interval_hours=req.interval_hours,
        root=".",
        start_at=start_at,
    )
    if schedule.get("status") == "canceled":
        return schedule
    return {"status": "scheduled", "schedule": schedule}


@router.post("/backups/restore")
async def dev_restore_backup(req: BackupRestoreRequest) -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    try:
        restored = restore_backup_zip(req.archive_path, ".")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "restored", "files": restored}


@router.delete("/backups/schedule")
async def dev_cancel_backup_schedule() -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    return cancel_backup_schedule()


@router.get("/retention")
async def dev_retention_status() -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    policy = retention.load_policy()
    preview = retention.purge_temporary_derivatives(dry_run=True)
    return {"policy": policy, "preview": preview}


@router.post("/retention")
async def dev_update_retention(req: RetentionRequest) -> dict[str, object]:
    if not os.getenv("DEV_MODE"):
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    policy = retention.load_policy()
    if req.temporary_derivatives_days is not None:
        policy["temporary_derivatives_days"] = req.temporary_derivatives_days
        retention.save_policy(policy)
    summary = None
    if req.run_purge:
        summary = retention.purge_temporary_derivatives()
    return {"policy": policy, "summary": summary}
