"""Git helpers powering developer mode operations."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

BACKUP_DIR_ENV = "ASTROENGINE_BACKUPS"


class GitOps:
    """Wrapper around git commands used by developer mode."""

    def __init__(self, root: str = ".") -> None:
        self.root = Path(root)

    def _run(self, *args: str) -> tuple[int, str, str]:
        process = subprocess.Popen(
            args,
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def ensure_repo(self) -> None:
        """Initialise a git repository when the working tree lacks one."""

        if (self.root / ".git").exists():
            return
        self._run("git", "init")
        self._run("git", "add", "-A")
        self._run("git", "commit", "-m", "init")

    def new_branch(self, name: str) -> None:
        """Create or reset *name* as the staging branch for dev patches."""

        self._run("git", "checkout", "-B", name)

    def apply_diff(self, unified_diff: str) -> tuple[bool, str]:
        """Apply a unified diff and commit the result."""

        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(unified_diff)
            tmp_path = handle.name
        code, stdout, stderr = self._run(
            "git", "apply", "--whitespace=fix", "--index", tmp_path
        )
        os.unlink(tmp_path)
        if code != 0:
            return False, stderr or stdout
        self._run("git", "commit", "-m", "devmode: apply AI patch")
        _, commit, _ = self._run("git", "rev-parse", "HEAD")
        return True, commit.strip()

    def backup_zip(self) -> str:
        """Create a zip snapshot of the working tree prior to modification."""

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        override = os.environ.get(BACKUP_DIR_ENV)
        if override:
            backup_root = Path(override)
        elif os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
            backup_root = base / "AstroEngine" / "backups"
        else:
            backup_root = Path.home() / ".astroengine" / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        archive_path = backup_root / f"snapshot_{timestamp}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in self.root.rglob("*"):
                if ".git" in path.parts:
                    continue
                if path.is_file():
                    archive.write(path, path.relative_to(self.root))
        return str(archive_path)

    def restore_commit(self, commit: str) -> tuple[bool, str]:
        """Hard reset the working tree to *commit*."""

        code, stdout, stderr = self._run("git", "reset", "--hard", commit)
        return code == 0, stderr or stdout

    def current_commit(self) -> str:
        """Return the hash of the current HEAD commit."""

        _, stdout, _ = self._run("git", "rev-parse", "HEAD")
        return stdout.strip()
