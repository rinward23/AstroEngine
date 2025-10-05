"""Launch the AstroEngine desktop shell."""

from __future__ import annotations

from astroengine.ux.desktop import AstroEngineDesktopApp, DesktopConfigManager


def main() -> None:
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
