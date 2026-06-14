from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

from silco.core.models.edge import Edge
from silco.core.models.node import Node
from silco.core.renderers.base.graphics import Element
from silco.core.renderers.base.positioned_node import PositionedNode

_TEMPLATE_KINDS = {"actor", "component", "database", "queue", "cache", "storage", "external"}


def render_group_bounds(diagram, layout, y_offset: float, class_name: str = "silco-group") -> Iterable[Element]:
    for group_id, group in diagram.groups.items():
        members = [layout.nodes[node.id] for node in diagram.nodes.values() if node.group == group_id and node.id in layout.nodes]
        if not members:
            continue
        left = min(item.x for item in members) - 16
        top = min(item.y for item in members) + y_offset - 26
        right = max(item.x + item.width for item in members) + 16
        bottom = max(item.y + item.height for item in members) + y_offset + 16
        yield Element(
            "g",
            children=(
                Element("path", {"class": class_name, "d": group_path(left, top, right - left, bottom - top)}),
                Element("text", {"class": "silco-group-label", "x": left + 20, "y": top + 14}, text=group.display_label),
            ),
        )


def group_path(x: float, y: float, width: float, height: float) -> str:
    tab_width = 72
    tab_height = 22
    return (
        f"M {x:.1f} {y + tab_height:.1f} "
        f"L {x + 14:.1f} {y:.1f} "
        f"H {x + 14 + tab_width:.1f} "
        f"V {y + tab_height:.1f} "
        f"H {x + width:.1f} "
        f"V {y + height:.1f} "
        f"H {x:.1f} "
        f"Z"
    )


def curved_edge(edge: Edge, layout, y_offset: float, marker_end: str, marker_start: str | None = None) -> Element:
    source = layout.nodes[edge.source]
    target = layout.nodes[edge.target]
    start_x = source.x + source.width
    start_y = source.y + y_offset + source.height / 2
    end_x = target.x
    end_y = target.y + y_offset + target.height / 2
    if target.x < source.x:
        start_x = source.x
        end_x = target.x + target.width
    mid_x = (start_x + end_x) / 2
    children = [
        Element(
            "path",
            {
                "class": "silco-edge",
                "d": f"M {start_x:.1f} {start_y:.1f} C {mid_x:.1f} {start_y:.1f}, {mid_x:.1f} {end_y:.1f}, {end_x:.1f} {end_y:.1f}",
                "marker-end": marker_end,
                "marker-start": marker_start if edge.bidirectional else None,
            },
        )
    ]
    if edge.display_label:
        children.append(
            Element(
                "text",
                {"class": "silco-edge-label", "x": mid_x, "y": (start_y + end_y) / 2 - 8},
                text=edge.display_label,
            )
        )
    return Element("g", children=tuple(children))


def stereotype_text(node: Node, item: PositionedNode, y_offset: float, *, center: bool = False, title_case: bool = False) -> Element:
    label = node.kind.replace("_", " ").title() if title_case else f"<<{node.kind}>>"
    x = item.x + item.width / 2 if center else item.x + 12
    return Element("text", {"class": "silco-kind", "x": x, "y": item.y + y_offset + 15}, text=label)


def centered_label(node: Node, item: PositionedNode, y_offset: float, y_ratio: float = 0.58) -> Element:
    return Element(
        "text",
        {"class": "silco-label", "x": item.x + item.width / 2, "y": item.y + y_offset + item.height * y_ratio},
        text=node.display_label,
    )


def actor_text(node: Node, item: PositionedNode, y_offset: float) -> tuple[Element, Element]:
    return (
        Element(
            "text",
            {"class": "silco-kind", "x": item.x + item.width / 2 - 14, "y": item.y + y_offset + item.height * 0.22},
            text=node.kind.title(),
        ),
        Element(
            "text",
            {"class": "silco-label", "x": item.x + item.width / 2, "y": item.y + y_offset + item.height * 0.78},
            text=node.display_label,
        ),
    )


def template_shape(kind: str, x: float, y: float, width: float, height: float) -> Element | None:
    if kind not in _TEMPLATE_KINDS:
        return None
    root = _load_svg_root(kind)
    if root is None:
        return None
    template_width, template_height = _template_size(root)
    if template_width <= 0 or template_height <= 0:
        return None
    children = tuple(_convert_svg_node(child) for child in list(root))
    if not children:
        return None
    scale = min(width / template_width, height / template_height)
    offset_x = (width - template_width * scale) / 2
    offset_y = (height - template_height * scale) / 2
    content = Element(
        "g",
        {"transform": f"translate({offset_x:.4f} {offset_y:.4f}) scale({scale:.4f} {scale:.4f})"},
        children=children,
    )
    return Element("g", {"transform": f"translate({x:.1f} {y:.1f})"}, children=(content,))


@lru_cache(maxsize=32)
def _load_svg_root(kind: str) -> ET.Element | None:
    template_path = Path(__file__).resolve().parents[1] / "templates" / "shapes" / f"{kind}.svg"
    if not template_path.exists():
        return None
    try:
        return ET.parse(template_path).getroot()
    except ET.ParseError:
        return None


def _template_size(root: ET.Element) -> tuple[float, float]:
    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.split()
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass
    try:
        return float(root.get("width", "160")), float(root.get("height", "72"))
    except ValueError:
        return 160.0, 72.0


def _convert_svg_node(node: ET.Element) -> Element:
    children = tuple(_convert_svg_node(child) for child in list(node))
    text = node.text.strip() if node.text and node.text.strip() else None
    attributes = {_strip_namespace(name): value for name, value in node.attrib.items()}
    return Element(_strip_namespace(node.tag), attributes, text=text, children=children)


def _strip_namespace(value: str) -> str:
    if "}" in value:
        return value.split("}", 1)[1]
    return value


def render_mermaid(diagram) -> str:
    lines = [f"flowchart {diagram.direction}"]
    rendered_groups: set[str] = set()
    for group_id, group in diagram.groups.items():
        members = [node for node in diagram.nodes.values() if node.group == group_id]
        if not members:
            continue
        rendered_groups.add(group_id)
        lines.append(f'    subgraph {group_id}["{escape_mermaid(group.display_label)}"]')
        lines.extend(mermaid_node(node) for node in members)
        lines.append("    end")
    for node in diagram.nodes.values():
        if node.group not in rendered_groups:
            lines.append(mermaid_node(node))
    for relation in (*diagram.edges, *diagram.flows):
        label = f"|{escape_mermaid(relation.display_label)}|" if relation.display_label else ""
        arrow = "<-->" if relation.bidirectional else "-->"
        lines.append(f"    {relation.source} {arrow}{label} {relation.target}")
    return "\n".join(lines)


def mermaid_node(node: Node) -> str:
    label = escape_mermaid(node.display_label)
    if node.kind in {"database", "queue", "storage"}:
        return f'    {node.id}[("{label}")]'
    if node.kind == "actor":
        return f'    {node.id}(["{label}"])'
    if node.kind == "external":
        return f'    {node.id}{{"{label}"}}'
    return f'    {node.id}["{label}"]'


def escape_mermaid(value: str | None) -> str:
    return (value or "").replace('"', "'")
