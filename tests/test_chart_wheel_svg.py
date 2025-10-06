from core.viz_plus.wheel_svg import WheelOptions, build_aspect_hits, render_chart_wheel

POLICY = {
    "per_object": {},
    "per_aspect": {
        "square": 6.0,
        "trine": 6.0,
        "conjunction": 8.0,
        "opposition": 7.0,
        "sextile": 4.0,
    },
    "adaptive_rules": {},
}


def test_svg_wheel_basic_and_labels():
    pos = {"Sun": 0.0, "Moon": 90.0, "Mars": 180.0}
    svg = render_chart_wheel(pos, options=WheelOptions(show_aspects=False))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "Sun" in svg and "Moon" in svg and "Mars" in svg
    # check sign tick for 0° label exists
    assert ">0°<" in svg
    assert "☀︎/☾ midpoint" in svg


def test_svg_houses_and_angles():
    pos = {"Sun": 10.0, "Moon": 190.0}
    houses = [i * 30.0 for i in range(12)]
    angles = {"asc": 100.0, "mc": 10.0}
    svg = render_chart_wheel(pos, houses=houses, angles=angles, options=WheelOptions(show_aspects=False))
    assert "ASC" in svg and "MC" in svg
    for numeral in ["I", "VI", "XII"]:
        assert numeral in svg


def test_aspect_detection_square():
    pos = {"Sun": 0.0, "Moon": 90.0}
    hits = build_aspect_hits(pos, aspects=["square", "trine", "sextile"], policy=POLICY)
    assert any(h["a"] == "Sun" and h["b"] == "Moon" and h["aspect"] == "square" for h in hits)


def test_svg_with_aspect_lines():
    pos = {"Sun": 0.0, "Moon": 90.0}
    svg = render_chart_wheel(pos, options=WheelOptions(show_aspects=True, aspects=["square"], policy=POLICY))
    # Should contain at least one line segment for an aspect
    assert "opacity='0.5'" in svg
