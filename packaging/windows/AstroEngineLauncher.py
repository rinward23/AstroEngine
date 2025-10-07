"""Frozen-entry launcher for the Windows desktop shell.

This thin wrapper exists so the PyInstaller bundle can resolve the
desktop experience defined in :mod:`app.desktop.launch_desktop`.  It
does not perform any orchestration itself—the heavy lifting lives in
the shared desktop module which keeps the FastAPI service, embedded
Streamlit portal, pywebview shell, and tray automation consistent with
the rest of the codebase.
"""

from __future__ import annotations

import runpy
from importlib import import_module


def _bootstrap() -> None:
    """Execute the packaged desktop launcher.

    We delegate to :func:`app.desktop.launch_desktop.main` so the same
    code path is exercised whether developers run ``python -m`` during
    development or the PyInstaller-built executable on Windows 11.
    ``runpy`` is used as a fallback for environments where the module
    import succeeds but ``main`` is not directly exposed (for example if
    packaging adjustments stub it out in the future).  This keeps the
    frozen entry point resilient without duplicating logic here.
    """

    try:
        module = import_module("app.desktop.launch_desktop")
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Unable to import AstroEngine desktop launcher") from exc

    main = getattr(module, "main", None)
    if callable(main):
        main()
        return

    # Fallback to executing the module as a script if ``main`` vanished
    runpy.run_module("app.desktop.launch_desktop", run_name="__main__")


def main() -> None:
    _bootstrap()


if __name__ == "__main__":
    main()
