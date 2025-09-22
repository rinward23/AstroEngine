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
from typing import Any, Dict, List, Tuple

from astroengine.ephemeris import EphemerisAdapter


@dataclass
class Check:
    name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    detail: str
    data: Dict[str, Any] | None = None


def _status_order(s: str) -> int:
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(s, 2)


def check_python(min_version: Tuple[int, int] = (3, 10)) -> Check:
    v = sys.version_info
    ok = (v.major, v.minor) >= min_version
    required_version = f"{min_version[0]}.{min_version[1]}"
    return Check(
        name="Python",
        status="PASS" if ok else "FAIL",
        detail=(f"Detected {v.major}.{v.minor}.{v.micro}; requires >= {required_version}"),
        data={
            "version": f"{v.major}.{v.minor}.{v.micro}",
            "impl": platform.python_implementation(),
        },
    )


def _try_import(mod: str) -> Tuple[bool, Any, str]:
    try:
        m = importlib.import_module(mod)
        return True, m, getattr(m, "__version__", "")
    except Exception as e:  # pragma: no cover - surface message only
        return False, None, f"{type(e).__name__}: {e}"


def check_core_imports() -> List[Check]:
    required = [
        "astroengine.api",
        "astroengine.engine",
        "astroengine.detectors",
        "astroengine.profiles",
    ]
    out: List[Check] = []
    for mod in required:
        ok, m, err = _try_import(mod)
        out.append(
            Check(
                name=f"Import {mod}",
                status="PASS" if ok else "FAIL",
                detail=f"{'ok' if ok else 'not importable'}",
                data={"version": getattr(m, "__version__", None), "error": None if ok else err},
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
            out.append(Check(name="Public API", status="FAIL", detail=f"missing symbols: {e}"))
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


def check_optional_deps() -> List[Check]:
    names = ["numpy", "pandas", "pyarrow"]
    out: List[Check] = []
    for n in names:
        ok, m, err = _try_import(n)
        out.append(
            Check(
                name=f"Optional {n}",
                status="PASS" if ok else "WARN",
                detail=f"{'found' if ok else 'not installed'}",
                data={"version": getattr(m, "__version__", None), "error": None if ok else err},
            )
        )
    # sqlite3 is stdlib, but verify load
    try:
        import sqlite3  # noqa: F401

        out.append(Check(name="sqlite3", status="PASS", detail="available (stdlib)"))
    except Exception as e:  # pragma: no cover - defensive surface only
        out.append(Check(name="sqlite3", status="FAIL", detail=f"sqlite3 unavailable: {e}"))
    return out


def check_timezone_libs() -> List[Check]:
    out: List[Check] = []
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
            data={"version": getattr(m, "__version__", None), "error": None if ok else err},
        )
    )
    return out


def check_swisseph() -> List[Check]:
    out: List[Check] = []
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
            name="Profiles registry", status="WARN", detail=f"could not inspect profiles: {e}"
        )


def collect_diagnostics(strict: bool = False) -> Dict[str, Any]:
    checks: List[Check] = []
    checks.append(check_python())
    checks.extend(check_core_imports())
    checks.extend(check_optional_deps())
    checks.extend(check_timezone_libs())
    checks.extend(check_swisseph())
    checks.append(check_ephemeris_config())
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


def _format_text_report(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
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


def _parse_iso_utc(ts: str) -> Tuple[int, int, int, float]:
    # Accepts YYYY-MM-DDTHH:MM:SSZ or without Z; returns y,m,d,ut_hours
    ts = ts.strip().replace("Z", "")
    date, time = (ts.split("T") + ["00:00:00"])[:2]
    y, m, d = [int(x) for x in date.split("-")]
    hh, mm, ss = [int(x) for x in time.split(":")]
    return y, m, d, hh + mm / 60.0 + ss / 3600.0


def smoketest_positions(iso_utc: str = "2025-01-01T00:00:00Z") -> List[Dict[str, Any]]:
    ok, swe, err = _try_import("swisseph")
    if not ok:
        return [{"body": "INFO", "detail": f"pyswisseph not installed: {err}"}]
    try:
        ephe = os.environ.get("SE_EPHE_PATH", "")
        if ephe:
            swe.set_ephe_path(ephe)
        y, m, d, ut = _parse_iso_utc(iso_utc)
        jd = swe.julday(y, m, d, ut)  # UT
        ids = [
            ("Sun", swe.SUN),
            ("Moon", swe.MOON),
            ("Mercury", swe.MERCURY),
            ("Venus", swe.VENUS),
            ("Mars", swe.MARS),
            ("Jupiter", swe.JUPITER),
            ("Saturn", swe.SATURN),
        ]
        out: List[Dict[str, Any]] = []
        for name, pid in ids:
            positions, *_ = swe.calc_ut(jd, pid)
            lon = float(positions[0])
            lat = float(positions[1])
            dist = float(positions[2])
            out.append({"body": name, "lon_deg": lon, "lat_deg": lat, "dist_au": dist})
        return out
    except Exception as e:  # pragma: no cover - smoketest is best-effort
        return [{"body": "ERROR", "detail": f"smoketest failed: {e}"}]


def main(argv: List[str] | None = None) -> int:
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
            from datetime import datetime, timezone

            iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
