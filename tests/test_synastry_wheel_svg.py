from __future__ import annotations

from xml.etree import ElementTree as ET

from core.viz_plus.synastry_wheel_svg import (
    SynastryWheelOptions,
    render_synastry_wheel_svg,
)


def _parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def test_synastry_wheel_filters_and_layers() -> None:
    wheel_a = [("Sun", 0.0), ("Moon", 90.0)]
    wheel_b = [("Sun", 10.0), ("Moon", 180.0)]
    hits = [
        ("Sun", "Moon", 90, 0.9, -1.2),  # challenging major
        ("Moon", "Sun", 60, 0.2, 0.5),  # harmonious major
        ("Moon", "Moon", 30, 0.7, 0.1),  # neutral minor
    ]

    svg = render_synastry_wheel_svg(
        wheel_a,
        wheel_b,
        hits,
        SynastryWheelOptions(show_aspect_labels=False, label_top_k=0),
    )

    root = _parse(svg)
    lines = root.findall(".//{http://www.w3.org/2000/svg}line")
    # Expect zodiac ticks + 3 aspects + structure. Aspect lines include stroke-opacity attr.
    aspect_lines = [
        el
        for el in lines
        if el.attrib.get("stroke-opacity") is not None and "wheel-tick" not in el.attrib.get("stroke", "")
    ]
    assert len(aspect_lines) == 3

    # Verify severity scaling
    widths = sorted(float(el.attrib["stroke-width"]) for el in aspect_lines)
    assert widths[0] < widths[-1]


def test_synastry_wheel_topk_and_family_filter() -> None:
    wheel_a = [("Sun", 0.0)]
    wheel_b = [("Moon", 180.0), ("Venus", 60.0)]
    hits = [
        ("Sun", "Moon", 180, 0.8, 0.0),
        ("Sun", "Venus", 60, 0.5, 0.0),
    ]

    svg = render_synastry_wheel_svg(
        wheel_a,
        wheel_b,
        hits,
        SynastryWheelOptions(families=["harmonious"], top_k=1, show_aspect_labels=False),
    )

    root = _parse(svg)
    lines = [
        el
        for el in root.findall(".//{http://www.w3.org/2000/svg}line")
        if el.attrib.get("stroke-opacity")
    ]
    # Only harmonious aspect remains
    assert len(lines) == 1
    assert "stroke" in lines[0].attrib
