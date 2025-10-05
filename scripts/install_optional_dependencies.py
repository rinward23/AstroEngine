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
        installed = install_requirements(REQUIREMENTS_OPTIONAL)
        if not installed:
            raise FileNotFoundError(
                f"Optional requirements file missing: {REQUIREMENTS_OPTIONAL}"
            )

    # Validate the optional stacks by ensuring each library imports successfully.
    for spec, import_name, minimum in (
        ('pymeeus>=0.5.12', 'pymeeus', (0, 5, 12)),
        ('PyYAML>=6.0', 'yaml', (6, 0, 0)),
        ('pydantic>=2.11', 'pydantic', (2, 11)),
        ('skyfield>=1.49', 'skyfield', (1, 49)),
        ('jplephem>=2.21', 'jplephem', (2, 21)),
        ('astroquery>=0.4', 'astroquery', (0, 4, 0)),
        ('pyarrow>=16', 'pyarrow', (16, 0, 0)),
        ('ics>=0.7', 'ics', (0, 7, 0)),
        ('jinja2>=3.1', 'jinja2', (3, 1, 0)),
        ('numba>=0.58', 'numba', (0, 58, 0)),
        ('click>=8.1', 'click', (8, 1, 0)),
        ('rich>=13.7', 'rich', (13, 7, 0)),
        ('pluggy>=1.5', 'pluggy', (1, 5, 0)),
        ('pypdf>=4.2', 'pypdf', (4, 2, 0)),
        ('weasyprint>=62', 'weasyprint', (62, 0, 0)),
        ('python-docx>=1.1', 'docx', (1, 1, 0)),
        ('playwright>=1.45', 'playwright', (1, 45, 0)),
        ('pypandoc>=1.12', 'pypandoc', (1, 12, 0)),
        ('markdown-it-py>=4.0', 'markdown_it', (4, 0, 0)),
        ('mdit-py-plugins>=0.5', 'mdit_py_plugins', (0, 5, 0)),
        ('streamlit>=1.35', 'streamlit', (1, 35, 0)),
        ('plotly>=5.20', 'plotly', (5, 20, 0)),
        ('fastapi>=0.117,<0.118', 'fastapi', (0, 117, 0)),
        ('uvicorn>=0.37,<0.38', 'uvicorn', (0, 37, 0)),
        ('icalendar>=6', 'icalendar', (6, 0, 0)),
        ('httpx>=0.28,<0.29', 'httpx', (0, 28, 0)),
        ('timezonefinder>=8.1', 'timezonefinder', (8, 1, 0)),
        ('tzdata>=2024.1', 'tzdata', (2024, 1)),
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
