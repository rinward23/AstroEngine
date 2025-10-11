"""Smoke tests exercising CLI entrypoints inside the Docker image."""

from __future__ import annotations
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.fixture(scope="session")
def docker_image():
    if not _docker_available():
        pytest.skip("docker is required for container integration tests")
    tag = f"astroengine-cli-test:{uuid.uuid4().hex[:8]}"
    build = subprocess.run(
        ["docker", "build", "--progress=plain", "-t", tag, "."],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        pytest.fail(f"docker build failed with exit code {build.returncode}\n{build.stdout}")
    try:
        yield tag
    finally:
        subprocess.run(
            ["docker", "rmi", "-f", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )


@pytest.mark.smoke
def test_transits_scan_help_runs_in_container(docker_image: str) -> None:
    proc = subprocess.run(
        ["docker", "run", "--rm", docker_image, "transits", "scan", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(f"transits scan --help failed\n{proc.stdout}")
    assert "Scan transits/events over a time range" in proc.stdout


@pytest.mark.smoke
def test_ephem_pull_copies_local_source_in_container(docker_image: str) -> None:
    script = (
        "set -euo pipefail; "
        "mkdir -p /tmp/source; "
        "printf 'kernel' >/tmp/source/de440s.bsp; "
        "astroengine ephe pull --set de440s --source /tmp/source --target /tmp/dest --force --skip-verify; "
        "test -f /tmp/dest/de440s.bsp"
    )
    proc = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "/bin/bash", docker_image, "-lc", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(f"ephem pull smoke failed\n{proc.stdout}")
    assert "Downloaded" in proc.stdout
    assert "Manifest written to" in proc.stdout
