from __future__ import annotations

import pytest

from astroengine.plugins.registry import AspectRegistry, LotRegistry


def test_aspect_registry_register_apply_and_disable() -> None:
    from astroengine.core.aspects_plus import harmonics

    original = dict(harmonics.BASE_ASPECTS)
    registry = AspectRegistry()
    try:
        spec = registry.register(
            "Septile",
            51.428,
            origin="tests.example",
            path=None,
            replace=False,
        )
        registry.apply({})
        assert pytest.approx(harmonics.BASE_ASPECTS[spec.runtime_name], rel=1e-6) == 51.428

        registry.apply({spec.key: False})
        assert spec.runtime_name not in harmonics.BASE_ASPECTS
    finally:
        harmonics.BASE_ASPECTS.clear()
        harmonics.BASE_ASPECTS.update(original)


def test_aspect_registry_replace_restores_original() -> None:
    from astroengine.core.aspects_plus import harmonics

    original = dict(harmonics.BASE_ASPECTS)
    registry = AspectRegistry()
    try:
        spec = registry.register(
            "square",
            95.0,
            origin="tests.override",
            path=None,
            replace=True,
        )
        registry.apply({})
        assert pytest.approx(harmonics.BASE_ASPECTS[spec.runtime_name], rel=1e-6) == 95.0

        registry.apply({spec.key: False})
        assert pytest.approx(harmonics.BASE_ASPECTS[spec.runtime_name], rel=1e-6) == original[
            spec.runtime_name
        ]
    finally:
        harmonics.BASE_ASPECTS.clear()
        harmonics.BASE_ASPECTS.update(original)


def test_lot_registry_register_apply_and_disable() -> None:
    from core.lots_plus import catalog

    original = dict(catalog.REGISTRY)
    registry = LotRegistry()
    try:
        spec = registry.register(
            "LotOfCuriosity",
            "Asc + Mercury - Jupiter",
            "Asc + Jupiter - Mercury",
            origin="tests.lots",
            path=None,
            replace=False,
        )
        registry.apply({})
        assert spec.name in catalog.REGISTRY
        assert catalog.REGISTRY[spec.name].day == "Asc + Mercury - Jupiter"

        registry.apply({spec.key: False})
        assert spec.name not in catalog.REGISTRY
    finally:
        catalog.REGISTRY.clear()
        catalog.REGISTRY.update(original)
