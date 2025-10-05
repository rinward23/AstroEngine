#!/usr/bin/env python3
"""Install and validate AstroEngine optional dependency stacks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from dependency_utils import ensure, install_requirements, PROJECT_ROOT

REQUIREMENTS_OPTIONAL = PROJECT_ROOT / "requirements-optional.txt"


def install_optional_dependencies() -> None:
    """Install optional stacks and validate that critical imports succeed."""

    # Ensure pyswisseph is present before handling flatlib.
    ensure('pyswisseph==2.10.3.2', import_name='swisseph', minimum=(2, 10, 3, 2))
    # Install flatlib without its upstream dependency pin so pyswisseph 2.10.x stays active.
    ensure(
        'flatlib==0.2.3',
        pip_args=('--no-deps',),
        import_name='flatlib',
        minimum=(0, 2, 3),
    )

    if REQUIREMENTS_OPTIONAL.exists():
        install_requirements(REQUIREMENTS_OPTIONAL)

    # Validate a subset of optional libraries commonly exercised in tests.
    for spec, import_name, minimum in (
        ('pymeeus>=0.5.12', 'pymeeus', (0, 5, 12)),
        ('PyYAML>=6.0', 'yaml', (6, 0, 0)),
        ('pydantic>=2.11', 'pydantic', (2, 11)),
        ('skyfield>=1.49', 'skyfield', (1, 49)),
        ('jplephem>=2.21', 'jplephem', (2, 21)),
        ('mdit-py-plugins>=0.4', 'mdit_py_plugins', (0, 4)),
    ):
        ensure(spec, import_name=import_name, minimum=minimum)


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
