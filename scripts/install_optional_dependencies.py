#!/usr/bin/env python3
"""Install and validate AstroEngine optional dependency stacks."""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_OPTIONAL = PROJECT_ROOT / "requirements-optional.txt"


def _version_tuple(raw: str) -> Tuple[int, ...]:
    parts: list[int] = []
    for segment in raw.split('.'):
        digits = ''.join(ch for ch in segment if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts)


def _needs_install(dist_name: str, minimum: Tuple[int, ...]) -> bool:
    try:
        current = importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return True
    return _version_tuple(current) < minimum


def _ensure(
    spec: str,
    *,
    pip_args: Iterable[str] = (),
    import_name: str | None = None,
    minimum: Tuple[int, ...] | None = None,
) -> None:
    target_dist = (import_name or spec.split('==')[0].split('>=')[0]).strip()
    if minimum is None:
        minimum = _version_tuple('0')
    if _needs_install(target_dist, minimum):
        cmd = [sys.executable, '-m', 'pip', 'install', spec, *pip_args]
        subprocess.check_call(cmd)
    importlib.import_module(import_name or target_dist)


def install_optional_dependencies() -> None:
    """Install optional stacks and validate that critical imports succeed."""

    # Ensure pyswisseph is present before handling flatlib.
    _ensure('pyswisseph==2.10.3.2', import_name='swisseph', minimum=(2, 10, 3, 2))
    # Install flatlib without its upstream dependency pin so pyswisseph 2.10.x stays active.
    _ensure('flatlib==0.2.3', pip_args=('--no-deps',), import_name='flatlib', minimum=(0, 2, 3))

    if REQUIREMENTS_OPTIONAL.exists():
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-r', str(REQUIREMENTS_OPTIONAL)]
        )

    # Validate a subset of optional libraries commonly exercised in tests.
    for spec, import_name, minimum in (
        ('pymeeus>=0.5.12', 'pymeeus', (0, 5, 12)),
        ('PyYAML>=6.0', 'yaml', (6, 0, 0)),
        ('pydantic>=2.11', 'pydantic', (2, 11)),
        ('skyfield>=1.49', 'skyfield', (1, 49)),
        ('jplephem>=2.21', 'jplephem', (2, 21)),
    ):
        _ensure(spec, import_name=import_name, minimum=minimum)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--upgrade-pip',
        action='store_true',
        help='Upgrade pip before installing optional dependencies.',
    )
    args = parser.parse_args()

    if args.upgrade_pip:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

    install_optional_dependencies()


if __name__ == '__main__':
    main()
