import importlib

packages = [
    "astroengine.core.aspects_plus",
    "astroengine.core.aspects_plus.search",
    "astroengine.core.charts_plus",
    "astroengine.core.charts_plus.returns",
    "astroengine.core.charts_plus.progressions",
    "astroengine.core.charts_plus.composite",
    "astroengine.core.events_plus",
    "astroengine.core.events_plus.voc_moon",
    "astroengine.core.events_plus.solar_phases",
    "astroengine.core.events_plus.next_event",
    "astroengine.core.asteroids_plus",
    "astroengine.core.asteroids_plus.catalog",
    "astroengine.core.asteroids_plus.mpc_import",
    "astroengine.core.export_plus",
    "astroengine.core.export_plus.ics",
    "astroengine.core.export_plus.reports",
    "astroengine.core.scan_plus",
    "astroengine.core.scan_plus.windows",
    "astroengine.core.scan_plus.ranking",
]


def test_plus_imports():
    for pkg in packages:
        assert importlib.import_module(pkg)
