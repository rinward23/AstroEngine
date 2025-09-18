from __future__ import annotations

from pathlib import Path

from astroengine import AstroEngine


def test_primary_directions(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    result = engine.run(
        {
            "module": "directions_progressions",
            "submodule": "directions_progressions",
            "channel": "primary_directions",
            "subchannel": "default",
            "data": {
                "positions": {"Sun": 10.0, "Mars": 70.0},
                "pairs": [{"significator": "Sun", "promissor": "Mars"}],
            },
        }
    )
    frame = result["primary_directions"]
    assert frame.iloc[0]["aspect"] == "sextile"
    assert frame.iloc[0]["orb"] == 0


def test_secondary_progressions(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    result = engine.run(
        {
            "module": "directions_progressions",
            "submodule": "directions_progressions",
            "channel": "secondary_progressions",
            "subchannel": "solar_arc",
            "data": {
                "positions": {"Sun": 10.0, "Moon": 120.0},
                "years": [0, 1, 2],
            },
        }
    )
    frame = result["secondary_progressions"]
    moon_year_two = frame[(frame["body"] == "Moon") & (frame["year"] == 2)]
    assert moon_year_two.iloc[0]["degree"] == 122.0
