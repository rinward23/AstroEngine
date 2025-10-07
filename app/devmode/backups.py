"""Utilities supporting developer-mode backup and restore workflows."""

from __future__ import annotations

import json
import logging
import shutil
import time
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from astroengine.infrastructure import retention
from astroengine.infrastructure.home import ae_home
from astroengine.scheduler.db import now as queue_now
from astroengine.scheduler.queue import cancel, enqueue, get

LOG = logging.getLogger(__name__)

BACKUP_GLOB_TARGETS: Sequence[Path] = (
    Path("profiles"),
    Path("astroengine/config"),
    Path("astroengine/chart"),
    Path("astroengine/profiles"),
)

HOME_TARGETS: Sequence[Path] = (
    Path("natals"),
)

BACKUP_PREFIXES: tuple[str, ...] = (
    "profiles",
    "astroengine/config",
    "astroengine/chart",
    "astroengine/profiles",
    ".astroengine",
)


def _backup_root() -> Path:
    root = ae_home() / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _schedule_path() -> Path:
    path = ae_home() / "backup_schedule.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _retention_summary_path() -> Path:
    return ae_home() / "backup_retention_summary.json"


def _iter_files(base: Path) -> Iterator[Path]:
    for path in base.rglob("*"):
        if path.is_file():
            yield path


def _arcname_for(path: Path, *, project_root: Path, home_root: Path) -> Path:
    try:
        relative_home = path.relative_to(home_root)
        return Path(".astroengine") / relative_home
    except ValueError:
        pass
    try:
        relative = path.relative_to(project_root)
        return relative
    except ValueError:
        pass
    raise ValueError(f"Path {path} is outside backup roots")


def _targets(project_root: Path, home_root: Path) -> Iterable[Path]:
    for rel in BACKUP_GLOB_TARGETS:
        candidate = project_root / rel
        if candidate.exists():
            yield candidate
    for rel in HOME_TARGETS:
        candidate = home_root / rel
        if candidate.exists():
            yield candidate


def _iso(ts: float | int | None) -> str | None:
    if ts is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def create_backup_zip(
    root: str | Path = ".",
    *,
    timestamp: float | None = None,
) -> Path:
    """Create a zip archive of key charts/config/profile artefacts."""

    project_root = Path(root).resolve()
    home_root = ae_home().resolve()
    backup_root = _backup_root()
    ts_struct = time.gmtime(timestamp or time.time())
    label = time.strftime("%Y%m%d_%H%M%S", ts_struct)
    archive_path = backup_root / f"astroengine_backup_{label}.zip"

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for target in _targets(project_root, home_root):
            for file_path in _iter_files(target):
                arcname = _arcname_for(
                    file_path, project_root=project_root, home_root=home_root
                )
                archive.write(file_path, arcname.as_posix())
    return archive_path


def list_backups(limit: int = 50) -> list[dict[str, object]]:
    root = _backup_root()
    items: list[tuple[float, Path]] = []
    for path in root.glob("*.zip"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        items.append((mtime, path))
    items.sort(reverse=True, key=lambda x: x[0])
    result: list[dict[str, object]] = []
    for _, path in items[:limit]:
        stat = path.stat()
        result.append(
            {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "modified_iso": _iso(stat.st_mtime),
            }
        )
    return result


def load_schedule() -> dict:
    path = _schedule_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_schedule(data: dict) -> None:
    path = _schedule_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cancel_backup_schedule() -> dict[str, object]:
    schedule = load_schedule()
    job_id = schedule.get("job_id")
    if job_id:
        try:
            cancel(str(job_id))
        except Exception as exc:  # pragma: no cover - defensive cleanup
            LOG.warning("Unable to cancel scheduled backup %s: %s", job_id, exc)
    path = _schedule_path()
    if path.exists():
        path.unlink()
    return {"status": "canceled"}


def schedule_backups(
    *,
    interval_hours: float,
    root: str | Path = ".",
    start_at: float | None = None,
    now_ts: float | None = None,
) -> dict[str, object]:
    if interval_hours <= 0:
        return cancel_backup_schedule()

    schedule = load_schedule()
    if "job_id" in schedule:
        try:
            cancel(str(schedule["job_id"]))
        except Exception as exc:  # pragma: no cover - defensive cleanup
            LOG.warning("Unable to cancel existing backup %s: %s", schedule["job_id"], exc)

    project_root = Path(root).resolve()
    current = now_ts if now_ts is not None else queue_now()
    interval_seconds = int(interval_hours * 3600)
    first_run = int(start_at if start_at is not None else current + interval_seconds)
    payload = {"root": str(project_root)}
    job_id = enqueue("backup:zip", payload, run_at=first_run)
    schedule.update(
        {
            "interval_seconds": interval_seconds,
            "next_run": first_run,
            "job_id": job_id,
            "root": str(project_root),
        }
    )
    save_schedule(schedule)
    return schedule


def restore_backup_zip(archive: str | Path, root: str | Path = ".") -> list[str]:
    archive_path = Path(archive)
    if not archive_path.exists():
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")

    project_root = Path(root).resolve()
    home_root = ae_home().resolve()
    restored: list[str] = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            if not name or name.endswith("/"):
                continue
            arc = Path(name)
            if any(part == ".." for part in arc.parts):
                raise ValueError(f"Unsafe archive member: {name}")
            if not any(
                arc == Path(prefix) or str(arc).startswith(f"{prefix}/")
                for prefix in BACKUP_PREFIXES
            ):
                continue
            if arc.parts[0] == ".astroengine":
                destination = home_root / Path(*arc.parts[1:])
            else:
                destination = project_root / arc
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as src, open(destination, "wb") as dst:
                shutil.copyfileobj(src, dst)
            restored.append(str(destination))
    return restored


def schedule_status() -> dict[str, object]:
    schedule = load_schedule()
    if not schedule:
        return {}

    result = dict(schedule)
    for key in ("next_run", "last_run"):
        if key in result and result[key] is not None:
            result[f"{key}_iso"] = _iso(result[key])
    job_id = result.get("job_id")
    if job_id:
        job = get(str(job_id))
        if job:
            result["job_state"] = job.get("state")
    return result


def run_backup_job(payload: dict[str, object]) -> dict[str, object]:
    project_root = Path(str(payload.get("root", "."))).resolve()
    archive_path = create_backup_zip(project_root)
    stat = archive_path.stat()
    now_ts = queue_now()
    schedule = load_schedule()
    schedule.update(
        {
            "last_run": now_ts,
            "last_backup": str(archive_path),
            "last_backup_size": stat.st_size,
        }
    )

    retention_summary = retention.purge_temporary_derivatives()
    if retention_summary:
        (_retention_summary_path()).write_text(
            json.dumps(retention_summary, indent=2), encoding="utf-8"
        )
        schedule["last_retention"] = retention_summary

    interval = int(schedule.get("interval_seconds" or 0))
    new_job_id = None
    if interval > 0:
        next_run = now_ts + interval
        new_job_id = enqueue(
            "backup:zip", {"root": str(project_root)}, run_at=int(next_run)
        )
        schedule["next_run"] = int(next_run)
        schedule["job_id"] = new_job_id
    else:
        schedule.pop("job_id", None)
        schedule.pop("next_run", None)

    save_schedule(schedule)
    return {
        "archive": str(archive_path),
        "size": stat.st_size,
        "timestamp": now_ts,
        "retention": retention_summary,
        "next_job": new_job_id,
    }


__all__ = [
    "BACKUP_GLOB_TARGETS",
    "BACKUP_PREFIXES",
    "HOME_TARGETS",
    "cancel_backup_schedule",
    "create_backup_zip",
    "list_backups",
    "load_schedule",
    "restore_backup_zip",
    "run_backup_job",
    "save_schedule",
    "schedule_backups",
    "schedule_status",
]

