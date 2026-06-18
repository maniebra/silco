from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from html import escape


@dataclass(frozen=True)
class Element:
    tag: str
    attributes: dict[str, object] = field(default_factory=dict)
    text: str | None = None
    children: tuple["Element", ...] = ()
    raw: bool = False

    def to_svg(self) -> str:
        attrs = _attributes(self.attributes)
        if self.raw and self.text is not None:
            return f"<{self.tag}{attrs}>{self.text}</{self.tag}>"
        if self.children:
            child_markup = "\n".join(child.to_svg() for child in self.children)
            return f"<{self.tag}{attrs}>\n{child_markup}\n</{self.tag}>"
        if self.text is not None:
            return f"<{self.tag}{attrs}>{escape(self.text)}</{self.tag}>"
        return f"<{self.tag}{attrs}/>"


@dataclass
class Canvas:
    """Small vector scene that can be serialized without a browser renderer."""

    width: float
    height: float
    attributes: dict[str, object] = field(default_factory=dict)
    styles: list[str] = field(default_factory=list)
    definitions: list[Element] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)

    def style(self, css: str) -> "Canvas":
        self.styles.append(css)
        return self

    def define(self, element: Element) -> "Canvas":
        self.definitions.append(element)
        return self

    def add(self, element: Element) -> "Canvas":
        self.elements.append(element)
        return self

    def rect(self, x: object, y: object, width: object, height: object, **attributes: object) -> Element:
        return self.add(Element("rect", {"x": x, "y": y, "width": width, "height": height, **attributes}))

    def text(self, value: str, x: object, y: object, **attributes: object) -> Element:
        return self.add(Element("text", {"x": x, "y": y, **attributes}, text=value))

    def path(self, d: str, **attributes: object) -> Element:
        return self.add(Element("path", {"d": d, **attributes}))

    def to_svg(self) -> str:
        attrs = {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": f"{self.width:.0f}",
            "height": f"{self.height:.0f}",
            "viewBox": f"0 0 {self.width:.0f} {self.height:.0f}",
            **self.attributes,
        }
        children: list[Element] = []
        if self.styles:
            children.append(Element("style", text="\n".join(self.styles), raw=True))
        if self.definitions:
            children.append(Element("defs", children=tuple(self.definitions)))
        children.extend(self.elements)
        return Element("svg", attrs, children=tuple(children)).to_svg()


def group(tag: str, attributes: dict[str, object] | None = None, children: Iterable[Element] = ()) -> Element:
    return Element(tag, attributes or {}, children=tuple(children))


def _attributes(attributes: dict[str, object]) -> str:
    rendered = []
    for name, value in attributes.items():
        if value is None:
            continue
        svg_name = name[:-1] if name.endswith("_") else name.replace("_", "-")
        rendered.append(f'{svg_name}="{escape(str(value), quote=True)}"')
    return f" {' '.join(rendered)}" if rendered else ""
