# >>> AUTO-GEN BEGIN: repo cleanup v1.0
#!/usr/bin/env python
"""
Lightweight cleanup:
- remove *.pyc/__pycache__
- normalize newline at EOF for .py/.md/.yml/.yaml/.toml/.txt
- run ruff --fix (if available)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rm_pycache():
    for p in ROOT.rglob("__pycache__"):
        for f in p.iterdir():
            try:
                f.unlink()
            except Exception:
                pass
        try:
            p.rmdir()
        except Exception:
            pass


def normalize_eof():
    exts = {".py", ".md", ".yml", ".yaml", ".toml", ".txt"}
    for p in ROOT.rglob("*"):
        if p.suffix in exts and p.is_file():
            t = p.read_text(encoding="utf-8", errors="ignore")
            if not t.endswith("\n"):
                p.write_text(t + "\n", encoding="utf-8")


def ruff_fix():
    try:
        subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--fix", str(ROOT)], check=False
        )
    except Exception:
        pass


def main():
    rm_pycache()
    normalize_eof()
    ruff_fix()
    print("Cleanup complete.")


if __name__ == "__main__":
    main()
# >>> AUTO-GEN END: repo cleanup v1.0
