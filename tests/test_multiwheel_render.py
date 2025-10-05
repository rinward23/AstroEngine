from __future__ import annotations

import json
from pathlib import Path

from astroengine.config.settings import MultiWheelCfg, Settings, SynastryCfg
from astroengine.visual import (
    MultiWheelComposition,
    MultiWheelLayer,
    MultiWheelOptions,
    build_multiwheel_layout,
    export_multiwheel,
    render_multiwheel_png,
    render_multiwheel_svg,
)
from astroengine.cli.export import _parse_multiwheel_spec


def _demo_settings() -> Settings:
    return Settings(
        multiwheel=MultiWheelCfg(default_wheels=2, max_wheels=3),
        synastry=SynastryCfg(declination=True, declination_orb=1.5),
    )


def test_layout_builds_aspects(tmp_path: Path) -> None:
    layers = (
        MultiWheelLayer(
            label="Natal",
            bodies={"Sun": 0.0, "Mars": 120.0},
            houses=[float(i * 30.0) for i in range(12)],
            declinations={"Sun": 0.3, "Mars": -0.2},
        ),
        MultiWheelLayer(
            label="Transit",
            bodies={"Sun": 180.0, "Mars": 300.0},
            declinations={"Sun": 0.8, "Mars": -0.1},
        ),
    )
    composition = MultiWheelComposition(layers=layers, title="Biwheel", subtitle="Demo")
    options = MultiWheelOptions(wheel_count=2, show_declination_synastry=True)
    result = build_multiwheel_layout(composition, options, _demo_settings())
    assert len(result.layout) == 2
    assert any(link.aspect == "opposition" for link in result.aspects)
    assert any(pair.body_a == "Sun" for pair in result.declination_pairs)

    svg = render_multiwheel_svg(composition, options, _demo_settings())
    assert "Declination matches" in svg
    png = render_multiwheel_png(composition, options, _demo_settings())
    assert png.startswith(b"\x89PNG")

    svg_bytes = export_multiwheel(composition, options, _demo_settings(), fmt="svg")
    out_svg = tmp_path / "chart.svg"
    out_svg.write_bytes(svg_bytes)
    assert out_svg.read_bytes().startswith(b"<svg")


def test_parse_multiwheel_spec_roundtrip(tmp_path: Path) -> None:
    spec = {
        "title": "Synastry",
        "layers": [
            {
                "label": "A",
                "bodies": {"Sun": 0, "Moon": 45},
                "houses": [i * 30 for i in range(12)],
            },
            {
                "label": "B",
                "bodies": {"Sun": 180, "Moon": 225},
            },
        ],
        "options": {"wheel_count": 2, "show_aspects": False},
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    composition, options = _parse_multiwheel_spec(str(spec_path))
    assert composition.title == "Synastry"
    assert len(composition.layers) == 2
    assert options.wheel_count == 2
    assert options.show_aspects is False
