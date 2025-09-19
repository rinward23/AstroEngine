# >>> AUTO-GEN BEGIN: Doctor Conda v1.0
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PREFERRED = ("micromamba", "mamba", "conda")


def _which() -> tuple[str | None, list[str]]:
    found = []
    for exe in PREFERRED:
        path = shutil.which(exe)
        if path:
            found.append(f"{exe}={path}")
    first = found[0].split("=")[0] if found else None
    return first, found


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except Exception as e:
        return 2, str(e)


def _env_exists(runner: str, name: str) -> bool:
    code, out = _run([runner, "env", "list"])
    if code != 0:
        return False
    lines = out.splitlines()
    for ln in lines:
        if ln.strip().startswith("#"):
            continue
        if name in ln.split():
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="astroengine.doctor_conda")
    ap.add_argument("--expect-name", default="py311", help="expected env name")
    ap.add_argument("--check", action="store_true", help="perform checks and report status")
    ap.add_argument("--fix-cache", action="store_true", help="clean package caches")
    ap.add_argument("--remove-env", metavar="NAME", help="remove the given environment")
    ap.add_argument("--recreate-env", action="store_true", help="recreate env from environment.yml using the preferred runner")
    args = ap.parse_args(argv)

    runner, found = _which()
    if args.check or not any([args.fix_cache, args.remove_env, args.recreate_env]):
        sys.stdout.write("# Env Doctor — Check\n")
        sys.stdout.write(f"Detected runners: {', '.join(found) if found else 'None'}\n")
        if not runner:
            sys.stdout.write("No Conda/Mamba/Micromamba found on PATH. Install Micromamba and retry.\n")
            return 0
        # Versions
        code, out = _run([runner, "--version"])
        sys.stdout.write(f"{runner} --version => code={code}\n")
        if out:
            sys.stdout.write(out + "\n")
        # Env presence
        exists = _env_exists(runner, args.expect_name)
        sys.stdout.write(f"env '{args.expect_name}': {'present' if exists else 'missing'}\n")

    # Optional: clean caches
    if args.fix_cache:
        if not runner:
            sys.stderr.write("Cannot clean caches: no runner found.\n")
            return 2
        cmd = [runner, "clean", "--all", "--yes"] if runner != "conda" else [runner, "clean", "--all", "-y"]
        code, out = _run(cmd)
        sys.stdout.write(out)
        if code != 0:
            return 2

    # Optional: remove env
    if args.remove_env:
        if not runner:
            sys.stderr.write("Cannot remove env: no runner found.\n")
            return 2
        name = args.remove_env
        cmd = [runner, "env", "remove", "-n", name]
        if runner == "conda":
            cmd.append("-y")
        code, out = _run(cmd)
        sys.stdout.write(out)
        if code != 0:
            return 2

    # Optional: recreate env
    if args.recreate_env:
        if not runner:
            sys.stderr.write("Cannot recreate env: no runner found.\n")
            return 2
        env_yml = Path("environment.yml")
        if not env_yml.exists():
            sys.stderr.write("environment.yml not found in CWD.\n")
            return 2
        cmd = [runner, "create", "-f", str(env_yml), "-y"] if runner != "micromamba" else [runner, "create", "-f", str(env_yml), "-y"]
        code, out = _run(cmd)
        sys.stdout.write(out)
        if code != 0:
            return 2

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
# >>> AUTO-GEN END: Doctor Conda v1.0
