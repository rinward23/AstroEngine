from __future__ import annotations

import pytest

from astroengine.astro.declination import DEFAULT_ANTISCIA_AXIS
from astroengine.engine import _build_scan_profile_context


def _profile_payload() -> dict[str, object]:
    return {
        "orb_policies": {
            "declination_aspect_orb_deg": {
                "parallel": {"default": 1.0},
                "contraparallel": {"default": 1.5},
            },
            "antiscia_orb_deg": {
                "antiscia": {"default": 2.0},
                "contra_antiscia": {"default": 2.5},
            },
        },
        "feature_flags": {
            "declination_aspects": {
                "enabled": True,
                "parallels": False,
                "contraparallels": True,
            },
            "antiscia": {"enabled": False},
        },
        "tradition": {"default": "renaissance"},
        "natal": {"chart_sect": "diurnal"},
        "resonance": {
            "weights": {"mind": 2.0, "body": 1.0, "spirit": 3.0},
            "uncertainty_bias": {"sun": "favourable"},
        },
    }


def test_profile_context_defaults_and_feature_toggles() -> None:
    profile = _profile_payload()
    context = _build_scan_profile_context(
        profile,
        moving="sun",
        target="moon",
        decl_parallel_orb=None,
        decl_contra_orb=None,
        antiscia_orb=None,
        contra_antiscia_orb=None,
        antiscia_axis=None,
        tradition_profile=None,
        chart_sect=None,
    )

    toggles = context.feature_toggles(
        include_declination=True,
        include_mirrors=True,
        include_aspects=True,
    )

    plan = context.plan_features(
        include_declination=True,
        include_mirrors=True,
        include_aspects=True,
    )

    assert toggles.do_declination is True
    assert toggles.do_parallels is False  # parallels disabled in feature flags
    assert toggles.do_contras is True
    assert toggles.do_mirrors is False  # antiscia feature disabled
    assert toggles.do_aspects is True
    assert toggles.declination_executed is True
    assert toggles.parallels_executed is False
    assert toggles.contras_executed is True

    feature_map = toggles.feature_toggle_map()
    assert feature_map == {
        "declination": True,
        "declination_parallels": False,
        "declination_contras": True,
        "antiscia": False,
        "aspects": True,
    }

    executed_map = toggles.executed_feature_map()
    assert executed_map == {
        "declination": True,
        "declination_parallels": False,
        "declination_contras": True,
        "antiscia": False,
        "aspects": True,
    }

    assert plan.toggles == toggles
    assert dict(plan.feature_toggles) == feature_map
    assert dict(plan.executed_features) == executed_map
    assert plan.declination_executed is True
    assert plan.requested_features == {
        "declination": True,
        "mirrors": True,
        "aspects": True,
    }

    plugin_meta = plan.plugin_metadata()
    assert plugin_meta["feature_toggles"] == feature_map
    assert plugin_meta["executed_features"] == executed_map
    assert plugin_meta["requested_features"] == {
        "declination": True,
        "mirrors": True,
        "aspects": True,
    }
    assert plugin_meta["include_declination"] is True
    assert plugin_meta["include_mirrors"] is False
    assert plugin_meta["include_aspects"] is True

    # Axis falls back to default when profile does not override it
    assert context.antiscia_axis == DEFAULT_ANTISCIA_AXIS
    assert context.tradition == "renaissance"
    assert context.chart_sect == "diurnal"
    assert context.uncertainty_bias == {"sun": "favourable"}
    assert context.decl_parallel_orb == pytest.approx(1.0)
    assert context.decl_contra_orb == pytest.approx(1.5)
    assert context.antiscia_orb == pytest.approx(2.0)
    assert context.contra_antiscia_orb == pytest.approx(2.5)

    weights = context.resonance_weights
    assert weights["mind"] == pytest.approx(2.0 / 6.0)
    assert weights["body"] == pytest.approx(1.0 / 6.0)
    assert weights["spirit"] == pytest.approx(3.0 / 6.0)


def test_profile_context_respects_overrides() -> None:
    profile = _profile_payload()
    context = _build_scan_profile_context(
        profile,
        moving="sun",
        target="moon",
        decl_parallel_orb=0.25,
        decl_contra_orb=0.75,
        antiscia_orb=1.25,
        contra_antiscia_orb=1.75,
        antiscia_axis="aries-libra",
        tradition_profile="modern",
        chart_sect="nocturnal",
    )

    assert context.decl_parallel_orb == pytest.approx(0.25)
    assert context.decl_contra_orb == pytest.approx(0.75)
    assert context.antiscia_orb == pytest.approx(1.25)
    assert context.contra_antiscia_orb == pytest.approx(1.75)
    assert context.antiscia_axis == "aries-libra"
    assert context.tradition == "modern"
    assert context.chart_sect == "nocturnal"

    toggles = context.feature_toggles(
        include_declination=False,
        include_mirrors=False,
        include_aspects=False,
    )

    plan = context.plan_features(
        include_declination=False,
        include_mirrors=False,
        include_aspects=False,
    )
    assert toggles.do_declination is False
    assert toggles.do_parallels is False
    assert toggles.do_contras is False
    assert toggles.do_mirrors is False
    assert toggles.do_aspects is False
    assert toggles.declination_executed is False
    assert toggles.parallels_executed is False
    assert toggles.contras_executed is False

    assert toggles.feature_toggle_map() == {
        "declination": False,
        "declination_parallels": False,
        "declination_contras": False,
        "antiscia": False,
        "aspects": False,
    }
    assert toggles.executed_feature_map() == {
        "declination": False,
        "declination_parallels": False,
        "declination_contras": False,
        "antiscia": False,
        "aspects": False,
    }

    assert plan.toggles == toggles
    assert plan.declination_executed is False
    assert plan.requested_features == {
        "declination": False,
        "mirrors": False,
        "aspects": False,
    }

    plugin_meta = plan.plugin_metadata()
    assert plugin_meta["feature_toggles"] == {
        "declination": False,
        "declination_parallels": False,
        "declination_contras": False,
        "antiscia": False,
        "aspects": False,
    }
    assert plugin_meta["executed_features"] == {
        "declination": False,
        "declination_parallels": False,
        "declination_contras": False,
        "antiscia": False,
        "aspects": False,
    }
    assert plugin_meta["requested_features"] == {
        "declination": False,
        "mirrors": False,
        "aspects": False,
    }
    assert plugin_meta["include_declination"] is False
    assert plugin_meta["include_mirrors"] is False
    assert plugin_meta["include_aspects"] is False
