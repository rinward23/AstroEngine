"""Runtime diagnostics powering the system doctor endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Literal, Mapping

import sqlite3
from shutil import disk_usage

from astroengine.config import Settings, get_config_home, load_settings
from astroengine.ephemeris.utils import get_se_ephe_path

if TYPE_CHECKING:  # pragma: no cover - imported for typing only
    from astroengine.ephemeris import SwissEphemerisAdapter as _SwissEphemerisAdapter

Status = Literal["ok", "warn", "error"]


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    """Structure returned for each doctor subsystem check."""

    name: str
    status: Status
    detail: str
    data: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.data is not None:
            payload["data"] = dict(self.data)
        return payload


_STATUS_WEIGHT: dict[Status, int] = {"ok": 0, "warn": 1, "error": 2}


def _merge_status(values: Iterable[Status]) -> Status:
    """Return the most severe status present in ``values``."""

    worst = "ok"
    for value in values:
        if _STATUS_WEIGHT.get(value, 2) > _STATUS_WEIGHT[worst]:
            worst = value
    return worst  # type: ignore[return-value]


def _get_default_adapter() -> "_SwissEphemerisAdapter":
    from astroengine.ephemeris import SwissEphemerisAdapter

    return SwissEphemerisAdapter.get_default_adapter()


def _check_swisseph(settings: Settings) -> DoctorCheck:
    """Verify pyswisseph availability and ability to compute within configured caps."""

    try:
        swe = import_module("swisseph")
    except ModuleNotFoundError as exc:
        return DoctorCheck(
            name="swiss_ephemeris",
            status="error",
            detail="pyswisseph is not installed",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )
    except Exception as exc:  # pragma: no cover - defensive import guard
        return DoctorCheck(
            name="swiss_ephemeris",
            status="error",
            detail="unable to import pyswisseph",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    version = getattr(swe, "__version__", "unknown")
    ephe_path = get_se_ephe_path()
    path_info: dict[str, Any] = {"configured": ephe_path}
    path_status: Status = "ok"
    if ephe_path:
        candidate = Path(ephe_path).expanduser()
        path_info["exists"] = candidate.exists()
        path_info["resolved"] = str(candidate)
        if not candidate.exists():
            path_status = "warn"
            path_info["warning"] = "configured ephemeris directory is missing"
    else:
        path_status = "warn"
        path_info["warning"] = "SE_EPHE_PATH not set; falling back to built-in data"

    samples: list[dict[str, Any]] = []
    compute_status: Status = "ok"
    try:
        adapter = _get_default_adapter()
    except Exception as exc:  # pragma: no cover - adapter should be available when swe loads
        return DoctorCheck(
            name="swiss_ephemeris",
            status="error",
            detail="SwissEphemerisAdapter unavailable",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    for year in {settings.swiss_caps.min_year, settings.swiss_caps.max_year}:
        try:
            jd = swe.julday(int(year), 1, 1, 0.0)
            sample = adapter.body_position(jd, int(getattr(swe, "SUN")), "Sun")
        except Exception as exc:  # pragma: no cover - runtime failure reported in detail
            compute_status = "error"
            samples.append(
                {
                    "year": int(year),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        else:
            samples.append(
                {
                    "year": int(year),
                    "julian_day_ut": float(jd),
                    "longitude": float(sample.longitude),
                    "declination": float(sample.declination),
                }
            )

    status = _merge_status(("ok", path_status, compute_status))
    detail = f"pyswisseph {version}"
    if status != "ok":
        detail += " (issues detected)"

    return DoctorCheck(
        name="swiss_ephemeris",
        status=status,
        detail=detail,
        data={
            "version": version,
            "ephemeris_path": path_info,
            "range_samples": samples,
            "caps": {
                "min_year": settings.swiss_caps.min_year,
                "max_year": settings.swiss_caps.max_year,
            },
        },
    )


def _check_database() -> DoctorCheck:
    """Execute a lightweight connectivity probe against the configured database."""

    try:
        from sqlalchemy import text

        from app.db.session import engine, session_scope
    except Exception as exc:  # pragma: no cover - missing optional dependency
        return DoctorCheck(
            name="database",
            status="error",
            detail="database stack unavailable",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        return DoctorCheck(
            name="database",
            status="error",
            detail="database query failed",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    url = engine.url
    detail = f"connected ({url.get_backend_name()}://)"
    return DoctorCheck(
        name="database",
        status="ok",
        detail=detail,
        data={
            "backend": url.get_backend_name(),
            "database": url.database,
        },
    )


def _check_migrations() -> DoctorCheck:
    """Compare the applied alembic revision with the migration head."""

    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.db.session import engine
    except Exception as exc:  # pragma: no cover - alembic optional in some envs
        return DoctorCheck(
            name="migrations",
            status="warn",
            detail="alembic stack unavailable",
            data={"warning": f"{type(exc).__name__}: {exc}"},
        )

    config_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    script_location = Path(__file__).resolve().parents[2] / "migrations"
    cfg = Config(str(config_path))
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    script = ScriptDirectory.from_config(cfg)
    head_revision = script.get_current_head()

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    if head_revision == current_revision:
        status: Status = "ok"
        detail = "database is at latest revision"
    else:
        status = "error"
        detail = "database revision mismatch"

    return DoctorCheck(
        name="migrations",
        status=status,
        detail=detail,
        data={
            "head": head_revision,
            "current": current_revision,
        },
    )


def _check_cache() -> DoctorCheck:
    """Ensure the Swiss ephemeris cache is reachable and writable."""

    from astroengine.cache import positions_cache

    cache_db = positions_cache.DB
    cache_dir = cache_db.parent
    cache_dir.mkdir(parents=True, exist_ok=True)

    info: dict[str, Any] = {
        "path": str(cache_db),
        "exists": cache_db.exists(),
        "directory": str(cache_dir),
    }

    if info["exists"]:
        try:
            info["size_bytes"] = cache_db.stat().st_size
        except FileNotFoundError:
            info["size_bytes"] = None
    else:
        info["size_bytes"] = None

    try:
        total_size = 0
        for child in cache_dir.glob("**/*"):
            if child.is_file():
                try:
                    total_size += child.stat().st_size
                except OSError:
                    continue
        info["directory_size_bytes"] = total_size
    except OSError:
        info["directory_size_bytes"] = None

    try:
        connection = sqlite3.connect(str(cache_db))
        try:
            cursor = connection.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            info["integrity"] = result[0] if result else None
        finally:
            connection.close()
    except Exception as exc:
        return DoctorCheck(
            name="cache",
            status="error",
            detail="cache database unavailable",
            data={"error": f"{type(exc).__name__}: {exc}", **info},
        )

    return DoctorCheck(
        name="cache",
        status="ok" if info.get("integrity") == "ok" else "warn",
        detail="cache database healthy" if info.get("integrity") == "ok" else "cache integrity uncertain",
        data=info,
    )


def _check_settings(settings: Settings) -> DoctorCheck:
    """Expose key runtime settings and validate their ranges."""

    swiss_caps = getattr(settings, "swiss_caps", None)
    perf = getattr(settings, "perf", None)
    observability_cfg = getattr(settings, "observability", None)

    status: Status = "ok"
    notes: list[str] = []
    data: dict[str, Any] = {}

    if swiss_caps is None:
        status = "warn"
        notes.append("Swiss ephemeris caps are not configured")
    else:
        min_year = int(getattr(swiss_caps, "min_year", 0))
        max_year = int(getattr(swiss_caps, "max_year", 0))
        data["swiss_caps"] = {"min_year": min_year, "max_year": max_year}
        if min_year >= max_year:
            status = "error"
            notes.append("Swiss caps min_year must be lower than max_year")

    if perf is None:
        notes.append("Performance tuning section unavailable; defaults assumed")
        status = "warn" if status == "ok" else status
    else:
        qcache_size = int(getattr(perf, "qcache_size", 0))
        qcache_sec = float(getattr(perf, "qcache_sec", 0.0))
        max_scan_days = int(getattr(perf, "max_scan_days", 0))
        data["performance"] = {
            "qcache_size": qcache_size,
            "qcache_sec": qcache_sec,
            "max_scan_days": max_scan_days,
        }
        if qcache_size <= 0:
            status = "error"
            notes.append("qcache_size must be a positive integer")
        if qcache_sec <= 0:
            status = "warn" if status == "ok" else status
            notes.append("qcache_sec is non-positive; cache expiration disabled")
        if max_scan_days <= 0:
            status = "warn" if status == "ok" else status
            notes.append("max_scan_days should be positive for transit scans")

    if observability_cfg is None:
        notes.append("Observability configuration missing; sampling defaults used")
        status = "warn" if status == "ok" else status
    else:
        sampling_ratio = float(getattr(observability_cfg, "sampling_ratio", 0.0))
        buckets = list(getattr(observability_cfg, "metrics_histogram_buckets", []))
        data["observability"] = {
            "otel_enabled": bool(getattr(observability_cfg, "otel_enabled", False)),
            "sampling_ratio": sampling_ratio,
            "metrics_histogram_buckets": buckets,
        }
        if not 0.0 <= sampling_ratio <= 1.0:
            status = "warn" if status != "error" else status
            notes.append("sampling_ratio should be within 0–1")

    detail = (
        "; ".join(notes)
        if notes
        else "settings ranges fall within expected bounds"
    )

    return DoctorCheck(
        name="settings",
        status=status,
        detail=detail,
        data=data,
    )


def _check_disk_free(settings: Settings) -> DoctorCheck:
    """Report disk capacity near the AstroEngine configuration home."""

    try:
        base_path = get_config_home()
    except Exception as exc:  # pragma: no cover - defensive
        return DoctorCheck(
            name="disk",
            status="warn",
            detail="unable to resolve AstroEngine home directory",
            data={"error": f"{type(exc).__name__}: {exc}"},
        )

    target = base_path if base_path.exists() else base_path.parent
    payload: dict[str, Any] = {"path": str(target), "resolved_home": str(base_path)}

    try:
        usage = disk_usage(str(target))
    except FileNotFoundError:
        return DoctorCheck(
            name="disk",
            status="warn",
            detail="configuration directory missing; cannot determine disk usage",
            data=payload,
        )

    total = int(usage.total)
    free = int(usage.free)
    used = total - free
    percent_free = (free / total * 100.0) if total else 0.0

    payload.update(
        {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "percent_free": round(percent_free, 2),
        }
    )

    if percent_free <= 5.0:
        status: Status = "error"
        detail = f"only {percent_free:.1f}% free; disk critically low"
    elif percent_free < 15.0:
        status = "warn"
        detail = f"{percent_free:.1f}% free; consider pruning caches"
    else:
        status = "ok"
        detail = f"{percent_free:.1f}% free"

    return DoctorCheck(name="disk", status=status, detail=detail, data=payload)


def run_system_doctor(settings: Settings | None = None) -> dict[str, Any]:
    """Execute all doctor checks and return a serialisable payload."""

    effective_settings = settings or load_settings()
    checks = [
        _check_swisseph(effective_settings),
        _check_database(),
        _check_migrations(),
        _check_cache(),
        _check_settings(effective_settings),
        _check_disk_free(effective_settings),
    ]
    overall = _merge_status(check.status for check in checks)
    return {
        "status": overall,
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": {check.name: check.as_dict() for check in checks},
    }


__all__ = ["DoctorCheck", "run_system_doctor"]
