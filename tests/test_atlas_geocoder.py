from __future__ import annotations

import time

import pytest

from astroengine.atlas.bundle_manager import AtlasBundleManager
from astroengine.atlas.geocoder import load_builtin_parser, normalize_token, transliterate, heatmap_hints


@pytest.fixture()
def parser():
    return load_builtin_parser()


def test_transliterate_cyrillic():
    assert transliterate("Москва") == "Moskva"
    assert normalize_token("Málaga") == "malaga"
    assert transliterate("Αθήνα") == "Αθήνα"  # Greek characters preserved without aggressive flag
    assert normalize_token("Αθήνα") == "athina"


def test_parser_multilingual_components(parser):
    components = parser.parse("221B Baker Street, London, Greater London, United Kingdom", language="en")
    assert components["city"].lower() == "london"
    assert components["country"].lower() == "united kingdom"
    assert "baker" in components.normalised_query().lower()

    spanish = parser.parse("Madrid, Comunidad de Madrid, España")
    assert spanish["city"].lower() == "madrid"

    russian = parser.parse("Россия, Москва, Москва, Арбат 12")
    assert "москва" in russian["city"].lower()


def test_heatmap_hints_latency():
    start = time.perf_counter()
    hints = heatmap_hints(51.5, -0.12)
    duration = time.perf_counter() - start
    assert len(hints) >= 5
    assert duration < 0.01


def test_tile_cache_prefetch_stats():
    manager = AtlasBundleManager(tile_capacity=4, ttl_seconds=5)
    cache = manager.tile_cache()
    tile_ids = [("atlas", 5, 16, 10), ("atlas", 5, 17, 11)]
    cache.prefetch(tile_ids, lambda tile: {"tile": tile})
    assert cache.stats.misses == 2
    cache.prefetch(tile_ids, lambda tile: {"tile": tile})
    assert cache.stats.hits >= 2
    assert cache.stats.hit_rate > 0.4
