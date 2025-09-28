"""Streamlit entrypoint for the Relationship Lab."""

from __future__ import annotations

import importlib
import pathlib
import sys


def _resolve_run():
    try:
        from streamlit.relationship_lab import run as streamlit_run
        return streamlit_run
    except ModuleNotFoundError:
        repo_root = pathlib.Path(__file__).resolve().parents[1]
        package_root = repo_root / "streamlit"
        for path in (str(repo_root), str(package_root)):
            if path not in sys.path:
                sys.path.insert(0, path)
        module = importlib.import_module("relationship_lab.app")
        sys.modules.setdefault("streamlit.relationship_lab", module)
        return module.run


run = _resolve_run()


if __name__ == "__main__":  # pragma: no cover - manual execution guard
    run()
