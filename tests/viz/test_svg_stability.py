from astroengine.viz.core.svg import SvgDocument, SvgElement


def test_svg_serialisation_is_stable():
    doc = SvgDocument(width=200, height=200)
    group = doc.group(id="layer-1", transform="rotate(30 100 100)")
    group.add(
        SvgElement("circle").set(cx=100, cy=100, r=50, fill="none", stroke="#fff"),
        SvgElement("text", text="☉").set(x=100, y=100, fill="#fff"),
    )
    doc.add(group)

    first = doc.to_string(pretty=True)
    second = doc.to_string(pretty=True)
    assert first == second

    # Calling ``to_bytes`` should yield the same data encoded in UTF-8.
    assert doc.to_bytes(pretty=True) == first.encode("utf-8")
