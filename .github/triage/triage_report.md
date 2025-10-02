# Automated Health Report

**Legend:** ✅ pass · ⚠️ warn · ❌ fail

- ✅ **pyswisseph import** — 20230604
- ❌ **Swiss ephemeris path** — candidates=['/workspace/AstroEngine/ephe', '/root/.sweph']
- ❌ **ruff lint** — warning: The top-level linter settings are deprecated in favour of their counterparts in the `lint` section. Please update the following options in `pyproject.toml`:
  - 'select' -> 'lint.select'
I001 [*] Import block is un-sorted or un-formatted
 --> app/db/__init__.py:4:1
  |
2 |   """Database primitives for AstroEngine Plus models."""
3 |
4 | / from __future__ import annotations
5 | |
6 | | from .base import Base
7 | | from . import models as models
  | |______________________________^
8 |
9 |   __all__ = ["Base", "models"]
  |
help: Organize imports

I001 [*] Import block is un-sorted or u
- ⚠️ **mypy typecheck** — skipped (not configured)
- ✅ **pytest smoke** — s......                                                                                                                  [100%]
======================================================= warnings summary =======================================================
tests/conftest.py:27
  /workspace/AstroEngine/tests/conftest.py:27: DeprecationWarning: Tests importing 'generated' are deprecated; using 'astroengine' instead.
    warnings.warn(

../../root/.pyenv/versions/3.11.12/lib/python3.11/site-packages/pydantic/_internal/_config.py:323
  /root/.pyenv/versions/3.11.12/lib/python3.11/site-packages/pyd

### TODO/FIXME (top 1):

- [ ] .github/triage/scan_repo.py:179 — (top {len(todos)}):\n")
