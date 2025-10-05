from __future__ import annotations

import importlib
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _constraint_args() -> list[str]:
    """Return pip constraint arguments when ``constraints.txt`` is present."""

    env_constraint = os.environ.get("PIP_CONSTRAINT")
    if env_constraint:
        return ["--constraint", env_constraint]
    candidate = PROJECT_ROOT / "constraints.txt"
    if candidate.exists():
        return ["--constraint", str(candidate)]
    return []


def version_tuple(raw: str) -> Tuple[int, ...]:
    """Return a comparable tuple extracted from a version string."""

    parts: list[int] = []
    for segment in raw.split('.'):
        digits = ''.join(ch for ch in segment if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts)


def needs_install(dist_name: str, minimum: Tuple[int, ...]) -> bool:
    """Determine whether the distribution is missing or below the minimum version."""

    try:
        current = importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return True
    return version_tuple(current) < minimum


def ensure(
    spec: str,
    *,
    pip_args: Iterable[str] = (),
    import_name: str | None = None,
    minimum: Tuple[int, ...] | None = None,
    install: bool = True,
    quiet: bool = False,
) -> bool:
    """Ensure the requested dependency is importable.

    Parameters
    ----------
    spec:
        The pip requirement specifier used for installation (e.g. ``"fastapi>=0.117,<0.118"``).
    pip_args:
        Additional command-line arguments to forward to ``pip install``.
    import_name:
        Optional module name to import after installation.  Defaults to the
        distribution name inferred from ``spec``.
    minimum:
        Minimum acceptable version for the dependency.  ``(0,)`` by default.
    install:
        When ``True`` (the default), missing or out-of-date dependencies are
        installed automatically.  When ``False``, a ``ModuleNotFoundError`` is
        raised if the dependency is unavailable.
    quiet:
        When ``True``, suppress ``pip`` output during installation.

    Returns
    -------
    bool
        ``True`` if an installation occurred, ``False`` otherwise.
    """

    dist_segment = spec.split(';', 1)[0]
    for delimiter in ('==', '>=', '<=', '~=', '!='):
        dist_segment = dist_segment.split(delimiter)[0]
    dist_name = dist_segment.strip()
    target_import = (import_name or dist_name).strip()
    if minimum is None:
        minimum = version_tuple('0')

    if needs_install(dist_name, minimum):
        if not install:
            raise ModuleNotFoundError(
                f"Dependency '{dist_name}' is missing or below the required version"
            )
        cmd = [
            sys.executable,
            '-m',
            'pip',
            'install',
            *_constraint_args(),
            spec,
            *pip_args,
        ]
        kwargs = {}
        if quiet:
            kwargs['stdout'] = subprocess.DEVNULL
            kwargs['stderr'] = subprocess.DEVNULL
        subprocess.check_call(cmd, **kwargs)
        installed = True
    else:
        installed = False

    importlib.import_module(target_import)
    return installed


def install_requirements(path: Path, *, quiet: bool = False) -> bool:
    """Install a requirements file if it exists."""

    if not path.exists():
        return False
    cmd = [
        sys.executable,
        '-m',
        'pip',
        'install',
        *_constraint_args(),
        '-r',
        str(path),
    ]
    kwargs = {}
    if quiet:
        kwargs['stdout'] = subprocess.DEVNULL
        kwargs['stderr'] = subprocess.DEVNULL
    subprocess.check_call(cmd, **kwargs)
    return True
