"""Smoke tests for the console-script entrypoint wiring."""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

import pytest

from astroengine import cli


def test_console_main_help(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ``console_main`` surfaces the parser help output."""

    monkeypatch.setattr(sys, "argv", ["astroengine", "--help"])
    buffer = io.StringIO()
    with redirect_stdout(buffer), pytest.raises(SystemExit) as exc:
        cli.console_main()
    assert exc.value.code == 0
    output = buffer.getvalue()
    assert "usage: astroengine" in output
