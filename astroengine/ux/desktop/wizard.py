"""Interactive first-run wizard for configuring AstroEngine settings."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from astroengine.config import (
    Settings,
    apply_profile_overlay,
    built_in_profiles,
    config_path,
    default_settings,
    load_settings,
    save_settings,
)

PromptFn = Callable[[str], str]
PrintFn = Callable[[str], None]


def should_run_wizard(*, settings_file: Path | None = None) -> bool:
    """Return ``True`` when the wizard should prompt for settings."""

    target = settings_file or config_path()
    if target.exists():
        return bool(os.getenv("ASTROENGINE_FORCE_WIZARD"))
    if os.getenv("ASTROENGINE_SKIP_WIZARD"):
        return False
    return sys.stdin.isatty() or bool(os.getenv("ASTROENGINE_FORCE_WIZARD"))


def run_first_run_wizard(
    *,
    settings_path: Path | None = None,
    input_func: PromptFn = input,
    print_func: PrintFn = print,
) -> Settings:
    """Prompt for the minimal configuration required to run AstroEngine."""

    settings_path = settings_path or config_path()
    print_func("\n🌟 Welcome to AstroEngine! Let's capture a few essentials.")

    ephemeris_path = _prompt_path(
        "Swiss Ephemeris directory (leave blank to skip)",
        allow_blank=True,
        require_directory=True,
        input_func=input_func,
        print_func=print_func,
    )

    enable_offline = _prompt_boolean(
        "Enable the offline atlas dataset? [y/N]",
        default=False,
        input_func=input_func,
        print_func=print_func,
    )

    atlas_path: str | None = None
    if enable_offline:
        atlas_path = _prompt_path(
            "Offline atlas SQLite path",
            allow_blank=False,
            require_directory=False,
            input_func=input_func,
            print_func=print_func,
        )

    profile_name = _prompt_profile(input_func=input_func, print_func=print_func)

    base_settings = default_settings()
    overlay = built_in_profiles().get(profile_name)
    if overlay:
        base_settings = apply_profile_overlay(base_settings, overlay)

    base_settings.ephemeris.path = ephemeris_path or None
    base_settings.atlas.offline_enabled = enable_offline
    base_settings.atlas.data_path = atlas_path
    base_settings.preset = profile_name

    save_settings(base_settings, settings_path)
    _stamp_metadata(settings_path)
    print_func(
        "✅ Configuration saved to {path}".format(path=settings_path)
    )
    return load_settings(settings_path)


def _prompt_path(
    prompt: str,
    *,
    allow_blank: bool,
    require_directory: bool,
    input_func: PromptFn,
    print_func: PrintFn,
) -> str:
    while True:
        response = input_func(f"{prompt}: ").strip()
        if not response and allow_blank:
            return ""
        candidate = Path(response).expanduser()
        exists = candidate.exists()
        if exists and require_directory and not candidate.is_dir():
            print_func("Please provide a directory path.")
            continue
        if exists and not require_directory and not candidate.is_file():
            print_func("Please provide a file path to the atlas database.")
            continue
        if not exists:
            print_func("Path not found. Please try again.")
            continue
        return str(candidate)


def _prompt_boolean(
    prompt: str,
    *,
    default: bool,
    input_func: PromptFn,
    print_func: PrintFn,
) -> bool:
    default_label = "Y/n" if default else "y/N"
    while True:
        response = input_func(f"{prompt} ({default_label}): ").strip().lower()
        if not response:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print_func("Please respond with 'y' or 'n'.")


def _prompt_profile(
    *, input_func: PromptFn, print_func: PrintFn
) -> str:
    available = list(built_in_profiles().keys())
    default = "modern_western" if "modern_western" in available else available[0]
    print_func(
        "Select a default profile (press Enter for {default}).".format(
            default=default
        )
    )
    for name in available:
        print_func(f" • {name}")
    while True:
        choice = input_func("Profile: ").strip() or default
        if choice in available:
            return choice
        print_func("Unknown profile. Please choose one from the list above.")


def _stamp_metadata(settings_path: Path) -> None:
    """Record a creation timestamp for transparency."""

    meta_path = settings_path.with_suffix(".first_run.json")
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings_path": str(settings_path),
    }
    try:
        import json

        meta_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except Exception:  # pragma: no cover - metadata best effort
        return


__all__ = ["run_first_run_wizard", "should_run_wizard"]

