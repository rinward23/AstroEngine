from __future__ import annotations

import importlib
import sys
import types


def test_ensure_sweph_alias(monkeypatch):
    fake_swisseph = types.ModuleType("swisseph")
    fake_swisseph.FLAG = 1
    monkeypatch.setitem(sys.modules, "swisseph", fake_swisseph)
    sys.modules.pop("sweph", None)

    bridge = importlib.import_module("astroengine.providers.sweph_bridge")
    bridge.ensure_sweph_alias()

    assert sys.modules["sweph"] is fake_swisseph
    assert sys.modules["sweph"].FLAG == 1

    sys.modules["sweph"].FLAG = 2
    bridge.ensure_sweph_alias()
    assert sys.modules["sweph"].FLAG == 2

    sys.modules.pop("swisseph", None)
    sys.modules.pop("sweph", None)
