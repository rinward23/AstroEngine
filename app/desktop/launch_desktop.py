"""Launch the AstroEngine desktop shell."""

from __future__ import annotations

from astroengine.ux.desktop import (
    AstroEngineDesktopApp,
    DesktopConfigManager,
    run_first_run_wizard,
    should_run_wizard,
)


def main() -> None:
    if should_run_wizard():
        try:
            run_first_run_wizard()
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"First-run wizard encountered an error: {exc}")
    manager = DesktopConfigManager()
    config = manager.load()
    if not manager.config_path.exists():
        manager.save(config)
    app = AstroEngineDesktopApp(config_manager=manager)
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == "__main__":
    main()
