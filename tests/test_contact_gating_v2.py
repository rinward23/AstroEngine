from __future__ import annotations

from pathlib import Path

import pandas as pd

from astroengine import AstroEngine


def test_contact_gating_v2(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    contacts = pd.DataFrame(
        [
            {
                "contact_id": "c1",
                "base_score": 10.0,
                "angular_distance": 5.0,
                "orb": 0.05,
                "aspect": "conjunction",
                "malefic_involved": False,
                "benefic_involved": False,
            },
            {
                "contact_id": "c2",
                "base_score": 8.0,
                "angular_distance": 15.0,
                "orb": 1.0,
                "aspect": "square",
                "malefic_involved": True,
                "benefic_involved": False,
            },
            {
                "contact_id": "c3",
                "base_score": 7.0,
                "angular_distance": 60.0,
                "orb": 1.2,
                "aspect": "trine",
                "malefic_involved": False,
                "benefic_involved": True,
            },
        ]
    )

    result = engine.run(
        {
            "module": "gating",
            "submodule": "contact_gating_v2",
            "channel": "natal_to_transit",
            "subchannel": "default",
            "data": {"contacts": contacts},
        }
    )

    assert result.summary["vetoed"] == 1
    assert result.summary["dampened"] == 1
    assert result.summary["boosted"] == 1

    output_path = tmp_path / "tables" / "contact_gate_states.parquet"
    assert output_path.exists()
    written = pd.read_parquet(output_path)
    assert list(written["state"]) == ["vetoed", "dampened", "boosted"]
    assert written.loc[written["contact_id"] == "c2", "final_score"].iloc[0] == 4.0
    assert written.loc[written["contact_id"] == "c3", "final_score"].iloc[0] == 8.75
