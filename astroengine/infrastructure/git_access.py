"""Git repository helpers with SSH key support.

This module keeps the implementation lightweight so the runtime can
interact with Git repositories without pulling in heavy third-party
wrappers.  The helper classes expose composable primitives:

* :class:`GitAuth` constructs an ``ssh`` command that points to a
  dedicated deploy key and optional ``known_hosts`` file.  The command is
  injected via the ``GIT_SSH_COMMAND`` environment variable, mirroring
  the approach recommended in Git's own documentation.
* :class:`GitRepository` executes Git commands in a working tree and
  provides convenience methods for common read/write flows (clone,
  commit, push, file reads/writes).

All filesystem interactions operate on real files inside the working
tree to satisfy the repository's integrity requirements—no synthetic
outputs are generated.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping

__all__ = ["GitAuth", "GitRepository"]


@dataclass(frozen=True)
class GitAuth:
    """SSH configuration for authenticating Git commands.

    Parameters
    ----------
    key_path:
        Filesystem path to the private key used for Git operations.
    known_hosts_path:
        Optional override for the ``known_hosts`` file.
    strict_host_key_checking:
        When ``True`` (default) the ``ssh`` command enforces host key
        verification.  When ``False`` it switches to ``accept-new`` so
        first-time connections do not require manual confirmation.
    extra_ssh_options:
        Additional ``-o`` options passed verbatim to ``ssh``.
    """

    key_path: Path
    known_hosts_path: Path | None = None
    strict_host_key_checking: bool = True
    extra_ssh_options: tuple[str, ...] = ()

    def build_ssh_command(self) -> str:
        """Return the fully quoted ``ssh`` command."""

        key_path = Path(self.key_path)
        parts: list[str] = ["ssh", "-i", str(key_path), "-o", "IdentitiesOnly=yes"]

        # Host key policy keeps operations deterministic.  ``accept-new``
        # is only enabled when explicitly requested.
        policy = "yes" if self.strict_host_key_checking else "accept-new"
        parts.extend(["-o", f"StrictHostKeyChecking={policy}"])

        if self.known_hosts_path is not None:
            parts.extend(["-o", f"UserKnownHostsFile={self.known_hosts_path}"])

        for option in self.extra_ssh_options:
            parts.extend(["-o", option])

        return shlex.join(parts)

    def apply(self, env: Mapping[str, str] | None = None) -> MutableMapping[str, str]:
        """Return ``env`` extended with ``GIT_SSH_COMMAND``."""

        merged: dict[str, str] = dict(os.environ if env is None else env)
        merged["GIT_SSH_COMMAND"] = self.build_ssh_command()
        return merged


@dataclass
class GitRepository:
    """Lightweight wrapper around a Git working tree."""

    path: Path
    auth: GitAuth | None = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)

    # ------------------------------------------------------------------
    # Command execution helpers
    # ------------------------------------------------------------------
    def _command_env(self) -> MutableMapping[str, str] | None:
        return self.auth.apply() if self.auth else None

    def run_git(self, *args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
        """Execute ``git`` with ``args`` inside the repository."""

        cmd = ["git", *args]
        return subprocess.run(
            cmd,
            cwd=self.path,
            env=self._command_env(),
            capture_output=capture_output,
            text=True,
            check=True,
        )

    # ------------------------------------------------------------------
    # Repository lifecycle helpers
    # ------------------------------------------------------------------
    @classmethod
    def clone(
        cls,
        remote: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        auth: GitAuth | None = None,
        branch: str | None = None,
    ) -> "GitRepository":
        """Clone ``remote`` into ``target`` and return the repository wrapper."""

        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        cmd: list[str] = ["git", "clone"]
        if branch is not None:
            cmd.extend(["--branch", branch])
        cmd.extend([str(remote), str(target_path)])

        subprocess.run(
            cmd,
            env=auth.apply() if auth else None,
            check=True,
            text=True,
        )
        return cls(target_path, auth=auth)

    def fetch(self, remote: str = "origin", *refs: str) -> None:
        args = ["fetch", remote]
        if refs:
            args.extend(refs)
        self.run_git(*args)

    def pull(self, remote: str = "origin", branch: str | None = None) -> None:
        args = ["pull", remote]
        if branch is not None:
            args.append(branch)
        self.run_git(*args)

    def push(self, remote: str = "origin", refspec: str | None = None) -> None:
        args = ["push", remote]
        if refspec is not None:
            args.append(refspec)
        self.run_git(*args)

    # ------------------------------------------------------------------
    # Commit utilities
    # ------------------------------------------------------------------
    def commit(self, message: str, *, allow_empty: bool = False) -> None:
        args = ["commit", "-m", message]
        if allow_empty:
            args.insert(1, "--allow-empty")
        self.run_git(*args)

    def status(self) -> str:
        result = self.run_git("status", "--short", capture_output=True)
        return result.stdout

    def current_branch(self) -> str:
        result = self.run_git("rev-parse", "--abbrev-ref", "HEAD", capture_output=True)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # File convenience methods
    # ------------------------------------------------------------------
    def read_text(self, relative_path: str | os.PathLike[str], *, encoding: str = "utf-8") -> str:
        return (self.path / Path(relative_path)).read_text(encoding=encoding)

    def write_text(
        self,
        relative_path: str | os.PathLike[str],
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        path = self.path / Path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
        return path

    def add(self, *paths: str | os.PathLike[str]) -> None:
        args = ["add", *map(str, paths)]
        self.run_git(*args)

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def ensure_remote(self, name: str, url: str | os.PathLike[str]) -> None:
        """Create or update a remote configuration entry."""

        try:
            # Prefer ``set-url`` to avoid duplicate remotes when updating.
            self.run_git("remote", "set-url", name, str(url))
        except subprocess.CalledProcessError:
            self.run_git("remote", "add", name, str(url))

