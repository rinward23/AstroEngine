"""Low level SVG scene graph utilities.

The helpers defined here provide a deterministic, vector-first building
block that higher level renderers can rely on.  The implementation
favours simple data structures so the export pipeline can serialise
scenes without pulling in heavyweight dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

SVG_NS = "http://www.w3.org/2000/svg"


@dataclass
class SvgElement:
    """A minimal SVG node.

    Attributes are stored as strings to avoid locale-dependent
    formatting.  Children are kept in insertion order to make the final
    SVG deterministic – a requirement for stable exports and regression
    tests.
    """

    tag: str
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List["SvgElement"] = field(default_factory=list)
    text: Optional[str] = None

    def set(self, **attrs: object) -> "SvgElement":
        """Assign attributes on the element and return ``self``.

        Values are converted to strings using ``repr`` for floats to
        preserve precision without triggering locale-specific
        formatting.
        """

        for key, value in attrs.items():
            if value is None:
                continue
            if isinstance(value, float):
                # ``repr`` keeps trailing precision without adding
                # unnecessary rounding noise.
                self.attributes[key] = repr(value)
            else:
                self.attributes[key] = str(value)
        return self

    def add(self, *children: "SvgElement") -> "SvgElement":
        self.children.extend(children)
        return self

    def to_string(self, indent: int = 0, pretty: bool = True) -> str:
        pad = "  " * indent if pretty else ""
        child_pad = "  " * (indent + 1) if pretty else ""
        parts: List[str] = []
        attrs = "".join(
            f" {name}={_quote(value)}" for name, value in sorted(self.attributes.items())
        )
        if not self.children and self.text is None:
            parts.append(f"{pad}<{self.tag}{attrs}/>")
            return "\n".join(parts)

        opening = f"{pad}<{self.tag}{attrs}>"
        parts.append(opening)
        if self.text is not None:
            text = self.text if not pretty else self.text.strip()
            parts.append(f"{child_pad}{_escape(text)}")
        for child in self.children:
            parts.append(child.to_string(indent + 1, pretty=pretty))
        parts.append(f"{pad}</{self.tag}>")
        return "\n".join(parts)


def _quote(value: str) -> str:
    return f'"{_escape(value)}"'


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


@dataclass
class SvgDocument:
    """Simple scene container that serialises to standalone SVG."""

    width: float
    height: float
    viewbox: Optional[Tuple[float, float, float, float]] = None
    background: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    root: SvgElement = field(init=False)

    def __post_init__(self) -> None:
        self.root = SvgElement(
            "svg",
            {
                "xmlns": SVG_NS,
                "width": str(self.width),
                "height": str(self.height),
            },
        )
        if self.viewbox is not None:
            self.root.set(viewBox=" ".join(repr(v) for v in self.viewbox))
        if self.background:
            self.root.add(
                SvgElement("rect", {
                    "fill": self.background,
                    "x": "0",
                    "y": "0",
                    "width": str(self.width),
                    "height": str(self.height),
                })
            )
        if self.metadata:
            self._install_metadata()

    def _install_metadata(self) -> None:
        if not self.metadata:
            return
        metadata_el = SvgElement("metadata")
        for key, value in sorted(self.metadata.items()):
            node = SvgElement("meta", {"key": key, "value": str(value)})
            metadata_el.add(node)
        # Metadata should be the first child according to SVG best
        # practices so it survives round-trips.
        self.root.children.insert(0, metadata_el)

    def set_metadata(self, **metadata: str) -> None:
        self.metadata.update(metadata)
        # Rebuild metadata node to keep ordering stable.
        self.root.children = [child for child in self.root.children if child.tag != "metadata"]
        self._install_metadata()

    # Element factories -------------------------------------------------
    def group(self, **attrs: object) -> SvgElement:
        return SvgElement("g").set(**attrs)

    def circle(self, cx: float, cy: float, r: float, **attrs: object) -> SvgElement:
        el = SvgElement("circle").set(cx=cx, cy=cy, r=r, **attrs)
        self.root.add(el)
        return el

    def line(self, x1: float, y1: float, x2: float, y2: float, **attrs: object) -> SvgElement:
        el = SvgElement("line").set(x1=x1, y1=y1, x2=x2, y2=y2, **attrs)
        self.root.add(el)
        return el

    def path(self, d: str, **attrs: object) -> SvgElement:
        el = SvgElement("path").set(d=d, **attrs)
        self.root.add(el)
        return el

    def text(
        self,
        x: float,
        y: float,
        value: str,
        **attrs: object,
    ) -> SvgElement:
        el = SvgElement("text", text=value).set(x=x, y=y, **attrs)
        self.root.add(el)
        return el

    def add(self, element: SvgElement) -> SvgElement:
        self.root.add(element)
        return element

    def extend(self, elements: Iterable[SvgElement]) -> None:
        for element in elements:
            self.add(element)

    def to_string(self, pretty: bool = True) -> str:
        return self.root.to_string(indent=0, pretty=pretty)

    def to_bytes(self, pretty: bool = True) -> bytes:
        return self.to_string(pretty=pretty).encode("utf-8")

    def viewbox_tuple(self) -> Tuple[float, float, float, float]:
        if self.viewbox is not None:
            return self.viewbox
        return (0.0, 0.0, self.width, self.height)
