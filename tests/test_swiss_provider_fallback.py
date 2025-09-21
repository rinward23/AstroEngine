# >>> AUTO-GEN BEGIN: AE Swiss Provider Fallback Tests v1.0
import math

import pytest

from astroengine.providers import get_provider, list_providers


@pytest.mark.parametrize("when", [
    "2024-06-01T00:00:00Z",
    "2024-06-01T12:00:00Z",
])
def test_swiss_provider_available_and_returns_positions(when):
    assert "swiss" in list(list_providers()), "Swiss provider should be registered"
    prov = get_provider("swiss")
    data = prov.positions_ecliptic(when, ["sun", "moon", "mars", "invalid"])
    assert set(data) >= {"sun", "moon", "mars"}
    for body, coords in data.items():
        assert 0.0 <= coords["lon"] < 360.0
        assert -90.0 <= coords["decl"] <= 90.0
        assert math.isfinite(coords.get("speed_lon", 0.0))
# >>> AUTO-GEN END: AE Swiss Provider Fallback Tests v1.0
