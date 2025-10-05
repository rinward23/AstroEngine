# >>> AUTO-GEN BEGIN: Maintenance Orchestrator v1.0
"""
AstroEngine Maintenance Orchestrator ("run everything").

Goals:
  - Run diagnostics (doctor) in strict mode.
  - Optionally auto-install missing dev/runtime deps (opt-in).
  - Run formatters/lints, tests, optional package build.
  - Clean caches/artifacts when asked.
  - Produce a single PASS/FAIL summary and exit code.

Usage (prompts):
  python -m astroengine.maint --full --strict
  python -m astroengine.maint --full --strict --auto-install all
  python -m astroengine.maint --fix all --with-build
  python -m astroengine.maint --clean

Flags:
  --full            : enables diagnostics + fix(format/lint) + tests + (optional) build
  --strict          : treat WARN as FAIL where applicable
  --fix [items]     : items ∈ {format,lint,imports,clean,all}
  --with-tests      : run pytest
  --with-build      : build sdist/wheel if 'build' is available
                      (auto-install when allowed)
  --auto-install X  : X ∈ {none,dev,runtime,all}; installs missing
                      entries from requirements-dev.txt when possible
  --clean           : remove caches/artifacts and exit
  --yes             : non-interactive for install prompts

Exit codes:
  0 = all gates passed, 1 = at least one gate failed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from .infrastructure.paths import project_root

ROOT = project_root()
REQ_DEV = ROOT / "requirements-dev.txt"
_env_constraint = os.environ.get("PIP_CONSTRAINT")
CONSTRAINT_FILE = Path(_env_constraint) if _env_constraint else ROOT / "constraints.txt"


# ---------- helpers ----------
def sh(
    cmd: list[str], cwd: Path | None = None, allow_fail: bool = False
) -> tuple[int, str]:
    """Run a subprocess, return (code, combined_output)."""

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    out, _ = proc.communicate()
    if proc.returncode != 0 and not allow_fail:
        print(out, end="")
    return proc.returncode, out


def have_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def parse_requirements(path: Path) -> list[str]:
    if not path.exists():
        return []
    pkgs: list[str] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("-r") or s.startswith("--"):
            continue
        pkgs.append(s)
    return pkgs


def pip_install(pkgs: Iterable[str]) -> int:
    pkgs = list(pkgs)
    if not pkgs:
        return 0
    cmd = [sys.executable, "-m", "pip", "install"]
    if CONSTRAINT_FILE.exists():
        cmd.extend(["--constraint", str(CONSTRAINT_FILE)])
    cmd.extend(pkgs)
    code, _ = sh(cmd)
    return code


# ---------- gates ----------
def gate_diagnostics(strict: bool) -> bool:
    try:
        from .diagnostics import collect_diagnostics  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure gets surfaced
        print(f"❌ diagnostics import failed: {exc}")
        return False
    payload = collect_diagnostics(strict=strict)
    print(json.dumps(payload, indent=2))
    return payload["summary"]["exit_code"] == 0


def gate_format_lint(apply_fixes: bool) -> bool:
    ok = True
    if apply_fixes:
        sh(["ruff", "check", "--fix", "."], allow_fail=True)
        sh(["black", "."], allow_fail=True)
        sh(["isort", "--profile=black", "."], allow_fail=True)
    ok &= sh(["ruff", "check", "."], allow_fail=True)[0] == 0
    ok &= sh(["black", "--check", "."], allow_fail=True)[0] == 0
    ok &= sh(["isort", "--check-only", "--profile=black", "."], allow_fail=True)[0] == 0
    return ok


def gate_tests() -> bool:
    return sh(["pytest", "-q"], allow_fail=True)[0] == 0


def gate_build(ensure_build_tool: bool) -> bool:
    if not have_module("build") and ensure_build_tool:
        pip_install(["build>=1"])
    if not have_module("build"):
        print("ℹ️  skipping package build (python -m build not available)")
        return True
    return sh([sys.executable, "-m", "build"], allow_fail=True)[0] == 0


def gate_auto_install(scope: str, non_interactive: bool) -> bool:
    if scope in ("none", "", None):
        return True
    pkgs = parse_requirements(REQ_DEV)
    if not pkgs:
        print("ℹ️  no requirements-dev.txt found; nothing to auto-install")
        return True
    if not non_interactive:
        print(
            "⚠️  Auto-install may modify your environment."
            " Re-run with --yes to proceed non-interactively."
        )
        return False
    code = pip_install(pkgs)
    return code == 0


def gate_clean() -> bool:
    cleaned: list[str] = []
    for name in [".pytest_cache", ".ruff_cache", ".mypy_cache"]:
        d = ROOT / name
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            cleaned.append(name)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d, ignore_errors=True)
    for name in ["build", "dist"]:
        d = ROOT / name
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            cleaned.append(name)
    diag = ROOT / "diagnostics.json"
    if diag.exists():
        diag.unlink()
        cleaned.append(diag.name)
    print(f"🧹 cleaned: {', '.join(cleaned) if cleaned else '(nothing)'}")
    return True


# ---------- CLI ----------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="astroengine.maint", description="AstroEngine maintenance orchestrator"
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="run diagnostics + (fix)format/lint + tests (+ build if --with-build)",
    )
    ap.add_argument(
        "--strict", action="store_true", help="treat WARN as failure in diagnostics"
    )
    ap.add_argument(
        "--fix",
        nargs="?",
        const="all",
        help="apply fixes: format,lint,imports,clean,all (default: all)",
    )
    ap.add_argument("--with-tests", action="store_true", help="run pytest")
    ap.add_argument(
        "--with-build",
        action="store_true",
        help="build the package (if build is available)",
    )
    ap.add_argument(
        "--auto-install",
        default="none",
        choices=["none", "dev", "runtime", "all"],
        help="auto-install missing deps from requirements-dev.txt",
    )
    ap.add_argument(
        "--clean", action="store_true", help="clean caches/artifacts and exit"
    )
    ap.add_argument("--yes", action="store_true", help="assume yes for auto-install")
    args = ap.parse_args(argv)

    if args.clean:
        return 0 if gate_clean() else 1

    strict = bool(args.strict)
    run_tests = bool(args.full or args.with_tests)
    run_build = bool(args.with_build or (args.full and False))
    apply_fixes = args.fix in ("all", "format", "lint", "imports") or args.full

    results: list[tuple[str, bool]] = []

    if args.auto_install != "none":
        results.append(("auto-install", gate_auto_install(args.auto_install, args.yes)))

    results.append(("diagnostics", gate_diagnostics(strict)))

    results.append(("format/lint", gate_format_lint(apply_fixes)))

    if run_tests:
        results.append(("tests", gate_tests()))

    if run_build:
        results.append(
            ("build", gate_build(ensure_build_tool=args.auto_install != "none"))
        )

    worst_fail = any(not ok for _, ok in results)
    print("\n=== Maintenance Summary ===")
    for name, ok in results:
        print(f"{'✅' if ok else '❌'} {name}")
    return 0 if not worst_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
# >>> AUTO-GEN END: Maintenance Orchestrator v1.0
