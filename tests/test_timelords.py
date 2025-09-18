from __future__ import annotations

from datetime import date
from pathlib import Path

from astroengine import AstroEngine


def test_zodiacal_releasing(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    result = engine.run(
        {
            "module": "timelords",
            "submodule": "timelords",
            "channel": "releasing",
            "subchannel": "lot_of_spirit",
            "data": {
                "start_sign": "Aries",
                "start_date": date(2000, 1, 1),
                "spans": 3,
            },
        }
    )
    releasing = result["zodiacal_releasing"]
    assert list(releasing["sign"]) == ["Aries", "Taurus", "Gemini"]
    assert releasing.iloc[0]["start"] == date(2000, 1, 1)
    assert releasing.iloc[0]["end"] > releasing.iloc[0]["start"]


def test_annual_profections(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    result = engine.run(
        {
            "module": "timelords",
            "submodule": "timelords",
            "channel": "profections",
            "subchannel": "annual",
            "data": {
                "ascendant_sign": "Cancer",
                "years": 5,
            },
        }
    )
    profections = result["profections"]
    assert list(profections["sign"])[:3] == ["Cancer", "Leo", "Virgo"]
    assert profections.iloc[5]["sign"] == "Sagittarius"
