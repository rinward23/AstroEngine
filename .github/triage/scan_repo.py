# >>> AUTO-GEN BEGIN: triage scanner v1.0
"""
Triage scanner:
- Runs lightweight checks (imports, swe ephemeris path, ruff, mypy, pytest smoke)
- Creates/updates a single meta issue: "Meta: Automated Health Report"
- Creates targeted issues for hard failures (e.g., missing pyswisseph) if not present
- Writes a Markdown Issue Index (links to GitHub Issues)
Idempotent: titles are stable; updates in-place.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN")
BASE_URL = f"https://api.github.com/repos/{REPO}" if REPO else ""
ROOT = Path(__file__).resolve().parents[2]
TRIAGE_DIR = Path(__file__).resolve().parent
TRIAGE_DIR.mkdir(parents=True, exist_ok=True)
REPORT = TRIAGE_DIR / "triage_report.md"

try:
    from github import Github  # PyGithub
except Exception:
    Github = None  # fallback to curl


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def check_import_swisseph() -> tuple[bool, str]:
    code = "import swisseph as swe; print(getattr(swe,'__version__', 'ok'))"
    rc, out = run([sys.executable, "-c", code])
    if rc != 0:
        return False, out.strip()
    return True, out.strip()


def check_ephe_path() -> tuple[bool, str]:
    # Accept env, common folders, or bundled ./ephe
    candidates = [
        os.environ.get("SE_EPHE_PATH"),
        str(ROOT / "ephe"),
        str(Path.home() / ".sweph"),
    ]
    candidates = [c for c in candidates if c]
    found = any(Path(c).exists() for c in candidates)
    msg = f"candidates={candidates}"
    return found, msg


def check_ruff() -> tuple[bool, str]:
    rc, out = run([sys.executable, "-m", "ruff", "check", str(ROOT)])
    return rc == 0, out


def check_mypy() -> tuple[bool, str]:
    # best-effort only if config exists
    ini = ROOT / "mypy.ini"
    if not shutil.which("mypy") or not ini.exists():
        return True, "skipped"
    rc, out = run(["mypy", "--install-types", "--non-interactive", str(ROOT)])
    return rc == 0, out


def check_pytest_smoke() -> tuple[bool, str]:
    # Run a quick smoke (won't fail build here)
    if not shutil.which("pytest"):
        return True, "skipped"
    rc, out = run(
        ["pytest", "-q", "-k", "smoke or smoketest or sanity", "--maxfail=1"]
    )  # best-effort
    return rc == 0, out


def harvest_todos() -> list[str]:
    patterns = re.compile(r"\b(TODO|FIXME|BUG|HACK)\b[:\s](.*)")
    items = []
    for p in ROOT.rglob("*.py"):
        try:
            for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
                m = patterns.search(line)
                if m:
                    items.append(f"{p.relative_to(ROOT)}:{i} — {m.group(2).strip()}")
        except Exception:
            continue
    return items[:200]


@dataclass
class GitHubUnavailable(Exception):
    reason: str


def gh_request(method: str, path: str, json_body=None):
    import json as _json
    import urllib.request

    if not BASE_URL or not TOKEN:
        raise GitHubUnavailable("missing GitHub repository or token in environment")

    req = urllib.request.Request(BASE_URL + path, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    if json_body is not None:
        data = _json.dumps(json_body).encode()
        req.add_header("Content-Type", "application/json")
    else:
        data = None
    try:
        with urllib.request.urlopen(req, data=data) as r:
            return json.loads(r.read().decode())
    except Exception as exc:  # pragma: no cover - best effort network call
        raise GitHubUnavailable(str(exc)) from exc


def upsert_issue(title: str, body: str, labels: list[str]):
    # search existing open issues by title
    try:
        q = "/issues?state=open&per_page=100"
        issues = gh_request("GET", q)
        for it in issues:
            if it.get("title") == title:
                gh_request(
                    "PATCH", f"/issues/{it['number']}", {"body": body, "labels": labels}
                )
                return it["number"]
        # create new
        it = gh_request("POST", "/issues", {"title": title, "body": body, "labels": labels})
        return it["number"]
    except GitHubUnavailable as exc:
        print(f"[triage] Skipping issue sync: {exc.reason}", file=sys.stderr)
        return None


def make_health_report() -> tuple[str, dict]:
    checks = {}
    ok, out = check_import_swisseph()
    checks["pyswisseph_import"] = (ok, out)
    ephe_ok, ephe_msg = check_ephe_path()
    checks["ephemeris_path"] = (ephe_ok, ephe_msg)
    ok_r, out_r = check_ruff()
    checks["ruff"] = (ok_r, out_r)
    ok_m, out_m = check_mypy()
    checks["mypy"] = (ok_m, out_m)
    ok_t, out_t = check_pytest_smoke()
    checks["pytest_smoke"] = (ok_t, out_t)
    todos = harvest_todos()

    lines = [
        "# Automated Health Report",
        "\n**Legend:** ✅ pass · ⚠️ warn · ❌ fail\n",
    ]

    def row(name, ok, details):
        icon = "✅" if ok else "❌"
        if details == "skipped":
            icon = "⚠️"
            details = "skipped (not configured)"
        return f"- {icon} **{name}** — {details[:600]}"

    lines.append(row("pyswisseph import", *checks["pyswisseph_import"]))
    lines.append(row("Swiss ephemeris path", *checks["ephemeris_path"]))
    lines.append(row("ruff lint", *checks["ruff"]))
    lines.append(row("mypy typecheck", *checks["mypy"]))
    lines.append(row("pytest smoke", *checks["pytest_smoke"]))

    if todos:
        lines.append(f"\n### TODO/FIXME (top {len(todos)}):\n")
        for t in todos[:50]:
            lines.append(f"- [ ] {t}")

    body = "\n".join(lines)
    REPORT.write_text(body)
    return body, {k: v[0] for k, v in checks.items()}


def write_index_md(path: Path):
    # Simple index of open issues for easy web reference from chat
    md = [
        "# AstroEngine — Issue Index (auto‑generated)",
        "Open issues grouped by label. Source of truth is GitHub Issues.",
        "",
    ]

    try:
        items = gh_request("GET", "/issues?state=open&per_page=100")
    except GitHubUnavailable as exc:
        md.append(
            "_Issue data unavailable: GitHub API could not be reached (" + exc.reason + ")._"
        )
    else:
        by_label = {}
        for it in items:
            for lab in it.get("labels", []):
                name = lab["name"] if isinstance(lab, dict) else lab
                by_label.setdefault(name, []).append(it)

        def link(i):
            return f"- #{i['number']} {i['title']} (by @{i['user']['login']})"

        for label in sorted(by_label.keys()):
            md.append(f"\n## {label}")
            for it in sorted(by_label[label], key=lambda x: x["number"]):
                md.append(link(it))

        if len(md) == 3:
            md.append("_No open issues detected for the configured repository._")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(md) + "\n")


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--update-issues", action="store_true")
    ap.add_argument("--write-index", type=str, default="")
    args = ap.parse_args()

    body, flags = make_health_report()

    labels = ["meta", "automated"]
    if os.environ.get("CI") or args.update_issues:
        upsert_issue("Meta: Automated Health Report", body, labels)

    # targeted issues for hard failures
    if not flags.get("pyswisseph_import", True):
        fix = textwrap.dedent(
            """
            **Detected**: `pyswisseph` import failed.

            **Likely fixes:**
            - Ensure dev dep installed: `pip install pyswisseph` (add to requirements-dev.txt)
            - Download Swiss Ephemeris data files and set `SE_EPHE_PATH`
              (e.g. `./ephe` or `~/.sweph`)
            - Run `python scripts/swe_smoketest.py --utc 2025-01-01T00:00:00Z`
            """
        )
        upsert_issue(
            "Dependency: pyswisseph missing or failing",
            fix,
            ["bug", "ephemeris", "automated"],
        )

    if not flags.get("ephemeris_path", True):
        fix = "Set SE_EPHE_PATH or place ephemeris files under ./ephe or ~/.sweph."
        upsert_issue(
            "Config: Swiss Ephemeris data path not found",
            fix,
            ["bug", "ephemeris", "automated"],
        )

    if args.write_index:
        write_index_md(Path(args.write_index))


if __name__ == "__main__":
    main()
# >>> AUTO-GEN END: triage scanner v1.0
