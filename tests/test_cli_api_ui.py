"""Cross-cutting smoke tests for CLI, API, and UI doctor integrations."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI


def _env_for_cli(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    home = tmp_path / "astro-home"
    home.mkdir(parents=True, exist_ok=True)
    env["ASTROENGINE_HOME"] = str(home)
    db_path = tmp_path / "doctor.sqlite"
    env["DATABASE_URL"] = f"sqlite:///{db_path}"  # ensures SQLite file lives under tmpdir
    pythonpath = env.get("PYTHONPATH")
    cwd = os.getcwd()
    if pythonpath:
        env["PYTHONPATH"] = os.pathsep.join([cwd, pythonpath])
    else:
        env["PYTHONPATH"] = cwd
    return env


def test_cli_doctor_json(tmp_path: Path) -> None:
    """The ``astroengine`` CLI should expose the doctor diagnostics command."""

    env = _env_for_cli(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "astroengine.cli",
            "diagnose",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=os.getcwd(),
    )
    assert result.stdout, result.stderr
    payload = json.loads(result.stdout)
    summary = payload.get("summary")
    assert isinstance(summary, dict)
    assert "exit_code" in summary
    assert isinstance(payload.get("checks"), list)
    assert result.returncode == int(summary["exit_code"])


def test_api_module_imports() -> None:
    """Importing :mod:`astroengine.api` should provide the FastAPI application."""

    api_module = importlib.import_module("astroengine.api")
    assert isinstance(api_module, ModuleType)
    assert hasattr(api_module, "app")
    assert isinstance(api_module.app, FastAPI)
    assert api_module.get_app() is api_module.app


def test_streamlit_doctor_import() -> None:
    """The Streamlit doctor module should be importable for UI integrations."""

    doctor_module = importlib.import_module("ui.streamlit.doctor")
    assert hasattr(doctor_module, "render_report")
    assert callable(doctor_module.render_report)
