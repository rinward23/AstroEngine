"""Tests for the lightweight Git access helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from astroengine.infrastructure import GitAuth, GitRepository


def test_git_auth_builds_command(tmp_path: Path) -> None:
    key_path = tmp_path / "id_ed25519"
    key_path.write_text("dummy-key")
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("example.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA")

    auth = GitAuth(key_path=key_path, known_hosts_path=known_hosts)

    command = auth.build_ssh_command()

    assert "ssh" in command
    assert str(key_path) in command
    assert str(known_hosts) in command

    env = auth.apply({})
    assert env["GIT_SSH_COMMAND"] == command


@pytest.mark.parametrize("strict", [True, False])
def test_git_auth_strict_policy(strict: bool, tmp_path: Path) -> None:
    key_path = tmp_path / "id_ed25519"
    key_path.write_text("dummy-key")

    auth = GitAuth(key_path=key_path, strict_host_key_checking=strict)
    command = auth.build_ssh_command()

    assert (
        ("StrictHostKeyChecking=yes" in command)
        if strict
        else ("StrictHostKeyChecking=accept-new" in command)
    )


def test_git_repository_clone_commit_push(tmp_path: Path) -> None:
    remote_dir = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote_dir)], check=True)

    clone_dir = tmp_path / "clone"
    repo = GitRepository.clone(remote_dir, clone_dir)

    repo.run_git("config", "user.name", "AstroEngine Test")
    repo.run_git("config", "user.email", "test@example.com")

    repo.write_text("README.md", "hello from astroengine\n")
    repo.add("README.md")
    repo.commit("Add README")

    # Push to the bare remote and verify the contents by cloning again.
    repo.push()

    second_dir = tmp_path / "second"
    repo2 = GitRepository.clone(remote_dir, second_dir)

    assert repo2.read_text("README.md") == "hello from astroengine\n"
