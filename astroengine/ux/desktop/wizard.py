"""Interactive first-run wizard for configuring AstroEngine settings."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from astroengine.config import (
    Settings,
    apply_profile_overlay,
    built_in_profiles,
    config_path,
    default_settings,
    load_settings,
    save_settings,
)
from astroengine.runtime_config import runtime_settings

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
        validator=_validate_swiss_ephemeris,
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
            validator=_validate_sqlite,
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

    swiss_meta: dict[str, object] | None = None
    if ephemeris_path:
        swiss_meta = _summarise_swiss(Path(ephemeris_path))

    atlas_meta: dict[str, object] | None = None
    if atlas_path:
        atlas_meta = _summarise_sqlite(Path(atlas_path))

    save_settings(base_settings, settings_path)
    metadata = _build_metadata(
        settings_path=settings_path,
        ephemeris_path=ephemeris_path,
        swiss_meta=swiss_meta,
        atlas_enabled=enable_offline,
        atlas_path=atlas_path,
        atlas_meta=atlas_meta,
        profile_name=profile_name,
    )
    _stamp_metadata(settings_path, metadata)
    _print_summary(
        print_func=print_func,
        settings_path=settings_path,
        ephemeris_path=ephemeris_path,
        swiss_meta=swiss_meta,
        atlas_enabled=enable_offline,
        atlas_path=atlas_path,
        atlas_meta=atlas_meta,
        profile_name=profile_name,
    )
    final_settings = load_settings(settings_path)
    runtime_settings.cache_persisted(final_settings)
    return final_settings


def _prompt_path(
    prompt: str,
    *,
    allow_blank: bool,
    require_directory: bool,
    input_func: PromptFn,
    print_func: PrintFn,
    validator: Callable[[Path], None] | None = None,
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
        if validator:
            try:
                validator(candidate)
            except ValueError as exc:
                print_func(str(exc))
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                print_func(f"Validation failed: {exc}")
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
        f"Select a default profile (press Enter for {default})."
    )
    for name in available:
        print_func(f" • {name}")
    while True:
        choice = input_func("Profile: ").strip() or default
        if choice in available:
            return choice
        print_func("Unknown profile. Please choose one from the list above.")


def _validate_swiss_ephemeris(path: Path) -> None:
    """Ensure ``path`` contains Swiss ephemeris data files."""

    if not any(path.glob("*.se*")):
        raise ValueError(
            "Swiss ephemeris directory must include *.se* data files for high-precision runs."
        )


def _validate_sqlite(path: Path) -> None:
    """Ensure ``path`` refers to a readable SQLite database."""

    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            conn.execute("PRAGMA schema_version;")
    except sqlite3.DatabaseError as exc:
        raise ValueError("Offline atlas path must be a readable SQLite database.") from exc


def _summarise_swiss(path: Path) -> dict[str, object]:
    files = [f for f in path.glob("*.se*") if f.is_file()]
    examples = [f.name for f in files[:5]]
    return {"count": len(files), "examples": examples}


def _summarise_sqlite(path: Path) -> dict[str, object]:
    uri = f"file:{path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    examples = [row[0] for row in rows[:5]]
    return {"tables": len(rows), "examples": examples}


def _build_metadata(
    *,
    settings_path: Path,
    ephemeris_path: str,
    swiss_meta: dict[str, object] | None,
    atlas_enabled: bool,
    atlas_path: str | None,
    atlas_meta: dict[str, object] | None,
    profile_name: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "created_at": datetime.now(UTC).isoformat(),
        "settings_path": str(settings_path),
        "profile": profile_name,
        "ephemeris": {
            "path": ephemeris_path or None,
            "files": (swiss_meta or {}).get("count", 0),
            "examples": (swiss_meta or {}).get("examples", []),
        },
        "atlas": {
            "enabled": atlas_enabled,
            "path": atlas_path,
            "tables": (atlas_meta or {}).get("tables", 0),
            "examples": (atlas_meta or {}).get("examples", []),
        },
        "post_setup": "python -m astroengine.maint --full --strict",
    }
    return payload


def _print_summary(
    *,
    print_func: PrintFn,
    settings_path: Path,
    ephemeris_path: str,
    swiss_meta: dict[str, object] | None,
    atlas_enabled: bool,
    atlas_path: str | None,
    atlas_meta: dict[str, object] | None,
    profile_name: str,
) -> None:
    print_func("")
    print_func(f"✅ Configuration saved to {settings_path}")
    print_func("Summary of detected data sources:")

    if ephemeris_path:
        count = int((swiss_meta or {}).get("count", 0))
        label = f"{ephemeris_path} ({count} Swiss ephemeris file(s))"
        print_func(f" • Swiss Ephemeris: {label}")
        examples = (swiss_meta or {}).get("examples") or []
        if examples:
            print_func(f"   sample files: {', '.join(examples)}")
    else:
        print_func(
            " • Swiss Ephemeris: not provided — Swiss-backed precision will remain disabled."
        )

    if atlas_enabled and atlas_path:
        tables = int((atlas_meta or {}).get("tables", 0))
        label = f"{atlas_path} ({tables} table(s))"
        print_func(f" • Offline Atlas: {label}")
        examples = (atlas_meta or {}).get("examples") or []
        if examples:
            print_func(f"   sample tables: {', '.join(examples)}")
    else:
        print_func(" • Offline Atlas: disabled — API calls will stream live atlas data.")

    print_func(f" • Profile preset: {profile_name}")
    print_func(
        "Next step: run `python -m astroengine.maint --full --strict` to verify the installation."
    )


def _stamp_metadata(settings_path: Path, metadata: dict[str, object]) -> None:
    """Record metadata describing the first-run configuration."""

    meta_path = settings_path.with_suffix(".first_run.json")
    try:
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    except Exception:  # pragma: no cover - metadata best effort
        return


__all__ = ["run_first_run_wizard", "should_run_wizard"]

