from astroengine.engine import scanning
from astroengine.engine.scanning import _attach_timelords
from astroengine.exporters import LegacyTransitEvent


class _FakePeriod:
    def __init__(self, *, system: str, ruler: str, level: str) -> None:
        self.system = system
        self.ruler = ruler
        self.level = level


class _FakeStack:
    def __init__(self, periods: list[_FakePeriod], rulers: list[str], payload: dict) -> None:
        self._periods = periods
        self._rulers = rulers
        self._payload = payload

    def rulers(self) -> list[str]:
        return self._rulers

    def iter_periods(self):
        return iter(self._periods)

    def to_dict(self) -> dict:
        return self._payload


class _FakeCalculator:
    def __init__(self, stack: _FakeStack) -> None:
        self._stack = stack

    def active_stack(self, when):
        return self._stack

def test_attach_timelords_injects_matching_metadata(monkeypatch):
    event = LegacyTransitEvent(
        kind="aspect",
        timestamp="2000-01-01T00:00:00Z",
        moving="Mars",
        target="Mars",
        orb_abs=0.0,
        orb_allow=1.0,
        applying_or_separating="applying",
        score=0.0,
    )
    stack_payload = {"systems": ["vimshottari"], "levels": ["maha"]}
    period = _FakePeriod(system="vimshottari", ruler="Mars", level="maha")
    stack = _FakeStack(periods=[period], rulers=["Mars"], payload=stack_payload)
    calculator = _FakeCalculator(stack)

    with monkeypatch.context() as patcher:
        patcher.setattr(scanning, "FEATURE_TIMELORDS", True)
        _attach_timelords(event, calculator)

    assert event.metadata["timelord_rulers"] == ["Mars"]
    assert event.metadata["timelords"] == stack_payload
    matches = event.metadata.get("transit_over_dasha_lords")
    assert matches is not None and len(matches) == 2
    assert {entry["role"] for entry in matches} == {"moving", "target"}
    assert all(entry["ruler"] == "Mars" for entry in matches)
    assert all(entry["system"] == "vimshottari" for entry in matches)
