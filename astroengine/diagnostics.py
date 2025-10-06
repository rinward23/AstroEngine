# >>> AUTO-GEN BEGIN: Diagnostics Module v1.0
"""
AstroEngine Diagnostics ("doctor"):
- Verifies Python version, core imports, optional deps, timezone libs
- Checks Swiss Ephemeris (pyswisseph) presence and SE_EPHE_PATH contents (if set)
- Confirms public API types import cleanly
- Pings the configured database and validates Alembic migration state
- Reports cache footprint, disk free capacity, and Swiss ephemeris path sanity
- Optional smoketest against Swiss Ephemeris (Sun..Saturn) if available
- Outputs human text or JSON; returns non-zero exit on FAIL (and WARN if --strict)

Usage:
  python -m astroengine.diagnostics
  python -m astroengine.diagnostics --json
  python -m astroengine.diagnostics --strict
  python -m astroengine.diagnostics --smoketest "2025-01-01T00:00:00Z"
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import UTC
from typing import Any, Iterable

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from astroengine.ephemeris import EphemerisAdapter
from astroengine.ephemeris.swisseph_adapter import swe_calc
from astroengine.ephemeris.utils import DEFAULT_ENV_KEYS, get_se_ephe_path
from astroengine.infrastructure.home import ae_home
from astroengine.infrastructure.paths import project_root
from astroengine.utils.dependencies import DependencySpec, inspect_dependencies


@dataclass
class Check:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    detail: str
    data: dict[str, Any] | None = None


def _status_order(s: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(s, 2)


def check_python(min_version: tuple[int, int] = (3, 10)) -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) >= min_version
    required_version = f"{min_version[0]}.{min_version[1]}"
    return Check(
        name="Python",
        status="PASS" if ok else "FAIL",
        detail=(
            f"Detected {v.major}.{v.minor}.{v.micro}; requires >= {required_version}"
        ),
        data={
            "version": f"{v.major}.{v.minor}.{v.micro}",
            "impl": platform.python_implementation(),
        },
    )


def _try_import(mod: str) -> tuple[bool, Any, str]:
    try:
        m = importlib.import_module(mod)
        return True, m, getattr(m, "__version__", "")
    except Exception as e:  # pragma: no cover - surface message only
        return False, None, f"{type(e).__name__}: {e}"


def check_core_imports() -> list[Check]:
    required = [
        "astroengine.api",
        "astroengine.engine",
        "astroengine.detectors",
        "astroengine.profiles",
    ]
    out: list[Check] = []
    for mod in required:
        ok, m, err = _try_import(mod)
        out.append(
            Check(
                name=f"Import {mod}",
                status="PASS" if ok else "FAIL",
                detail=f"{'ok' if ok else 'not importable'}",
                data={
                    "version": getattr(m, "__version__", None),
                    "error": None if ok else err,
                },
            )
        )
    # Public API types
    ok_api, _, err_api = _try_import("astroengine.api")
    if ok_api:
        try:
            from astroengine.api import (  # type: ignore
                TransitEngine,
                TransitEvent,
                TransitScanConfig,
            )

            _ = (TransitEngine, TransitScanConfig, TransitEvent)
            out.append(
                Check(
                    name="Public API",
                    status="PASS",
                    detail="TransitEngine/ScanConfig/Event available",
                )
            )
        except Exception as e:  # pragma: no cover - defensive surface only
            out.append(
                Check(name="Public API", status="FAIL", detail=f"missing symbols: {e}")
            )
    else:
        out.append(
            Check(
                name="Public API",
                status="FAIL",
                detail="api module missing",
                data={"error": err_api},
            )
        )
    return out


_DEPENDENCY_SPECS: tuple[DependencySpec, ...] = (
    DependencySpec("numpy>=1.26", min_version="1.26"),
    DependencySpec("pandas>=2.2", min_version="2.2"),
    DependencySpec(
        "pyarrow>=16",
        min_version="16",
        required=False,
        note="Arrow exports and Parquet ingestion",
    ),
    DependencySpec("duckdb>=0.10", min_version="0.10"),
    DependencySpec("SQLAlchemy>=2.0", import_name="sqlalchemy", min_version="2.0"),
    DependencySpec("alembic>=1.13", min_version="1.13"),
    DependencySpec("orjson>=3.10", min_version="3.10"),
    DependencySpec("fastapi>=0.117", min_version="0.117"),
    DependencySpec("httpx>=0.28", min_version="0.28"),
    DependencySpec("jinja2>=3.1", min_version="3.1"),
    DependencySpec("pydantic>=2.7", min_version="2.7"),
    DependencySpec(
        "PyYAML>=6.0",
        import_name="yaml",
        min_version="6.0",
        required=False,
        note="YAML profiles & rule ingestion",
    ),
    DependencySpec(
        "astropy>=5.0",
        min_version="5.0",
        required=False,
        note="Solar Fire catalogue crosswalks",
    ),
    DependencySpec(
        "numba>=0.58",
        min_version="0.58",
        required=False,
        note="Accelerates ephemeris transforms",
    ),
    DependencySpec(
        "skyfield>=1.49",
        min_version="1.49",
        required=False,
        note="Satellite & mundane overlays",
    ),
    DependencySpec(
        "swisseph",
        import_name="swisseph",
        required=False,
        note="Swiss ephemeris extension (see dedicated checks for ephe path)",
    ),
)


def check_optional_deps() -> list[Check]:
    statuses = inspect_dependencies(_DEPENDENCY_SPECS)
    out: list[Check] = []
    for status in statuses:
        name = f"Dependency {status.spec.distribution()}"
        out.append(
            Check(
                name=name,
                status=status.status,
                detail=status.detail,
                data=status.data(),
            )
        )
    # sqlite3 is stdlib, but verify load
    try:
        import sqlite3  # noqa: F401

        out.append(Check(name="Dependency sqlite3", status="PASS", detail="available (stdlib)"))
    except Exception as e:  # pragma: no cover - defensive surface only
        out.append(
            Check(
                name="Dependency sqlite3",
                status="FAIL",
                detail=f"sqlite3 unavailable: {e}",
            )
        )
    return out


def _format_bytes(num_bytes: int) -> str:
    if num_bytes <= 0:
        return "0 B"
    units: tuple[str, ...] = ("B", "KB", "MB", "GB", "TB", "PB")
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def check_timezone_libs() -> list[Check]:
    out: list[Check] = []
    # zoneinfo (stdlib 3.9+)
    try:
        import zoneinfo  # noqa: F401

        out.append(Check(name="zoneinfo", status="PASS", detail="available"))
    except Exception as e:  # pragma: no cover - depends on Python build
        out.append(Check(name="zoneinfo", status="WARN", detail=f"not available: {e}"))
    # pytz optional
    ok, m, err = _try_import("pytz")
    out.append(
        Check(
            name="Optional pytz",
            status="PASS" if ok else "WARN",
            detail="found" if ok else "not installed",
            data={
                "version": getattr(m, "__version__", None),
                "error": None if ok else err,
            },
        )
    )
    return out


def check_swisseph() -> list[Check]:
    out: list[Check] = []
    ok_swe, swe, err = _try_import("swisseph")
    if not ok_swe:
        out.append(
            Check(
                name="pyswisseph",
                status="WARN",
                detail="not installed; core engine may still run limited features",
                data={"error": err},
            )
        )
        return out
    out.append(
        Check(
            name="pyswisseph",
            status="PASS",
            detail=f"installed (version: {getattr(swe, '__version__', 'n/a')})",
        )
    )
    # SE_EPHE_PATH
    ephe_path = os.environ.get("SE_EPHE_PATH", "")
    if not ephe_path:
        out.append(
            Check(
                name="SE_EPHE_PATH",
                status="PASS",
                detail=(
                    "not set; pyswisseph will use the bundled Moshier fallback — "
                    "set SE_EPHE_PATH to enable high-precision Swiss ephemeris files"
                ),
            )
        )
        return out
    p = pathlib.Path(ephe_path)
    if not p.exists() or not p.is_dir():
        out.append(
            Check(
                name="SE_EPHE_PATH",
                status="FAIL",
                detail=f"path does not exist or not a dir: {ephe_path}",
            )
        )
        return out
    # look for any *.se1/*.se2 files
    files = list(p.glob("*.se*"))
    if files:
        out.append(
            Check(
                name="SE Ephemeris Files",
                status="PASS",
                detail=f"{len(files)} file(s) detected",
                data={"examples": [f.name for f in files[:5]]},
            )
        )
    else:
        out.append(
            Check(
                name="SE Ephemeris Files",
                status="WARN",
                detail="no *.se* files found; computations may be degraded",
            )
        )
    return out


def check_ephemeris_path_sanity() -> Check:
    env_bindings = {
        key: os.environ.get(key)
        for key in DEFAULT_ENV_KEYS
        if os.environ.get(key)
    }
    resolved = get_se_ephe_path()
    data: dict[str, Any] = {"env": env_bindings, "resolved": resolved}
    if not resolved:
        return Check(
            name="Ephemeris path",
            status="WARN",
            detail="no Swiss ephemeris path resolved; using built-in fallbacks",
            data=data,
        )

    path = pathlib.Path(resolved)
    data["path"] = str(path)
    if not path.exists():
        return Check(
            name="Ephemeris path",
            status="FAIL",
            detail=f"resolved path missing: {path}",
            data=data,
        )

    swiss_files = list(path.glob("*.se*"))
    data["files"] = len(swiss_files)
    if swiss_files:
        data["examples"] = [f.name for f in swiss_files[:5]]
        return Check(
            name="Ephemeris path",
            status="PASS",
            detail=f"{path} ({len(swiss_files)} Swiss ephemeris file(s))",
            data=data,
        )
    return Check(
        name="Ephemeris path",
        status="WARN",
        detail=f"{path} present but no Swiss ephemeris files detected",
        data=data,
    )


def check_ephemeris_config() -> Check:
    try:
        adapter = EphemerisAdapter()
    except Exception as exc:  # pragma: no cover - surface only
        return Check(
            name="Ephemeris config",
            status="WARN",
            detail=f"adapter unavailable: {exc}",
        )

    summary = adapter.describe_configuration()
    observer_mode = summary.get("observer_mode", "geocentric")
    observer_detail = summary.get("observer_location")
    detail = f"time-scale {summary.get('time_scale')}  observer={observer_mode}"
    if observer_detail:
        detail += f" ({observer_detail})"
    return Check(
        name="Ephemeris config",
        status="PASS",
        detail=detail,
        data=summary,
    )


def _resolve_database_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    return os.environ.get("DATABASE_URL", "sqlite:///./dev.db")


def _mask_database_url(url: str) -> str:
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:  # pragma: no cover - defensive for unparsable URLs
        return url


def check_database_ping(url: str | None = None) -> Check:
    database_url = _resolve_database_url(url)
    safe_url = _mask_database_url(database_url)
    try:
        engine = create_engine(database_url, future=True, poolclass=NullPool)
    except Exception as exc:  # pragma: no cover - configuration surface only
        return Check(
            name="Database ping",
            status="FAIL",
            detail=f"engine creation failed: {exc}",
            data={"url": safe_url},
        )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return Check(
            name="Database ping",
            status="PASS",
            detail=f"connected to {safe_url}",
            data={"url": safe_url},
        )
    except SQLAlchemyError as exc:
        return Check(
            name="Database ping",
            status="FAIL",
            detail=f"connection failed: {exc}",
            data={"url": safe_url},
        )
    finally:
        engine.dispose()


def _alembic_config(database_url: str) -> Config | None:
    ini_path = project_root() / "alembic.ini"
    if not ini_path.exists():
        return None
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def check_migrations_current(url: str | None = None) -> Check:
    database_url = _resolve_database_url(url)
    safe_url = _mask_database_url(database_url)
    cfg = _alembic_config(database_url)
    if cfg is None:
        return Check(
            name="Migrations",
            status="WARN",
            detail="alembic.ini not found; cannot verify migration state",
            data={"url": safe_url},
        )

    script = ScriptDirectory.from_config(cfg)
    heads = list(script.get_heads())
    head = script.get_current_head()
    try:
        engine = create_engine(database_url, future=True, poolclass=NullPool)
    except Exception as exc:  # pragma: no cover - configuration surface only
        return Check(
            name="Migrations",
            status="FAIL",
            detail=f"engine creation failed: {exc}",
            data={"url": safe_url, "heads": heads},
        )

    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
    except Exception as exc:
        return Check(
            name="Migrations",
            status="FAIL",
            detail=f"unable to inspect revision: {exc}",
            data={"url": safe_url, "heads": heads},
        )
    finally:
        engine.dispose()

    data = {"url": safe_url, "current": current, "head": head, "heads": heads}
    if not heads:
        return Check(
            name="Migrations",
            status="WARN",
            detail="no Alembic heads found in migrations directory",
            data=data,
        )
    if current is None:
        return Check(
            name="Migrations",
            status="WARN",
            detail=f"database not stamped; latest head {head}",
            data=data,
        )
    if current not in heads:
        return Check(
            name="Migrations",
            status="FAIL",
            detail=f"database at {current}; expected {head}",
            data=data,
        )
    return Check(
        name="Migrations",
        status="PASS",
        detail=f"database revision {current} matches head {head}",
        data=data,
    )


def _cache_directory() -> pathlib.Path:
    return ae_home() / "cache"


def check_cache_sizes() -> Check:
    cache_dir = _cache_directory()
    if not cache_dir.exists():
        return Check(
            name="Cache usage",
            status="PASS",
            detail="cache directory not initialised",
            data={"path": str(cache_dir), "files": 0, "total_bytes": 0},
        )

    total = 0
    file_entries: list[tuple[str, int]] = []
    for path in cache_dir.rglob("*"):
        if path.is_file():
            size = path.stat().st_size
            total += size
            file_entries.append((str(path.relative_to(cache_dir)), size))

    file_entries.sort(key=lambda item: item[1], reverse=True)
    top_entries = file_entries[:5]
    detail = (
        f"{_format_bytes(total)} across {len(file_entries)} file(s) under {cache_dir}"
    )
    data = {
        "path": str(cache_dir),
        "files": len(file_entries),
        "total_bytes": total,
        "top": top_entries,
    }
    return Check(name="Cache usage", status="PASS", detail=detail, data=data)


def check_disk_free(path: pathlib.Path | None = None) -> Check:
    target = path or ae_home()
    target.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target)
    free = usage.free
    used_pct = (usage.used / usage.total * 100) if usage.total else 0.0
    threshold = 512 * 1024 * 1024  # 512 MiB
    status = "PASS" if free >= threshold else "WARN"
    detail = (
        f"{_format_bytes(free)} free ({used_pct:.1f}% used) on volume hosting {target}"
    )
    data = {
        "path": str(target),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": free,
        "threshold_bytes": threshold,
    }
    return Check(name="Disk space", status=status, detail=detail, data=data)


def _trim_probe_rows(rows: Iterable[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if idx >= limit:
            break
        out.append(row)
    return out


def check_swiss_probes(iso_utc: str = "2025-01-01T00:00:00Z") -> Check:
    rows = smoketest_positions(iso_utc)
    sample = _trim_probe_rows(rows)
    errors = [r for r in rows if r.get("body") == "ERROR"]
    successes = [r for r in rows if "lon_deg" in r]
    infos = [r for r in rows if r.get("body") == "INFO"]
    data = {"timestamp": iso_utc, "sample": sample}
    if errors:
        detail = errors[0].get("detail", "Swiss probe failed")
        return Check(name="Swiss probes", status="FAIL", detail=detail, data=data)
    if successes:
        detail = f"computed {len(successes)} Swiss ephemeris position(s)"
        return Check(name="Swiss probes", status="PASS", detail=detail, data=data)
    if infos:
        detail = infos[0].get("detail", "Swiss ephemeris unavailable")
        return Check(name="Swiss probes", status="WARN", detail=detail, data=data)
    return Check(
        name="Swiss probes",
        status="WARN",
        detail="no Swiss ephemeris data returned",
        data=data,
    )


def check_profiles_presence() -> Check:
    # Verify that VCA domain profiles symbol is importable
    ok, _, err = _try_import("astroengine.profiles")
    if not ok:
        return Check(
            name="Profiles module",
            status="FAIL",
            detail="astroengine.profiles not importable",
            data={"error": err},
        )
    try:
        from astroengine.profiles import VCA_DOMAIN_PROFILES  # type: ignore

        try:
            count = len(VCA_DOMAIN_PROFILES)  # type: ignore[arg-type]
        except TypeError:
            keys = getattr(VCA_DOMAIN_PROFILES, "keys", None)
            count = len(list(keys())) if callable(keys) else "present"
        return Check(name="Profiles registry", status="PASS", detail=str(count))
    except Exception as e:  # pragma: no cover - defensive surface only
        return Check(
            name="Profiles registry",
            status="WARN",
            detail=f"could not inspect profiles: {e}",
        )


def collect_diagnostics(strict: bool = False) -> dict[str, Any]:
    checks: list[Check] = []
    checks.append(check_python())
    checks.extend(check_core_imports())
    checks.extend(check_optional_deps())
    checks.extend(check_timezone_libs())
    checks.extend(check_swisseph())
    checks.append(check_ephemeris_path_sanity())
    checks.append(check_ephemeris_config())
    checks.append(check_database_ping())
    checks.append(check_migrations_current())
    checks.append(check_cache_sizes())
    checks.append(check_disk_free())
    checks.append(check_swiss_probes())
    checks.append(check_profiles_presence())
    # summarize
    worst = max((c.status for c in checks), key=_status_order, default="PASS")
    has_fail = any(c.status == "FAIL" for c in checks)
    has_warn = any(c.status == "WARN" for c in checks)
    exit_code = 1 if has_fail or (strict and has_warn) else 0
    return {
        "summary": {
            "pass": sum(c.status == "PASS" for c in checks),
            "warn": sum(c.status == "WARN" for c in checks),
            "fail": sum(c.status == "FAIL" for c in checks),
            "worst": worst,
            "strict": strict,
            "exit_code": exit_code,
            "platform": platform.platform(),
        },
        "checks": [asdict(c) for c in checks],
    }


def _format_text_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    s = payload["summary"]
    lines.append("AstroEngine Doctor — Diagnostics Report")
    summary_line = (
        f"Result: worst={s['worst']}  pass={s['pass']}  warn={s['warn']}  "
        f"fail={s['fail']}  strict={s['strict']}"
    )
    lines.append(summary_line)
    lines.append(f"Platform: {s['platform']}")
    lines.append("")
    for c in payload["checks"]:
        emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(c["status"], "❓")
        line = f"{emoji} {c['status']:4}  {c['name']}: {c['detail']}"
        lines.append(line)
    return "\n".join(lines)


def _parse_iso_utc(ts: str) -> tuple[int, int, int, float]:
    # Accepts YYYY-MM-DDTHH:MM:SSZ or without Z; returns y,m,d,ut_hours
    ts = ts.strip().replace("Z", "")
    date, time = (ts.split("T") + ["00:00:00"])[:2]
    y, m, d = [int(x) for x in date.split("-")]
    hh, mm, ss = [int(x) for x in time.split(":")]
    return y, m, d, hh + mm / 60.0 + ss / 3600.0


def smoketest_positions(iso_utc: str = "2025-01-01T00:00:00Z") -> list[dict[str, Any]]:
    ok, swe, err = _try_import("swisseph")
    if not ok:
        return [{"body": "INFO", "detail": f"pyswisseph not installed: {err}"}]
    try:
        ephe = os.environ.get("SE_EPHE_PATH", "")
        if ephe:
            swe().set_ephe_path(ephe)
        y, m, d, ut = _parse_iso_utc(iso_utc)
        jd = swe().julday(y, m, d, ut)  # UT
        ids = [
            ("Sun", swe().SUN),
            ("Moon", swe().MOON),
            ("Mercury", swe().MERCURY),
            ("Venus", swe().VENUS),
            ("Mars", swe().MARS),
            ("Jupiter", swe().JUPITER),
            ("Saturn", swe().SATURN),
        ]
        out: list[dict[str, Any]] = []
        for name, pid in ids:
            xx, _, serr = swe_calc(jd_ut=jd, planet_index=pid, flag=0)
            if serr:
                raise RuntimeError(serr)
            lon = float(xx[0])
            lat = float(xx[1])
            dist = float(xx[2])
            out.append({"body": name, "lon_deg": lon, "lat_deg": lat, "dist_au": dist})
        return out
    except Exception as e:  # pragma: no cover - smoketest is best-effort
        return [{"body": "ERROR", "detail": f"smoketest failed: {e}"}]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astroengine.diagnostics", description="AstroEngine diagnostics (doctor)"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument(
        "--strict", action="store_true", help="treat WARN as failure (exit non-zero)"
    )
    parser.add_argument(
        "--smoketest",
        metavar="ISO_UTC",
        nargs="?",
        const="now",
        help="print Sun..Saturn positions via Swiss Ephemeris (if installed)",
    )

    args = parser.parse_args(argv)

    payload = collect_diagnostics(strict=args.strict)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(_format_text_report(payload))

    if args.smoketest is not None:
        iso = args.smoketest
        if iso == "now":
            from datetime import datetime

            iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        print("\nSmoketest (Sun..Saturn) —", iso)
        for row in smoketest_positions(iso):
            if "lon_deg" in row:
                position_line = (
                    f"  {row['body']:8} λ={row['lon_deg']:9.5f}°  "
                    f"β={row['lat_deg']:8.5f}°  Δ={row['dist_au']:.6f} au"
                )
                print(position_line)
            else:
                print(f"  {row['body']}: {row.get('detail','')}")

    return int(payload["summary"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: Diagnostics Module v1.0
