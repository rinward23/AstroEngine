from __future__ import annotations

from pathlib import Path

from astroengine import AstroEngine, CompositeTransitPipeline


def test_composite_transit_pipeline(tmp_path: Path) -> None:
    engine = AstroEngine(Path("rulesets/vca_astroengine_master.yaml"), output_root=tmp_path)
    result = engine.run(
        {
            "module": "synastry_composite",
            "submodule": "synastry_composite",
            "channel": "composite_transits",
            "subchannel": "default",
            "data": {
                "natal_a": {"Sun": 15.0, "Moon": 120.0, "Ascendant": 90.0},
                "natal_b": {"Sun": 195.0, "Moon": 300.0, "Ascendant": 270.0},
                "transits": {"Jupiter": 105.0, "Saturn": 181.2},
            },
        }
    )
    pipeline = CompositeTransitPipeline(orb=2, tracked_points=["Sun", "Moon", "Ascendant"])
    frame = pipeline.to_frame(result)
    assert any(frame["composite_point"] == "Ascendant")
    assert frame.loc[frame["transit_body"] == "Saturn", "orb"].iloc[0] <= 1.2
