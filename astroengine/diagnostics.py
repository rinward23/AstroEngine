# >>> AUTO-GEN BEGIN: Diagnostics Module v1.0
"""
AstroEngine Diagnostics ("doctor"):
- Verifies Python version, core imports, optional deps, timezone libs
- Checks Swiss Ephemeris (pyswisseph) presence and SE_EPHE_PATH contents (if set)
- Confirms public API types import cleanly
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
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Tuple


def _ensure_repo_on_sys_path() -> None:
    """Make sure the repository root is discoverable when run as a script."""

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_ensure_repo_on_sys_path()


@dataclass
class Check:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    detail: str
    data: Dict[str, Any] | None = None


def _status_order(status: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(status, 2)


def check_python(min_version: Tuple[int, int] = (3, 10)) -> Check:
    version_info = sys.version_info
    ok = (version_info.major, version_info.minor) >= min_version
    return Check(
        name="Python",
        status="PASS" if ok else "FAIL",
        detail=(
            f"Detected {version_info.major}.{version_info.minor}.{version_info.micro}; "
            f"requires >= {min_version[0]}.{min_version[1]}"
        ),
        data={
            "version": f"{version_info.major}.{version_info.minor}.{version_info.micro}",
            "impl": platform.python_implementation(),
        },
    )


def _try_import(module: str) -> Tuple[bool, Any, str]:
    try:
        imported = importlib.import_module(module)
        return True, imported, getattr(imported, "__version__", "")
    except Exception as exc:  # pragma: no cover - we capture message only
        return False, None, f"{type(exc).__name__}: {exc}"


def check_core_imports() -> List[Check]:
    required = [
        "astroengine.api",
        "astroengine.engine",
        "astroengine.detectors",
        "astroengine.profiles",
    ]
    output: List[Check] = []
    for module in required:
        ok, imported, error = _try_import(module)
        output.append(
            Check(
                name=f"Import {module}",
                status="PASS" if ok else "FAIL",
                detail="ok" if ok else "not importable",
                data={
                    "version": getattr(imported, "__version__", None) if ok else None,
                    "error": None if ok else error,
                },
            )
        )

    ok_api, _, err_api = _try_import("astroengine.api")
    if ok_api:
        try:
            from astroengine.api import TransitEngine, TransitEvent, TransitScanConfig  # type: ignore

            _ = (TransitEngine, TransitScanConfig, TransitEvent)
            output.append(
                Check(
                    name="Public API",
                    status="PASS",
                    detail="TransitEngine/ScanConfig/Event available",
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            output.append(
                Check(
                    name="Public API",
                    status="FAIL",
                    detail=f"missing symbols: {exc}",
                )
            )
    else:
        output.append(Check(name="Public API", status="FAIL", detail="api module missing"))
    return output


def check_optional_deps() -> List[Check]:
    names = ["numpy", "pandas", "pyarrow"]
    output: List[Check] = []
    for name in names:
        ok, imported, error = _try_import(name)
        output.append(
            Check(
                name=f"Optional {name}",
                status="PASS" if ok else "WARN",
                detail="found" if ok else "not installed",
                data={
                    "version": getattr(imported, "__version__", None) if ok else None,
                    "error": None if ok else error,
                },
            )
        )

    try:
        import sqlite3  # noqa: F401

        output.append(Check(name="sqlite3", status="PASS", detail="available (stdlib)"))
    except Exception as exc:  # pragma: no cover - sqlite3 generally present
        output.append(Check(name="sqlite3", status="FAIL", detail=f"sqlite3 unavailable: {exc}"))
    return output


def check_timezone_libs() -> List[Check]:
    output: List[Check] = []
    try:
        import zoneinfo  # noqa: F401

        output.append(Check(name="zoneinfo", status="PASS", detail="available"))
    except Exception as exc:  # pragma: no cover - depends on Python build
        output.append(Check(name="zoneinfo", status="WARN", detail=f"not available: {exc}"))

    ok, imported, error = _try_import("pytz")
    output.append(
        Check(
            name="Optional pytz",
            status="PASS" if ok else "WARN",
            detail="found" if ok else "not installed",
            data={
                "version": getattr(imported, "__version__", None) if ok else None,
                "error": None if ok else error,
            },
        )
    )
    return output


def check_swisseph() -> List[Check]:
    output: List[Check] = []
    ok_swe, swe, error = _try_import("swisseph")
    if not ok_swe:
        output.append(
            Check(
                name="pyswisseph",
                status="WARN",
                detail="not installed; core engine may still run limited features",
                data={"error": error},
            )
        )
        return output

    output.append(
        Check(
            name="pyswisseph",
            status="PASS",
            detail=f"installed (version: {getattr(swe, '__version__', 'n/a')})",
        )
    )

    ephe_path = os.environ.get("SE_EPHE_PATH", "")
    if not ephe_path:
        output.append(
            Check(
                name="SE_EPHE_PATH",
                status="WARN",
                detail="environment var not set; Moshier fallback may apply; high-precision files recommended",
            )
        )
        return output

    path = pathlib.Path(ephe_path)
    if not path.exists() or not path.is_dir():
        output.append(
            Check(
                name="SE_EPHE_PATH",
                status="FAIL",
                detail=f"path does not exist or not a dir: {ephe_path}",
            )
        )
        return output

    files = list(path.glob("*.se*"))
    if files:
        output.append(
            Check(
                name="SE Ephemeris Files",
                status="PASS",
                detail=f"{len(files)} file(s) detected",
                data={"examples": [f.name for f in files[:5]]},
            )
        )
    else:
        output.append(
            Check(
                name="SE Ephemeris Files",
                status="WARN",
                detail="no *.se* files found; computations may be degraded",
            )
        )
    return output


def check_profiles_presence() -> Check:
    ok, _, error = _try_import("astroengine.profiles")
    if not ok:
        return Check(
            name="Profiles module",
            status="FAIL",
            detail="astroengine.profiles not importable",
            data={"error": error},
        )
    try:
        from astroengine.profiles import VCA_DOMAIN_PROFILES  # type: ignore

        count: Any
        try:
            count = len(VCA_DOMAIN_PROFILES)  # type: ignore[arg-type]
        except TypeError:
            keys: Iterable[Any] | None = getattr(VCA_DOMAIN_PROFILES, "keys", None)  # type: ignore[attr-defined]
            if callable(keys):
                count = len(list(keys()))
            else:
                count = "present"
        return Check(name="Profiles registry", status="PASS", detail=str(count))
    except Exception as exc:  # pragma: no cover - defensive
        return Check(name="Profiles registry", status="WARN", detail=f"could not inspect profiles: {exc}")


def collect_diagnostics(strict: bool = False) -> Dict[str, Any]:
    checks: List[Check] = []
    checks.append(check_python())
    checks.extend(check_core_imports())
    checks.extend(check_optional_deps())
    checks.extend(check_timezone_libs())
    checks.extend(check_swisseph())
    checks.append(check_profiles_presence())

    worst = max((check.status for check in checks), key=_status_order, default="PASS")
    has_fail = any(check.status == "FAIL" for check in checks)
    has_warn = any(check.status == "WARN" for check in checks)
    exit_code = 1 if has_fail or (strict and has_warn) else 0
    return {
        "summary": {
            "pass": sum(check.status == "PASS" for check in checks),
            "warn": sum(check.status == "WARN" for check in checks),
            "fail": sum(check.status == "FAIL" for check in checks),
            "worst": worst,
            "strict": strict,
            "exit_code": exit_code,
            "platform": platform.platform(),
        },
        "checks": [asdict(check) for check in checks],
    }


def _format_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    summary = payload["summary"]
    lines.append("AstroEngine Doctor — Diagnostics Report")
    lines.append(
        "Result: worst={worst}  pass={pass}  warn={warn}  fail={fail}  strict={strict}".format(**summary)
    )
    lines.append(f"Platform: {summary['platform']}")
    lines.append("")
    for check in payload["checks"]:
        emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(check["status"], "❓")
        lines.append(f"{emoji} {check['status']:4}  {check['name']}: {check['detail']}")
    return "\n".join(lines)


def _parse_iso_utc(timestamp: str) -> Tuple[int, int, int, float]:
    ts = timestamp.strip().replace("Z", "")
    if "T" in ts:
        date_str, time_str = ts.split("T", 1)
    else:
        date_str, time_str = ts, "00:00:00"
    if not time_str:
        time_str = "00:00:00"
    y_str, m_str, d_str = date_str.split("-")
    hh_str, mm_str, ss_str = (time_str.split(":") + ["0", "0", "0"])[:3]
    hours = int(hh_str)
    minutes = int(mm_str)
    seconds = float(ss_str)
    return int(y_str), int(m_str), int(d_str), hours + minutes / 60.0 + seconds / 3600.0


def smoketest_positions(iso_utc: str = "2025-01-01T00:00:00Z") -> List[Dict[str, Any]]:
    ok, swe, error = _try_import("swisseph")
    if not ok:
        return [{"body": "INFO", "detail": f"pyswisseph not installed: {error}"}]
    try:
        ephe_path = os.environ.get("SE_EPHE_PATH", "")
        if ephe_path:
            swe.set_ephe_path(ephe_path)
        year, month, day, ut = _parse_iso_utc(iso_utc)
        julian_day = swe.julday(year, month, day, ut)
        bodies = [
            ("Sun", swe.SUN),
            ("Moon", swe.MOON),
            ("Mercury", swe.MERCURY),
            ("Venus", swe.VENUS),
            ("Mars", swe.MARS),
            ("Jupiter", swe.JUPITER),
            ("Saturn", swe.SATURN),
        ]
        rows: List[Dict[str, Any]] = []
        for name, pid in bodies:
            result = swe.calc_ut(julian_day, pid)
            coords = result[0]
            lon = float(coords[0])
            lat = float(coords[1])
            dist = float(coords[2])
            rows.append({"body": name, "lon_deg": lon, "lat_deg": lat, "dist_au": dist})
        return rows
    except Exception as exc:  # pragma: no cover - smoketest is best-effort
        return [{"body": "ERROR", "detail": f"smoketest failed: {exc}"}]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="astroengine.diagnostics",
        description="AstroEngine diagnostics (doctor)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    parser.add_argument("--strict", action="store_true", help="treat WARN as failure (exit non-zero)")
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
            from datetime import datetime, timezone

            iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print("\nSmoketest (Sun..Saturn) —", iso)
        for row in smoketest_positions(iso):
            if {"lon_deg", "lat_deg", "dist_au"}.issubset(row):
                print(
                    "  {body:8} λ={lon_deg:9.5f}°  β={lat_deg:8.5f}°  Δ={dist_au:.6f} au".format(
                        body=row["body"],
                        lon_deg=row["lon_deg"],
                        lat_deg=row["lat_deg"],
                        dist_au=row["dist_au"],
                    )
                )
            else:
                print(f"  {row.get('body', 'INFO')}: {row.get('detail', '')}")

    return int(payload["summary"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: Diagnostics Module v1.0
