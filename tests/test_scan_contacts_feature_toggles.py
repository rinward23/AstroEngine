from __future__ import annotations

import pytest

import astroengine.engine.scanning as scanning
from astroengine.detectors import CoarseHit
from astroengine.engine import scan_contacts


class _DummyScore:
    def __init__(self, value: float) -> None:
        self.score = float(value)


class _DummyPluginManager:
    def __init__(self) -> None:
        self.calls = 0
        self.contexts = []

    def run_detectors(self, context):
        self.calls += 1
        self.contexts.append(context)
        return []


@pytest.mark.parametrize(
    "decl_enabled, parallels_enabled, contras_enabled, expected_kinds",
    [
        (True, True, True, ["decl_parallel", "decl_contra"]),
        (True, True, False, ["decl_parallel"]),
        (True, False, True, ["decl_contra"]),
        (True, False, False, []),
        (False, True, True, []),
    ],
)
def test_scan_contacts_respects_declination_feature_flags(
    monkeypatch: pytest.MonkeyPatch,
    decl_enabled: bool,
    parallels_enabled: bool,
    contras_enabled: bool,
    expected_kinds: list[str],
) -> None:
    """Ensure declination feature toggles govern emitted event kinds."""

    base_hits = [
        CoarseHit(
            kind="decl_parallel",
            when_iso="2020-01-01T00:00:00Z",
            moving="sun",
            target="moon",
            lon_moving=100.0,
            lon_target=210.0,
            dec_moving=10.0,
            dec_target=11.0,
            delta=-1.0,
            applying_or_separating="applying",
            orb_allow=1.0,
        ),
        CoarseHit(
            kind="decl_contra",
            when_iso="2020-01-01T01:00:00Z",
            moving="sun",
            target="moon",
            lon_moving=120.0,
            lon_target=200.0,
            dec_moving=12.0,
            dec_target=-12.5,
            delta=0.5,
            applying_or_separating="separating",
            orb_allow=1.5,
        ),
    ]

    monkeypatch.setattr(
        scanning,
        "detect_decl_contacts",
        lambda *_args, **_kwargs: list(base_hits),
    )
    monkeypatch.setattr(
        scanning, "detect_antiscia_contacts", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(scanning, "detect_aspects", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        scanning, "compute_score", lambda *_args, **_kwargs: _DummyScore(0.0)
    )

    plugin_manager = _DummyPluginManager()
    monkeypatch.setattr(scanning, "get_plugin_manager", lambda: plugin_manager)

    profile = {
        "feature_flags": {
            "declination_aspects": {
                "enabled": decl_enabled,
                "parallels": parallels_enabled,
                "contraparallels": contras_enabled,
            }
        },
        "orb_policies": {
            "declination_aspect_orb_deg": {
                "parallel": {"default": 1.0},
                "contraparallel": {"default": 1.5},
            }
        },
    }

    events = scan_contacts(
        start_iso="2020-01-01T00:00:00Z",
        end_iso="2020-01-01T02:00:00Z",
        moving="sun",
        target="moon",
        provider_name="stub",
        provider=object(),
        step_minutes=60,
        include_declination=True,
        include_mirrors=False,
        include_aspects=False,
        profile=profile,
    )

    assert [event.kind for event in events] == expected_kinds
    assert plugin_manager.calls == 1

    context = plugin_manager.contexts[0]
    options = context.options
    feature_toggles = options["feature_toggles"]
    executed_features = options["executed_features"]

    expected_decl_toggle = bool(decl_enabled)
    expected_parallels_toggle = bool(decl_enabled and parallels_enabled)
    expected_contras_toggle = bool(decl_enabled and contras_enabled)
    expected_decl_executed = expected_decl_toggle and (
        expected_parallels_toggle or expected_contras_toggle
    )

    assert options["include_declination"] is expected_decl_executed
    assert feature_toggles["declination"] is expected_decl_toggle
    assert feature_toggles["declination_parallels"] is expected_parallels_toggle
    assert feature_toggles["declination_contras"] is expected_contras_toggle
    assert executed_features["declination"] is expected_decl_executed
    assert executed_features["declination_parallels"] is expected_parallels_toggle
    assert executed_features["declination_contras"] is expected_contras_toggle
    assert options["requested_features"]["declination"] is True
    assert options["declination_flags"]["enabled"] is decl_enabled
